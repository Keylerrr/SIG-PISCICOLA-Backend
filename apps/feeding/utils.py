from __future__ import annotations
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.cycle.models import Cycle, CyclePondBatch
from apps.purchases.models import InventoryMovement
from apps.purchases.utils import create_out_movement

from .models import FeedingEvent, FeedingPlan, FeedingSchedule


_MASS_GRAMS_PER_UNIT_SYMBOL = {
    "mg": Decimal("0.001"),
    "g": Decimal("1"),
    "gr": Decimal("1"),
    "kg": Decimal("1000"),
    "t": Decimal("1000000"),
    "ton": Decimal("1000000"),
}


def _mass_grams_per_unit_symbol(unit) -> Decimal | None:
    if unit is None:
        return None
    key = (getattr(unit, "symbol", None) or "").strip().lower()
    return _MASS_GRAMS_PER_UNIT_SYMBOL.get(key)


def quantity_in_product_unit(
    quantity: Decimal,
    from_unit,
    to_unit,
) -> Decimal:
    """
    Convierte una cantidad de masa desde ``from_unit`` hacia ``to_unit`` (unidad del producto).

    Si las unidades coinciden, devuelve ``quantity``. Si no, usa factores solo para
    símbolos de masa conocidos (mg, g, kg, t). Si no puede convertir, lanza ``ValueError``.
    """
    if from_unit is None or to_unit is None:
        raise ValueError(
            "Faltan unidades para alinear la cantidad consumida con el inventario del producto."
        )
    if from_unit.pk == to_unit.pk:
        return quantity
    g_from = _mass_grams_per_unit_symbol(from_unit)
    g_to = _mass_grams_per_unit_symbol(to_unit)
    if g_from is None or g_to is None:
        raise ValueError(
            "No se puede convertir entre la unidad indicada y la unidad del producto "
            f"({getattr(to_unit, 'symbol', '')}). Use la misma unidad que el producto o "
            "unidades de masa estándar (mg, g, kg, t)."
        )
    out = quantity * g_from / g_to
    return out.quantize(Decimal("0.0001"))


def active_plan_date_overlap(
    *,
    cycle_id: int,
    start_date,
    end_date,
    exclude_plan_ids: set | None = None,
) -> bool:
    qs = FeedingPlan.objects.filter(
        cycle_id=cycle_id,
        deleted_at__isnull=True,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_plan_ids:
        qs = qs.exclude(pk__in=exclude_plan_ids)
    return qs.exists()


def feeding_plan_lifecycle_state(plan: FeedingPlan, today=None):
    today = today or timezone.now().date()
    if plan.end_date < today:
        return "finished"
    if plan.start_date <= today <= plan.end_date:
        return "in_progress"
    return "scheduled"


def register_feeding_consume(feeding_event: FeedingEvent):
    try:
        fe = FeedingEvent.objects.select_related(
            "farm",
            "cycle",
            "cycle__pond",
            "actual_unit",
            "feeding_plan__feeding_schedule__product",
            "feeding_plan__feeding_schedule__product__unit",
        ).get(pk=feeding_event.pk)

        product = fe.feeding_plan.feeding_schedule.product
        qty_stock = quantity_in_product_unit(
            Decimal(str(feeding_event.actual_quantity)),
            feeding_event.actual_unit,
            product.unit,
        )
        return create_out_movement(
            farm=fe.farm,
            product=product,
            quantity=float(qty_stock),
            source_type=InventoryMovement.SourceType.FEEDING,
            source_id=fe.id,
            pond=fe.cycle.pond,
            cycle=fe.cycle,
        )
    except FeedingEvent.DoesNotExist:
        raise ValueError("El evento de alimentación no existe.") from None
    except ValueError:
        raise


def cycle_fish_count_and_avg_weight_g(cycle_id: int) -> tuple[Decimal, Decimal] | None:
    rows = list(
        CyclePondBatch.objects.filter(cycle_id=cycle_id).values_list(
            "quantity", "avg_weight_g"
        )
    )
    if not rows:
        return None
    total_fish = sum(int(q) for q, _ in rows)
    if total_fish <= 0:
        return None
    weighted = sum(Decimal(q) * Decimal(str(w)) for q, w in rows)
    avg_g = weighted / Decimal(total_fish)
    return Decimal(total_fish), avg_g


def planned_feed_quantity_per_ration(
    fish_count: Decimal,
    avg_weight_g: Decimal,
    feeding_rate_percentage: Decimal,
    times_per_day: int,
) -> Decimal:
    """
    Ración planificada por toma (misma unidad que la ración diaria: kg de alimento
    si ``peso_promedio`` está en gramos por pez, coherente con alimento en kg).

    Fórmula de negocio (peso promedio en g por pez):

    - Biomasa = (cantidad de peces × peso promedio) / 1000
    - Relación diaria = (Biomasa × feeding_rate) / 100
    - Ración por toma (quantity) = relación diaria / veces al día
    """
    if times_per_day < 1:
        return Decimal("0").quantize(Decimal("0.01"))
    biomasa = (fish_count * avg_weight_g) / Decimal("1000")
    relacion_diaria = (biomasa * feeding_rate_percentage) / Decimal("100")
    racion_por_toma = relacion_diaria / Decimal(times_per_day)
    return racion_por_toma.quantize(Decimal("0.01"))


def create_feeding_events_for_plan(plan: FeedingPlan) -> int:
    schedule = FeedingSchedule.objects.select_related("product").get(
        pk=plan.feeding_schedule_id
    )
    unit_id = schedule.product.unit_id

    stock = cycle_fish_count_and_avg_weight_g(plan.cycle_id)
    if stock is not None:
        fish_count, avg_g = stock
        planned_qty = planned_feed_quantity_per_ration(
            fish_count,
            avg_g,
            Decimal(str(schedule.feeding_rate_percentage)),
            schedule.times_per_day,
        )
    else:
        planned_qty = Decimal("0")

    day_stride = schedule.gap_between_completed_day + 1
    first_ration_time = time(0, 0)

    events: list[FeedingEvent] = []
    ration_number = 1
    day_index = 0
    current = plan.start_date

    while current <= plan.end_date:
        if day_index % day_stride == 0:
            base = datetime.combine(current, first_ration_time)
            for i in range(schedule.times_per_day):
                st = base + timedelta(minutes=i * schedule.gap_between_times_per_day)
                events.append(
                    FeedingEvent(
                        farm_id=plan.farm_id,
                        cycle_id=plan.cycle_id,
                        feeding_plan=plan,
                        date=st.date(),
                        scheduled_time=st.time(),
                        ration_number=ration_number,
                        planned_quantity=planned_qty,
                        planned_unit_id=unit_id,
                        status=FeedingEvent.Status.SCHEDULED,
                    )
                )
                ration_number += 1
        current += timedelta(days=1)
        day_index += 1

    if not events:
        return 0
    FeedingEvent.objects.bulk_create(events)
    return len(events)


def _last_completed_or_skipped_event(old_plan_id: int):
    return (
        FeedingEvent.objects.filter(
            feeding_plan_id=old_plan_id,
            status__in=(
                FeedingEvent.Status.COMPLETED,
                FeedingEvent.Status.SKIPPED,
            ),
        )
        .order_by("-date", "-scheduled_time", "-ration_number")
        .first()
    )


def update_in_progress_feeding_plan(
    *,
    farm_id: int,
    old_plan: FeedingPlan,
    cycle,
    feeding_schedule: FeedingSchedule,
    start_date,
    end_date,
) -> FeedingPlan:
    with transaction.atomic():
        locked_old = FeedingPlan.objects.select_for_update().get(pk=old_plan.pk)
        if locked_old.deleted_at is not None:
            raise ValueError(
                "El plan ya fue archivado. No se puede modificar de este modo."
            )
        if locked_old.farm_id != farm_id:
            raise ValueError("Inconsistencia de granja del plan.")

        last_ev = _last_completed_or_skipped_event(locked_old.pk)
        if last_ev is None:
            raise ValueError(
                "Para actualizar un plan en curso debe existir al menos un evento de "
                "alimentación marcado como completado u omitido. Mantenga los eventos del "
                "plan al día con la operación real (raciones ya ejecutadas o omitidas) y "
                "vuelva a intentar."
            )

        locked_old.end_date = last_ev.date
        locked_old.save(update_fields=["end_date"])

        FeedingEvent.objects.filter(
            feeding_plan_id=locked_old.pk,
            status=FeedingEvent.Status.SCHEDULED,
        ).filter(
            Q(date__gt=last_ev.date)
            | Q(date=last_ev.date, scheduled_time__gt=last_ev.scheduled_time)
            | Q(
                date=last_ev.date,
                scheduled_time=last_ev.scheduled_time,
                ration_number__gt=last_ev.ration_number,
            )
        ).delete()

        new_plan = _create_plan_with_events_locked(
            farm_id=farm_id,
            cycle=cycle,
            feeding_schedule=feeding_schedule,
            start_date=start_date,
            end_date=end_date,
            exclude_plan_ids={locked_old.pk},
        )
    return new_plan


def update_scheduled_feeding_plan(
    *,
    farm_id: int,
    plan: FeedingPlan,
    cycle,
    feeding_schedule: FeedingSchedule,
    start_date,
    end_date,
) -> FeedingPlan:
    with transaction.atomic():
        locked = FeedingPlan.objects.select_for_update().get(pk=plan.pk)
        today = timezone.now().date()
        if not (today < locked.start_date):
            raise ValueError("El plan no está programado (aún en curso o finalizado).")
        if locked.deleted_at is not None:
            raise ValueError("El plan ya fue archivado.")
        if locked.farm_id != farm_id:
            raise ValueError("Inconsistencia de granja del plan.")

        if active_plan_date_overlap(
            cycle_id=cycle.pk,
            start_date=start_date,
            end_date=end_date,
            exclude_plan_ids={locked.pk},
        ):
            raise ValueError(
                "Las fechas se solapan con otro plan vigente del mismo ciclo."
            )

        FeedingEvent.objects.filter(feeding_plan_id=locked.pk).delete()
        locked.cycle_id = cycle.pk
        locked.feeding_schedule_id = feeding_schedule.pk
        locked.start_date = start_date
        locked.end_date = end_date
        locked.save(
            update_fields=[
                "cycle_id",
                "feeding_schedule_id",
                "start_date",
                "end_date",
            ]
        )
        create_feeding_events_for_plan(locked)
    return locked


def _create_plan_with_events_locked(
    *,
    farm_id: int,
    cycle,
    feeding_schedule: FeedingSchedule,
    start_date,
    end_date,
    exclude_plan_ids: set | None = None,
) -> FeedingPlan:
    Cycle.objects.select_for_update().get(pk=cycle.pk)
    if active_plan_date_overlap(
        cycle_id=cycle.pk,
        start_date=start_date,
        end_date=end_date,
        exclude_plan_ids=exclude_plan_ids,
    ):
        raise ValueError(
            "Las fechas se solapan con otro plan vigente del mismo ciclo."
        )
    plan = FeedingPlan.objects.create(
        farm_id=farm_id,
        cycle=cycle,
        feeding_schedule=feeding_schedule,
        start_date=start_date,
        end_date=end_date,
    )
    create_feeding_events_for_plan(plan)
    return plan


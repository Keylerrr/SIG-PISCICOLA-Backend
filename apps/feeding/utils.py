from __future__ import annotations
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.cycle.models import Cycle

from .models import FeedingEvent, FeedingPlan, FeedingSchedule


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
    """``finished`` | ``in_progress`` | ``scheduled`` según la fecha actual (timezone)."""
    today = today or timezone.now().date()
    if plan.end_date < today:
        return "finished"
    if plan.start_date <= today <= plan.end_date:
        return "in_progress"
    return "scheduled"


def create_feeding_events_for_plan(plan: FeedingPlan) -> int:
    """Crea eventos ``SCHEDULED`` del plan según su ``FeedingSchedule``; devuelve cantidad creada."""
    schedule = FeedingSchedule.objects.select_related("product").get(
        pk=plan.feeding_schedule_id
    )
    unit_id = schedule.product.unit_id

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
                        planned_quantity=Decimal("0"),
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
    """Acorta el plan vigente al último evento ejecutado, elimina raciones futuras en BD, crea plan nuevo.

    Debe llamarse solo si el plan está en curso; ``farm_id`` debe coincidir con el plan bloqueado.
    """
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

        # Solo FeedingEvent admite DELETE físico (plan/cronograma: baja por deleted_at).
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
    """Elimina en BD los eventos del plan, actualiza el mismo registro y vuelve a generar eventos.

    Solo si hoy es anterior a ``start_date`` del plan bloqueado.
    """
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

        # Mismo criterio: solo eventos se borran en BD; el plan se actualiza abajo.
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
    """Crea fila ``FeedingPlan`` y sus eventos; bloquea el ciclo destino (misma transacción)."""
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

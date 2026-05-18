# utils.py

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from .models import Harvest, HarvestClassification


def _get_cycle(cycle_id):
    Cycle = apps.get_model("cycle", "Cycle")
    try:
        return Cycle.objects.select_related("farm").get(pk=cycle_id)
    except Cycle.DoesNotExist:
        return None


def _get_active_pond_batch(cycle):
    PondBatch = apps.get_model("batch", "PondBatch")
    return (
        PondBatch.objects.filter(
            pond=cycle.pond,
            end_date__isnull=True,
        )
        .select_for_update()
        .first()
    )


def _validate_harvest(cycle, harvest_type, total_fish_count):
    Cycle = apps.get_model("cycle", "Cycle")
    errors = {}

    blocked_states = [
        Cycle.State.FINISHED,
        Cycle.State.CANCELLED,
        Cycle.State.PAUSED,
    ]
    if cycle.state in blocked_states:
        errors["cycle"] = f"No se puede cosechar un ciclo en estado '{cycle.state}'."

    if harvest_type == Harvest.Type.TOTAL:
        already_total = Harvest.objects.filter(
            cycle=cycle,
            type=Harvest.Type.TOTAL,
        ).exists()
        if already_total:
            errors["type"] = "Ya existe una cosecha Total para este ciclo."

    return errors


def _get_available_quantity(cycle):
    pond_batch = _get_active_pond_batch(cycle)
    if not pond_batch:
        return 0
    return pond_batch.current_quantity


def _check_active_treatment(cycle):
    TreatmentPlan = apps.get_model("events", "TreatmentPlan")
    return TreatmentPlan.objects.filter(
        cycle=cycle,
        status=TreatmentPlan.Status.PROGRESS,
    ).exists()


def _cancel_scheduled_events(cycle):
    FeedingEvent = apps.get_model("feeding", "FeedingEvent")
    TreatmentEvent = apps.get_model("events", "TreatmentEvent")

    FeedingEvent.objects.filter(
        cycle=cycle,
        status=FeedingEvent.Status.SCHEDULED,
    ).delete()

    TreatmentEvent.objects.filter(
        treatment_plan__cycle=cycle,
        status=TreatmentEvent.Status.SCHEDULED,
    ).delete()


def _resolve_cycle_alerts(cycle):
    Alert = apps.get_model("core", "Alert")
    Alert.objects.filter(
        cycle=cycle,
        is_resolved=False,
    ).update(
        is_resolved=True,
        resolved_at=timezone.now(),
    )


def _close_cycle(cycle):
    Cycle = apps.get_model("cycle", "Cycle")
    cycle.state = Cycle.State.FINISHED
    cycle.finish_date = timezone.now().date()
    cycle.save(update_fields=["state", "finish_date"])


def _reduce_pond_batch_quantity(cycle, quantity):
    pond_batch = _get_active_pond_batch(cycle)
    if not pond_batch:
        raise ValueError("No existe un PondBatch activo para este ciclo.")

    if quantity > pond_batch.current_quantity:
        raise ValueError(
            f"La cantidad cosechada ({quantity}) excede la disponible "
            f"({pond_batch.current_quantity})."
        )

    pond_batch.current_quantity -= quantity
    pond_batch.save(update_fields=["current_quantity"])

    if pond_batch.current_quantity == 0:
        pond_batch.end_date = timezone.now().date()
        pond_batch.save(update_fields=["end_date"])

    return pond_batch


@transaction.atomic
def confirm_harvest(harvest: Harvest) -> None:
    cycle = harvest.cycle

    _reduce_pond_batch_quantity(cycle, harvest.total_fish_count)

    if harvest.type == Harvest.Type.TOTAL:
        _cancel_scheduled_events(cycle)
        _resolve_cycle_alerts(cycle)
        _close_cycle(cycle)


@transaction.atomic
def create_batch_from_classification(
    classification: HarvestClassification,
    specie_id: int,
    biological_state: str,
    min_weight_g: float,
    avg_weight_g: float,
    max_weight_g: float,
    pond_id: int,
    comments: str = "",
) -> object:
    Batch = apps.get_model("batch", "Batch")
    PondBatch = apps.get_model("batch", "PondBatch")
    BatchSource = apps.get_model("batch", "BatchSource")

    already_derived = Batch.objects.filter(
        origin_type=Batch.OriginType.HARVEST_CLASSIFICATION,
        origin_id=classification.id,
    ).exists()
    if already_derived:
        raise ValueError("Esta clasificación ya tiene un lote derivado.")

    farm = classification.farm
    timestamp = int(timezone.now().timestamp())
    code = f"BATCH-{farm.id}-{timestamp}"
    while Batch.objects.filter(code=code, farm=farm).exists():
        timestamp += 1
        code = f"BATCH-{farm.id}-{timestamp}"

    batch = Batch.objects.create(
        farm=farm,
        specie_id=specie_id,
        origin_type=Batch.OriginType.HARVEST_CLASSIFICATION,
        origin_id=classification.id,
        code=code,
        biological_state=biological_state,
        status=Batch.Status.ACTIVE,
        initial_quantity=classification.fish_count,
        min_weight_g=min_weight_g,
        avg_weight_g=avg_weight_g,
        max_weight_g=max_weight_g,
        comments=comments,
    )

    PondBatch.objects.create(
        pond_id=pond_id,
        batch=batch,
        initial_quantity=classification.fish_count,
        current_quantity=classification.fish_count,
        start_date=timezone.now().date(),
    )

    parent_batch = _get_parent_batch(classification)
    if parent_batch:
        BatchSource.objects.get_or_create(
            parent_batch=parent_batch,
            child_batch=batch,
            defaults={"quantity": classification.fish_count},
        )

    return batch


def _get_parent_batch(classification: HarvestClassification):
    PondBatch = apps.get_model("batch", "PondBatch")
    cycle = classification.harvest.cycle
    pond_batch = (
        PondBatch.objects.filter(
            pond=cycle.pond,
        )
        .order_by("-start_date")
        .first()
    )
    if not pond_batch:
        return None
    return pond_batch.batch


def get_cycle_weights(cycle) -> dict:
    ControlStat = apps.get_model("monitoring", "ControlStat")

    last_control = (
        ControlStat.objects.filter(
            cycle=cycle,
            deleted_at__isnull=True,
        )
        .order_by("-control_date")
        .first()
    )

    if not last_control:
        return {
            "min_weight_g": 0.0,
            "avg_weight_g": 0.0,
            "max_weight_g": 0.0,
        }

    return {
        "min_weight_g": last_control.min_weight_g,
        "avg_weight_g": last_control.avg_weight_g,
        "max_weight_g": last_control.max_weight_g,
    }

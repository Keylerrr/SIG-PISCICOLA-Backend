from apps.core.services.alerts import resolve_alerts
from django.apps import apps
from django.db import transaction
from django.utils import timezone


def _validate_cycle_finish_date(cycle, finish_date):
    if finish_date < cycle.start_date:
        raise ValueError(
            f"La fecha de fin ({finish_date}) no puede ser anterior al inicio del ciclo "
            f"({cycle.start_date})."
        )
    if finish_date > cycle.estimated_finish_date:
        raise ValueError(
            f"La fecha de fin ({finish_date}) no puede ser posterior a la fecha estimada "
            f"del ciclo ({cycle.estimated_finish_date})."
        )


def _get_cycle_ponds(cycle):
    CyclePondBatch = apps.get_model("cycle", "CyclePondBatch")
    ponds = set()
    for cpb in CyclePondBatch.objects.filter(cycle=cycle).select_related(
        "pond_batch__pond"
    ):
        ponds.add(cpb.pond_batch.pond)
    return ponds


def cleanup_scheduled_events(cycle):
    try:
        FeedingEvent = apps.get_model("feeding", "FeedingEvent")
    except LookupError:
        pass
    else:
        FeedingEvent.objects.filter(
            cycle=cycle,
            status=FeedingEvent.Status.SCHEDULED,
        ).delete()

    try:
        # A2: TreatmentEvent está en apps.health (no en events).
        TreatmentEvent = apps.get_model("health", "TreatmentEvent")
    except LookupError:
        pass
    else:
        TreatmentEvent.objects.filter(
            cycle=cycle,
            status=TreatmentEvent.Status.SCHEDULED,
        ).delete()


def _update_ponds_to_cleaning(cycle):
    ponds = _get_cycle_ponds(cycle)
    Pond = apps.get_model("ponds", "Pond")

    for pond in ponds:
        if pond.status == Pond.Status.IN_USE:
            pond.status = Pond.Status.CLEANING
            pond.save(update_fields=["status"])


@transaction.atomic
def finish_cycle(cycle, finish_date):
    _validate_cycle_finish_date(cycle, finish_date)

    cycle.state = cycle.State.FINISHED
    cycle.finish_date = finish_date
    cycle.save(update_fields=["state", "finish_date"])

    _update_ponds_to_cleaning(cycle)
    cleanup_scheduled_events(cycle)
    resolve_alerts(cycle=cycle)


@transaction.atomic
def cancel_cycle(cycle, finish_date=None, resolved_by=None):
    if finish_date is None:
        finish_date = timezone.now().date()

    if finish_date < cycle.start_date:
        raise ValueError(
            f"La fecha de fin ({finish_date}) no puede ser anterior al inicio del ciclo "
            f"({cycle.start_date})."
        )

    cycle.state = cycle.State.CANCELLED
    cycle.finish_date = finish_date
    cycle.save(update_fields=["state", "finish_date"])

    _update_ponds_to_cleaning(cycle)
    cleanup_scheduled_events(cycle)
    resolve_alerts(cycle=cycle, resolved_by=resolved_by)

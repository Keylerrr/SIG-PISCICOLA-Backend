from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.core.models import Alert
from apps.core.utils import create_alert, resolve_alert

from .models import TreatmentEvent


@receiver(
    post_save,
    sender=TreatmentEvent,
    dispatch_uid="treatment_event_alert_v1",
)
def treatment_event_alert(sender, instance: TreatmentEvent, created, **kwargs):
    today = timezone.now().date()
    if instance.status == TreatmentEvent.Status.SCHEDULED and instance.date <= today:
        create_alert(
            farm=instance.farm,
            pond=getattr(instance, "pond", None),
            cycle=instance.cycle,
            source_type=Alert.SourceType.HEALTH,
            source_id=instance.id,
            description=f"TreatmentEvent pendiente ({instance.id})",
            message=f"Evento de tratamiento programado para {instance.date} no cumplido.",
            severity=Alert.Severity.MEDIUM,
        )
    else:
        resolve_alert(source_type=Alert.SourceType.HEALTH, source_id=instance.id)

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.core.models import Alert
from apps.core.utils import create_alert, resolve_alert

from .models import FeedingEvent


@receiver(
    post_save,
    sender=FeedingEvent,
    dispatch_uid="feeding_event_alert_v1",
)
def feeding_event_alert(sender, instance: FeedingEvent, created, **kwargs):
    # If scheduled and date <= today, create an alert (frontend polls endpoint)
    today = timezone.now().date()
    if instance.status == FeedingEvent.Status.SCHEDULED and instance.date <= today:
        create_alert(
            farm=instance.farm,
            pond=None,
            cycle=instance.cycle,
            source_type=Alert.SourceType.FEEDING,
            source_id=instance.id,
            description=f"FeedingEvent pendiente ({instance.id})",
            message=f"Evento programado para {instance.date} no cumplido.",
            severity=Alert.Severity.MEDIUM,
        )
    else:
        # if status changed to non-scheduled, resolve any existing alert
        resolve_alert(source_type=Alert.SourceType.FEEDING, source_id=instance.id)

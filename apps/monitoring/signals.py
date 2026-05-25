from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.core.models import Alert
from apps.core.services.alerts import resolve_farm
from apps.core.utils import create_alert

from .models import FishEvaluated

THRESHOLDS = [5, 10, 15, 20, 25]


@receiver(
    post_save,
    sender=FishEvaluated,
    dispatch_uid="fish_evaluated_mortality_alert_v1",
)
def fish_evaluated_mortality_alert(sender, instance: FishEvaluated, created, **kwargs):
    # Only on create or when mortality_quantity changed.
    if instance.mortality_quantity <= 0 or instance.sampled_quantity <= 0:
        return

    farm = resolve_farm(farm=instance.farm, cycle=instance.cycle, pond=instance.pond)
    if farm is None:
        return

    mortality_pct = instance.mortality_quantity / instance.sampled_quantity * 100.0
    reached = None
    for t in THRESHOLDS:
        if mortality_pct >= t:
            reached = t

    # find existing unresolved health alerts for same farm/pond/cycle
    existing_qs = Alert.objects.filter(
        farm=farm,
        pond=instance.pond,
        cycle=instance.cycle,
        source_type=Alert.SourceType.HEALTH,
        is_resolved=False,
    )

    if reached is None:
        # no threshold reached; resolve existing alerts
        if existing_qs.exists():
            existing_qs.update(is_resolved=True, resolved_at=timezone.now())
        return

    # check highest existing threshold
    existing_high = existing_qs.order_by("-threshold").first()
    if existing_high and (existing_high.threshold or 0) >= reached:
        return

    # resolve older ones and create new
    if existing_qs.exists():
        existing_qs.update(is_resolved=True, resolved_at=timezone.now())

    create_alert(
        farm=farm,
        pond=instance.pond,
        cycle=instance.cycle,
        source_type=Alert.SourceType.HEALTH,
        source_id=instance.id,
        description=f"Mortalidad en estanque {instance.pond_id} ciclo {instance.cycle_id}",
        message=f"Mortalidad {mortality_pct:.2f}% >= {reached}%",
        value=float(mortality_pct),
        threshold=float(reached),
        severity=(Alert.Severity.HIGH if reached >= 15 else Alert.Severity.MEDIUM),
    )

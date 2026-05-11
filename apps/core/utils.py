from django.utils import timezone

from .models import Alert


def create_alert(
    *,
    farm,
    source_type: str,
    description: str,
    message: str,
    severity: str = Alert.Severity.MEDIUM,
    source_id: int | None = None,
    value: float | None = None,
    threshold: float | None = None,
    pond=None,
    cycle=None,
) -> Alert:
    existing = Alert.objects.filter(
        farm=farm,
        source_type=source_type,
        source_id=source_id,
        is_resolved=False,
    ).first()

    if existing:
        return existing

    return Alert.objects.create(
        farm=farm,
        pond=pond,
        cycle=cycle,
        source_type=source_type,
        source_id=source_id,
        description=description,
        message=message,
        value=value,
        threshold=threshold,
        severity=severity,
    )


def resolve_alert(*, source_type: str, source_id: int, resolved_by=None) -> None:
    Alert.objects.filter(
        source_type=source_type,
        source_id=source_id,
        is_resolved=False,
    ).update(
        is_resolved=True,
        resolved_at=timezone.now(),
        resolved_by=resolved_by,
    )

# utils.py

import uuid

from django.utils import timezone

from .models import Pond, UserFarmPond


def generate_pond_code() -> str:
    return f"PND-{uuid.uuid4().hex[:8].upper()}"


def get_pond_or_404(farm, pond_id) -> Pond:
    try:
        return Pond.objects.get(pk=pond_id, farm=farm, deleted_at__isnull=True)
    except Pond.DoesNotExist:
        return None


def soft_delete_pond(pond: Pond) -> None:
    from apps.cycle.models import CyclePondBatch

    has_cycles = CyclePondBatch.objects.filter(pond_batch__pond=pond).exists()

    if has_cycles:
        raise ValueError(
            "No se puede eliminar el estanque porque tiene ciclos asociados. "
        )

    pond.deleted_at = timezone.now()
    pond.save(update_fields=["deleted_at"])


def get_pond_members(pond: Pond):
    return UserFarmPond.objects.filter(pond=pond).select_related("user")


def remove_pond_member(farm, pond: Pond, user_id: int) -> bool:
    deleted, _ = UserFarmPond.objects.filter(
        pond=pond,
        farm=farm,
        user_id=user_id,
    ).delete()
    return deleted > 0

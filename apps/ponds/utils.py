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
    """
    Soft delete a pond (marca como eliminado).
    Verifica que no haya ciclos activos asociados.
    """
    from apps.cycle.models import CyclePondBatch, Cycle
    
    # Verificar si hay ciclos activos asociados al estanque
    active_cycles = CyclePondBatch.objects.filter(
        pond_batch__pond=pond,
        cycle__state=Cycle.State.IN_PROGRESS
    ).exists()
    
    if active_cycles:
        raise ValueError(
            "No se puede eliminar un estanque que tiene ciclos activos asociados. "
            "Finaliza los ciclos primero."
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

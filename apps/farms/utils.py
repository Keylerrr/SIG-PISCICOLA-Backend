# utils.py
from .enums import FarmPermission
from .models import FarmRole, UserFarm

OPERARIO_FORBIDDEN = {
    FarmPermission.DELETE,
    FarmPermission.MANAGE_USERS,
    FarmPermission.MANAGE_ROLES,
}


def user_has_farm_permission(user, farm_id: int, permission: FarmPermission) -> bool:
    if user.role.name == "Admin":
        return True

    try:
        uf = UserFarm.objects.get(
            user=user,
            farm_id=farm_id,
            farm__deleted_at__isnull=True,
        )
    except UserFarm.DoesNotExist:
        return False

    if uf.is_owner:
        return True

    return bool(uf.permissions & permission)


def get_effective_permissions(user_farm: UserFarm) -> int:
    if user_farm.is_owner:
        return int(FarmPermission.ALL)
    return user_farm.permissions


def assign_operario_permissions(user_farm: UserFarm, permissions: list[str]) -> None:
    """Asigna permisos a un Operario validando que no tenga permisos prohibidos."""
    result = 0
    for name in permissions:
        try:
            perm = FarmPermission[name]
        except KeyError:
            raise ValueError(f"Permiso inválido: '{name}'.")
        if perm in OPERARIO_FORBIDDEN:
            raise ValueError(f"No se puede asignar el permiso '{name}' a un Operario.")
        result |= perm
    user_farm.permissions = int(result)
    user_farm.save(update_fields=["permissions"])


def assign_role_to_operario(user_farm: UserFarm, role: FarmRole) -> None:
    """
    Asigna un FarmRole a un Operario y copia sus permisos,
    filtrando los que están prohibidos para ese rol.
    """
    if role.farm_id != user_farm.farm_id:
        raise ValueError("El rol no pertenece a esta finca.")

    allowed = int(role.permissions)
    for forbidden in OPERARIO_FORBIDDEN:
        allowed &= ~int(forbidden)  # limpiar cada bit prohibido

    user_farm.farm_role = role
    user_farm.permissions = allowed
    user_farm.save(update_fields=["farm_role", "permissions"])

# permissions.py
from rest_framework.permissions import BasePermission

from .enums import FarmPermission
from .models import UserFarm


def _get_user_farm(user, farm_pk) -> UserFarm | None:
    try:
        return UserFarm.objects.select_related("farm").get(
            user=user,
            farm_id=farm_pk,
            farm__deleted_at__isnull=True,
        )
    except UserFarm.DoesNotExist:
        return None


class IsFarmOwner(BasePermission):
    def has_permission(self, request, view):
        farm_pk = view.kwargs.get("farm_pk") or view.kwargs.get("pk")
        if not farm_pk:
            return True
        uf = _get_user_farm(request.user, farm_pk)
        return bool(uf and uf.is_owner)


class HasFarmPermission(BasePermission):
    required_permission: FarmPermission = FarmPermission.VIEW

    def has_permission(self, request, view):
        farm_pk = view.kwargs.get("farm_pk") or view.kwargs.get("pk")
        if not farm_pk:
            return True

        if request.user.role.name == "Admin":
            return True

        uf = _get_user_farm(request.user, farm_pk)
        if uf is None:
            return False

        if uf.is_owner:
            return True

        return bool(uf.permissions & self.required_permission)


def make_farm_permission(perm: FarmPermission) -> type:
    return type(
        f"Has{perm.name.title()}Permission",
        (HasFarmPermission,),
        {"required_permission": perm},
    )


CanViewFarm = make_farm_permission(FarmPermission.VIEW)
CanEditFarm = make_farm_permission(FarmPermission.EDIT)
CanDeleteFarm = make_farm_permission(FarmPermission.DELETE)
CanManageUsers = make_farm_permission(FarmPermission.MANAGE_USERS)
CanManageRoles = make_farm_permission(FarmPermission.MANAGE_ROLES)

# permissions.py
from rest_framework.permissions import BasePermission

ROLE_ADMIN = "Admin"
ROLE_PRODUCTOR = "Productor"
ROLE_OPERARIO = "Operario"

ALLOWED_PATH_PREFIXES = (
    "/api/users/me/complete/",
    "/api/auth/logout/",
    "/api/invitations/",
)


class RolePermission(BasePermission):
    role_name = None

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role.name == self.role_name
        )


class CompletionPermission(BasePermission):
    message = "Debes completar tu perfil antes de continuar."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if any(request.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
            return True

        if user.is_temp_password:
            return request.path.startswith("/api/auth/change-password/")

        if not user.is_profile_complete:
            return False

        return True


class IsAdmin(RolePermission):
    role_name = ROLE_ADMIN


class IsProductor(RolePermission):
    role_name = ROLE_PRODUCTOR


class IsOperario(RolePermission):
    role_name = ROLE_OPERARIO


def AdminOr(permission_class):
    class _Permission(BasePermission):
        def has_permission(self, request, view):
            return IsAdmin().has_permission(request, view) or (
                CompletionPermission().has_permission(request, view)
                and permission_class().has_permission(request, view)
            )

    return _Permission


class IsAdminOrValid(BasePermission):
    def has_permission(self, request, view):
        return IsAdmin().has_permission(
            request, view
        ) or CompletionPermission().has_permission(request, view)

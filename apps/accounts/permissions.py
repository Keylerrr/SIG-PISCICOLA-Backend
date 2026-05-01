# permissions.py
from rest_framework.permissions import BasePermission


class CompletionPermission(BasePermission):
    message = "Debes completar tu perfil antes de continuar."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        allowed_paths = [
            "/api/users/me/complete/",
            "/api/auth/logout/",
        ]

        if request.path in allowed_paths:
            return True

        if user.is_temp_password:
            return request.path.startswith("/api/auth/change-password/")

        if not user.is_profile_complete:
            return False

        return True


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.name == "Admin"


class IsProductor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.name == "Productor"


class IsOperario(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.name == "Operario"


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

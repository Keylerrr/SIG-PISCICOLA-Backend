from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        payload = getattr(request, "user_payload", None)
        return bool(payload and payload.get("role") == "admin")


class IsManager(BasePermission):
    def has_permission(self, request, view):
        payload = getattr(request, "user_payload", None)
        return bool(payload and payload.get("role") == "manager")


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        payload = getattr(request, "user_payload", None)
        return bool(payload and payload.get("role") in ("admin", "manager"))


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, "user_payload", None))

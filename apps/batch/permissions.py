from rest_framework.permissions import BasePermission

from apps.accounts.permissions import CompletionPermission, IsAdmin
from apps.farms.permissions import IsFarmMember


class BatchPermission(BasePermission):
    """Lectura de batches - acceso para miembros de la granja"""
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return IsFarmMember().has_permission(request, view)
        return CanManageBatch().has_permission(request, view)


class CanManageBatch(BasePermission):
    """Gestión de batches - solo admin o productor"""
    def has_permission(self, request, view):
        is_admin = IsAdmin().has_permission(request, view)
        is_productor = CompletionPermission().has_permission(
            request, view
        ) and IsFarmMember().has_permission(request, view)
        return is_admin or is_productor

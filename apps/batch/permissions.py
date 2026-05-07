from rest_framework.permissions import BasePermission

from apps.accounts.permissions import CompletionPermission, IsAdmin
from apps.farms.permissions import IsFarmMember


class CanManageBatch(BasePermission):
    """Gestión de batches - solo admin o productor"""
    def has_permission(self, request, view):
        is_admin = IsAdmin().has_permission(request, view)
        is_productor = CompletionPermission().has_permission(
            request, view
        ) and IsFarmMember().has_permission(request, view)
        return is_admin or is_productor

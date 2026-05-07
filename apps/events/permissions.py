from rest_framework.permissions import BasePermission

from apps.farms.permissions import IsFarmMember


class EventPermission(BasePermission):
    def has_permission(self, request, view):
        return IsFarmMember().has_permission(request, view)

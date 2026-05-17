from rest_framework.permissions import BasePermission

from apps.farms.permissions import HasFarmPermission
from apps.farms.enums import FarmPermission


class CanManageMonitoring(HasFarmPermission):
    """
    Permission to manage monitoring data (fish evaluations, daily stats, control stats).
    Requires MANAGE_REVIEWS permission on the farm.
    """
    required_permission = FarmPermission.MANAGE_REVIEWS


__all__ = ["CanManageMonitoring"]

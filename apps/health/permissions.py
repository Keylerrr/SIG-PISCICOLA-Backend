from apps.farms.permissions import make_farm_permission
from apps.farms.models import FarmPermission

CanManageReviews = make_farm_permission(FarmPermission.MANAGE_REVIEWS)

__all__ = ["CanManageReviews"]

from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import ProductionPlanViewSet, CycleViewSet, CyclePondBatchViewSet

router = DefaultRouter()

urlpatterns = [
    path(
        "farms/<int:farm_pk>/production-plans/",
        ProductionPlanViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="production-plan-list",
    ),
    path(
        "farms/<int:farm_pk>/production-plans/<int:pk>/",
        ProductionPlanViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="production-plan-detail",
    ),
    path(
        "farms/<int:farm_pk>/ponds/<int:pond_pk>/cycles/",
        CycleViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="pond-cycle-list",
    ),
    path(
        "farms/<int:farm_pk>/ponds/<int:pond_pk>/cycles/<int:pk>/",
        CycleViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="pond-cycle-detail",
    ),
    path(
        "farms/<int:farm_pk>/ponds/<int:pond_pk>/cycles/<int:cycle_pk>/cycle-batches/",
        CyclePondBatchViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="pond-cycle-batch-list",
    ),
    path(
        "farms/<int:farm_pk>/ponds/<int:pond_pk>/cycles/<int:cycle_pk>/cycle-batches/<int:pk>/",
        CyclePondBatchViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="pond-cycle-batch-detail",
    ),
]

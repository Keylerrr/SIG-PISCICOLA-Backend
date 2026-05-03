from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import ProductionPlanViewSet, CycleViewSet, CycleBatchViewSet

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
        "farms/<int:farm_pk>/cycles/",
        CycleViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="cycle-list",
    ),
    path(
        "farms/<int:farm_pk>/cycles/<int:pk>/",
        CycleViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="cycle-detail",
    ),
    path(
        "farms/<int:farm_pk>/cycle-batches/",
        CycleBatchViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="cycle-batch-list",
    ),
    path(
        "farms/<int:farm_pk>/cycle-batches/<int:pk>/",
        CycleBatchViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="cycle-batch-detail",
    ),
]

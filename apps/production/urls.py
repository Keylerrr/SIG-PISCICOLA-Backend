from rest_framework.routers import DefaultRouter
from django.urls import path, include

from apps.batch.views import (
    BatchViewSet,
    PondBatchViewSet,
    BatchTransferViewSet,
)
from apps.cycle.views import (
    ProductionPlanViewSet,
    CycleViewSet,
    CycleBatchViewSet,
)
from apps.events.views import GradingEventViewSet

router = DefaultRouter()

urlpatterns = [
    path(
        "farms/<int:farm_pk>/batches/",
        BatchViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="batch-list",
    ),
    path(
        "farms/<int:farm_pk>/batches/<int:pk>/",
        BatchViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
            }
        ),
        name="batch-detail",
    ),
    path(
        "farms/<int:farm_pk>/batches/<int:pk>/set-status/",
        BatchViewSet.as_view({"patch": "set_status"}),
        name="batch-set-status",
    ),
    path(
        "farms/<int:farm_pk>/pond-batches/",
        PondBatchViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="pond-batch-list",
    ),
    path(
        "farms/<int:farm_pk>/pond-batches/<int:pk>/",
        PondBatchViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
            }
        ),
        name="pond-batch-detail",
    ),
    path(
        "farms/<int:farm_pk>/batch-transfers/",
        BatchTransferViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="batch-transfer-list",
    ),
    path(
        "farms/<int:farm_pk>/batch-transfers/<int:pk>/",
        BatchTransferViewSet.as_view({"get": "retrieve"}),
        name="batch-transfer-detail",
    ),
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
    path(
        "farms/<int:farm_pk>/grading-events/",
        GradingEventViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="grading-event-list",
    ),
    path(
        "farms/<int:farm_pk>/grading-events/<int:pk>/",
        GradingEventViewSet.as_view({"get": "retrieve"}),
        name="grading-event-detail",
    ),
]

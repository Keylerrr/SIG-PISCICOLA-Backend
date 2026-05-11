from django.db.models import Exists, OuterRef
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.permissions import AdminOr
from apps.farms.permissions import IsFarmMember
from .models import Batch, BatchTransfer, PondBatch
from .permissions import CanManageBatch
from .serializers import (
    BatchSerializer,
    BatchTransferSerializer,
    PondBatchSerializer,
)


class BatchViewSet(viewsets.ModelViewSet):
    serializer_class = BatchSerializer

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH"):
            return [AdminOr(CanManageBatch)()]
        return [AdminOr(IsFarmMember)()]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        qs = Batch.objects.filter(farm_id=farm_id)

        pond_param = self.request.query_params.get("pond")
        if pond_param is not None:
            try:
                pond_id = int(pond_param)
            except (TypeError, ValueError):
                raise ValidationError(
                    {"pond": "Debe ser un id entero válido."},
                )
            pond_batches = PondBatch.objects.filter(
                batch_id=OuterRef("pk"),
                pond_id=pond_id,
                pond__farm_id=farm_id,
            )
            activos = self.request.query_params.get("activos")
            if activos is not None and str(activos).lower() in (
                "true",
                "1",
                "yes",
            ):
                pond_batches = pond_batches.filter(end_date__isnull=True)
            qs = qs.filter(Exists(pond_batches))

        sin_estanque = self.request.query_params.get("sin_estanque")
        if sin_estanque is not None and str(sin_estanque).lower() in (
            "true",
            "1",
            "yes",
        ):
            qs = qs.filter(
                ~Exists(PondBatch.objects.filter(batch_id=OuterRef("pk")))
            )
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        farm_id = self.kwargs.get("farm_pk")
        serializer.save(farm_id=farm_id)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Use PATCH to update status instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["patch"])
    def set_status(self, request, pk=None):
        batch = self.get_object()
        new_status = request.data.get("status")

        if new_status not in [choice[0] for choice in Batch.Status.choices]:
            return Response(
                {"detail": "Invalid status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch.status = new_status
        batch.save(update_fields=["status"])
        return Response(BatchSerializer(batch).data)


class PondBatchViewSet(viewsets.ModelViewSet):
    serializer_class = PondBatchSerializer

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH"):
            return [AdminOr(CanManageBatch)()]
        return [AdminOr(IsFarmMember)()]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        qs = PondBatch.objects.filter(batch__farm_id=farm_id).select_related(
            "pond", "batch"
        )

        pond_param = self.request.query_params.get("pond")
        if pond_param is not None:
            try:
                pond_id = int(pond_param)
            except (TypeError, ValueError):
                raise ValidationError(
                    {"pond": "Debe ser un id entero válido."},
                )
            qs = qs.filter(pond_id=pond_id, pond__farm_id=farm_id)

        batch_param = self.request.query_params.get("batch")
        if batch_param is not None:
            try:
                batch_id = int(batch_param)
            except (TypeError, ValueError):
                raise ValidationError(
                    {"batch": "Debe ser un id entero válido."},
                )
            qs = qs.filter(batch_id=batch_id)

        activos = self.request.query_params.get("activos")
        if activos is not None and str(activos).lower() in (
            "true",
            "1",
            "yes",
        ):
            qs = qs.filter(end_date__isnull=True)

        return qs.order_by("-start_date")

    def perform_create(self, serializer):
        serializer.save()


class BatchTransferViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.request.method in ("POST", "PATCH"):
            return [AdminOr(CanManageBatch)()]
        return [AdminOr(IsFarmMember)()]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        return BatchTransfer.objects.filter(farm_id=farm_id).select_related(
            "source_pond_batch", "to_pond_batch"
        ).order_by("-date")

    def create(self, request, farm_id=None):
        serializer = BatchTransferSerializer(
            data=request.data,
            context={"request": request, "farm_id": farm_id},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(farm_id=farm_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, farm_id=None):
        queryset = self.get_queryset()
        serializer = BatchTransferSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, farm_id=None):
        transfer = self.get_queryset().get(pk=pk)
        serializer = BatchTransferSerializer(transfer)
        return Response(serializer.data)

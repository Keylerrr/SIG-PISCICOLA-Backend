from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Batch, BatchTransfer, PondBatch
from ..serializers import (
    BatchSerializer,
    BatchTransferSerializer,
    PondBatchSerializer,
)


class BatchViewSet(viewsets.ModelViewSet):
    serializer_class = BatchSerializer

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        return Batch.objects.filter(farm_id=farm_id).order_by("-created_at")

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

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        return PondBatch.objects.filter(batch__farm_id=farm_id).select_related(
            "pond", "batch"
        ).order_by("-start_date")

    def perform_create(self, serializer):
        serializer.save()


class BatchTransferViewSet(viewsets.ViewSet):
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

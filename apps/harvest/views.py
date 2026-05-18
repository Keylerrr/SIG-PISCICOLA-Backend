# views.py

from apps.accounts.permissions import AdminOr
from apps.farms.permissions import CanManageCycle, IsFarmMember
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Harvest, HarvestClassification
from .serializers import (BatchFromClassificationSerializer,
                          HarvestClassificationSerializer, HarvestSerializer)
from .utils import create_batch_from_classification


class HarvestListCreateView(generics.ListCreateAPIView):
    serializer_class = HarvestSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageCycle)()]

    def get_queryset(self):
        qs = (
            Harvest.objects.filter(
                farm_id=self.kwargs["farm_pk"],
            )
            .prefetch_related("classifications")
            .order_by("-date")
        )

        cycle_id = self.request.query_params.get("cycle_id")
        harvest_type = self.request.query_params.get("type")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if cycle_id:
            qs = qs.filter(cycle_id=cycle_id)
        if harvest_type:
            qs = qs.filter(type=harvest_type)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs

    def perform_create(self, serializer):
        serializer.save(
            farm_id=self.kwargs["farm_pk"],
            created_by=self.request.user,
        )


class HarvestDetailView(generics.RetrieveAPIView):
    serializer_class = HarvestSerializer
    permission_classes = [AdminOr(IsFarmMember)]

    def get_queryset(self):
        return Harvest.objects.filter(
            farm_id=self.kwargs["farm_pk"],
        ).prefetch_related("classifications")


class HarvestClassificationListView(generics.ListAPIView):
    serializer_class = HarvestClassificationSerializer
    permission_classes = [AdminOr(IsFarmMember)]

    def get_queryset(self):
        return HarvestClassification.objects.filter(
            farm_id=self.kwargs["farm_pk"],
            harvest_id=self.kwargs["harvest_pk"],
        )


class BatchFromClassificationView(APIView):
    permission_classes = [AdminOr(CanManageCycle)]

    def post(self, request, farm_pk, harvest_pk, classification_pk):
        try:
            classification = HarvestClassification.objects.get(
                pk=classification_pk,
                harvest_id=harvest_pk,
                farm_id=farm_pk,
            )
        except HarvestClassification.DoesNotExist:
            return Response(
                {"detail": "Clasificación no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BatchFromClassificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            batch = create_batch_from_classification(
                classification=classification,
                **serializer.validated_data,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"detail": "Lote creado correctamente.", "batch_id": batch.id},
            status=status.HTTP_201_CREATED,
        )

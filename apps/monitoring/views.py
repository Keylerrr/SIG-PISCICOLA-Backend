from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from apps.accounts.permissions import AdminOr
from apps.farms.permissions import IsFarmMember
from .models import FishEvaluated, DailyStat, ControlStat
from .permissions import CanManageMonitoring
from .serializers import (
    FishEvaluatedSerializer,
    DailyStatSerializer,
    ControlStatSerializer,
)


class FishEvaluatedViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar evaluaciones de peces.

    Permisos:
    - GET: IsFarmMember
    - POST/PATCH/DELETE: AdminOr(CanManageMonitoring)
    """
    serializer_class = FishEvaluatedSerializer

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH", "DELETE"):
            return [AdminOr(CanManageMonitoring)()]
        return [AdminOr(IsFarmMember)()]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        pond_pk = self.kwargs.get("pond_pk")
        cycle_id = self.kwargs.get("cycle_pk")
        
        if not pond_pk or not cycle_id:
            raise ValidationError(
                "Debe especificar estanque (pond_pk) y ciclo (cycle_pk). "
                "Use: /farms/<farm_pk>/ponds/<pond_pk>/cycles/<cycle_pk>/fish-evaluations/"
            )

        qs = FishEvaluated.objects.filter(
            cycle__farm_id=farm_id,
            cycle__pond_id=pond_pk,
            cycle_id=cycle_id,
            deleted_at__isnull=True,
        ).select_related("cycle", "pond")

        return qs.order_by("-evaluation_date")

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.deleted_at = timezone.now()
        obj.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class DailyStatViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar estadísticas diarias.

    Permisos:
    - GET: IsFarmMember
    - POST/PATCH/DELETE: AdminOr(CanManageMonitoring)
    """
    serializer_class = DailyStatSerializer

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH", "DELETE"):
            return [AdminOr(CanManageMonitoring)()]
        return [AdminOr(IsFarmMember)()]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        pond_pk = self.kwargs.get("pond_pk")
        cycle_id = self.kwargs.get("cycle_pk")
        
        qs = DailyStat.objects.filter(
            cycle__farm_id=farm_id,
            deleted_at__isnull=True,
        ).select_related("cycle", "pond").prefetch_related("product_usages")

        # Si viene cycle_pk en URL, validar pond_pk también
        if cycle_id:
            if not pond_pk:
                raise ValidationError(
                    "Debe especificar estanque (pond_pk). "
                    "Use: /farms/<farm_pk>/ponds/<pond_pk>/cycles/<cycle_pk>/daily-stats/"
                )
            qs = qs.filter(cycle_id=cycle_id, cycle__pond_id=pond_pk)
        # Si no viene cycle_pk, es lista por granja (sin validación de pond)

        return qs.order_by("-stat_date", "-created_at")

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.deleted_at = timezone.now()
        obj.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ControlStatViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar estadísticas de control.

    Los campos de estadísticas se calculan automáticamente a partir de FishEvaluated.

    Permisos:
    - GET: IsFarmMember
    - POST/PATCH/DELETE: AdminOr(CanManageMonitoring)
    """
    serializer_class = ControlStatSerializer

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH", "DELETE"):
            return [AdminOr(CanManageMonitoring)()]
        return [AdminOr(IsFarmMember)()]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        pond_pk = self.kwargs.get("pond_pk")
        cycle_id = self.kwargs.get("cycle_pk")

        qs = ControlStat.objects.filter(
            cycle__farm_id=farm_id,
            deleted_at__isnull=True,
        ).select_related("cycle", "pond")

        # Si viene cycle_pk en URL, validar pond_pk también
        if cycle_id:
            if not pond_pk:
                raise ValidationError(
                    "Debe especificar estanque (pond_pk). "
                    "Use: /farms/<farm_pk>/ponds/<pond_pk>/cycles/<cycle_pk>/control-stats/"
                )
            qs = qs.filter(cycle_id=cycle_id, cycle__pond_id=pond_pk)
        # Si no viene cycle_pk, es lista por granja (sin validación de pond)

        return qs.order_by("-control_date")

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.deleted_at = timezone.now()
        obj.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


__all__ = [
    "FishEvaluatedViewSet",
    "DailyStatViewSet",
    "ControlStatViewSet",
]

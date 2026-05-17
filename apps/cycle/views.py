from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.accounts.permissions import AdminOr
from apps.farms.permissions import IsFarmMember, CanManageCycle
from .models import Cycle, CyclePondBatch, ProductionPlan
from .serializers import (
    CyclePondBatchSerializer,
    CycleSerializer,
    ProductionPlanSerializer,
)


class ProductionPlanViewSet(viewsets.ModelViewSet):
    serializer_class = ProductionPlanSerializer

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH", "DELETE"):
            return [AdminOr(CanManageCycle)()]
        return [AdminOr(IsFarmMember)()]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        return ProductionPlan.objects.filter(
            farm_id=farm_id,
            deleted_at__isnull=True,
        ).order_by("-created_at")

    def perform_create(self, serializer):
        farm_id = self.kwargs.get("farm_pk")
        serializer.save(farm_id=farm_id)

    def destroy(self, request, *args, **kwargs):
        plan = self.get_object()
        plan.deleted_at = timezone.now()
        plan.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CycleViewSet(viewsets.ModelViewSet):
    serializer_class = CycleSerializer

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH", "DELETE"):
            return [AdminOr(CanManageCycle)()]
        return [AdminOr(IsFarmMember)()]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        return Cycle.objects.filter(
            farm_id=farm_id,
            deleted_at__isnull=True,
        ).select_related("production_plan").order_by("-start_date")

    def perform_create(self, serializer):
        farm_id = self.kwargs.get("farm_pk")
        serializer.save(farm_id=farm_id)

    def destroy(self, request, *args, **kwargs):
        cycle = self.get_object()
        
        # Verificar si hay lotes activos vinculados al ciclo
        active_batches = CyclePondBatch.objects.filter(
            cycle=cycle,
            pond_batch__end_date__isnull=True
        )
        
        if active_batches.exists():
            count = active_batches.count()
            batch_info = []
            for cpb in active_batches[:3]:  # Mostrar hasta 3 lotes
                batch_info.append(f"Lote {cpb.pond_batch.batch.code} en {cpb.pond_batch.pond.code}")
            
            message = f"No se puede borrar este ciclo. Tiene {count} lote(s) activo(s): {', '.join(batch_info)}"
            if count > 3:
                message += f" +{count-3} más"
            
            return Response(
                {"detail": message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar si el ciclo tiene datos de monitoring registrados
        from apps.monitoring.services import CycleStateCalculator
        
        if CycleStateCalculator.has_monitoring_data(cycle.id):
            return Response(
                {
                    "detail": "No se puede eliminar este ciclo. Tiene datos de monitoreo registrados "
                             "(evaluaciones de peces, estadísticas diarias o controles). "
                             "El ciclo puede ser cosechado o cancelado, pero no eliminado completamente."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cycle.deleted_at = timezone.now()
        cycle.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CyclePondBatchViewSet(viewsets.ModelViewSet):
    serializer_class = CyclePondBatchSerializer

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH", "DELETE"):
            return [AdminOr(CanManageCycle)()]
        return [AdminOr(IsFarmMember)()]

    def get_queryset(self):
        farm_id = self.kwargs.get("farm_pk")
        cycle_id = self.kwargs.get("cycle_pk")
        
        queryset = CyclePondBatch.objects.filter(
            cycle__farm_id=farm_id
        ).select_related(
            "cycle",
            "pond_batch",
            "pond_batch__batch",
            "pond_batch__batch__specie",
            "pond_batch__pond",
        ).order_by("-id")
        
        # Si viene cycle_pk en la URL, filtra por ese ciclo específico
        if cycle_id:
            queryset = queryset.filter(cycle_id=cycle_id)
        
        return queryset

    def perform_create(self, serializer):
        serializer.save()

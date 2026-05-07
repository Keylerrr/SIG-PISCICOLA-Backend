from django.apps import apps
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import AdminOr
from apps.farms.permissions import CanManageCycle, IsFarmMember

from .models import FeedingPlan, FeedingSchedule
from .serializers import FeedingPlanSerializer, FeedingScheduleSerializer


def _get_farm(farm_id):
    Farm = apps.get_model("farms", "Farm")
    try:
        return Farm.objects.get(pk=farm_id, deleted_at__isnull=True)
    except Farm.DoesNotExist:
        return None


def _farm_not_found_response():
    return Response(
        {"detail": "Granja no encontrada."}, status=status.HTTP_404_NOT_FOUND
    )


def _plan_not_found_response():
    return Response(
        {"detail": "Plan de alimentación no encontrado."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _schedule_not_found_response():
    return Response(
        {"detail": "Cronograma de alimentación no encontrado."},
        status=status.HTTP_404_NOT_FOUND,
    )


class FeedingScheduleListCreateView(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageCycle)()]

    def get(self, request, farm_id):
        farm = _get_farm(farm_id)
        if not farm:
            return _farm_not_found_response()
        qs = (
            FeedingSchedule.objects.filter(farm=farm, deleted_at__isnull=True)
            .select_related("product", "specie", "parent")
            .order_by("-updated_at")
        )
        return Response(FeedingScheduleSerializer(qs, many=True).data)

    def post(self, request, farm_id):
        farm = _get_farm(farm_id)
        if not farm:
            return _farm_not_found_response()
        serializer = FeedingScheduleSerializer(
            data=request.data, context={"farm": farm}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(farm=farm)
        data = dict(FeedingScheduleSerializer(instance).data)
        data["warnings"] = FeedingScheduleSerializer.reference_warnings(instance)
        return Response(data, status=status.HTTP_201_CREATED)


class FeedingScheduleDetailView(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageCycle)()]

    def _get_schedule(self, farm_id, schedule_id):
        try:
            return FeedingSchedule.objects.select_related(
                "product", "specie", "parent"
            ).get(
                pk=schedule_id,
                farm_id=farm_id,
                deleted_at__isnull=True,
            )
        except FeedingSchedule.DoesNotExist:
            return None

    def get(self, request, farm_id, schedule_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        schedule = self._get_schedule(farm_id, schedule_id)
        if not schedule:
            return _schedule_not_found_response()
        return Response(FeedingScheduleSerializer(schedule).data)

    def patch(self, request, farm_id, schedule_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        schedule = self._get_schedule(farm_id, schedule_id)
        if not schedule:
            return _schedule_not_found_response()
        serializer = FeedingScheduleSerializer(
            schedule, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        data = dict(FeedingScheduleSerializer(instance).data)
        data["warnings"] = FeedingScheduleSerializer.reference_warnings(instance)
        return Response(data)

    def delete(self, request, farm_id, schedule_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        schedule = self._get_schedule(farm_id, schedule_id)
        if not schedule:
            return _schedule_not_found_response()
        schedule.deleted_at = timezone.now()
        schedule.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FeedingPlanListCreateView(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageCycle)()]

    def get(self, request, farm_id):
        farm = _get_farm(farm_id)
        if not farm:
            return _farm_not_found_response()
        qs = FeedingPlan.objects.filter(
            farm_id=farm_id, deleted_at__isnull=True
        ).select_related("cycle", "feeding_schedule", "farm")
        cycle_param = request.query_params.get("cycle")
        if cycle_param is not None:
            qs = qs.filter(cycle_id=cycle_param)
        return Response(FeedingPlanSerializer(qs, many=True).data)

    def post(self, request, farm_id):
        farm = _get_farm(farm_id)
        if not farm:
            return _farm_not_found_response()
        serializer = FeedingPlanSerializer(
            data=request.data, context={"farm": farm}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            FeedingPlanSerializer(instance).data, status=status.HTTP_201_CREATED
        )


class FeedingPlanDetailView(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageCycle)()]

    def _get_plan(self, farm_id, plan_id):
        try:
            return FeedingPlan.objects.select_related(
                "cycle", "feeding_schedule", "farm"
            ).get(pk=plan_id, farm_id=farm_id, deleted_at__isnull=True)
        except FeedingPlan.DoesNotExist:
            return None

    def get(self, request, farm_id, plan_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        plan = self._get_plan(farm_id, plan_id)
        if not plan:
            return _plan_not_found_response()
        return Response(FeedingPlanSerializer(plan).data)

    def delete(self, request, farm_id, plan_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        plan = self._get_plan(farm_id, plan_id)
        if not plan:
            return _plan_not_found_response()
        plan.deleted_at = timezone.now()
        plan.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

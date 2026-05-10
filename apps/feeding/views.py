from django.apps import apps
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import AdminOr
from apps.farms.permissions import CanManageCycle, IsFarmMember

from .models import FeedingEvent, FeedingPlan, FeedingSchedule
from .serializers import (
    FeedingEventSerializer,
    FeedingEventUpdateSerializer,
    FeedingPlanReplaceSerializer,
    FeedingPlanSerializer,
    FeedingScheduleSerializer,
)
from .utils import (
    feeding_plan_lifecycle_state,
    update_in_progress_feeding_plan,
    update_scheduled_feeding_plan,
)


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


def _event_not_found_response():
    return Response(
        {"detail": "Evento de alimentación no encontrado."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _schedule_not_found_response():
    return Response(
        {"detail": "Cronograma de alimentación no encontrado."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _bad_request(detail: str):
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _parse_optional_id(params, key: str):
    raw = params.get(key)
    if raw is None or raw == "":
        return None, None
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return None, _bad_request(f"Parámetro '{key}' debe ser un entero válido.")
    if v < 1:
        return None, _bad_request(f"Parámetro '{key}' debe ser mayor a 0.")
    return v, None


def _parse_schedule_type_param(params):
    raw = params.get("type")
    if raw is None or raw == "":
        return None, None
    valid = {c[0] for c in FeedingSchedule.Stage.choices}
    if raw not in valid:
        return None, _bad_request(
            f"Parámetro 'type' inválido. Valores: {', '.join(sorted(valid))}."
        )
    return raw, None


class FeedingScheduleListCreateView(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageCycle)()]

    def get(self, request, farm_id):
        farm = _get_farm(farm_id)
        if not farm:
            return _farm_not_found_response()

        specie_id, err = _parse_optional_id(request.query_params, "specie")
        if err:
            return err
        product_id, err = _parse_optional_id(request.query_params, "product")
        if err:
            return err
        schedule_type, err = _parse_schedule_type_param(request.query_params)
        if err:
            return err

        qs = (
            FeedingSchedule.objects.filter(
                farm=farm,
                deleted_at__isnull=True,
                is_current=True,
            )
            .select_related("product", "specie", "parent")
        )
        if specie_id is not None:
            qs = qs.filter(specie_id=specie_id)
        if product_id is not None:
            qs = qs.filter(product_id=product_id)
        if schedule_type is not None:
            qs = qs.filter(type=schedule_type)

        qs = qs.order_by("-created_at")
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
                is_current=True,
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
        return Response(data, status=status.HTTP_201_CREATED)

    def delete(self, request, farm_id, schedule_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        schedule = self._get_schedule(farm_id, schedule_id)
        if not schedule:
            return _schedule_not_found_response()
        if FeedingPlan.objects.filter(
            feeding_schedule_id=schedule.pk,
            deleted_at__isnull=True,
        ).exists():
            return Response(
                {
                    "detail": (
                        "No puede eliminar el cronograma mientras existan planes de "
                        "alimentación vigentes asociados a él."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        now = timezone.now()
        schedule.is_current = False
        schedule.deleted_at = now
        schedule.save(update_fields=["is_current", "deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class FeedingScheduleVersionsListView(APIView):

    def get_permissions(self):
        return [AdminOr(IsFarmMember)()]

    def get(self, request, farm_id, schedule_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        try:
            head = FeedingSchedule.objects.select_related(
                "product", "specie", "parent"
            ).get(
                pk=schedule_id,
                farm_id=farm_id,
                is_current=True,
                deleted_at__isnull=True,
            )
        except FeedingSchedule.DoesNotExist:
            return _schedule_not_found_response()

        chain = []
        cur = head
        seen: set[int] = set()
        while cur is not None and cur.pk not in seen:
            seen.add(cur.pk)
            chain.append(cur)
            pid = cur.parent_id
            if not pid:
                break
            cur = (
                FeedingSchedule.objects.select_related(
                    "product", "specie", "parent"
                )
                .filter(pk=pid, farm_id=farm_id)
                .first()
            )
        chain.reverse()
        return Response(FeedingScheduleSerializer(chain, many=True).data)


class FeedingPlanListCreateView(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageCycle)()]

    def get(self, request, farm_id):
        farm = _get_farm(farm_id)
        if not farm:
            return _farm_not_found_response()
        qs = FeedingPlan.objects.filter(farm_id=farm_id).select_related(
            "cycle", "feeding_schedule", "farm"
        )
        if not AdminOr(CanManageCycle)().has_permission(request, self):
            qs = qs.filter(deleted_at__isnull=True)
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


class FeedingPlanOccupiedRangesView(APIView):

    def get_permissions(self):
        return [AdminOr(IsFarmMember)()]

    def get(self, request, farm_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()

        cycle_param = request.query_params.get("cycle")
        if cycle_param is None or str(cycle_param).strip() == "":
            return Response(
                {
                    "detail": (
                        "Se requiere el parámetro de consulta «cycle» (id del ciclo)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            cycle_id = int(cycle_param)
        except (TypeError, ValueError):
            return Response(
                {"detail": "El parámetro «cycle» debe ser un entero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Cycle = apps.get_model("cycle", "Cycle")
        try:
            cycle = Cycle.objects.get(pk=cycle_id, deleted_at__isnull=True)
        except Cycle.DoesNotExist:
            return Response(
                {"detail": "Ciclo no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if cycle.farm_id != farm_id:
            return Response(
                {"detail": "El ciclo no pertenece a esta granja."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = (
            FeedingPlan.objects.filter(
                farm_id=farm_id,
                cycle_id=cycle_id,
                deleted_at__isnull=True,
            )
            .order_by("start_date", "pk")
            .values("start_date", "end_date")
        )
        ranges = list(qs)
        return Response({"cycle": cycle_id, "ranges": ranges})


class FeedingPlanDetailView(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageCycle)()]

    def _get_plan(self, farm_id, plan_id, *, current_only: bool = False):
        try:
            qs = FeedingPlan.objects.select_related(
                "cycle", "feeding_schedule", "farm"
            ).filter(pk=plan_id, farm_id=farm_id)
            if current_only:
                qs = qs.filter(deleted_at__isnull=True)
            return qs.get()
        except FeedingPlan.DoesNotExist:
            return None

    def get(self, request, farm_id, plan_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        plan = self._get_plan(farm_id, plan_id, current_only=False)
        if not plan:
            return _plan_not_found_response()
        if plan.deleted_at is not None and not AdminOr(CanManageCycle)().has_permission(
            request, self
        ):
            return _plan_not_found_response()
        return Response(FeedingPlanSerializer(plan).data)

    def patch(self, request, farm_id, plan_id):
        farm = _get_farm(farm_id)
        if not farm:
            return _farm_not_found_response()
        plan = self._get_plan(farm_id, plan_id, current_only=True)
        if not plan:
            return _plan_not_found_response()

        state = feeding_plan_lifecycle_state(plan)
        if state == "finished":
            return Response(
                {
                    "detail": (
                        "No se puede modificar un plan cuya fecha de fin ya pasó."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FeedingPlanReplaceSerializer(
            data=request.data,
            context={"plan": plan, "farm_id": farm_id},
        )
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        try:
            if state == "in_progress":
                new_plan = update_in_progress_feeding_plan(
                    farm_id=farm_id,
                    old_plan=plan,
                    cycle=vd["cycle"],
                    feeding_schedule=vd["feeding_schedule"],
                    start_date=vd["start_date"],
                    end_date=vd["end_date"],
                )
                return Response(
                    FeedingPlanSerializer(new_plan).data,
                    status=status.HTTP_201_CREATED,
                )
            updated_plan = update_scheduled_feeding_plan(
                farm_id=farm_id,
                plan=plan,
                cycle=vd["cycle"],
                feeding_schedule=vd["feeding_schedule"],
                start_date=vd["start_date"],
                end_date=vd["end_date"],
            )
            return Response(FeedingPlanSerializer(updated_plan).data)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request, farm_id, plan_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        plan = self._get_plan(farm_id, plan_id, current_only=True)
        if not plan:
            return _plan_not_found_response()
        if feeding_plan_lifecycle_state(plan) == "in_progress":
            return Response(
                {
                    "detail": (
                        "No puede eliminar un plan en curso. Solo se permiten bajas "
                        "lógicas de planes programados o ya terminados."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        plan.deleted_at = timezone.now()
        plan.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class FeedingEventListView(APIView):

    def get_permissions(self):
        return [AdminOr(IsFarmMember)()]

    def get(self, request, farm_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        qs = FeedingEvent.objects.filter(farm_id=farm_id).select_related(
            "cycle",
            "feeding_plan",
            "farm",
            "planned_unit",
            "actual_unit",
            "completed_by",
        )
        if not AdminOr(CanManageCycle)().has_permission(request, self):
            qs = qs.filter(feeding_plan__deleted_at__isnull=True)
        plan_param = request.query_params.get("feeding_plan")
        if plan_param is not None:
            qs = qs.filter(feeding_plan_id=plan_param)
        cycle_param = request.query_params.get("cycle")
        if cycle_param is not None:
            qs = qs.filter(cycle_id=cycle_param)
        qs = qs.order_by("date", "scheduled_time", "ration_number")
        return Response(FeedingEventSerializer(qs, many=True).data)


class FeedingEventDetailView(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageCycle)()]

    def _get_event(self, farm_id, event_id):
        try:
            return FeedingEvent.objects.select_related(
                "cycle",
                "feeding_plan",
                "farm",
                "planned_unit",
                "actual_unit",
                "completed_by",
            ).get(
                pk=event_id,
                farm_id=farm_id,
            )
        except FeedingEvent.DoesNotExist:
            return None

    def get(self, request, farm_id, event_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        event = self._get_event(farm_id, event_id)
        if not event:
            return _event_not_found_response()
        if (
            event.feeding_plan_id
            and event.feeding_plan.deleted_at is not None
            and not AdminOr(CanManageCycle)().has_permission(request, self)
        ):
            return _event_not_found_response()
        return Response(FeedingEventSerializer(event).data)

    def patch(self, request, farm_id, event_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        event = self._get_event(farm_id, event_id)
        if not event:
            return _event_not_found_response()
        if (
            event.feeding_plan_id
            and event.feeding_plan.deleted_at is not None
            and not AdminOr(CanManageCycle)().has_permission(request, self)
        ):
            return _event_not_found_response()
        serializer = FeedingEventUpdateSerializer(
            event,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        event.refresh_from_db()
        return Response(FeedingEventSerializer(event).data)

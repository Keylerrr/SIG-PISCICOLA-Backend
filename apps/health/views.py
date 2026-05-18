from datetime import datetime

from django.apps import apps
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import AdminOr
from apps.farms.permissions import IsFarmMember

from .models import HealthStat, TreatmentEvent, TreatmentPlan
from .permissions import CanManageReviews
from .serializers import (
    HealthStatSerializer,
    TreatmentEventSerializer,
    TreatmentPlanSerializer,
)
from .utils import (
    cancel_treatment_plan,
    sync_treatment_plan_queryset,
    sync_treatment_plan_status,
    treatment_plan_lifecycle_state,
    update_in_progress_treatment_plan,
    update_scheduled_treatment_plan,
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


def _cycle_not_found_response():
    return Response(
        {"detail": "Ciclo no encontrado."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _get_cycle_in_farm(farm_id: int, cycle_id: int):
    Cycle = apps.get_model("cycle", "Cycle")
    try:
        return Cycle.objects.get(
            pk=cycle_id, farm_id=farm_id, deleted_at__isnull=True
        )
    except Cycle.DoesNotExist:
        return None


def _health_stat_not_found_response():
    return Response(
        {"detail": "Registro de salud no encontrado."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _treatment_plan_not_found_response():
    return Response(
        {"detail": "Plan de tratamiento no encontrado."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _treatment_event_not_found_response():
    return Response(
        {"detail": "Evento de tratamiento no encontrado."},
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


def _parse_optional_date(params, key: str):
    raw = params.get(key)
    if raw is None or raw == "":
        return None, None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date(), None
    except (TypeError, ValueError):
        return None, _bad_request(
            f"Parámetro '{key}' debe tener formato de fecha YYYY-MM-DD."
        )


def _parse_choice_param(params, key: str, *, choices) -> tuple[str | None, Response | None]:
    raw = params.get(key)
    if raw is None or raw == "":
        return None, None
    valid = {c[0] for c in choices}
    if raw not in valid:
        return None, _bad_request(
            f"Parámetro '{key}' inválido. Valores: {', '.join(sorted(valid))}."
        )
    return raw, None


def _parse_optional_bool(params, key: str) -> tuple[bool | None, Response | None]:
    raw = params.get(key)
    if raw is None or raw == "":
        return None, None
    if raw.lower() in ("true", "1", "yes"):
        return True, None
    if raw.lower() in ("false", "0", "no"):
        return False, None
    return None, _bad_request(
        f"Parámetro '{key}' inválido. Use true o false."
    )


def _choices_payload(choices) -> list[dict]:
    return [{"value": v, "label": lbl} for v, lbl in choices]


def _apply_health_stat_filters(qs, params):
    pond_id, err = _parse_optional_id(params, "pond")
    if err:
        return None, err
    if pond_id is not None:
        qs = qs.filter(pond_id=pond_id)

    severity, err = _parse_choice_param(
        params, "severity_level", choices=HealthStat.SeverityLevel.choices
    )
    if err:
        return None, err
    if severity is not None:
        qs = qs.filter(severity_level=severity)

    date_from, err = _parse_optional_date(params, "date_from")
    if err:
        return None, err
    if date_from is not None:
        qs = qs.filter(date__gte=date_from)

    date_to, err = _parse_optional_date(params, "date_to")
    if err:
        return None, err
    if date_to is not None:
        qs = qs.filter(date__lte=date_to)

    disease = params.get("disease_name")
    if disease:
        qs = qs.filter(disease_name__icontains=disease.strip())

    return qs, None


def _apply_treatment_plan_filters(qs, params):
    status_val, err = _parse_choice_param(
        params, "status", choices=TreatmentPlan.Status.choices
    )
    if err:
        return None, err
    if status_val is not None:
        qs = qs.filter(status=status_val)

    method, err = _parse_choice_param(
        params,
        "application_method",
        choices=TreatmentPlan.ApplicationMethod.choices,
    )
    if err:
        return None, err
    if method is not None:
        qs = qs.filter(application_method=method)

    product_id, err = _parse_optional_id(params, "product")
    if err:
        return None, err
    if product_id is not None:
        qs = qs.filter(product_id=product_id)

    exclude_cancelled, err = _parse_optional_bool(params, "exclude_cancelled")
    if err:
        return None, err
    if exclude_cancelled is True:
        qs = qs.exclude(status=TreatmentPlan.Status.CANCELLED)

    start_from, err = _parse_optional_date(params, "start_date_from")
    if err:
        return None, err
    if start_from is not None:
        qs = qs.filter(start_date__gte=start_from)

    end_to, err = _parse_optional_date(params, "end_date_to")
    if err:
        return None, err
    if end_to is not None:
        qs = qs.filter(end_date__lte=end_to)

    return qs, None


def _apply_treatment_event_filters(qs, params):
    status_val, err = _parse_choice_param(
        params, "status", choices=TreatmentEvent.Status.choices
    )
    if err:
        return None, err
    if status_val is not None:
        qs = qs.filter(status=status_val)

    date_from, err = _parse_optional_date(params, "date_from")
    if err:
        return None, err
    if date_from is not None:
        qs = qs.filter(date__gte=date_from)

    date_to, err = _parse_optional_date(params, "date_to")
    if err:
        return None, err
    if date_to is not None:
        qs = qs.filter(date__lte=date_to)

    return qs, None


class HealthOptionsView(APIView):
    """
    Catálogo de valores permitidos para formularios y filtros del módulo de salud.

    GET sin farm_id: enums de HealthStat, TreatmentPlan y TreatmentEvent.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response(
            {
                "health_stat": {
                    "severity_level": _choices_payload(
                        HealthStat.SeverityLevel.choices
                    ),
                },
                "treatment_plan": {
                    "status": _choices_payload(TreatmentPlan.Status.choices),
                    "application_method": _choices_payload(
                        TreatmentPlan.ApplicationMethod.choices
                    ),
                },
                "treatment_event": {
                    "status": _choices_payload(TreatmentEvent.Status.choices),
                    "status_closeable": _choices_payload(
                        (
                            (TreatmentEvent.Status.COMPLETED, "Completado"),
                            (TreatmentEvent.Status.SKIPPED, "Omitido"),
                        )
                    ),
                },
            }
        )


def _get_health_stat_in_cycle(farm_id: int, cycle_id: int, health_stat_id: int):
    try:
        return HealthStat.objects.select_related("cycle", "pond", "farm").get(
            pk=health_stat_id,
            farm_id=farm_id,
            cycle_id=cycle_id,
        )
    except HealthStat.DoesNotExist:
        return None


def _get_treatment_plan_for_farm(
    farm_id: int,
    health_stat_id: int,
    plan_id: int,
    *,
    exclude_cancelled: bool = False,
):
    try:
        qs = TreatmentPlan.objects.select_related(
            "health_stat", "health_stat__cycle", "product", "unit", "farm"
        ).filter(
            pk=plan_id,
            farm_id=farm_id,
            health_stat_id=health_stat_id,
        )
        if exclude_cancelled:
            qs = qs.exclude(status=TreatmentPlan.Status.CANCELLED)
        return qs.get()
    except TreatmentPlan.DoesNotExist:
        return None


class CycleHealthStatListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageReviews)()]

    @extend_schema(
        parameters=[
            OpenApiParameter("pond", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter(
                "severity_level", OpenApiTypes.STR, OpenApiParameter.QUERY
            ),
            OpenApiParameter("disease_name", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: HealthStatSerializer(many=True)},
    )
    def get(self, request, farm_id, cycle_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()

        qs = HealthStat.objects.filter(
            farm_id=farm_id,
            cycle_id=cycle_id,
        ).select_related("cycle", "pond", "farm")
        qs, err = _apply_health_stat_filters(qs, request.query_params)
        if err:
            return err
        qs = qs.order_by("-date", "-created_at")
        return Response(HealthStatSerializer(qs, many=True).data)

    @extend_schema(
        request=HealthStatSerializer,
        responses={201: HealthStatSerializer},
    )
    def post(self, request, farm_id, cycle_id):
        farm = _get_farm(farm_id)
        if not farm:
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()

        body = (
            request.data.copy()
            if hasattr(request.data, "copy")
            else dict(request.data)
        )
        raw_farm = body.get("farm")
        if raw_farm is not None:
            try:
                if int(raw_farm) != farm_id:
                    return _bad_request(
                        "El campo «farm» del cuerpo debe coincidir con la granja de la URL."
                    )
            except (TypeError, ValueError):
                return _bad_request("El campo «farm» debe ser un entero válido.")
        body["farm"] = farm_id

        raw_cycle = body.get("cycle")
        if raw_cycle is not None:
            try:
                if int(raw_cycle) != cycle_id:
                    return _bad_request(
                        "El campo «cycle» del cuerpo debe coincidir con el ciclo de la URL."
                    )
            except (TypeError, ValueError):
                return _bad_request("El campo «cycle» debe ser un entero válido.")
        body["cycle"] = cycle_id

        serializer = HealthStatSerializer(
            data=body,
            context={"request": request, "farm": farm},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CycleHealthStatDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageReviews)()]

    @extend_schema(responses={200: HealthStatSerializer})
    def get(self, request, farm_id, cycle_id, health_stat_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        health_stat = _get_health_stat_in_cycle(farm_id, cycle_id, health_stat_id)
        if not health_stat:
            return _health_stat_not_found_response()
        return Response(HealthStatSerializer(health_stat).data)


class HealthStatTreatmentPlanListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageReviews)()]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter(
                "application_method", OpenApiTypes.STR, OpenApiParameter.QUERY
            ),
            OpenApiParameter("product", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter(
                "exclude_cancelled", OpenApiTypes.BOOL, OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                "start_date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY
            ),
            OpenApiParameter("end_date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: TreatmentPlanSerializer(many=True)},
    )
    def get(self, request, farm_id, cycle_id, health_stat_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        if not _get_health_stat_in_cycle(farm_id, cycle_id, health_stat_id):
            return _health_stat_not_found_response()

        qs = TreatmentPlan.objects.filter(
            farm_id=farm_id,
            health_stat_id=health_stat_id,
        ).select_related("health_stat", "product", "unit", "farm")
        qs, err = _apply_treatment_plan_filters(qs, request.query_params)
        if err:
            return err
        qs = qs.order_by("-created_at")
        sync_treatment_plan_queryset(qs)
        return Response(TreatmentPlanSerializer(qs, many=True).data)

    @extend_schema(
        request=TreatmentPlanSerializer,
        responses={201: TreatmentPlanSerializer},
    )
    def post(self, request, farm_id, cycle_id, health_stat_id):
        farm = _get_farm(farm_id)
        if not farm:
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        if not _get_health_stat_in_cycle(farm_id, cycle_id, health_stat_id):
            return _health_stat_not_found_response()

        body = (
            request.data.copy()
            if hasattr(request.data, "copy")
            else dict(request.data)
        )
        raw_hs = body.get("health_stat")
        if raw_hs is not None:
            try:
                if int(raw_hs) != health_stat_id:
                    return _bad_request(
                        "El campo «health_stat» del cuerpo debe coincidir con el de la URL."
                    )
            except (TypeError, ValueError):
                return _bad_request("El campo «health_stat» debe ser un entero válido.")
        body["health_stat"] = health_stat_id

        serializer = TreatmentPlanSerializer(
            data=body,
            context={
                "farm": farm,
                "fixed_health_stat_id": health_stat_id,
                "request": request,
            },
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            TreatmentPlanSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


class HealthStatTreatmentPlanDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageReviews)()]

    @extend_schema(responses={200: TreatmentPlanSerializer})
    def get(self, request, farm_id, cycle_id, health_stat_id, plan_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        if not _get_health_stat_in_cycle(farm_id, cycle_id, health_stat_id):
            return _health_stat_not_found_response()
        plan = _get_treatment_plan_for_farm(farm_id, health_stat_id, plan_id)
        if not plan:
            return _treatment_plan_not_found_response()
        sync_treatment_plan_status(plan)
        return Response(TreatmentPlanSerializer(plan).data)

    @extend_schema(
        request=TreatmentPlanSerializer,
        responses={200: TreatmentPlanSerializer, 201: TreatmentPlanSerializer},
    )
    def patch(self, request, farm_id, cycle_id, health_stat_id, plan_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        if not _get_health_stat_in_cycle(farm_id, cycle_id, health_stat_id):
            return _health_stat_not_found_response()
        plan = _get_treatment_plan_for_farm(
            farm_id,
            health_stat_id,
            plan_id,
            exclude_cancelled=True,
        )
        if not plan:
            return _treatment_plan_not_found_response()

        sync_treatment_plan_status(plan)
        if plan.status == TreatmentPlan.Status.COMPLETED:
            return Response(
                {
                    "detail": (
                        "No se puede modificar un plan terminado "
                        "(se conserva por trazabilidad)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if plan.status == TreatmentPlan.Status.CANCELLED:
            return Response(
                {"detail": "No se puede modificar un plan cancelado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TreatmentPlanSerializer(
            plan,
            data=request.data,
            partial=True,
            context={
                "replace_plan": plan,
                "farm_id": farm_id,
                "fixed_health_stat_id": health_stat_id,
            },
        )
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        try:
            if plan.status == TreatmentPlan.Status.IN_PROGRESS:
                new_plan = update_in_progress_treatment_plan(
                    farm_id=farm_id,
                    old_plan=plan,
                    health_stat=vd["health_stat"],
                    created_by=request.user,
                    product=vd.get("product"),
                    start_date=vd["start_date"],
                    end_date=vd["end_date"],
                    dose_per_application=vd["dose_per_application"],
                    unit=vd["unit"],
                    times_per_day=vd["times_per_day"],
                    gap_between_times_per_day=vd["gap_between_times_per_day"],
                    gap_between_completed_day=vd["gap_between_completed_day"],
                    application_method=vd["application_method"],
                    reason=vd.get("reason"),
                    notes=vd.get("notes"),
                )
                return Response(
                    TreatmentPlanSerializer(new_plan).data,
                    status=status.HTTP_201_CREATED,
                )
            updated_plan = update_scheduled_treatment_plan(
                farm_id=farm_id,
                plan=plan,
                health_stat=vd["health_stat"],
                product=vd.get("product"),
                start_date=vd["start_date"],
                end_date=vd["end_date"],
                dose_per_application=vd["dose_per_application"],
                unit=vd["unit"],
                times_per_day=vd["times_per_day"],
                gap_between_times_per_day=vd["gap_between_times_per_day"],
                gap_between_completed_day=vd["gap_between_completed_day"],
                application_method=vd["application_method"],
                reason=vd.get("reason"),
                notes=vd.get("notes"),
            )
            return Response(TreatmentPlanSerializer(updated_plan).data)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(responses={204: None})
    def delete(self, request, farm_id, cycle_id, health_stat_id, plan_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        if not _get_health_stat_in_cycle(farm_id, cycle_id, health_stat_id):
            return _health_stat_not_found_response()
        plan = _get_treatment_plan_for_farm(
            farm_id,
            health_stat_id,
            plan_id,
            exclude_cancelled=True,
        )
        if not plan:
            return _treatment_plan_not_found_response()

        try:
            cancel_treatment_plan(plan)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TreatmentPlanOccupiedRangesView(APIView):
    """Rangos de fechas de planes vigentes de un registro de salud (evitar solapes en UI)."""

    def get_permissions(self):
        return [AdminOr(IsFarmMember)()]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, farm_id, cycle_id, health_stat_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        if not _get_health_stat_in_cycle(farm_id, cycle_id, health_stat_id):
            return _health_stat_not_found_response()

        qs = (
            TreatmentPlan.objects.filter(
                farm_id=farm_id,
                health_stat_id=health_stat_id,
            )
            .exclude(status=TreatmentPlan.Status.CANCELLED)
            .order_by("start_date", "pk")
            .values("id", "start_date", "end_date", "status")
        )
        return Response(
            {
                "health_stat_id": health_stat_id,
                "ranges": list(qs),
            }
        )


class CycleTreatmentEventListView(APIView):
    """
    Eventos de tratamiento del ciclo (calendario / bandeja operativa).

    Equivalente al listado por ciclo de feeding-events.
    """

    def get_permissions(self):
        return [AdminOr(IsFarmMember)()]

    @extend_schema(
        parameters=[
            OpenApiParameter("pond", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("health_stat", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("plan", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: TreatmentEventSerializer(many=True)},
    )
    def get(self, request, farm_id, cycle_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()

        qs = TreatmentEvent.objects.filter(
            farm_id=farm_id,
            cycle_id=cycle_id,
        ).select_related(
            "cycle",
            "treatment_plan",
            "treatment_plan__health_stat",
            "treatment_plan__health_stat__pond",
            "farm",
            "planned_unit",
            "actual_unit",
            "completed_by",
        ).exclude(treatment_plan__status=TreatmentPlan.Status.CANCELLED)

        pond_id, err = _parse_optional_id(request.query_params, "pond")
        if err:
            return err
        if pond_id is not None:
            qs = qs.filter(treatment_plan__health_stat__pond_id=pond_id)

        health_stat_id, err = _parse_optional_id(request.query_params, "health_stat")
        if err:
            return err
        if health_stat_id is not None:
            qs = qs.filter(treatment_plan__health_stat_id=health_stat_id)

        plan_id, err = _parse_optional_id(request.query_params, "plan")
        if err:
            return err
        if plan_id is not None:
            qs = qs.filter(treatment_plan_id=plan_id)

        qs, err = _apply_treatment_event_filters(qs, request.query_params)
        if err:
            return err

        qs = qs.order_by("date", "scheduled_time", "application_number")
        return Response(TreatmentEventSerializer(qs, many=True).data)


class HealthStatTreatmentPlanEventListView(APIView):
    def get_permissions(self):
        return [AdminOr(IsFarmMember)()]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("date_from", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("date_to", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: TreatmentEventSerializer(many=True)},
    )
    def get(self, request, farm_id, cycle_id, health_stat_id, plan_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        if not _get_health_stat_in_cycle(farm_id, cycle_id, health_stat_id):
            return _health_stat_not_found_response()
        plan = _get_treatment_plan_for_farm(farm_id, health_stat_id, plan_id)
        if not plan:
            return _treatment_plan_not_found_response()
        if plan.status == TreatmentPlan.Status.CANCELLED:
            return _treatment_plan_not_found_response()

        sync_treatment_plan_status(plan)
        qs = TreatmentEvent.objects.filter(
            farm_id=farm_id,
            treatment_plan_id=plan_id,
        ).select_related(
            "cycle",
            "treatment_plan",
            "farm",
            "planned_unit",
            "actual_unit",
            "completed_by",
        )
        qs, err = _apply_treatment_event_filters(qs, request.query_params)
        if err:
            return err
        qs = qs.order_by("date", "scheduled_time", "application_number")
        return Response(TreatmentEventSerializer(qs, many=True).data)


class HealthStatTreatmentPlanEventDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AdminOr(IsFarmMember)()]
        return [AdminOr(CanManageReviews)()]

    def _get_event(self, farm_id, cycle_id, health_stat_id, plan_id, event_id):
        try:
            return TreatmentEvent.objects.select_related(
                "cycle",
                "treatment_plan",
                "treatment_plan__health_stat",
                "farm",
                "planned_unit",
                "actual_unit",
                "completed_by",
            ).get(
                pk=event_id,
                farm_id=farm_id,
                cycle_id=cycle_id,
                treatment_plan_id=plan_id,
                treatment_plan__health_stat_id=health_stat_id,
            )
        except TreatmentEvent.DoesNotExist:
            return None

    @extend_schema(responses={200: TreatmentEventSerializer})
    def get(self, request, farm_id, cycle_id, health_stat_id, plan_id, event_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        event = self._get_event(farm_id, cycle_id, health_stat_id, plan_id, event_id)
        if not event:
            return _treatment_event_not_found_response()
        if event.treatment_plan.status == TreatmentPlan.Status.CANCELLED:
            return _treatment_plan_not_found_response()
        return Response(TreatmentEventSerializer(event).data)

    @extend_schema(
        request=TreatmentEventSerializer,
        responses={200: TreatmentEventSerializer},
    )
    def patch(self, request, farm_id, cycle_id, health_stat_id, plan_id, event_id):
        if not _get_farm(farm_id):
            return _farm_not_found_response()
        if not _get_cycle_in_farm(farm_id, cycle_id):
            return _cycle_not_found_response()
        event = self._get_event(farm_id, cycle_id, health_stat_id, plan_id, event_id)
        if not event:
            return _treatment_event_not_found_response()
        if event.treatment_plan.status == TreatmentPlan.Status.CANCELLED:
            return _treatment_plan_not_found_response()
        if event.treatment_plan.status == TreatmentPlan.Status.COMPLETED:
            return Response(
                {
                    "detail": (
                        "No se pueden modificar eventos de un plan terminado."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sync_treatment_plan_status(event.treatment_plan)
        serializer = TreatmentEventSerializer(
            event,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        event.refresh_from_db()
        event.treatment_plan.refresh_from_db()
        return Response(TreatmentEventSerializer(event).data)

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.cycle.models import Cycle
from apps.products.models import Product
from apps.species.models import SpecieFeedingReference

from .constants import (
    FEED_SCHEDULE_PRODUCT_TYPE_NAMES,
    FEEDING_WORKDAY_END_HOUR,
    FEEDING_WORKDAY_START_HOUR,
    feeding_work_window_minutes,
)
from .models import FeedingEvent, FeedingPlan, FeedingSchedule
from .utils import create_feeding_events_for_plan


class FeedingScheduleSerializer(serializers.ModelSerializer):
    warnings = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FeedingSchedule
        fields = [
            "id",
            "farm",
            "product",
            "specie",
            "name",
            "comments",
            "type",
            "aceptable_min_weight_g",
            "aceptable_max_weight_g",
            "feed_form",
            "pellet_size_mm",
            "feeding_rate_percentage",
            "times_per_day",
            "gap_between_times_per_day",
            "gap_between_completed_day",
            "expected_fca",
            "expected_daily_gain_g",
            "version",
            "is_current",
            "parent",
            "created_at",
            "updated_at",
            "deleted_at",
            "warnings",
        ]
        read_only_fields = [
            "farm",
            "created_at",
            "updated_at",
            "deleted_at",
            "warnings",
        ]

    def validate_aceptable_min_weight_g(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "El peso mínimo aceptable debe ser mayor a 0."
            )
        return value

    def validate_aceptable_max_weight_g(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "El peso máximo aceptable debe ser mayor a 0."
            )
        return value

    def validate_feeding_rate_percentage(self, value):
        if not (0 < value <= 100):
            raise serializers.ValidationError(
                "El porcentaje de alimentación debe ser mayor a 0 y como máximo 100."
            )
        return value

    def validate_pellet_size_mm(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "El tamaño del pellet debe ser mayor a 0."
            )
        return value

    def validate_times_per_day(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Las veces por día deben ser al menos 1."
            )
        return value

    def validate_gap_between_times_per_day(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "El intervalo entre raciones debe ser de al menos 1 minuto."
            )
        return value

    def validate_gap_between_completed_day(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "El intervalo entre jornadas debe ser de al menos 1 día."
            )
        return value

    def validate_expected_fca(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "El FCA esperado debe ser mayor a 0."
            )
        return value

    def validate_expected_daily_gain_g(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La ganancia diaria esperada debe ser mayor a 0."
            )
        return value

    def validate(self, data):
        instance = self.instance
        min_w = data.get(
            "aceptable_min_weight_g",
            getattr(instance, "aceptable_min_weight_g", None),
        )
        max_w = data.get(
            "aceptable_max_weight_g",
            getattr(instance, "aceptable_max_weight_g", None),
        )
        if min_w is not None and max_w is not None and min_w > max_w:
            raise serializers.ValidationError(
                {
                    "aceptable_min_weight_g": (
                        "El peso mínimo no puede ser mayor que el máximo."
                    )
                }
            )

        times_pd = data.get(
            "times_per_day",
            getattr(instance, "times_per_day", None),
        )
        gap_min = data.get(
            "gap_between_times_per_day",
            getattr(instance, "gap_between_times_per_day", None),
        )
        if times_pd is not None and gap_min is not None and times_pd > 1:
            window = feeding_work_window_minutes()
            total_span = (times_pd - 1) * gap_min
            if total_span > window:
                max_gap = window // (times_pd - 1)
                raise serializers.ValidationError(
                    {
                        "gap_between_times_per_day": (
                            f"Con la jornada en campo ({FEEDING_WORKDAY_START_HOUR:02d}:00–"
                            f"{FEEDING_WORKDAY_END_HOUR:02d}:00), {times_pd} raciones por día "
                            f"no caben con {gap_min} minutos entre consecutivas: de la primera "
                            f"a la última serían {total_span} minutos y el máximo en ventana es "
                            f"{window}. Con esta frecuencia, el intervalo no debe superar "
                            f"{max_gap} minutos."
                        )
                    }
                )

        farm = self.context.get("farm")
        farm_id = getattr(farm, "pk", farm) if farm is not None else None
        if farm_id is None and instance is not None:
            farm_id = instance.farm_id

        raw_product = data.get("product", getattr(instance, "product_id", None))
        product_id = getattr(raw_product, "pk", raw_product)

        if farm_id is not None and product_id is not None:
            try:
                product = Product.objects.select_related("type_product").get(
                    pk=product_id
                )
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    {"product": "Producto no encontrado."}
                )
            if product.deleted_at:
                raise serializers.ValidationError(
                    {"product": "El producto no está disponible."}
                )
            if product.farm_id != farm_id:
                raise serializers.ValidationError(
                    {
                        "product": (
                            "El producto debe pertenecer a la misma granja del cronograma."
                        )
                    }
                )
            tname = (product.type_product.name or "").casefold()
            if not any(tname == a.casefold() 
                for a in FEED_SCHEDULE_PRODUCT_TYPE_NAMES):
                    raise serializers.ValidationError(
                        {
                            "product": (
                                "El tipo de producto debe ser de alimentación permitida "
                                "para cronogramas."
                            ),
                        }
                    )

        return data

    @staticmethod
    def reference_warnings(schedule: FeedingSchedule) -> dict[str, str]:
        """
        Compara el schedule con SpecieFeedingReference (misma especie, etapa y forma). Solo se emiten advertencias cuando hay rangos recomendados (min/max) y el dato del schedule queda fuera de esos límites.
        """
        if schedule.specie_id is None or not schedule.type or not schedule.feed_form:
            return {}

        ref = (
            SpecieFeedingReference.objects.filter(
                specie_id=schedule.specie_id,
                stage=schedule.type,
                recommended_feed_form=schedule.feed_form,
            )
            .only(
                "reference_fca_min",
                "reference_fca_max",
                "reference_daily_gain_g_min",
                "reference_daily_gain_g_max",
                "min_weight_g",
                "max_weight_g",
            )
            .first()
        )

        if ref is None:
            return {
                "_reference": (
                    "No hay referencia técnica registrada para esta especie, "
                    "etapa y forma de alimento."
                )
            }

        def _fmt_pair(lo, hi):
            return f"{lo} – {hi}"

        def _scalar_outside_range(value, lo, hi) -> bool:
            return (
                value is not None
                and lo is not None
                and hi is not None
                and (value < lo or value > hi)
            )

        def _weight_span_not_inside_reference(s_lo, s_hi, r_lo, r_hi) -> bool:
            return (
                s_lo is not None
                and s_hi is not None
                and r_lo is not None
                and r_hi is not None
                and (s_lo < r_lo or s_hi > r_hi)
            )

        w: dict[str, str] = {}

        if _scalar_outside_range(
            schedule.expected_fca,
            ref.reference_fca_min,
            ref.reference_fca_max,
        ):
            w["expected_fca"] = (
                "Fuera del rango recomendado "
                f"({_fmt_pair(ref.reference_fca_min, ref.reference_fca_max)})."
            )

        if _scalar_outside_range(
            schedule.expected_daily_gain_g,
            ref.reference_daily_gain_g_min,
            ref.reference_daily_gain_g_max,
        ):
            w["expected_daily_gain_g"] = (
                "Fuera del rango recomendado "
                f"({_fmt_pair(ref.reference_daily_gain_g_min, ref.reference_daily_gain_g_max)} g/día)."
            )

        if _weight_span_not_inside_reference(
            schedule.aceptable_min_weight_g,
            schedule.aceptable_max_weight_g,
            ref.min_weight_g,
            ref.max_weight_g,
        ):
            w["aceptable_min_weight_g"] = (
                "El rango de peso aceptable debería estar contenido en el recomendado "
                f"({_fmt_pair(ref.min_weight_g, ref.max_weight_g)} g), según referencia técnica."
            )

        return w

    def get_warnings(self, obj):
        if obj.pk is None:
            return {}
        return self.reference_warnings(obj)


class FeedingPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedingPlan
        fields = [
            "id",
            "farm",
            "cycle",
            "feeding_schedule",
            "start_date",
            "end_date",
            "created_at",
            "deleted_at",
        ]
        read_only_fields = ["farm", "created_at", "deleted_at"]

    def validate(self, data):
        farm = self.context.get("farm")
        farm_id = getattr(farm, "pk", farm) if farm is not None else None
        if farm_id is None:
            raise serializers.ValidationError(
                {"farm": "Contexto de granja requerido para crear el plan."}
            )

        raw_cycle = data.get("cycle")
        raw_schedule = data.get("feeding_schedule")
        cycle_pk = getattr(raw_cycle, "pk", raw_cycle)
        schedule_pk = getattr(raw_schedule, "pk", raw_schedule)

        try:
            cycle = Cycle.objects.select_related("farm", "specie").get(pk=cycle_pk)
        except Cycle.DoesNotExist:
            raise serializers.ValidationError({"cycle": "Ciclo no encontrado."})

        try:
            schedule = FeedingSchedule.objects.select_related("farm", "specie").get(
                pk=schedule_pk,
                deleted_at__isnull=True,
            )
        except FeedingSchedule.DoesNotExist:
            raise serializers.ValidationError(
                {"feeding_schedule": "Cronograma no encontrado o no disponible."}
            )

        if cycle.deleted_at:
            raise serializers.ValidationError(
                {"cycle": "El ciclo no está disponible."}
            )
        if cycle.farm_id != farm_id:
            raise serializers.ValidationError(
                {"cycle": "El ciclo debe pertenecer a la misma granja."}
            )
        if schedule.farm_id != farm_id:
            raise serializers.ValidationError(
                {
                    "feeding_schedule": (
                        "El cronograma debe pertenecer a la misma granja."
                    )
                }
            )
        if cycle.specie_id != schedule.specie_id:
            raise serializers.ValidationError(
                {
                    "feeding_schedule": (
                        "La especie del cronograma debe coincidir con la del ciclo."
                    )
                }
            )
        if cycle.state in (Cycle.State.FINISHED, Cycle.State.CANCELLED):
            raise serializers.ValidationError(
                {
                    "cycle": (
                        "No se puede asociar un plan a un ciclo finalizado o cancelado."
                    )
                }
            )

        start = data["start_date"]
        end = data["end_date"]
        if start > end:
            raise serializers.ValidationError(
                {"end_date": "La fecha de fin debe ser mayor o igual al inicio."}
            )
        if start < cycle.start_date:
            raise serializers.ValidationError(
                {
                    "start_date": (
                        "El inicio del plan no puede ser anterior al inicio del ciclo."
                    )
                }
            )
        if end > cycle.estimated_finish_date:
            raise serializers.ValidationError(
                {
                    "end_date": (
                        "La fecha de fin no puede superar la fecha estimada de fin del ciclo."
                    )
                }
            )
        if cycle.finish_date and end > cycle.finish_date:
            raise serializers.ValidationError(
                {
                    "end_date": (
                        "La fecha de fin no puede superar la fecha de cierre del ciclo."
                    )
                }
            )

        return data

    def create(self, validated_data):
        validated_data["farm"] = self.context["farm"]
        with transaction.atomic():
            plan = super().create(validated_data)
            create_feeding_events_for_plan(plan)
        return plan


class FeedingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedingEvent
        fields = [
            "id",
            "farm",
            "cycle",
            "feeding_plan",
            "date",
            "scheduled_time",
            "ration_number",
            "planned_quantity",
            "planned_unit",
            "status",
            "completed_at",
            "actual_quantity",
            "actual_unit",
            "created_at",
            "updated_at",
            "completed_by",
        ]
        read_only_fields = fields


class FeedingEventUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedingEvent
        fields = [
            "date",
            "scheduled_time",
            "status",
            "actual_quantity",
            "actual_unit",
        ]

    def validate(self, data):
        instance = self.instance
        if instance.status != FeedingEvent.Status.SCHEDULED:
            raise serializers.ValidationError(
                "Solo se pueden actualizar eventos en estado programado."
            )

        wants_close = "status" in data
        wants_reschedule = "date" in data or "scheduled_time" in data

        if not wants_close and not wants_reschedule:
            raise serializers.ValidationError(
                "Indique status (completed o skipped) para cerrar el evento, "
                "o date y/o scheduled_time para reprogramar."
            )

        if wants_reschedule:
            plan = instance.feeding_plan
            effective_date = data.get("date", instance.date)
            if effective_date < plan.start_date or effective_date > plan.end_date:
                raise serializers.ValidationError(
                    {
                        "date": (
                            "La fecha debe estar entre el inicio y el fin del plan "
                            "de alimentación."
                        )
                    }
                )

        if wants_close:
            new_status = data["status"]
            if new_status == FeedingEvent.Status.SCHEDULED:
                raise serializers.ValidationError(
                    {
                        "status": (
                            "El evento ya está programado. "
                            "Para reprogramar omita status y envíe date y/o scheduled_time."
                        )
                    }
                )
            if new_status not in (
                FeedingEvent.Status.COMPLETED,
                FeedingEvent.Status.SKIPPED,
            ):
                raise serializers.ValidationError(
                    {"status": "Solo se admite completar u omitir el evento."}
                )
            if new_status == FeedingEvent.Status.COMPLETED:
                aq = data.get("actual_quantity", instance.actual_quantity)
                if aq is None:
                    raise serializers.ValidationError(
                        {
                            "actual_quantity": (
                                "Indique la cantidad real al completar el evento."
                            )
                        }
                    )
                if "actual_unit" not in data:
                    raise serializers.ValidationError(
                        {
                            "actual_unit": (
                                "Indique la unidad de la cantidad real al completar el evento."
                            )
                        }
                    )
        return data

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = (
            request.user
            if request and getattr(request.user, "is_authenticated", False)
            else None
        )

        if "date" in validated_data:
            instance.date = validated_data["date"]
        if "scheduled_time" in validated_data:
            instance.scheduled_time = validated_data["scheduled_time"]

        if "status" in validated_data:
            new_status = validated_data["status"]
            instance.status = new_status
            if "actual_quantity" in validated_data:
                instance.actual_quantity = validated_data["actual_quantity"]
            if "actual_unit" in validated_data:
                instance.actual_unit = validated_data["actual_unit"]
            if new_status in (
                FeedingEvent.Status.COMPLETED,
                FeedingEvent.Status.SKIPPED,
            ):
                instance.completed_at = timezone.now()
                if user is not None:
                    instance.completed_by = user

        instance.save()
        return instance

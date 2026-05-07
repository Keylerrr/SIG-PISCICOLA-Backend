from rest_framework import serializers

from apps.cycle.models import Cycle
from apps.products.models import Product
from apps.species.models import SpecieFeedingReference

from .constants import FEED_SCHEDULE_PRODUCT_TYPE_NAMES
from .models import FeedingPlan, FeedingSchedule


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
        return super().create(validated_data)

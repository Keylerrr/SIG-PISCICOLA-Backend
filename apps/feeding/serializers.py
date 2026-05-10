from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.cycle.models import Cycle
from apps.products.models import Product
from apps.species.models import SpecieFeedingReference

from .constants import FEED_SCHEDULE_PRODUCT_TYPE_NAMES, MINUTES_PER_DAY
from .models import FeedingEvent, FeedingPlan, FeedingSchedule
from .utils import create_feeding_events_for_plan


def _validate_feeding_plan_business_rules(
    *,
    farm_id: int,
    cycle: Cycle,
    schedule: FeedingSchedule,
    start_date,
    end_date,
):
    errors = {}
    if cycle.deleted_at:
        errors["cycle"] = "El ciclo no está disponible."
    if cycle.farm_id != farm_id:
        errors["cycle"] = "El ciclo debe pertenecer a la misma granja."
    if schedule.farm_id != farm_id:
        errors["feeding_schedule"] = "El cronograma debe pertenecer a la misma granja."
    if cycle.specie_id != schedule.specie_id:
        errors["feeding_schedule"] = (
            "La especie del cronograma debe coincidir con la del ciclo."
        )
    if cycle.state in (Cycle.State.FINISHED, Cycle.State.CANCELLED):
        errors["cycle"] = (
            "No se puede asociar un plan a un ciclo finalizado o cancelado."
        )
    if start_date > end_date:
        errors["end_date"] = "La fecha de fin debe ser mayor o igual al inicio."
    if start_date < cycle.start_date:
        errors["start_date"] = (
            "El inicio del plan no puede ser anterior al inicio del ciclo."
        )
    if end_date > cycle.estimated_finish_date:
        errors["end_date"] = (
            "La fecha de fin no puede superar la fecha estimada de fin del ciclo."
        )
    if cycle.finish_date and end_date > cycle.finish_date:
        errors["end_date"] = (
            "La fecha de fin no puede superar la fecha de cierre del ciclo."
        )
    if errors:
        raise serializers.ValidationError(errors)


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

    _SCHEDULE_PATCH_FORBIDDEN = {
        "name": "El nombre se hereda del cronograma anterior; no se puede enviar al versionar.",
        "product": (
            "El producto se hereda del cronograma anterior; para otro alimento cree un "
            "cronograma nuevo (POST)."
        ),
        "specie": (
            "La especie se hereda del cronograma anterior; para otra especie cree un "
            "cronograma nuevo (POST)."
        ),
        "parent": (
            "No envíe parent: la nueva versión queda automáticamente ligada al "
            "cronograma que está actualizando."
        ),
        "version": "La versión la asigna el servidor al crear la nueva fila.",
        "is_current": (
            "La marca de versión vigente la define el sistema al crear la nueva versión."
        ),
    }

    _SCHEDULE_VERSION_MERGE_FIELDS = (
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
    )

    def validate_name(self, value):
        text = (value or "").strip()
        if not text:
            raise serializers.ValidationError(
                "El nombre no puede estar vacío ni ser solo espacios."
            )
        return text

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
        if value < 0:
            raise serializers.ValidationError(
                "El intervalo entre jornadas no puede ser negativo. Use 0 para alimentar todos los días."
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
        if instance is not None:
            for field, message in self._SCHEDULE_PATCH_FORBIDDEN.items():
                if field in data:
                    raise serializers.ValidationError({field: message})
        if instance is None and data.get("parent") is not None:
            raise serializers.ValidationError(
                {
                    "parent": (
                        "Al crear un cronograma nuevo no debe enviar parent. "
                        "Para publicar una nueva versión, use el flujo de actualización "
                        "del cronograma vigente que desea sustituir."
                    ),
                }
            )
        if instance is None:
            for field in ("version", "is_current"):
                if field in data:
                    raise serializers.ValidationError(
                        {
                            field: (
                                "Este campo lo asigna el sistema al crear el cronograma."
                            ),
                        }
                    )
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
            total_span = (times_pd - 1) * gap_min
            if total_span >= MINUTES_PER_DAY:
                max_gap = (MINUTES_PER_DAY - 1) // (times_pd - 1)
                raise serializers.ValidationError(
                    {
                        "gap_between_times_per_day": (
                            f"Con {times_pd} raciones por día no caben intervalos de "
                            f"{gap_min} minutos entre raciones consecutivas: de la primera a la "
                            f"última suman {total_span} minutos y deben caber en un día "
                            f"(menos de {MINUTES_PER_DAY}). Con esa frecuencia el intervalo "
                            f"máximo es {max_gap} minutos."
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

        if farm_id is not None:
            if instance is None:
                schedule_name = data.get("name")
                if schedule_name is not None and data.get("parent") is None:
                    if FeedingSchedule.objects.filter(
                        farm_id=farm_id,
                        name__iexact=str(schedule_name),
                        is_current=True,
                    ).exists():
                        raise serializers.ValidationError(
                            {
                                "name": (
                                    "Ya existe un cronograma vigente con este nombre "
                                    "en la granja."
                                ),
                            }
                        )

        return data

    def create(self, validated_data):
        validated_data["is_current"] = True
        validated_data["parent"] = None
        validated_data["version"] = 1
        validated_data["farm"] = self.context["farm"]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        with transaction.atomic():
            old = (
                FeedingSchedule.objects.select_for_update()
                .select_related("farm", "product", "specie", "parent")
                .get(pk=instance.pk)
            )
            if old.deleted_at is not None:
                raise serializers.ValidationError(
                    {"non_field_errors": ["El cronograma no está disponible."]}
                )
            if not old.is_current:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Solo puede versionar el cronograma vigente (is_current). "
                            "Use el último registro de la cadena."
                        ],
                    }
                )
            create_kwargs = {
                "farm_id": old.farm_id,
                "name": old.name,
                "parent_id": old.pk,
                "version": old.version + 1,
                "is_current": True,
                "product_id": old.product_id,
                "specie_id": old.specie_id,
            }
            for f in self._SCHEDULE_VERSION_MERGE_FIELDS:
                create_kwargs[f] = (
                    validated_data[f] if f in validated_data else getattr(old, f)
                )
            new_obj = FeedingSchedule.objects.create(**create_kwargs)
            old.is_current = False
            old.deleted_at = timezone.now()
            old.save(update_fields=["is_current", "deleted_at"])
        return new_obj

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
                is_current=True,
            )
        except FeedingSchedule.DoesNotExist:
            raise serializers.ValidationError(
                {"feeding_schedule": "Cronograma no encontrado o no disponible."}
            )

        start = data["start_date"]
        end = data["end_date"]
        _validate_feeding_plan_business_rules(
            farm_id=farm_id,
            cycle=cycle,
            schedule=schedule,
            start_date=start,
            end_date=end,
        )

        if FeedingPlan.objects.filter(
            cycle=cycle,
            deleted_at__isnull=True,
        ).exists():
            raise serializers.ValidationError(
                {
                    "cycle": (
                        "Ya existe un plan de alimentación vigente para este ciclo. "
                        "Para cambiarlo, use PATCH sobre ese plan: se creará uno nuevo, se "
                        "archivará el anterior y se conservará el historial de eventos "
                        "ejecutados u omitidos."
                    )
                }
            )

        return data

    def create(self, validated_data):
        validated_data["farm"] = self.context["farm"]
        cycle = validated_data["cycle"]
        with transaction.atomic():
            Cycle.objects.select_for_update().get(pk=cycle.pk)
            if FeedingPlan.objects.filter(
                cycle=cycle,
                deleted_at__isnull=True,
            ).exists():
                raise serializers.ValidationError(
                    {
                        "cycle": (
                            "Ya existe un plan de alimentación vigente para este ciclo."
                        )
                    }
                )
            plan = super().create(validated_data)
            create_feeding_events_for_plan(plan)
        return plan


class FeedingPlanReplaceSerializer(serializers.Serializer):
    cycle = serializers.PrimaryKeyRelatedField(
        queryset=Cycle.objects.select_related("farm", "specie").all(),
        required=False,
    )
    feeding_schedule = serializers.PrimaryKeyRelatedField(
        queryset=FeedingSchedule.objects.filter(
            deleted_at__isnull=True,
            is_current=True,
        ).select_related(
            "farm", "specie"
        ),
        required=False,
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, data):
        old: FeedingPlan = self.context["plan"]
        farm_id = self.context["farm_id"]
        if not data:
            raise serializers.ValidationError(
                "Debe enviar al menos uno de: cycle, feeding_schedule, "
                "start_date, end_date."
            )

        cycle_obj = data.get("cycle", old.cycle)
        schedule_obj = data.get("feeding_schedule", old.feeding_schedule)
        start = data.get("start_date", old.start_date)
        end = data.get("end_date", old.end_date)

        try:
            cycle_obj = Cycle.objects.select_related("farm", "specie").get(
                pk=cycle_obj.pk
            )
        except Cycle.DoesNotExist:
            raise serializers.ValidationError({"cycle": "Ciclo no encontrado."})

        try:
            schedule_obj = FeedingSchedule.objects.select_related(
                "farm", "specie"
            ).get(
                pk=schedule_obj.pk,
                deleted_at__isnull=True,
                is_current=True,
            )
        except FeedingSchedule.DoesNotExist:
            raise serializers.ValidationError(
                {"feeding_schedule": "Cronograma no encontrado o no disponible."}
            )

        _validate_feeding_plan_business_rules(
            farm_id=farm_id,
            cycle=cycle_obj,
            schedule=schedule_obj,
            start_date=start,
            end_date=end,
        )

        return {
            "cycle": cycle_obj,
            "feeding_schedule": schedule_obj,
            "start_date": start,
            "end_date": end,
        }


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
            "status",
            "actual_quantity",
            "actual_unit",
        ]

    def validate_actual_quantity(self, value):
        if value is None:
            raise serializers.ValidationError(
                "La cantidad real es obligatoria y debe ser mayor a 0."
            )
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad real debe ser mayor a 0."
            )
        return value

    def validate(self, data):
        instance = self.instance

        if instance.status == FeedingEvent.Status.SKIPPED:
            raise serializers.ValidationError(
                "No se puede modificar un evento omitido."
            )

        if instance.status == FeedingEvent.Status.COMPLETED:
            if "status" in data:
                raise serializers.ValidationError(
                    {
                        "status": (
                            "No puede cambiar el estado de un evento ya completado; solo "
                            "puede corregir la cantidad y la unidad reales."
                        )
                    }
                )
            if not data:
                raise serializers.ValidationError(
                    "Envíe actual_quantity y/o actual_unit para corregir el registro."
                )
            return data

        # scheduled
        if "actual_quantity" in data or "actual_unit" in data:
            raise serializers.ValidationError(
                {
                    "actual_quantity": (
                        "Mientras el evento está programado no se aceptan cantidad ni unidad "
                        "reales. Cierre el evento con status=completed y envíe ambos campos, "
                        "o status=skipped."
                    )
                }
            )

        if "status" not in data:
            raise serializers.ValidationError(
                {
                    "status": (
                        "Indique status=completed o status=skipped para cerrar el evento."
                    )
                }
            )

        new_status = data["status"]
        if new_status not in (
            FeedingEvent.Status.COMPLETED,
            FeedingEvent.Status.SKIPPED,
        ):
            raise serializers.ValidationError(
                {
                    "status": (
                        "Cuando envía «status», solo se aceptan «completed» o «skipped». "
                        "No use «scheduled»: el evento ya está programado. Otros valores no "
                        "son válidos."
                    )
                }
            )

        if new_status == FeedingEvent.Status.COMPLETED:
            if "actual_quantity" not in data:
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

        if instance.status == FeedingEvent.Status.COMPLETED:
            if "actual_quantity" in validated_data:
                instance.actual_quantity = validated_data["actual_quantity"]
            if "actual_unit" in validated_data:
                instance.actual_unit = validated_data["actual_unit"]
            instance.save()
            return instance

        new_status = validated_data["status"]
        instance.status = new_status
        if new_status == FeedingEvent.Status.COMPLETED:
            instance.actual_quantity = validated_data["actual_quantity"]
            instance.actual_unit = validated_data["actual_unit"]
        instance.completed_at = timezone.now()
        if user is not None:
            instance.completed_by = user
        instance.save()
        return instance

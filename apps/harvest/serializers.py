# serializers.py

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.batch.models import Batch

from .models import (Harvest, HarvestClassification,
                     HarvestClassificationDerivation,
                     HarvestClassificationSource, HarvestSource)
from .utils import (_check_active_treatment, _get_available_quantity,
                    _validate_harvest, confirm_harvest,
                    get_classification_available_fish_count,
                    get_classification_derived_fish_count, get_cycle_weights,
                    validate_exact_classification_sources)
from .validators import (validate_pond_for_derivation,
                         validate_specie_for_derivation)


class HarvestClassificationSourceInputSerializer(serializers.Serializer):
    cycle_pond_batch_id = serializers.IntegerField()
    fish_count = serializers.IntegerField(min_value=1)
    total_weight_g = serializers.DecimalField(max_digits=14, decimal_places=2)


class HarvestClassificationSourceSerializer(serializers.ModelSerializer):
    cycle_pond_batch_id = serializers.IntegerField(read_only=True)
    batch_code = serializers.CharField(
        source="cycle_pond_batch.pond_batch.batch.code",
        read_only=True,
    )

    class Meta:
        model = HarvestClassificationSource
        fields = [
            "id",
            "cycle_pond_batch_id",
            "batch_code",
            "fish_count",
            "total_weight_g",
            "traceability_type",
            "created_at",
        ]
        read_only_fields = fields


class HarvestClassificationDerivationSerializer(serializers.ModelSerializer):
    batch_id = serializers.IntegerField(source="batch_id", read_only=True)

    class Meta:
        model = HarvestClassificationDerivation
        fields = [
            "id",
            "batch_id",
            "fish_count",
            "total_weight_g",
            "pond_id",
            "created_at",
        ]
        read_only_fields = fields


class HarvestClassificationSerializer(serializers.ModelSerializer):
    sources = HarvestClassificationSourceSerializer(many=True, read_only=True)
    derivations = HarvestClassificationDerivationSerializer(many=True, read_only=True)
    derived_fish_count = serializers.SerializerMethodField()
    available_fish_count = serializers.SerializerMethodField()

    class Meta:
        model = HarvestClassification
        fields = [
            "id",
            "size_category",
            "fish_count",
            "total_weight_g",
            "reference_price",
            "observations",
            "sources",
            "derivations",
            "derived_fish_count",
            "available_fish_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "sources",
            "derivations",
            "derived_fish_count",
            "available_fish_count",
            "created_at",
            "updated_at",
        ]

    def get_derived_fish_count(self, obj):
        if hasattr(obj, "_derived_fish_count"):
            return obj._derived_fish_count
        return get_classification_derived_fish_count(obj.id)

    def get_available_fish_count(self, obj):
        if hasattr(obj, "_available_fish_count"):
            return obj._available_fish_count
        return get_classification_available_fish_count(obj)


class HarvestClassificationWriteSerializer(serializers.ModelSerializer):

    sources = HarvestClassificationSourceInputSerializer(many=True, required=False)

    class Meta:
        model = HarvestClassification
        fields = [
            "size_category",
            "fish_count",
            "total_weight_g",
            "reference_price",
            "observations",
            "sources",
        ]


class HarvestSourceSerializer(serializers.ModelSerializer):
    cycle_pond_batch_id = serializers.IntegerField(read_only=True)
    batch_code = serializers.CharField(
        source="cycle_pond_batch.pond_batch.batch.code",
        read_only=True,
    )

    class Meta:
        model = HarvestSource
        fields = [
            "id",
            "cycle_pond_batch_id",
            "batch_code",
            "fish_count",
            "total_weight_g",
            "traceability_type",
            "created_at",
        ]
        read_only_fields = fields


class HarvestSerializer(serializers.ModelSerializer):
    classifications = HarvestClassificationWriteSerializer(many=True)
    sources = HarvestSourceSerializer(many=True, read_only=True)
    has_active_treatment = serializers.SerializerMethodField()

    min_weight_g = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    avg_weight_g = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    max_weight_g = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = Harvest
        fields = [
            "id",
            "farm",
            "cycle",
            "date",
            "total_fish_count",
            "total_weight_g",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "observations",
            "type",
            "traceability_mode",
            "classifications",
            "sources",
            "has_active_treatment",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "farm",
            "created_by",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "sources",
            "created_at",
            "updated_at",
        ]

    def get_has_active_treatment(self, obj):
        return _check_active_treatment(obj.cycle)

    def validate_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError(
                "La fecha de cosecha no puede ser futura."
            )
        return value

    def validate(self, data):
        cycle = data.get("cycle")
        harvest_type = data.get("type")
        total_fish_count = data.get("total_fish_count")
        total_weight_g = data.get("total_weight_g")
        date = data.get("date")
        classifications = data.get("classifications", [])
        traceability_mode = data.get(
            "traceability_mode",
            Harvest.TraceabilityMode.PROPORTIONAL,
        )

        if date and cycle and date < cycle.start_date:
            raise serializers.ValidationError(
                {
                    "date": "La fecha de cosecha no puede ser anterior al inicio del ciclo."
                }
            )

        errors = _validate_harvest(cycle, harvest_type, total_fish_count)
        if errors:
            raise serializers.ValidationError(errors)

        available = _get_available_quantity(cycle)
        if total_fish_count > available:
            raise serializers.ValidationError(
                {
                    "total_fish_count": (
                        f"La cantidad a cosechar ({total_fish_count}) excede "
                        f"la disponible ({available})."
                    )
                }
            )

        if not classifications:
            raise serializers.ValidationError(
                {"classifications": "Debe incluir al menos una clasificación."}
            )

        total_classified_fish = sum(c["fish_count"] for c in classifications)
        total_classified_weight = sum(c["total_weight_g"] for c in classifications)

        if total_classified_fish > total_fish_count:
            raise serializers.ValidationError(
                {
                    "classifications": (
                        f"La suma de peces clasificados ({total_classified_fish}) "
                        f"excede el total cosechado ({total_fish_count})."
                    )
                }
            )

        if total_classified_weight > total_weight_g:
            raise serializers.ValidationError(
                {
                    "classifications": (
                        f"La suma de peso clasificado ({total_classified_weight} g) "
                        f"excede el total cosechado ({total_weight_g} g)."
                    )
                }
            )

        categories = [c["size_category"] for c in classifications]
        if len(categories) != len(set(categories)):
            raise serializers.ValidationError(
                {"classifications": "No puede haber categorías de tamaño duplicadas."}
            )

        if traceability_mode == Harvest.TraceabilityMode.EXACT:
            try:
                validate_exact_classification_sources(
                    Harvest(cycle=cycle, traceability_mode=traceability_mode),
                    classifications,
                )
            except ValueError as exc:
                raise serializers.ValidationError(
                    {"classifications": str(exc)}
                ) from exc
        else:
            for classification in classifications:
                if classification.get("sources"):
                    raise serializers.ValidationError(
                        {
                            "classifications": (
                                "sources solo se permiten con traceability_mode=exact."
                            )
                        }
                    )

        return data

    @transaction.atomic
    def create(self, validated_data):
        classifications_data = validated_data.pop("classifications")
        cycle = validated_data["cycle"]

        weights = get_cycle_weights(cycle)

        harvest = Harvest.objects.create(**validated_data, **weights)

        classifications_with_sources = []
        for classification_data in classifications_data:
            sources = classification_data.pop("sources", None)
            classification = HarvestClassification.objects.create(
                harvest=harvest,
                farm=harvest.farm,
                created_by=harvest.created_by,
                **classification_data,
            )
            entry = {
                "size_category": classification.size_category,
                "fish_count": classification.fish_count,
                "total_weight_g": classification.total_weight_g,
            }
            if sources:
                entry["sources"] = sources
            classifications_with_sources.append(entry)

        try:
            confirm_harvest(harvest, classifications_with_sources)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc

        return Harvest.objects.prefetch_related(
            "classifications__sources__cycle_pond_batch__pond_batch__batch",
            "classifications__derivations",
            "sources__cycle_pond_batch__pond_batch__batch",
        ).get(pk=harvest.pk)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        classifications = []
        for classification in instance.classifications.all():
            classifications.append(HarvestClassificationSerializer(classification).data)
        data["classifications"] = classifications
        return data


class HarvestDetailSerializer(HarvestSerializer):

    classifications = HarvestClassificationSerializer(many=True, read_only=True)


class BatchFromClassificationSerializer(serializers.Serializer):
    specie_id = serializers.IntegerField()
    biological_state = serializers.ChoiceField(choices=Batch.BiologicalState.choices)
    pond_id = serializers.IntegerField()
    fish_count = serializers.IntegerField(required=False, min_value=1)
    comments = serializers.CharField(required=False, allow_blank=True, default="")

    min_weight_g = serializers.FloatField(required=False)
    avg_weight_g = serializers.FloatField(required=False)
    max_weight_g = serializers.FloatField(required=False)

    def validate(self, data):
        classification = self.context.get("classification")
        farm_id = self.context.get("farm_id")

        if classification is None or farm_id is None:
            raise serializers.ValidationError(
                "Contexto de validación incompleto (classification, farm_id)."
            )

        validate_pond_for_derivation(farm_id=farm_id, pond_id=data["pond_id"])
        validate_specie_for_derivation(
            specie_id=data["specie_id"],
            cycle=classification.harvest.cycle,
        )

        min_w = data.get("min_weight_g")
        avg_w = data.get("avg_weight_g")
        max_w = data.get("max_weight_g")

        weights_provided = [min_w, avg_w, max_w]
        if any(w is not None for w in weights_provided):
            if not all(w is not None for w in weights_provided):
                raise serializers.ValidationError(
                    "Si ingresa pesos manualmente debe enviar min_weight_g, avg_weight_g y max_weight_g."
                )
            if not (min_w <= avg_w <= max_w):
                raise serializers.ValidationError(
                    "min_weight_g <= avg_weight_g <= max_weight_g debe cumplirse."
                )
        return data

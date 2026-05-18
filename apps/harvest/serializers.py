# serializers.py

from django.utils import timezone
from rest_framework import serializers

from .models import Harvest, HarvestClassification
from .utils import (_check_active_treatment, _get_available_quantity,
                    _get_cycle, _validate_harvest)


class HarvestClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HarvestClassification
        fields = [
            "id",
            "size_category",
            "fish_count",
            "total_weight_kg",
            "reference_price",
            "observations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class HarvestSerializer(serializers.ModelSerializer):
    classifications = HarvestClassificationSerializer(many=True)
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
            "total_weight_kg",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "observations",
            "type",
            "classifications",
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
        total_weight_kg = data.get("total_weight_kg")
        date = data.get("date")
        classifications = data.get("classifications", [])

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
        total_classified_weight = sum(c["total_weight_kg"] for c in classifications)

        if total_classified_fish > total_fish_count:
            raise serializers.ValidationError(
                {
                    "classifications": (
                        f"La suma de peces clasificados ({total_classified_fish}) "
                        f"excede el total cosechado ({total_fish_count})."
                    )
                }
            )

        if total_classified_weight > total_weight_kg:
            raise serializers.ValidationError(
                {
                    "classifications": (
                        f"La suma de peso clasificado ({total_classified_weight} kg) "
                        f"excede el total cosechado ({total_weight_kg} kg)."
                    )
                }
            )

        categories = [c["size_category"] for c in classifications]
        if len(categories) != len(set(categories)):
            raise serializers.ValidationError(
                {"classifications": "No puede haber categorías de tamaño duplicadas."}
            )

        return data

    def create(self, validated_data):
        from .utils import confirm_harvest, get_cycle_weights

        classifications_data = validated_data.pop("classifications")
        cycle = validated_data["cycle"]

        weights = get_cycle_weights(cycle)

        harvest = Harvest.objects.create(**validated_data, **weights)

        for classification_data in classifications_data:
            HarvestClassification.objects.create(
                harvest=harvest,
                farm=harvest.farm,
                created_by=harvest.created_by,
                **classification_data,
            )

        confirm_harvest(harvest)
        return harvest


class BatchFromClassificationSerializer(serializers.Serializer):

    specie_id = serializers.IntegerField()
    biological_state = serializers.CharField()
    min_weight_g = serializers.FloatField()
    avg_weight_g = serializers.FloatField()
    max_weight_g = serializers.FloatField()
    pond_id = serializers.IntegerField()
    comments = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data):
        if not (data["min_weight_g"] <= data["avg_weight_g"] <= data["max_weight_g"]):
            raise serializers.ValidationError(
                "min_weight_g <= avg_weight_g <= max_weight_g debe cumplirse."
            )
        return data

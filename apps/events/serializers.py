from rest_framework import serializers

from .models import GradingEvent


class GradingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingEvent
        fields = [
            "id",
            "cycle",
            "source_pond_batch",
            "to_pond_batch",
            "quantity",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "date",
        ]

    def validate(self, data):
        source = data["source_pond_batch"]
        quantity = data["quantity"]
        
        if source.current_quantity < quantity:
            raise serializers.ValidationError(
                {
                    "quantity": f"Insufficient quantity. Available: {source.current_quantity}"
                }
            )
        return data

    def create(self, validated_data):
        source = validated_data["source_pond_batch"]
        destination = validated_data["to_pond_batch"]
        quantity = validated_data["quantity"]
        
        source.current_quantity -= quantity
        source.save(update_fields=["current_quantity"])
        
        destination.current_quantity += quantity
        destination.save(update_fields=["current_quantity"])
        
        return super().create(validated_data)

from django.db.models import Sum
from rest_framework import serializers

from apps.batch.models import PondBatch
from apps.cycle.models import Cycle
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
        cycle = data.get("cycle")
        source = data.get("source_pond_batch")
        destination = data.get("to_pond_batch")
        quantity = data.get("quantity")

        
        if cycle and cycle.state != Cycle.State.IN_PROGRESS:
            raise serializers.ValidationError({
                "cycle": "Solo se puede clasificar en ciclos que están en progreso."
            })

        
        if source and destination and source.pond == destination.pond:
            raise serializers.ValidationError({
                "to_pond_batch": "El estanque origen y destino no pueden ser el mismo."
            })

        
        if source and quantity and source.current_quantity < quantity:
            raise serializers.ValidationError({
                "quantity": f"Cantidad insuficiente. Disponible: {source.current_quantity}."
            })

        
        if destination and quantity:
            cantidad_actual_destino = PondBatch.objects.filter(
                pond=destination.pond,
                end_date__isnull=True
            ).aggregate(total=Sum("current_quantity"))["total"] or 0

            if cantidad_actual_destino + quantity > destination.pond.capacity:
                raise serializers.ValidationError({
                    "to_pond_batch": f"El estanque destino '{destination.pond.name}' supera su capacidad de "
                                    f"{destination.pond.capacity} peces. "
                                    f"Disponible: {destination.pond.capacity - cantidad_actual_destino}."
                })

        
        if cycle and source and source.batch.specie != cycle.specie:
            raise serializers.ValidationError({
                "source_pond_batch": "La especie del lote no coincide con la especie del ciclo."
            })

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
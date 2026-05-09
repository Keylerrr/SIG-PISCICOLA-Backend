from django.db.models import Sum
from rest_framework import serializers
from datetime import date

from apps.batch.models import PondBatch
from apps.cycle.models import Cycle, CyclePondBatch
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
        min_weight = data.get("min_weight_g")
        avg_weight = data.get("avg_weight_g")
        max_weight = data.get("max_weight_g")
        event_date = data.get("date")

        if quantity is not None and quantity <= 0:
            raise serializers.ValidationError({
                "quantity": "La cantidad debe ser mayor a 0."
            })

        if min_weight and avg_weight and max_weight:
            if not (min_weight <= avg_weight <= max_weight):
                raise serializers.ValidationError({
                    "weights": "min_weight_g <= avg_weight_g <= max_weight_g debe cumplirse."
                })

        if event_date and event_date > date.today():
            raise serializers.ValidationError({
                "date": "La fecha del evento no puede ser futura."
            })

        if cycle and cycle.state != Cycle.State.IN_PROGRESS:
            raise serializers.ValidationError({
                "cycle": "Solo se puede clasificar en ciclos que están en progreso."
            })

        if source and destination and source.batch.biological_state != destination.batch.biological_state:
            raise serializers.ValidationError({
                "to_pond_batch": "Los lotes deben tener el mismo estado biológico para clasificar."
            })

        if cycle and source:
            if not CycleBatch.objects.filter(cycle=cycle, pond_batch=source).exists():
                raise serializers.ValidationError({
                    "source_pond_batch": "El PondBatch origen no está actualmente en este ciclo."
                })

        if cycle and destination:
            if not CycleBatch.objects.filter(cycle=cycle, pond_batch=destination).exists():
                raise serializers.ValidationError({
                    "to_pond_batch": "El PondBatch destino no está actualmente en este ciclo."
                })

        if destination:
            destination_pond = destination.pond
            active_cycle_in_pond = Cycle.objects.filter(
                farm_id=destination_pond.farm_id,
                state=Cycle.State.IN_PROGRESS
            ).exclude(id=cycle.id if cycle else None).exists()
            
            if active_cycle_in_pond:
                raise serializers.ValidationError({
                    "to_pond_batch": "El estanque destino tiene un ciclo en proceso. Solo se puede transferir a estanques sin ciclo activo."
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

        if source and destination and source.batch.farm_id != destination.batch.farm_id:
            raise serializers.ValidationError({
                "to_pond_batch": "Los lotes deben pertenecer a la misma granja."
            })

        if cycle and destination and destination.batch.specie != cycle.specie:
            raise serializers.ValidationError({
                "to_pond_batch": "La especie del lote destino no coincide con la especie del ciclo."
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
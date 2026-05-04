from django.utils import timezone
from django.db.models import Sum
from rest_framework import serializers

from .models import Batch, BatchSource, BatchTransfer, PondBatch


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = [
            "id",
            "specie",
            "farm",
            "origin_type",
            "origin_id",
            "code",
            "biological_state",
            "status",
            "comments",
            "initial_quantity",
            "min_weight_g",
            "avg_weight_g",
            "max_weight_g",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["code", "created_at", "updated_at"]



    def create(self, validated_data):
        farm = validated_data["farm"]
        timestamp = int(timezone.now().timestamp())
        code = f"BATCH-{farm.id}-{timestamp}"
        
        while Batch.objects.filter(code=code, farm=farm).exists():
            timestamp += 1
            code = f"BATCH-{farm.id}-{timestamp}"
        
        validated_data["code"] = code
        return super().create(validated_data)


class BatchSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BatchSource
        fields = ["id", "parent_batch", "child_batch", "quantity"]
        unique_together = ("parent_batch", "child_batch")

    def validate(self, data):
        if data["parent_batch"] == data["child_batch"]:
            raise serializers.ValidationError(
                "A batch cannot be its own parent or child."
            )
        return data


class PondBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PondBatch
        fields = [
            "id",
            "pond",
            "batch",
            "initial_quantity",
            "current_quantity",
            "start_date",
            "end_date",
        ]
        read_only_fields = ["current_quantity"]

    def validate(self, data):
        pond = data.get("pond")
        cantidad_nueva = data.get("initial_quantity", 0)

        cantidad_actual = PondBatch.objects.filter(
            pond=pond,
            end_date__isnull=True
        ).aggregate(total=Sum("current_quantity"))["total"] or 0

        if cantidad_actual + cantidad_nueva > pond.capacity:
            raise serializers.ValidationError(
                f"El estanque '{pond.name}' supera su capacidad de "
                f"{pond.capacity} peces. Disponible: {pond.capacity - cantidad_actual}."
            )
        return data
    
    def create(self, validated_data):
        validated_data["current_quantity"] = validated_data["initial_quantity"]
        return super().create(validated_data)


class BatchTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = BatchTransfer
        fields = [
            "id",
            "source_pond_batch",
            "to_pond_batch",
            "farm",
            "quantity",
            "date",
            "reason",
        ]

    def validate(self, data):
        source = data["source_pond_batch"]
        destination = data["to_pond_batch"]
        quantity = data["quantity"]

        
        if source.current_quantity < quantity:
            raise serializers.ValidationError({
                "quantity": f"Cantidad insuficiente. Disponible: {source.current_quantity}"
            })

        
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

from django.db import transaction
from rest_framework import serializers

from .models import Buy, InventoryMovement, PurchaseDetail
from .utils import _create_inventory_movement, _delete_details_with_movements


class PurchaseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseDetail
        fields = [
            "id",
            "product",
            "unit",
            "quantity",
            "unit_value",
            "total_value",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["unit", "total_value", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs["total_value"] = attrs["quantity"] * attrs["unit_value"]
        return attrs


class BuySerializer(serializers.ModelSerializer):
    details = PurchaseDetailSerializer(many=True)

    class Meta:
        model = Buy
        fields = [
            "id",
            "farm",
            "supplier",
            "date",
            "invoice_number",
            "comments",
            "details",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["farm", "created_at", "updated_at"]

    def validate_details(self, value):
        if not value:
            raise serializers.ValidationError(
                "Una compra debe tener al menos un detalle."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        details_data = validated_data.pop("details")
        buy = Buy.objects.create(**validated_data)

        for detail_data in details_data:
            detail_data["unit"] = detail_data["product"].unit
            detail = PurchaseDetail.objects.create(buy=buy, **detail_data)
            _create_inventory_movement(buy, detail)

        return buy

    @transaction.atomic
    def update(self, instance, validated_data):
        details_data = validated_data.pop("details", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if details_data is not None:
            _delete_details_with_movements(instance)
            for detail_data in details_data:
                detail_data["unit"] = detail_data["product"].unit
                detail = PurchaseDetail.objects.create(buy=instance, **detail_data)
                _create_inventory_movement(instance, detail)

        return instance


class InventoryMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryMovement
        fields = [
            "id",
            "farm",
            "product",
            "pond_id",
            "cycle_id",
            "movement_type",
            "quantity",
            "unit_cost",
            "total_cost",
            "observations",
            "source_type",
            "source_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

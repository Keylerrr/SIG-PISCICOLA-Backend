from rest_framework import serializers
from .models import Pond


class PondSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pond
        fields = ['farm', 'code', 'name', 'status', 'capacity', 'area', 'volume', 'depth', 'description']
        extra_kwargs = {
            'code': {'required': False},
            'status': {'required': False},
            'description': {'required': False},
        }

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than 0.")
        return value


class PondUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pond
        fields = ['name', 'status', 'capacity', 'area', 'volume', 'depth', 'description']
        extra_kwargs = {
            'name': {'required': False},
            'status': {'required': False},
            'capacity': {'required': False},
            'area': {'required': False},
            'volume': {'required': False},
            'depth': {'required': False},
            'description': {'required': False},
        }

    def validate(self, data):
        if 'code' in self.initial_data:
            raise serializers.ValidationError({"code": "The pond code cannot be modified."})
        return data

    def validate_capacity(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Capacity must be greater than 0.")
        return value


class PondResponseSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.name', read_only=True)

    class Meta:
        model = Pond
        fields = [
            'id', 'farm', 'farm_name', 'code', 'name',
            'status', 'capacity', 'area', 'volume', 'depth', 'description',
            'created_at', 'updated_at'
        ]


class PondToggleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pond
        fields = ['status']


class PondChangeStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Pond.STATUS_CHOICES)

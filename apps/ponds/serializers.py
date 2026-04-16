from rest_framework import serializers
from .models import Pond


class PondSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pond
        fields = ['farm', 'code', 'name', 'type', 'status', 'capacity', 'description']
        extra_kwargs = {
            'type': {'required': False},
            'status': {'required': False},
            'description': {'required': False},
        }

    def validate_code(self, value):
        farm = self.initial_data.get('farm')
        if farm and Pond.objects.filter(farm=farm, code=value).exists():
            raise serializers.ValidationError("A pond with this code already exists in the farm.")
        return value

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than 0.")
        return value


class PondUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pond
        fields = ['name', 'type', 'status', 'capacity', 'description', 'is_active']
        extra_kwargs = {
            'name': {'required': False},
            'type': {'required': False},
            'status': {'required': False},
            'capacity': {'required': False},
            'description': {'required': False},
            'is_active': {'required': False},
        }

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
            'type', 'status', 'capacity', 'description', 'is_active',
            'created_at', 'updated_at'
        ]


class PondToggleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pond
        fields = ['is_active']


class PondChangeStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Pond.STATUS_CHOICES)

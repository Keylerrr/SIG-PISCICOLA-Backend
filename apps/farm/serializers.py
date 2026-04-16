from rest_framework import serializers
from .models import Farm

class CreateFarmSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    manager_id = serializers.IntegerField(required=False) # Solo lo usa el admin
    nit = serializers.CharField(max_length=50, required=False, allow_blank=True)
    owner = serializers.CharField(max_length=200, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    municipality = serializers.CharField(max_length=100, required=False, allow_blank=True)
    village = serializers.CharField(max_length=100, required=False, allow_blank=True)
    coordinates = serializers.CharField(max_length=100, required=False, allow_blank=True)
    total_area_ha = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True) # serializers.TextField no existe en DRF. Por lo tanto usamos CharField.

class FarmResponseSerializer(serializers.ModelSerializer):
    manager_id = serializers.IntegerField(source='manager.id', allow_null=True)
    manager_name = serializers.CharField(source='manager.user.name', allow_null=True)

    class Meta:
        model = Farm
        fields = [
            'id', 'name', 'nit', 'owner', 'department', 'municipality',
            'village', 'coordinates', 'total_area_ha', 'description',
            'is_active', 'created_at', 'manager_id', 'manager_name'
        ]

class UpdateFarmSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    nit = serializers.CharField(max_length=50, required=False, allow_blank=True)
    owner = serializers.CharField(max_length=200, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    municipality = serializers.CharField(max_length=100, required=False, allow_blank=True)
    village = serializers.CharField(max_length=100, required=False, allow_blank=True)
    coordinates = serializers.CharField(max_length=100, required=False, allow_blank=True)
    total_area_ha = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
from rest_framework import serializers
from .models import Farm, DEPARTMENT_CHOICES, CITY_CHOICES, DEPARTMENT_CITY_MAP


class CreateFarmSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    manager_id = serializers.IntegerField(required=False)  # Solo lo usa el admin
    department = serializers.ChoiceField(choices=DEPARTMENT_CHOICES, required=False, allow_null=True)
    city = serializers.ChoiceField(choices=CITY_CHOICES, required=False, allow_null=True)
    address = serializers.CharField(max_length=200, required=False, allow_blank=True)
    total_area_ha = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def validate(self, data):
        department = data.get('department')
        city = data.get('city')
        if department and city:
            valid_cities = DEPARTMENT_CITY_MAP.get(department, [])
            if city not in valid_cities:
                raise serializers.ValidationError({
                    'city': 'La ciudad no pertenece al departamento seleccionado.'
                })
        return data

    def validate_total_area_ha(self, value):
        if value <= 0:
             raise serializers.ValidationError("El área total debe ser mayor a cero.")
        return value    


class FarmResponseSerializer(serializers.ModelSerializer):
    manager_id = serializers.IntegerField(source='manager.id', allow_null=True)
    manager_name = serializers.CharField(source='manager.user.name', allow_null=True)

    class Meta:
        model = Farm
        fields = [
            'id', 'name', 'department', 'city', 'address',
            'total_area_ha', 'created_at', 'manager_id', 'manager_name'
        ]


class UpdateFarmSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    manager_id = serializers.IntegerField(required=False)
    department = serializers.ChoiceField(choices=DEPARTMENT_CHOICES, required=False, allow_null=True)
    city = serializers.ChoiceField(choices=CITY_CHOICES, required=False, allow_null=True)
    address = serializers.CharField(max_length=200, required=False, allow_blank=True)
    total_area_ha = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def validate(self, data):
        department = data.get('department')
        city = data.get('city')
        if department and city:
            valid_cities = DEPARTMENT_CITY_MAP.get(department, [])
            if city not in valid_cities:
                raise serializers.ValidationError({
                    'city': 'La ciudad no pertenece al departamento seleccionado.'
                })
        return data
    
    def validate_total_area_ha(self, value):
        if value <= 0:
             raise serializers.ValidationError("El área total debe ser mayor a cero.")
        return value    
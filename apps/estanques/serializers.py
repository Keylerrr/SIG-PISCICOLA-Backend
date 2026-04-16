from rest_framework import serializers
from .models import Estanque


class EstanqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estanque
        fields = ['granja_id', 'codigo', 'nombre', 'tipo', 'estado', 'capacidad', 'descripcion']
        extra_kwargs = {
            'tipo': {'required': False},
            'estado': {'required': False},
            'descripcion': {'required': False},
        }

    def validate_codigo(self, value):
        granja_id = self.initial_data.get('granja_id')
        if granja_id and Estanque.objects.filter(granja_id=granja_id, codigo=value).exists():
            raise serializers.ValidationError("Un estanque con este código ya existe en la granja.")
        return value

    def validate_capacidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La capacidad debe ser mayor a 0.")
        return value


class EstanqueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estanque
        fields = ['nombre', 'tipo', 'estado', 'capacidad', 'descripcion', 'activo_interruptor']
        extra_kwargs = {
            'nombre': {'required': False},
            'tipo': {'required': False},
            'estado': {'required': False},
            'capacidad': {'required': False},
            'descripcion': {'required': False},
            'activo_interruptor': {'required': False},
        }

    def validate_capacidad(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("La capacidad debe ser mayor a 0.")
        return value


class EstanqueResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estanque
        fields = [
            'id', 'granja_id', 'codigo', 'nombre',
            'tipo', 'estado', 'capacidad', 'descripcion', 'activo_interruptor',
            'fecha_creacion', 'fecha_actualizacion'
        ]


class EstanqueToggleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estanque
        fields = ['activo_interruptor']


class EstanqueCambiarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=Estanque.ESTADO_CHOICES)

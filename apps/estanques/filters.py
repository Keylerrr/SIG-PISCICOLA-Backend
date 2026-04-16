import django_filters
from .models import Estanque


class EstanqueFilter(django_filters.FilterSet):
    estado = django_filters.ChoiceFilter(choices=Estanque.ESTADO_CHOICES)
    tipo = django_filters.ChoiceFilter(choices=Estanque.TIPO_CHOICES)
    granja = django_filters.NumberFilter(field_name='granja_id')
    activo_interruptor = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Estanque
        fields = ['estado', 'tipo', 'granja', 'activo_interruptor']

    def filter_search(self, queryset, name, value):
        """Búsqueda case-insensitive en código y nombre"""
        return queryset.filter(
            models.Q(codigo__icontains=value) | models.Q(nombre__icontains=value)
        )


# Importar models para el filter_search
from django.db import models

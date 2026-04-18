import django_filters
from django.db import models
from .models import Pond


class PondFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Pond.STATUS_CHOICES)
    # type = django_filters.ChoiceFilter(choices=Pond.TYPE_CHOICES)
    farm = django_filters.NumberFilter(field_name='farm_id')
    is_active = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Pond
        fields = ['status', 'farm', 'is_active']

    def filter_search(self, queryset, name, value):
        """Case-insensitive search in code and name"""
        return queryset.filter(
            models.Q(code__icontains=value) | models.Q(name__icontains=value)
        )

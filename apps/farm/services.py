# apps/farm/services.py
from django.utils import timezone
from .models import Farm

def create_farm(data: dict, manager=None ) -> Farm:
    return Farm.objects.create(
        name=data['name'],
        manager = manager,
        nit=data.get('nit'),
        owner=data.get('owner'),
        department=data.get('department'),
        municipality=data.get('municipality'),
        village=data.get('village'),
        coordinates=data.get('coordinates'),
        total_area_ha=data.get('total_area_ha'),
        description=data.get('description'),
    )

def get_all_farms():
    return Farm.objects.select_related('manager', 'manager__user').all()

def get_farms_by_manager(manager):
    return Farm.objects.filter(manager=manager)
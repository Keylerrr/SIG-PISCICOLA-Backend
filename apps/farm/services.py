from django.utils import timezone
from .models import Farm

def create_farm(data: dict, manager=None ) -> Farm:
    return Farm.objects.create(
        name=data['name'],
        manager=manager,
        department=data.get('department'),
        city=data.get('city'),
        address=data.get('address'),
        total_area_ha=data.get('total_area_ha'),
    )

def get_all_farms():
    return Farm.objects.select_related('manager', 'manager__user').all()

def get_farms_by_manager(manager):
    return Farm.objects.filter(manager=manager)

def update_farm(farm, data: dict):
    for field, value in data.items():
        setattr(farm, field, value)
    farm.updated_at = timezone.now()
    farm.save()
    return farm

def delete_farm(farm):
    farm.delete()
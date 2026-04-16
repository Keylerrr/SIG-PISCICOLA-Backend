from django.db import models
from django.utils import timezone

# Create your models here.

class Farm(models.Model):
    name = models.CharField(max_length=200)
    nit = models.CharField(max_length=50, blank=True, null=True)
    owner = models.CharField(max_length=200, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    municipality = models.CharField(max_length=100, blank=True, null=True)
    village = models.CharField(max_length=100, blank=True, null=True)
    coordinates = models.CharField(max_length=100, blank=True, null=True)
    total_area_ha = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    manager = models.ForeignKey("user.Manager", on_delete=models.SET_NULL, null=True, blank=True, related_name="farms")
    # deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "farm"

    def __str__(self):
        return self.name

    # def soft_delete(self):
    #     self.deleted_at = timezone.now()
    #     self.save(update_fields=["deleted_at"])
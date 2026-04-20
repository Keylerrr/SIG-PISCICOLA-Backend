from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from apps.farm.models import Farm


class Pond(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('in_use', 'In Use'),
        ('cleaning', 'Cleaning'),
        ('inactive', 'Inactive'),
    ]

    id = models.AutoField(primary_key=True)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="ponds")
    code = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    capacity = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    area = models.FloatField(validators=[MinValueValidator(0.01)], help_text="Area in m²", default=0.01)
    volume = models.FloatField(validators=[MinValueValidator(0.01)], help_text="Volume in m³", default=0.01)
    depth = models.FloatField(validators=[MinValueValidator(0.01)], help_text="Depth in m", default=0.01)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "pond"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['farm', 'code'], name='unique_code_per_farm')
        ]

    def __str__(self):
        return f"{self.code} - {self.name} (Farm: {self.farm.name})"

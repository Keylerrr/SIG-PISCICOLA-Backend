# models.py

from django.conf import settings
from django.db import models


class Harvest(models.Model):
    class Type(models.TextChoices):
        TOTAL = "Total", "Total"
        PARTIAL = "Partial", "Parcial"

    farm = models.ForeignKey(
        "farms.Farm",
        on_delete=models.CASCADE,
        related_name="harvests",
    )
    cycle = models.ForeignKey(
        "cycle.Cycle",
        on_delete=models.PROTECT,
        related_name="harvests",
    )
    date = models.DateField()
    total_fish_count = models.PositiveIntegerField()
    total_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    observations = models.TextField(blank=True)
    type = models.CharField(max_length=10, choices=Type.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="harvests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "harvest"
        ordering = ["-date"]

    def __str__(self):
        return f"Harvest [{self.type}] - {self.cycle} ({self.date})"


class HarvestClassification(models.Model):
    class SizeCategory(models.TextChoices):
        SMALL = "Small", "Pequeño"
        MEDIUM = "Medium", "Mediano"
        LARGE = "Large", "Grande"
        EXTRA_LARGE = "Extra Large", "Extra Grande"

    farm = models.ForeignKey(
        "farms.Farm",
        on_delete=models.CASCADE,
        related_name="harvest_classifications",
    )
    harvest = models.ForeignKey(
        Harvest,
        on_delete=models.PROTECT,
        related_name="classifications",
    )
    size_category = models.CharField(
        max_length=15,
        choices=SizeCategory.choices,
    )
    fish_count = models.PositiveIntegerField()
    total_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    reference_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    observations = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="harvest_classifications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "harvest_classification"
        constraints = [
            models.UniqueConstraint(
                fields=["harvest", "size_category"],
                name="uq_harvest_size_category",
            )
        ]

    def __str__(self):
        return f"{self.size_category} - {self.harvest}"

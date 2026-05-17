from django.db import models
from django.utils import timezone


class FishEvaluated(models.Model):
    """
    Representa la evaluación individual de peces en un momento determinado.
    """
    cycle = models.ForeignKey(
        "cycle.Cycle",
        on_delete=models.CASCADE,
        related_name="fish_evaluations",
    )
    pond = models.ForeignKey(
        "ponds.Pond",
        on_delete=models.CASCADE,
        related_name="fish_evaluations",
    )
    evaluation_date = models.DateField()
    sampled_quantity = models.PositiveIntegerField()
    min_weight_g = models.FloatField()
    avg_weight_g = models.FloatField()
    max_weight_g = models.FloatField()
    mortality_quantity = models.PositiveIntegerField(default=0)
    observations = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "fish_evaluated"
        ordering = ["-evaluation_date"]
        unique_together = ("cycle", "evaluation_date", "pond")
        verbose_name = "Fish Evaluation"
        verbose_name_plural = "Fish Evaluations"

    def __str__(self):
        return f"Evaluation {self.id} - Cycle {self.cycle.name} - {self.evaluation_date}"


class DailyStat(models.Model):
    """
    Estadística diaria flexible, puede contener cualquier registro del día.
    """
    cycle = models.ForeignKey(
        "cycle.Cycle",
        on_delete=models.CASCADE,
        related_name="daily_stats",
    )
    pond = models.ForeignKey(
        "ponds.Pond",
        on_delete=models.CASCADE,
        related_name="daily_stats",
    )
    stat_date = models.DateField()
    name = models.CharField(max_length=150)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "daily_stat"
        ordering = ["-stat_date", "-created_at"]
        verbose_name = "Daily Stat"
        verbose_name_plural = "Daily Stats"

    def __str__(self):
        return f"Daily Stat {self.id} - {self.stat_date}: {self.name}"


class ProductUsageLog(models.Model):
    """
    Registro de uso de productos (alimento u otros).
    """
    UNIT_CHOICES = [
        ("kg", "Kilogramos"),
        ("l", "Litros"),
        ("unit", "Unidades"),
    ]

    daily_stat = models.ForeignKey(
        DailyStat,
        on_delete=models.CASCADE,
        related_name="product_usages",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
    )
    quantity_used = models.FloatField()
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    batch = models.ForeignKey(
        "batch.Batch",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_usage_log"
        ordering = ["-created_at"]
        verbose_name = "Product Usage Log"
        verbose_name_plural = "Product Usage Logs"

    def __str__(self):
        return f"Usage {self.id} - {self.product.name} x{self.quantity_used}{self.unit}"


class ControlStat(models.Model):
    """
    Estadística de control cada ~15 días. Datos calculados automáticamente a partir de FishEvaluated.
    """
    cycle = models.ForeignKey(
        "cycle.Cycle",
        on_delete=models.CASCADE,
        related_name="control_stats",
    )
    pond = models.ForeignKey(
        "ponds.Pond",
        on_delete=models.CASCADE,
        related_name="control_stats",
    )
    control_date = models.DateField()
    sampled_quantity = models.PositiveIntegerField()
    live_quantity = models.PositiveIntegerField()
    min_weight_g = models.FloatField()
    avg_weight_g = models.FloatField()
    max_weight_g = models.FloatField()
    mortality_percentage = models.FloatField()
    biomass_kg = models.FloatField()
    fca = models.FloatField(null=True, blank=True)
    biomass_gain_kg = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "control_stat"
        ordering = ["-control_date"]
        unique_together = ("cycle", "pond", "control_date")
        verbose_name = "Control Stat"
        verbose_name_plural = "Control Stats"

    def __str__(self):
        return f"Control {self.id} - Cycle {self.cycle.name} - {self.control_date}"


__all__ = [
    "FishEvaluated",
    "DailyStat",
    "ProductUsageLog",
    "ControlStat",
]

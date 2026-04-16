from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator


class Estanque(models.Model):
    TIPO_CHOICES = [
        ('estanque', 'Estanque'),
        ('jaula', 'Jaula'),
    ]

    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('en_uso', 'En Uso'),
        ('en_limpieza', 'En Limpieza'),
        ('inactivo', 'Inactivo'),
    ]

    id = models.AutoField(primary_key=True)
    granja_id = models.IntegerField()  # Referencia a Granja (manejada por otro servicio)
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='estanque')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    capacidad = models.IntegerField(validators=[MinValueValidator(1)])
    descripcion = models.TextField(blank=True, null=True)
    activo_interruptor = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "estanque"
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(fields=['granja_id', 'codigo'], name='unique_codigo_por_granja')
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre} (Granja: {self.granja_id})"

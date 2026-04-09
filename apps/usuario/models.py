import uuid
from django.db import models
from django.utils import timezone

class Usuario(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=200, unique=True)
    password_hash = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    token_reset = models.CharField(max_length=255, blank=True, null=True)
    token_reset_expiry = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "usuario"

    def __str__(self):
        return f"{self.name} ({self.email})"

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None


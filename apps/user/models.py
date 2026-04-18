import uuid

from django.db import models
from django.utils import timezone


class User(models.Model):
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

    class Meta:
        db_table = "user"

    def __str__(self):
        return f"{self.name} ({self.email})"

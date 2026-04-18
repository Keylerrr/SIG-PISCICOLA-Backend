from django.db import models
from django.utils import timezone


class User(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        WORKER = "worker", "Worker"

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=200, unique=True)
    password_hash = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    password_reset_token = models.TextField(null=True)
    password_reset_expiry = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user"

    def __str__(self):
        return f"{self.name} ({self.email}) [{self.role}]"


class Manager(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="manager_profile"
    )

    class Meta:
        db_table = "manager"

    def __str__(self):
        return f"Manager: {self.user.name}"


class Worker(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="worker_profile"
    )
    manager = models.ForeignKey(
        Manager,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workers",
    )

    class Meta:
        db_table = "worker"

    def __str__(self):
        return f"Worker: {self.user.name}"


class BlacklistedToken(models.Model):
    token = models.TextField(unique=True)
    blacklisted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "blacklisted_token"

    def __str__(self):
        return f"Blacklisted at {self.blacklisted_at}"

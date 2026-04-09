from rest_framework import serializers
from .models import Usuario


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Usuario
        fields = ["name", "lastname", "email", "password", "phone"]

    def validate_email(self, value):
        if Usuario.objects.filter(email=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UpdateUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["name", "lastname", "phone"]
        extra_kwargs = {
            "name": {"required": False},
            "lastname": {"required": False},
            "phone": {"required": False},
        }


class UsuarioResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "name", "lastname", "email", "phone", "created_at", "updated_at"]


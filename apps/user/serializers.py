from rest_framework import serializers

from .models import Manager, User, Worker


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class CreateManagerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    lastname = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")
        return value


class CreateWorkerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    lastname = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")
        return value


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "lastname", "phone"]
        extra_kwargs = {f: {"required": False} for f in fields}


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)


class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmPasswordResetSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "lastname", "email", "phone", "role", "created_at"]


class WorkerResponseSerializer(serializers.ModelSerializer):
    user = UserResponseSerializer()
    manager_id = serializers.IntegerField(source="manager.id", allow_null=True)
    manager_name = serializers.CharField(source="manager.user.name", allow_null=True)

    class Meta:
        model = Worker
        fields = ["id", "user", "manager_id", "manager_name"]

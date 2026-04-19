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
    worker_id = serializers.IntegerField(source="id")
    user_id = serializers.IntegerField(source="user.id")
    name = serializers.CharField(source="user.name")
    lastname = serializers.CharField(source="user.lastname")
    email = serializers.EmailField(source="user.email")
    phone = serializers.CharField(source="user.phone")
    role = serializers.CharField(source="user.role")
    created_at = serializers.DateTimeField(source="user.created_at")
    manager_id = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Worker
        fields = [
            "worker_id",
            "user_id",
            "name",
            "lastname",
            "email",
            "phone",
            "role",
            "manager_id",
            "manager_name",
            "created_at",
        ]

    def get_manager_id(self, obj):
        return obj.manager.id if obj.manager else None

    def get_manager_name(self, obj):
        return obj.manager.user.name if obj.manager else None


class ManagerResponseSerializer(serializers.ModelSerializer):
    manager_id = serializers.IntegerField(source="id")
    user_id = serializers.IntegerField(source="user.id")
    name = serializers.CharField(source="user.name")
    lastname = serializers.CharField(source="user.lastname")
    email = serializers.EmailField(source="user.email")
    phone = serializers.CharField(source="user.phone")
    role = serializers.CharField(source="user.role")
    created_at = serializers.DateTimeField(source="user.created_at")

    class Meta:
        model = Manager
        fields = [
            "manager_id",
            "user_id",
            "name",
            "lastname",
            "email",
            "phone",
            "role",
            "created_at",
        ]

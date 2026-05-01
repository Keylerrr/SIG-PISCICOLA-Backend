# serializers.py
from django.apps import apps
from rest_framework import serializers

from .enums import FarmPermission
from .models import City, Department, Farm, FarmRole, UserFarm


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        User = apps.get_model("accounts", "User")
        model = User
        fields = ["id", "name", "lastname", "cc", "email", "phone"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class CitySerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = City
        fields = ["id", "name", "department"]


class PermissionsField(serializers.Field):
    def to_representation(self, value: int) -> list[str]:
        return [
            p.name for p in FarmPermission if p != FarmPermission.ALL and (value & p)
        ]

    def to_internal_value(self, data) -> int:
        if not isinstance(data, list):
            raise serializers.ValidationError("Se esperaba una lista de permisos.")

        result = 0
        valid_names = {p.name for p in FarmPermission if p != FarmPermission.ALL}

        for name in data:
            if name not in valid_names:
                raise serializers.ValidationError(
                    f"Permiso inválido: '{name}'. Opciones: {sorted(valid_names)}"
                )
            result |= FarmPermission[name]

        return int(result)


class FarmSerializer(serializers.ModelSerializer):
    productor_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Farm
        fields = [
            "id",
            "name",
            "department",
            "city",
            "address",
            "total_area_ha",
            "water_source",
            "status",
            "productor_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, data):
        user = self.context["request"].user

        if self.instance is not None or user.role.name != "Admin":
            return data

        if "productor_id" not in data:
            raise serializers.ValidationError(
                {"user_id": "Un Admin debe asignar un Productor al crear una granja."}
            )

        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        try:
            productor = user_model.objects.get(pk=data["productor_id"], role__name="Productor")
        except user_model.DoesNotExist:
            raise serializers.ValidationError(
                {"productor_id": "No existe un Productor con ese ID."}
            )
        data["_productor"] = productor

        return data

    def validate_name(self, value):
        user = self.context["request"].user
        qs = Farm.objects.filter(
            user_farms__user=user,
            user_farms__is_owner=True,
            name__iexact=value,
            deleted_at__isnull=True,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Ya eres propietario de una finca con este nombre."
            )
        return value


class FarmRoleSerializer(serializers.ModelSerializer):
    permissions = PermissionsField(required=False, default=0)

    class Meta:
        model = FarmRole
        fields = ["id", "farm", "name", "permissions"]
        read_only_fields = ["farm"]

    def validate(self, attrs):
        farm = getattr(self.instance, "farm", None) or attrs.get("farm")

        qs = FarmRole.objects.filter(
            farm=farm,
            name__iexact=attrs.get("name", getattr(self.instance, "name", "")),
            deleted_at__isnull=True,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                {"name": "Ya existe un rol con este nombre en la finca."}
            )
        return attrs


class UserFarmSerializer(serializers.ModelSerializer):
    user_model = apps.get_model("accounts", "User")
    permissions = PermissionsField(required=False, default=0)
    user = UserSummarySerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=user_model.objects.all(),
        source="user",
        write_only=True,
    )

    class Meta:
        model = UserFarm
        fields = [
            "user",
            "user_id",
            "farm",
            "farm_role",
            "permissions",
            "status",
            "is_owner",
        ]

    def validate(self, attrs):
        farm = attrs.get("farm", getattr(self.instance, "farm", None))
        farm_role = attrs.get("farm_role", getattr(self.instance, "farm_role", None))
        user = attrs.get("user", getattr(self.instance, "user", None))
        is_owner = attrs.get("is_owner", getattr(self.instance, "is_owner", False))
        farm_name = farm.name if farm else ""

        if farm_role and farm_role.farm_id != farm.id:
            raise serializers.ValidationError(
                {"farm_role": "El rol no pertenece a esta finca."}
            )
        if is_owner:
            qs = Farm.objects.filter(
                user_farms__user=user,
                user_farms__is_owner=True,
                name__iexact=farm_name,
                deleted_at__isnull=True,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.farm_id)

            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "farm": "Este usuario ya es propietario de una finca con ese nombre."
                    }
                )

        return attrs

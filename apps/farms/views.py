# views.py
from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import (AdminOr, CompletionPermission, IsAdmin,
                                       IsAdminOrValid, IsProductor)

from .enums import FarmPermission
from .models import City, Department, Farm, FarmRole, UserFarm
from .permissions import (CanDeleteFarm, CanEditFarm, CanManageRoles,
                          CanManageUsers, CanViewFarm, IsFarmOwner)
from .serializers import (CitySerializer, DepartmentSerializer,
                          FarmRoleSerializer, FarmSerializer,
                          UserFarmSerializer)
from .utils import assign_operario_permissions, assign_role_to_operario


class DepartmentListView(generics.ListAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]
    queryset = Department.objects.order_by("name")


class CityListView(generics.ListAPIView):
    serializer_class = CitySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = City.objects.select_related("department").order_by("name")
        department_id = self.request.query_params.get("department_id")
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs


class FarmViewSet(viewsets.ModelViewSet):
    serializer_class = FarmSerializer

    def get_permissions(self):
        if self.action == "create":
            perms = [AdminOr(IsProductor)]
        elif self.action in ("update", "partial_update"):
            perms = [AdminOr(CanEditFarm)]
        elif self.action == "destroy":
            perms = [AdminOr(CanDeleteFarm)]
        else:
            perms = [AdminOr(CanViewFarm)]
        return [p() for p in perms]

    def get_queryset(self):
        user = self.request.user
        if user.role.name == "Admin":
            qs = Farm.objects.filter(deleted_at__isnull=True).distinct().order_by("-id")
            productor_id = self.request.query_params.get("productor_id")
            if productor_id:
                qs = qs.filter(
                    user_farms__user_id=productor_id,
                    user_farms__is_owner=True,
                )
            return qs

        return (
            Farm.objects.filter(
                user_farms__user=user,
                deleted_at__isnull=True,
            )
            .distinct()
            .order_by("-id")
        )

    def perform_create(self, serializer):
        validated = serializer.validated_data
        productor = validated.pop("_productor", None)

        farm = serializer.save()

        owner = productor if productor else self.request.user

        UserFarm.objects.create(
            user=owner,
            farm=farm,
            permissions=int(FarmPermission.ALL),
            is_owner=True,
            status=UserFarm.Status.ACTIVE,
        )

    def destroy(self, request, *args, **kwargs):
        farm = self.get_object()
        farm.deleted_at = timezone.now()
        farm.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=["get"], url_path="productor/(?P<productor_id>[^/.]+)"
    )
    def by_productor(self, request, productor_id=None):
        if request.user.role.name != "Admin":
            return Response(
                {"detail": "No tienes permiso para realizar esta acción."},
                status=status.HTTP_403_FORBIDDEN,
            )
        farms = (
            Farm.objects.filter(
                user_farms__user_id=productor_id,
                user_farms__is_owner=True,
                deleted_at__isnull=True,
            )
            .distinct()
            .order_by("-id")
        )

        serializer = self.get_serializer(farms, many=True)
        return Response(serializer.data)


class FarmRoleViewSet(viewsets.ModelViewSet):
    serializer_class = FarmRoleSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            perms = [AdminOr(IsFarmOwner)]
        else:
            perms = [AdminOr(CanViewFarm)]
        return [p() for p in perms]

    def get_queryset(self):
        return FarmRole.objects.filter(
            farm_id=self.kwargs["farm_pk"],
            farm__user_farms__user=self.request.user,
            farm__deleted_at__isnull=True,
            deleted_at__isnull=True,
        ).order_by("name")

    def perform_create(self, serializer):
        serializer.save(farm_id=self.kwargs["farm_pk"])

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        role.deleted_at = timezone.now()
        role.save(update_fields=["deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserFarmViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserFarmSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            perms = [AdminOr(CanManageUsers)]
        else:
            perms = [AdminOr(CanViewFarm)]
        return [p() for p in perms]

    def get_queryset(self):
        return (
            UserFarm.objects.filter(
                farm_id=self.kwargs["farm_pk"],
                farm__user_farms__user=self.request.user,
                farm__deleted_at__isnull=True,
            )
            .select_related("user", "farm_role")
            .order_by("user__id")
        )

    def update(self, request, *args, **kwargs):
        member = self.get_object()

        if member.user.role.name == "Operario":
            farm_role_id = request.data.get("farm_role")
            if farm_role_id:
                try:
                    role = FarmRole.objects.get(
                        pk=farm_role_id,
                        farm_id=member.farm_id,
                        deleted_at__isnull=True,
                    )
                except FarmRole.DoesNotExist:
                    return Response(
                        {"farm_role": "Rol no encontrado en esta finca."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                try:
                    assign_role_to_operario(member, role)
                except ValueError as e:
                    return Response(
                        {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
                    )

            if "permissions" in request.data:
                try:
                    assign_operario_permissions(member, request.data["permissions"])
                except ValueError as e:
                    return Response(
                        {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
                    )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        member = self.get_object()
        if member.is_owner:
            return Response(
                {"detail": "No se puede eliminar al propietario de la finca."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

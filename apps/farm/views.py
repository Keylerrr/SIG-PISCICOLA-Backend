from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.user.permissions import IsAdminOrManager
from apps.user.models import Manager, User
from . import services
from .serializers import CreateFarmSerializer, FarmResponseSerializer, UpdateFarmSerializer
from .models import Farm


class FarmListCreateView(APIView):
    permission_classes = [IsAdminOrManager]  

    
    def get(self, request):
        role = request.user_payload.get("role")
        user_id = request.user_payload.get("user_id")

        if role == 'admin':
            farms = services.get_all_farms()
        else:
            user = User.objects.get(id=user_id)
            manager = Manager.objects.get(user=user)
            farms = services.get_farms_by_manager(manager)

        return Response(FarmResponseSerializer(farms, many=True).data)

    def post(self, request):
        serializer = CreateFarmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        role = request.user_payload.get("role")
        user_id = request.user_payload.get("user_id")

        if role == 'manager':
            # El manager crea la granja para sí mismo
            user = User.objects.get(id=user_id)
            manager = Manager.objects.get(user=user)
        elif role == 'admin':
            # El admin debe especificar el manager_id
            manager_id = serializer.validated_data.get('manager_id')
            if not manager_id:
                return Response(
                    {"error": "El admin debe especificar un manager_id."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                manager = Manager.objects.get(id=manager_id)
            except Manager.DoesNotExist:
                return Response(
                    {"error": "Manager no encontrado."},
                    status=status.HTTP_404_NOT_FOUND
                )
        farm = services.create_farm(serializer.validated_data, manager=manager)
        return Response(
            {"message": "Granja creada exitosamente.", "farm": FarmResponseSerializer(farm).data},
            status=status.HTTP_201_CREATED,
        )

class FarmDetailView(APIView):
    permission_classes = [IsAdminOrManager]

    def _get_farm(self, farm_id):
        try:
            return Farm.objects.get(id=farm_id)
        except Farm.DoesNotExist:
            return None

    def patch(self, request, farm_id):
        farm = self._get_farm(farm_id)
        if not farm:
            return Response({"error": "Granja no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        role = request.user_payload.get("role")
        user_id = request.user_payload.get("user_id")

        if role == 'manager':
            user = User.objects.get(id=user_id)
            manager = Manager.objects.get(user=user)
            if farm.manager != manager:
                return Response({"error": "No tienes acceso a esta granja."}, status=status.HTTP_403_FORBIDDEN)

        serializer = UpdateFarmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        farm = services.update_farm(farm, serializer.validated_data)
        return Response({"message": "Granja actualizada.", "farm": FarmResponseSerializer(farm).data})

    def delete(self, request, farm_id):
        farm = self._get_farm(farm_id)
        if not farm:
            return Response({"error": "Granja no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        role = request.user_payload.get("role")
        user_id = request.user_payload.get("user_id")

        if role == 'manager':
            user = User.objects.get(id=user_id)
            manager = Manager.objects.get(user=user)
            if farm.manager != manager:
                return Response({"error": "No tienes acceso a esta granja."}, status=status.HTTP_403_FORBIDDEN)

        services.delete_farm(farm)
        return Response({"message": "Granja eliminada."}, status=status.HTTP_200_OK)
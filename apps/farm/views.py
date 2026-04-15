from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.user.permissions import IsAdminOrManager
from apps.user.models import Manager, User
from . import services
from .serializers import CreateFarmSerializer, FarmResponseSerializer


class FarmListCreateView(APIView):
    permission_classes = [IsAdminOrManager]  
    
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
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.user.permissions import IsAdmin
from . import services
from .serializers import CreateFarmSerializer, FarmResponseSerializer


class FarmListCreateView(APIView):
    permission_classes = [IsAdmin]  
    def post(self, request):
        serializer = CreateFarmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        farm = services.create_farm(serializer.validated_data)
        return Response(
            {
                "message": "Granja creada exitosamente.",
                "farm": FarmResponseSerializer(farm).data,
            },
            status=status.HTTP_201_CREATED,
        )
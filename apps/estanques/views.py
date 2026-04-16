from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Estanque
from .serializers import (
    EstanqueSerializer,
    EstanqueUpdateSerializer,
    EstanqueResponseSerializer,
    EstanqueToggleSerializer,
    EstanqueCambiarEstadoSerializer,
)
from .filters import EstanqueFilter


class EstanqueListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Listar estanques del usuario con filtros y búsqueda"""
        user_id = request.user_payload.get('user_id')

        # Obtener todos los estanques (no hay filtro por usuario en esta etapa)
        # La validación de autorización puede hacerse en el frontend o si hay relación usuario-granja
        estanques = Estanque.objects.all()

        # Aplicar filtros
        filterset = EstanqueFilter(request.GET, queryset=estanques)
        estanques = filterset.qs

        serializer = EstanqueResponseSerializer(estanques, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Crear nuevo estanque"""
        user_id = request.user_payload.get('user_id')

        # Validar que granja_id está presente
        granja_id = request.data.get('granja_id')
        if not granja_id:
            return Response(
                {'error': 'granja_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EstanqueSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        estanque = Estanque.objects.create(
            granja_id=granja_id,
            codigo=serializer.validated_data['codigo'],
            nombre=serializer.validated_data['nombre'],
            tipo=serializer.validated_data.get('tipo', 'estanque'),
            estado=serializer.validated_data.get('estado', 'activo'),
            capacidad=serializer.validated_data['capacidad'],
            descripcion=serializer.validated_data.get('descripcion'),
            activo_interruptor=True,
            fecha_creacion=timezone.now(),
            fecha_actualizacion=timezone.now(),
        )

        return Response(
            EstanqueResponseSerializer(estanque).data,
            status=status.HTTP_201_CREATED,
        )


class EstanqueDetailUpdateDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def get_estanque(self, estanque_id):
        """Obtener estanque por ID"""
        try:
            estanque = Estanque.objects.get(id=estanque_id)
            return estanque
        except Estanque.DoesNotExist:
            return None

    def get(self, request, estanque_id):
        """Obtener detalle de estanque"""
        estanque = self.get_estanque(estanque_id)

        if not estanque:
            return Response(
                {'error': 'Estanque no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            EstanqueResponseSerializer(estanque).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, estanque_id):
        """Actualizar estanque"""
        estanque = self.get_estanque(estanque_id)

        if not estanque:
            return Response(
                {'error': 'Estanque no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EstanqueUpdateSerializer(data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        for field, value in serializer.validated_data.items():
            setattr(estanque, field, value)

        estanque.fecha_actualizacion = timezone.now()
        estanque.save()

        return Response(
            EstanqueResponseSerializer(estanque).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, estanque_id):
        """Eliminar estanque (solo si está inactivo)"""
        estanque = self.get_estanque(estanque_id)

        if not estanque:
            return Response(
                {'error': 'Estanque no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if estanque.estado != 'inactivo':
            return Response(
                {'error': 'Solo se pueden eliminar estanques en estado inactivo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        estanque.delete()
        return Response(
            {'message': 'Estanque eliminado exitosamente.'},
            status=status.HTTP_200_OK,
        )


class EstanqueToggleStateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, estanque_id):
        """Toggle del campo activo_interruptor (activar/desactivar rápidamente)"""
        try:
            estanque = Estanque.objects.get(id=estanque_id)
        except Estanque.DoesNotExist:
            return Response(
                {'error': 'Estanque no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Toggle del interruptor
        estanque.activo_interruptor = not estanque.activo_interruptor
        estanque.fecha_actualizacion = timezone.now()
        estanque.save(update_fields=['activo_interruptor', 'fecha_actualizacion'])

        return Response(
            {
                'message': 'Estado del interruptor actualizado.',
                'activo_interruptor': estanque.activo_interruptor,
                'estanque': EstanqueResponseSerializer(estanque).data,
            },
            status=status.HTTP_200_OK,
        )


class EstanqueCambiarEstadoView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, estanque_id):
        """Cambiar estado operativo del estanque"""
        try:
            estanque = Estanque.objects.get(id=estanque_id)
        except Estanque.DoesNotExist:
            return Response(
                {'error': 'Estanque no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EstanqueCambiarEstadoSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        nuevo_estado = serializer.validated_data['estado']
        estanque.estado = nuevo_estado
        estanque.fecha_actualizacion = timezone.now()
        estanque.save(update_fields=['estado', 'fecha_actualizacion'])

        return Response(
            {
                'message': f'Estado del estanque cambiado a {nuevo_estado}.',
                'estanque': EstanqueResponseSerializer(estanque).data,
            },
            status=status.HTTP_200_OK,
        )

from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Pond
from .serializers import (
    PondSerializer,
    PondUpdateSerializer,
    PondResponseSerializer,
    PondToggleSerializer,
    PondChangeStatusSerializer,
)
from .filters import PondFilter


class PondListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List ponds with filters and search"""
        user_id = request.user_payload.get('user_id')

        # Get all ponds (no user filter at this stage)
        # Authorization validation can be done in frontend or if there's user-farm relation
        ponds = Pond.objects.all()

        # Apply filters
        filterset = PondFilter(request.GET, queryset=ponds)
        ponds = filterset.qs

        serializer = PondResponseSerializer(ponds, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create new pond"""
        user_id = request.user_payload.get('user_id')

        # Validate that farm is present
        farm = request.data.get('farm')
        if not farm:
            return Response(
                {'error': 'farm is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PondSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        pond = Pond.objects.create(
            farm_id=farm,
            code=serializer.validated_data['code'],
            name=serializer.validated_data['name'],
            status=serializer.validated_data.get('status', 'active'),
            capacity=serializer.validated_data['capacity'],
            area=serializer.validated_data['area'],
            volume=serializer.validated_data['volume'],
            depth=serializer.validated_data['depth'],
            description=serializer.validated_data.get('description'),
            is_active=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        return Response(
            PondResponseSerializer(pond).data,
            status=status.HTTP_201_CREATED,
        )


class PondDetailUpdateDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def get_pond(self, pond_id):
        """Get pond by ID"""
        try:
            pond = Pond.objects.get(id=pond_id)
            return pond
        except Pond.DoesNotExist:
            return None

    def get(self, request, pond_id):
        """Get pond details"""
        pond = self.get_pond(pond_id)

        if not pond:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            PondResponseSerializer(pond).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pond_id):
        """Update pond"""
        pond = self.get_pond(pond_id)

        if not pond:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PondUpdateSerializer(data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        for field, value in serializer.validated_data.items():
            setattr(pond, field, value)

        pond.updated_at = timezone.now()
        pond.save()

        return Response(
            PondResponseSerializer(pond).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pond_id):
        """Delete pond (only if inactive)"""
        pond = self.get_pond(pond_id)

        if not pond:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if pond.status != 'inactive':
            return Response(
                {'error': 'Only ponds in inactive status can be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pond.delete()
        return Response(
            {'message': 'Pond deleted successfully.'},
            status=status.HTTP_200_OK,
        )


class PondToggleStateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pond_id):
        """Toggle is_active field (quickly enable/disable)"""
        try:
            pond = Pond.objects.get(id=pond_id)
        except Pond.DoesNotExist:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Toggle is_active
        pond.is_active = not pond.is_active
        pond.updated_at = timezone.now()
        pond.save(update_fields=['is_active', 'updated_at'])

        return Response(
            {
                'message': 'Pond active state updated.',
                'is_active': pond.is_active,
                'pond': PondResponseSerializer(pond).data,
            },
            status=status.HTTP_200_OK,
        )


class PondChangeStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pond_id):
        """Change operational status of pond"""
        try:
            pond = Pond.objects.get(id=pond_id)
        except Pond.DoesNotExist:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PondChangeStatusSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data['status']
        pond.status = new_status
        pond.updated_at = timezone.now()
        pond.save(update_fields=['status', 'updated_at'])

        return Response(
            {
                'message': f'Pond status changed to {new_status}.',
                'pond': PondResponseSerializer(pond).data,
            },
            status=status.HTTP_200_OK,
        )

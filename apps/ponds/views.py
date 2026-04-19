from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.farm.models import Farm

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

    def _get_user_manager(self, user_id):
        """Get manager associated with user"""
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            return user.manager_profile if hasattr(user, 'manager_profile') else None
        except:
            return None

    def _user_owns_farm(self, user_id, farm_id):
        """Check if user (manager) owns the farm"""
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            manager = user.manager_profile if hasattr(user, 'manager_profile') else None
            if not manager:
                return False
            farm = Farm.objects.get(id=farm_id, manager=manager)
            return True
        except Farm.DoesNotExist:
            return False
        except:
            return False

    def get(self, request):
        """List ponds with filters and search - only user's ponds"""
        user_id = request.user_payload.get('user_id')
        
        # Get manager associated with user
        manager = self._get_user_manager(user_id)
        
        if not manager:
            return Response([], status=status.HTTP_200_OK)
        
        # Get ponds only from farms owned by this manager
        ponds = Pond.objects.filter(farm__manager=manager)

        # Apply filters
        filterset = PondFilter(request.GET, queryset=ponds)
        ponds = filterset.qs

        serializer = PondResponseSerializer(ponds, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create new pond - only in user's farms"""
        user_id = request.user_payload.get('user_id')

        # Validate that farm is present
        farm_id = request.data.get('farm')
        if not farm_id:
            return Response(
                {'error': 'farm is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify user owns the farm
        if not self._user_owns_farm(user_id, farm_id):
            return Response(
                {'error': 'You do not have permission to create ponds in this farm.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PondSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        pond = Pond.objects.create(
            farm_id=farm_id,
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

    def _get_user_manager(self, user_id):
        """Get manager associated with user"""
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            return user.manager_profile if hasattr(user, 'manager_profile') else None
        except:
            return None

    def _user_owns_pond(self, user_id, pond_id):
        """Check if user (manager) owns the pond"""
        manager = self._get_user_manager(user_id)
        if not manager:
            return False
        try:
            Pond.objects.get(id=pond_id, farm__manager=manager)
            return True
        except Pond.DoesNotExist:
            return False

    def get_pond(self, pond_id):
        """Get pond by ID"""
        try:
            pond = Pond.objects.get(id=pond_id)
            return pond
        except Pond.DoesNotExist:
            return None

    def get(self, request, pond_id):
        """Get pond details"""
        user_id = request.user_payload.get('user_id')
        pond = self.get_pond(pond_id)

        if not pond:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify user owns the pond
        if not self._user_owns_pond(user_id, pond_id):
            return Response(
                {'error': 'You do not have permission to view this pond.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            PondResponseSerializer(pond).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pond_id):
        """Update pond - only if user owns it"""
        user_id = request.user_payload.get('user_id')
        pond = self.get_pond(pond_id)

        if not pond:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify user owns the pond
        if not self._user_owns_pond(user_id, pond_id):
            return Response(
                {'error': 'You do not have permission to update this pond.'},
                status=status.HTTP_403_FORBIDDEN,
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
        """Delete pond - only if inactive and user owns it"""
        user_id = request.user_payload.get('user_id')
        pond = self.get_pond(pond_id)

        if not pond:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify user owns the pond
        if not self._user_owns_pond(user_id, pond_id):
            return Response(
                {'error': 'You do not have permission to delete this pond.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if pond.is_active:
            return Response(
                {'error': 'Only inactive ponds can be deleted. Please deactivate it first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pond.delete()
        return Response(
            {'message': 'Pond deleted successfully.'},
            status=status.HTTP_200_OK,
        )


class PondToggleStateView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user_manager(self, user_id):
        """Get manager associated with user"""
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            return user.manager_profile if hasattr(user, 'manager_profile') else None
        except:
            return None

    def _user_owns_pond(self, user_id, pond_id):
        """Check if user (manager) owns the pond"""
        manager = self._get_user_manager(user_id)
        if not manager:
            return False
        try:
            Pond.objects.get(id=pond_id, farm__manager=manager)
            return True
        except Pond.DoesNotExist:
            return False

    def patch(self, request, pond_id):
        """Toggle is_active field - only if user owns it"""
        user_id = request.user_payload.get('user_id')
        
        try:
            pond = Pond.objects.get(id=pond_id)
        except Pond.DoesNotExist:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify user owns the pond
        if not self._user_owns_pond(user_id, pond_id):
            return Response(
                {'error': 'You do not have permission to toggle this pond.'},
                status=status.HTTP_403_FORBIDDEN,
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

    def _get_user_manager(self, user_id):
        """Get manager associated with user"""
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            return user.manager_profile if hasattr(user, 'manager_profile') else None
        except:
            return None

    def _user_owns_pond(self, user_id, pond_id):
        """Check if user (manager) owns the pond"""
        manager = self._get_user_manager(user_id)
        if not manager:
            return False
        try:
            Pond.objects.get(id=pond_id, farm__manager=manager)
            return True
        except Pond.DoesNotExist:
            return False

    def patch(self, request, pond_id):
        """Change operational status of pond - only if user owns it"""
        user_id = request.user_payload.get('user_id')
        
        try:
            pond = Pond.objects.get(id=pond_id)
        except Pond.DoesNotExist:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify user owns the pond
        if not self._user_owns_pond(user_id, pond_id):
            return Response(
                {'error': 'You do not have permission to change status on this pond.'},
                status=status.HTTP_403_FORBIDDEN,
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

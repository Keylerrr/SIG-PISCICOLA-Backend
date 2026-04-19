from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.farm.models import Farm
from apps.user.permissions import IsAdmin, IsManager, IsAuthenticated

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
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            return user.manager_profile if hasattr(user, 'manager_profile') else None
        except:
            return None

    def _user_owns_farm(self, user_id, farm_id):
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
        user_id = request.user_payload.get('user_id')
        user_role = request.user_payload.get('role')
        
        if user_role == 'admin':
            ponds = Pond.objects.all()
            
            farm_id = request.query_params.get('farm_id')
            if farm_id:
                ponds = ponds.filter(farm_id=farm_id)
            
            manager_id = request.query_params.get('manager_id')
            if manager_id:
                ponds = ponds.filter(farm__manager_id=manager_id)
        else:
            manager = self._get_user_manager(user_id)
            
            if not manager:
                return Response([], status=status.HTTP_200_OK)
            
            ponds = Pond.objects.filter(farm__manager=manager)
        filterset = PondFilter(request.GET, queryset=ponds)
        ponds = filterset.qs

        serializer = PondResponseSerializer(ponds, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user_id = request.user_payload.get('user_id')
        user_role = request.user_payload.get('role')

        farm_id = request.data.get('farm')
        if not farm_id:
            return Response(
                {'error': 'farm is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_role != 'admin' and not self._user_owns_farm(user_id, farm_id):
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
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            return user.manager_profile if hasattr(user, 'manager_profile') else None
        except:
            return None

    def _user_owns_pond(self, user_id, pond_id):
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            if user.role == 'admin':
                return True
            manager = user.manager_profile if hasattr(user, 'manager_profile') else None
            if not manager:
                return False
            Pond.objects.get(id=pond_id, farm__manager=manager)
            return True
        except Pond.DoesNotExist:
            return False
        except:
            return False

    def get_pond(self, pond_id):
        try:
            pond = Pond.objects.get(id=pond_id)
            return pond
        except Pond.DoesNotExist:
            return None

    def get(self, request, pond_id):
        user_id = request.user_payload.get('user_id')
        pond = self.get_pond(pond_id)

        if not pond:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

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
        user_id = request.user_payload.get('user_id')
        pond = self.get_pond(pond_id)

        if not pond:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

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
        user_id = request.user_payload.get('user_id')
        pond = self.get_pond(pond_id)

        if not pond:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not self._user_owns_pond(user_id, pond_id):
            return Response(
                {'error': 'You do not have permission to delete this pond.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        pond.delete()
        return Response(
            {'message': 'Pond deleted successfully.'},
            status=status.HTTP_200_OK,
        )


class PondListByFarmView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        user_id = request.user_payload.get('user_id')
        user_role = request.user_payload.get('role')
        
        try:
            farm = Farm.objects.get(id=farm_id)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'Farm not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if user_role != 'admin':
            from apps.user.models import User
            try:
                user = User.objects.get(id=user_id)
                manager = user.manager_profile if hasattr(user, 'manager_profile') else None
                if not manager or farm.manager_id != manager.id:
                    return Response(
                        {'error': 'You do not have permission to view this farm\'s ponds.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except:
                return Response(
                    {'error': 'You do not have permission to view this farm\'s ponds.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        
        ponds = Pond.objects.filter(farm_id=farm_id)
        
        filterset = PondFilter(request.GET, queryset=ponds)
        ponds = filterset.qs
        
        serializer = PondResponseSerializer(ponds, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PondChangeStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user_manager(self, user_id):
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            return user.manager_profile if hasattr(user, 'manager_profile') else None
        except:
            return None

    def _user_owns_pond(self, user_id, pond_id):
        from apps.user.models import User
        try:
            user = User.objects.get(id=user_id)
            if user.role == 'admin':
                return True
            manager = user.manager_profile if hasattr(user, 'manager_profile') else None
            if not manager:
                return False
            Pond.objects.get(id=pond_id, farm__manager=manager)
            return True
        except Pond.DoesNotExist:
            return False
        except:
            return False

    def patch(self, request, pond_id):
        user_id = request.user_payload.get('user_id')
        
        try:
            pond = Pond.objects.get(id=pond_id)
        except Pond.DoesNotExist:
            return Response(
                {'error': 'Pond not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )


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

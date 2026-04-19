import jwt
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Manager, User, Worker
from .permissions import IsAdmin, IsAdminOrManager, IsAuthenticated
from .serializers import (ChangePasswordSerializer,
                          ConfirmPasswordResetSerializer,
                          CreateManagerSerializer, CreateWorkerSerializer,
                          LoginSerializer, ManagerResponseSerializer,
                          RequestPasswordResetSerializer, UpdateUserSerializer,
                          UserResponseSerializer, WorkerResponseSerializer)


def _get_tokens_for_user(user: User) -> dict:
    import time

    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "exp": int(time.time()) + 60 * 60 * 24,  # 24h
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return {"access": token}


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = services.login_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            {
                "message": "Login exitoso.",
                "user": UserResponseSerializer(user).data,
                "tokens": _get_tokens_for_user(user),
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.token
        exp = request.user_payload.get("exp")
        services.logout_user(token=token, exp_timestamp=exp)
        return Response({"message": "Sesión cerrada correctamente."})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = request.user_payload.get("user_id")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            services.change_password(
                user=user,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Contraseña actualizada correctamente."})


class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        services.request_password_reset(serializer.validated_data["email"])
        return Response(
            {"message": "Si el correo existe, recibirás las instrucciones."}
        )


class ConfirmPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConfirmPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            services.confirm_password_reset(
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Contraseña restablecida correctamente."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user(self, request):
        user_id = request.user_payload.get("user_id")
        try:
            return User.objects.get(id=user_id), None
        except User.DoesNotExist:
            return None, Response(
                {"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request):
        user, error = self._get_user(request)
        if error:
            return error
        return Response(UserResponseSerializer(user).data)

    def patch(self, request):
        user, error = self._get_user(request)
        if error:
            return error
        serializer = UpdateUserSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = services.update_user(user, serializer.validated_data)
        return Response(
            {
                "message": "Perfil actualizado.",
                "user": UserResponseSerializer(user).data,
            }
        )


class ManagerListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        managers = Manager.objects.select_related("user").all()
        return Response(ManagerResponseSerializer(managers, many=True).data)

    def post(self, request):
        serializer = CreateManagerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        manager = services.create_manager(serializer.validated_data)
        return Response(
            {
                "message": "Manager creado. Se enviaron las credenciales por correo.",
                "user": ManagerResponseSerializer(manager).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ManagerDetailView(APIView):
    permission_classes = [IsAdmin]

    def _get_manager(self, user_id):
        try:
            return Manager.objects.select_related("user").get(user__id=user_id)
        except Manager.DoesNotExist:
            return None

    def get(self, request, user_id):
        manager = self._get_manager(user_id)
        if not manager:
            return Response(
                {"error": "Manager no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(ManagerResponseSerializer(manager).data)

    def patch(self, request, user_id):
        manager = self._get_manager(user_id)
        if not manager:
            return Response(
                {"error": "Manager no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = UpdateUserSerializer(manager.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        services.update_user(manager.user, serializer.validated_data)
        manager.refresh_from_db()
        return Response(
            {
                "message": "Manager actualizado.",
                "user": ManagerResponseSerializer(manager).data,
            }
        )

    def delete(self, request, user_id):
        try:
            services.delete_user(user_id, role=User.Role.MANAGER)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Manager eliminado."})


class WorkerListCreateView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        role = request.user_payload.get("role")
        user_id = request.user_payload.get("user_id")

        if role == "admin":
            workers = services.get_all_workers()
        else:
            try:
                manager = Manager.objects.get(user__id=user_id)
            except Manager.DoesNotExist:
                return Response(
                    {"error": "Manager no encontrado."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            workers = services.get_workers_by_manager(manager)

        return Response(WorkerResponseSerializer(workers, many=True).data)

    def post(self, request):
        serializer = CreateWorkerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        role = request.user_payload.get("role")
        user_id = request.user_payload.get("user_id")

        manager = None
        if role == "manager":
            try:
                manager = Manager.objects.get(user__id=user_id)
            except Manager.DoesNotExist:
                return Response(
                    {"error": "Manager no encontrado."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        worker = services.create_worker(
            serializer.validated_data, created_by_manager=manager
        )
        return Response(
            {
                "message": "Worker creado. Credenciales enviadas por correo.",
                "user": WorkerResponseSerializer(worker).data,
            },
            status=status.HTTP_201_CREATED,
        )


class WorkerDetailView(APIView):
    permission_classes = [IsAdminOrManager]

    def _get_worker_and_check_access(self, request, worker_user_id):
        try:
            worker = Worker.objects.select_related("user", "manager__user").get(
                user__id=worker_user_id
            )
        except Worker.DoesNotExist:
            return None, Response(
                {"error": "Worker no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

        role = request.user_payload.get("role")
        if role == "manager":
            manager_user_id = request.user_payload.get("user_id")
            if not worker.manager or worker.manager.user.id != manager_user_id:
                return None, Response(
                    {"error": "No tienes acceso a este worker."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return worker, None

    def get(self, request, user_id):
        worker, error = self._get_worker_and_check_access(request, user_id)
        if error:
            return error
        return Response(WorkerResponseSerializer(worker).data)

    def patch(self, request, user_id):
        worker, error = self._get_worker_and_check_access(request, user_id)
        if error:
            return error

        serializer = UpdateUserSerializer(worker.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        services.update_user(worker.user, serializer.validated_data)
        worker.refresh_from_db()
        return Response(
            {
                "message": "Worker actualizado.",
                "user": WorkerResponseSerializer(worker).data,
            }
        )

    def delete(self, request, user_id):
        worker, error = self._get_worker_and_check_access(request, user_id)
        if error:
            return error
        try:
            services.delete_user(user_id, role=User.Role.WORKER)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Worker eliminado."})

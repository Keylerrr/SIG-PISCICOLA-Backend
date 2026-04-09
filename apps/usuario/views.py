import uuid
import bcrypt
from datetime import timedelta, timezone as dt_timezone 

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Usuario
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UpdateUsuarioSerializer,
    UsuarioResponseSerializer,
)


def get_tokens_for_user(user: Usuario) -> dict:
    refresh = RefreshToken()
    refresh["user_id"] = user.id
    refresh["email"] = user.email
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(APIView):
   
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        password_hash = bcrypt.hashpw(
            data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        verification_token = str(uuid.uuid4())
        token_expiry = timezone.now() + timedelta(hours=24)

        user = Usuario.objects.create(
            name=data["name"],
            lastname=data.get("lastname"),
            email=data["email"],
            password_hash=password_hash,
            phone=data.get("phone"),
            token_reset=verification_token,
            token_reset_expiry=token_expiry,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        verify_url = f"{settings.FRONTEND_URL}/api/auth/verify/{verification_token}/"
        send_mail(
            subject="Verify your email address",
            message=(
                f"Hi {user.name},\n\n"
                f"Please verify your email by clicking the link below:\n{verify_url}\n\n"
                f"This link expires in 24 hours."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(
            {
                "message": "Registration successful. Please check your email to verify your account.",
                "user": UsuarioResponseSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):


    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = Usuario.objects.get(
                token_reset=token,
            )
        except Usuario.DoesNotExist:
            return Response(
                {"error": "Invalid or expired verification token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.token_reset_expiry and user.token_reset_expiry.replace(tzinfo=dt_timezone.utc) < timezone.now():
            return Response(
                {"error": "Verification token has expired. Please register again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.token_reset = None
        user.token_reset_expiry = None
        user.updated_at = timezone.now()
        user.save(update_fields=["token_reset", "token_reset_expiry", "updated_at"])

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "message": "Email verified successfully.",
                "user": UsuarioResponseSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )

class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.token_reset is not None:
            return Response(
                {"error": "Please verify your email before logging in."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "message": "Login successful.",
                "user": UsuarioResponseSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class UpdateUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        try:
            user = Usuario.objects.get(id=user_id)
        except Usuario.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.user_payload.get("user_id") != user.id:
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = UpdateUsuarioSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(updated_at=timezone.now())
        return Response(
            {
                "message": "User updated successfully.",
                "user": UsuarioResponseSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class DeleteUsuarioView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        try:
            user = Usuario.objects.get(id=user_id)
        except Usuario.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.user_payload.get("user_id") != user.id:
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        user.delete()
        return Response(
            {"message": "User deleted successfully."},
            status=status.HTTP_200_OK,
        )


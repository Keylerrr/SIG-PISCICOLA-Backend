import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import BlacklistedToken


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ", 1)[1]

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token has expired.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token.")

        if BlacklistedToken.objects.filter(token=token).exists():
            raise AuthenticationFailed("Token has been invalidated.")

        request.user_payload = payload
        request.token = token
        return (_AuthenticatedUser(payload), token)


class _AuthenticatedUser:
    def __init__(self, payload):
        self.payload = payload
        self.is_authenticated = True

    def get(self, key, default=None):
        return self.payload.get(key, default)

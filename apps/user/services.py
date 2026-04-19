import secrets
import string
import uuid
from datetime import timedelta

import bcrypt
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import BlacklistedToken, Manager, User, Worker


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def login_user(email: str, password: str) -> User:
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        raise ValueError("Credenciales inválidas.")

    if not _check_password(password, user.password_hash):
        raise ValueError("Credenciales inválidas.")

    return user


def logout_user(token: str, exp_timestamp: int) -> None:
    from datetime import datetime
    from datetime import timezone as dt_timezone

    expires_at = datetime.fromtimestamp(exp_timestamp, tz=dt_timezone.utc)
    BlacklistedToken.objects.get_or_create(
        token=token, defaults={"expires_at": expires_at}
    )
    BlacklistedToken.objects.filter(expires_at__lt=timezone.now()).delete()


def change_password(user: User, current_password: str, new_password: str) -> None:
    if not _check_password(current_password, user.password_hash):
        raise ValueError("La contraseña actual es incorrecta.")
    user.password_hash = _hash_password(new_password)
    user.updated_at = timezone.now()
    user.save(update_fields=["password_hash", "updated_at"])


def request_password_reset(email: str) -> None:
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return

    token = str(uuid.uuid4())
    user.password_reset_token = token
    user.password_reset_expiry = timezone.now() + timedelta(hours=2)
    user.save(update_fields=["password_reset_token", "password_reset_expiry"])

    reset_url = f"{settings.BACKEND_URL}/resetPassword?uuid={token}"
    send_mail(
        subject="Restablecer tu contraseña",
        message=(
            f"Hola {user.name},\n\n"
            f"Recibimos una solicitud para restablecer tu contraseña.\n\n"
            f"Haz clic en el siguiente enlace (válido por 2 horas):\n{reset_url}\n\n"
            f"Si no solicitaste esto, ignora este correo."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def confirm_password_reset(token: str, new_password: str) -> None:
    try:
        user = User.objects.get(password_reset_token=token)
    except User.DoesNotExist:
        raise ValueError("Token inválido o expirado.")

    if not user.password_reset_expiry or user.password_reset_expiry < timezone.now():
        raise ValueError("Token inválido o expirado.")

    user.password_hash = _hash_password(new_password)
    user.password_reset_token = None
    user.password_reset_expiry = None
    user.updated_at = timezone.now()
    user.save(
        update_fields=[
            "password_hash",
            "password_reset_token",
            "password_reset_expiry",
            "updated_at",
        ]
    )


def create_manager(data: dict) -> User:
    temp_password = _generate_temp_password()
    user = User.objects.create(
        name=data["name"],
        lastname=data.get("lastname"),
        email=data["email"],
        password_hash=_hash_password(temp_password),
        phone=data.get("phone"),
        role=User.Role.MANAGER,
    )
    manager = Manager.objects.create(user=user)
    _send_credentials_email(user, temp_password, role="manager")
    return manager


def create_worker(data: dict, created_by_manager: Manager | None = None) -> User:
    temp_password = _generate_temp_password()
    user = User.objects.create(
        name=data["name"],
        lastname=data.get("lastname"),
        email=data["email"],
        password_hash=_hash_password(temp_password),
        phone=data.get("phone"),
        role=User.Role.WORKER,
    )
    worker = Worker.objects.create(user=user, manager=created_by_manager)
    _send_credentials_email(user, temp_password, role="worker")
    return worker


def update_user(user: User, data: dict) -> User:
    for field, value in data.items():
        setattr(user, field, value)
    user.updated_at = timezone.now()
    user.save(update_fields=list(data.keys()) + ["updated_at"])
    return user


def delete_user(user_id: int, role: str) -> None:
    deleted, _ = User.objects.filter(id=user_id, role=role).delete()
    if not deleted:
        raise ValueError("Usuario no encontrado.")


def get_workers_by_manager(manager: Manager):
    return Worker.objects.select_related("user", "manager__user").filter(
        manager=manager
    )


def get_all_workers():
    return Worker.objects.select_related("user", "manager__user").all()


def get_all_managers():
    return Manager.objects.select_related("user").all()


def _send_credentials_email(user: User, temp_password: str, role: str) -> None:
    role_label = "Manager" if role == "manager" else "Trabajador"
    send_mail(
        subject="Bienvenido al sistema - Tus credenciales de acceso",
        message=(
            f"Hola {user.name},\n\n"
            f"Has sido registrado como {role_label} en el sistema.\n\n"
            f"Tus credenciales:\n"
            f"  Email:      {user.email}\n"
            f"  Contraseña: {temp_password}\n\n"
            f"Por seguridad, te recomendamos cambiar tu contraseña al ingresar.\n\n"
            f"Ingresa en: {settings.BACKEND_URL}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

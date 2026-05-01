# utils.py
import random
import string

from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import Invitation, Role, User


def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(random.choices(chars, k=length))


def send_credentials_email(email: str, temp_password: str) -> None:
    send_mail(
        subject="Bienvenido - Tus credenciales de acceso",
        message=f"""
Hola,

Tu cuenta ha sido creada. Estas son tus credenciales temporales:
  Correo:     {email}
  Contraseña: {temp_password}

Al iniciar sesión deberás completar tu perfil y cambiar tu contraseña.
        """,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )


def send_invitation_notification(email: str, farm_id: int, invited_by: User) -> None:
    send_mail(
        subject="Tienes una nueva invitación",
        message=f"""
Hola,

{invited_by.name} {invited_by.lastname} te ha invitado a unirte a la granja #{farm_id},

Ingresa a la plataforma para aceptar o rechazar la invitación.
              """,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )


def send_reset_password_email(email: str, uuidb64: str, token: str) -> None:
    send_mail(
        subject="Recuperación de contraseña",
        message=f"""
Hola,

Se solicitó un restablecimiento de contraseña. Entra en el siguiente enlace para restaurarla:
{settings.HOST_URL}/{uuidb64}/{token}

Si no enviaste esta solicitud, puedes ignorar este correo.
        """,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )


def invite_productor(email: str, creator: User) -> Invitation:
    role = Role.objects.get(name="Productor")
    temp_password = generate_temp_password()

    user = User.objects.create_user(
        email=email,
        password=temp_password,
        role=role,
        is_temp_password=True,
        is_profile_complete=False,
    )
    invitation = Invitation.objects.create(
        farm_id=None,
        user=user,
        invited_by=creator,
        email=email,
        status=Invitation.Status.ACCEPTED,
    )
    send_credentials_email(email, temp_password)
    return invitation


def invite_operario(email: str, farm_id: int, creator: User) -> Invitation:

    UserFarm = apps.get_model("farms", "UserFarm")
    Farm = apps.get_model("farms", "Farm")
    existing_user = User.objects.filter(email=email).first()
    farm = Farm.objects.get(id=farm_id)

    if existing_user:
        already_in_farm = UserFarm.objects.filter(
            user=existing_user,
            farm=farm,
        ).exists()
        if already_in_farm:
            raise ValueError("Este usuario ya pertenece a la granja.")

        with transaction.atomic():
            invitation = Invitation.objects.create(
                farm_id=farm,
                user=existing_user,
                invited_by=creator,
                email=email,
                status=Invitation.Status.PENDING,
            )
            send_invitation_notification(email, farm_id, creator)
            return invitation

    role = Role.objects.get(name="Operario")
    temp_password = generate_temp_password()
    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            password=temp_password,
            role=role,
            is_temp_password=True,
            is_profile_complete=False,
        )

        UserFarm.objects.create(
            user=user,
            farm=farm,
            is_owner=False,
            status=UserFarm.Status.ACTIVE,
        )

        invitation = Invitation.objects.create(
            farm_id=farm,
            user=user,
            invited_by=creator,
            email=email,
            status=Invitation.Status.ACCEPTED,
        )
        send_credentials_email(email, temp_password)
        return invitation


def accept_invitation(invitation: Invitation, user: User) -> None:
    UserFarm = apps.get_model("farms", "UserFarm")
    UserFarm.objects.create(
        user=user,
        farm_id=invitation.farm_id,
        is_owner=False,
        status=UserFarm.Status.ACTIVE,
    )
    invitation.status = Invitation.Status.ACCEPTED
    invitation.save(update_fields=["status"])


def change_user_password(user: User, new_password: str) -> None:
    user.set_password(new_password)
    user.is_temp_password = False
    user.save(update_fields=["password", "is_temp_password"])

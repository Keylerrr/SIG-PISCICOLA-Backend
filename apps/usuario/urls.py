from django.urls import path
from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    UpdateUsuarioView,
    DeleteUsuarioView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/verify/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("users/<int:user_id>/", UpdateUsuarioView.as_view(), name="update-user"),
    path("users/<int:user_id>/delete/", DeleteUsuarioView.as_view(), name="delete-user"),
]

from django.urls import path

from .views import (ChangePasswordView, ConfirmPasswordResetView, LoginView,
                    LogoutView, ManagerDetailView, ManagerListCreateView,
                    MeView, RequestPasswordResetView, WorkerDetailView,
                    WorkerListCreateView)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path(
        "auth/reset-password/",
        RequestPasswordResetView.as_view(),
        name="reset-password-request",
    ),
    path(
        "auth/reset-password/confirm/",
        ConfirmPasswordResetView.as_view(),
        name="reset-password-confirm",
    ),
    path("managers/", ManagerListCreateView.as_view(), name="managers"),
    path("managers/<int:user_id>/", ManagerDetailView.as_view(), name="manager-detail"),
    path("workers/", WorkerListCreateView.as_view(), name="workers"),
    path("workers/<int:user_id>/", WorkerDetailView.as_view(), name="worker-detail"),
    path("users/me/", MeView.as_view(), name="me"),
]

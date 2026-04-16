from django.urls import path, include

urlpatterns = [
    path("", include("apps.usuario.urls")),
    path("", include("apps.estanques.urls")),
]

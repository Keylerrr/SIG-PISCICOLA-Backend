from django.urls import include, path

urlpatterns = [
    path("", include("apps.estanques.urls")),
    path("", include("apps.user.urls")),
    path("", include("apps.farm.urls")),
]

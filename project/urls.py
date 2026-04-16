from django.urls import include, path

urlpatterns = [
    path("", include("apps.ponds.urls")),
    path("", include("apps.user.urls")),
    path("", include("apps.farm.urls")),
]

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.farms.urls")),
    path("api/", include("apps.ponds.urls")),
    path("api/", include("apps.products.urls")),
    path("api/", include("apps.purchases.urls")),
]

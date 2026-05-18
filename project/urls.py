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
    path("api/", include("apps.batch.urls")),
    path("api/", include("apps.cycle.urls")),
    path("api/", include("apps.events.urls")),
    path("api/", include("apps.species.urls")),
    path("api/", include("apps.products.urls")),
    path("api/", include("apps.purchases.urls")),
    path("api/", include("apps.feeding.urls")),
    path("api/", include("apps.monitoring.urls")),
    path("api/", include("apps.health.urls")),
    path("api/", include("apps.harvest.urls")),
]

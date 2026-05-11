from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AlertViewSet, AuditLogView, UnitView

router = DefaultRouter()
router.register(r"unit", UnitView)
router.register(r"auditlog", AuditLogView)
router.register(r"alerts", AlertViewSet, basename="alert")

urlpatterns = [
    path("farms/<int:farm_pk>/", include(router.urls)),
]

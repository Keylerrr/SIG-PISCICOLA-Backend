from rest_framework.routers import DefaultRouter

from .views import AuditLogView, UnitView

router = DefaultRouter()
router.register(r"unit", UnitView)
router.register(r"auditlog", AuditLogView)

urlpatterns = router.urls

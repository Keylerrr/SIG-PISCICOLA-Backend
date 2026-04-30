from rest_framework import viewsets

from ..accounts.permissions import IsAdmin
from .models import AuditLog, Unit
from .seralizers import AuditLogSerializer, UnitSerializer


class UnitView(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer


class AuditLogView(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer

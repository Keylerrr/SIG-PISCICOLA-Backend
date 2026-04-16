from django.urls import path
from .views import (
    PondListCreateView,
    PondDetailUpdateDeleteView,
    PondToggleStateView,
    PondChangeStatusView,
)

urlpatterns = [
    # Ponds
    path('ponds/', PondListCreateView.as_view(), name='pond-list-create'),
    path('ponds/<int:pond_id>/', PondDetailUpdateDeleteView.as_view(), name='pond-detail'),
    path('ponds/<int:pond_id>/toggle-state/', PondToggleStateView.as_view(), name='pond-toggle'),
    path('ponds/<int:pond_id>/change-status/', PondChangeStatusView.as_view(), name='pond-change-status'),
]


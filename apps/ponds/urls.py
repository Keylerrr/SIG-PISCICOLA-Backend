from django.urls import path
from .views import (
    PondListCreateView,
    PondDetailUpdateDeleteView,
    PondChangeStatusView,
    PondListByFarmView,
)

urlpatterns = [
    # Ponds
    path('ponds/', PondListCreateView.as_view(), name='pond-list-create'),
    path('ponds/<int:pond_id>/', PondDetailUpdateDeleteView.as_view(), name='pond-detail'),
    path('ponds/<int:pond_id>/change-status/', PondChangeStatusView.as_view(), name='pond-change-status'),
    path('farms/<int:farm_id>/ponds/', PondListByFarmView.as_view(), name='pond-list-by-farm'),
]


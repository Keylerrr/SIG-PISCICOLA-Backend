from django.urls import path
from .views import FarmListCreateView, FarmDetailView

urlpatterns = [
    path('farms/', FarmListCreateView.as_view(), name='farms'),
    path('farms/<int:farm_id>/', FarmDetailView.as_view(), name='farm-detail'),
]
from django.urls import path
from .views import FarmListCreateView, FarmDetailView, CityListView

urlpatterns = [
    path('farm/', FarmListCreateView.as_view(), name='farm-list'),
    path('farm/cities/', CityListView.as_view(), name='farm-cities'),
    path('farm/<int:farm_id>/', FarmDetailView.as_view(), name='farm-detail'),
]
from django.urls import path
from .views import FarmListCreateView, FarmDetailView, CityListView, DepartmentListView

urlpatterns = [
    path('farm/', FarmListCreateView.as_view(), name='farm-list'),
    path('farm/departments/', DepartmentListView.as_view(), name='farm-departments'),
    path('farm/departments/<str:department>/cities/', CityListView.as_view(), name='farm-cities'),
    path('farm/<int:farm_id>/', FarmDetailView.as_view(), name='farm-detail'),
]
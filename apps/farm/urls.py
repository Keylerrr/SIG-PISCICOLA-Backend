from django.urls import path
from .views import FarmListCreateView

urlpatterns = [
    path('farms/', FarmListCreateView.as_view(), name='farms'),
]
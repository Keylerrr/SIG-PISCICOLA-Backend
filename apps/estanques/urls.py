from django.urls import path
from .views import (
    EstanqueListCreateView,
    EstanqueDetailUpdateDeleteView,
    EstanqueToggleStateView,
    EstanqueCambiarEstadoView,
)

urlpatterns = [
    # Estanques
    path('estanques/', EstanqueListCreateView.as_view(), name='estanque-list-create'),
    path('estanques/<int:estanque_id>/', EstanqueDetailUpdateDeleteView.as_view(), name='estanque-detail'),
    path('estanques/<int:estanque_id>/toggle-estado/', EstanqueToggleStateView.as_view(), name='estanque-toggle'),
    path('estanques/<int:estanque_id>/cambiar-estado/', EstanqueCambiarEstadoView.as_view(), name='estanque-cambiar-estado'),
]


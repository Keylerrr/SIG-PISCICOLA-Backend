# urls.py

from django.urls import path

from .views import (PondAllowedListView, PondDetailView, PondListCreateView,
                    PondMemberDetailView, PondMemberListView)

urlpatterns = [
    path("farms/<int:farm_id>/ponds/", PondListCreateView.as_view()),
    path("farms/<int:farm_id>/ponds/alloweds/", PondAllowedListView.as_view()),
    path("farms/<int:farm_id>/ponds/members/", PondMemberListView.as_view()),
    path("farms/<int:farm_id>/ponds/<int:pond_id>/", PondDetailView.as_view()),
    path(
        "farms/<int:farm_id>/ponds/<int:pond_id>/members/<int:user_id>/",
        PondMemberDetailView.as_view(),
    ),
]

from django.urls import path

from .views import FeedingScheduleDetailView, FeedingScheduleListCreateView

urlpatterns = [
    path(
        "farms/<int:farm_id>/feeding-schedules/",
        FeedingScheduleListCreateView.as_view(),
    ),
    path(
        "farms/<int:farm_id>/feeding-schedules/<int:schedule_id>/",
        FeedingScheduleDetailView.as_view(),
    ),
]

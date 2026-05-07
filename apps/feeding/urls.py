from django.urls import path

from .views import (
    FeedingEventDetailView,
    FeedingEventListView,
    FeedingPlanDetailView,
    FeedingPlanListCreateView,
    FeedingScheduleDetailView,
    FeedingScheduleListCreateView,
)

urlpatterns = [
    path(
        "farms/<int:farm_id>/feeding-schedules/",
        FeedingScheduleListCreateView.as_view(),
    ),
    path(
        "farms/<int:farm_id>/feeding-schedules/<int:schedule_id>/",
        FeedingScheduleDetailView.as_view(),
    ),
    path(
        "farms/<int:farm_id>/feeding-plans/",
        FeedingPlanListCreateView.as_view(),
    ),
    path(
        "farms/<int:farm_id>/feeding-plans/<int:plan_id>/",
        FeedingPlanDetailView.as_view(),
    ),
    path(
        "farms/<int:farm_id>/feeding-events/",
        FeedingEventListView.as_view(),
    ),
    path(
        "farms/<int:farm_id>/feeding-events/<int:event_id>/",
        FeedingEventDetailView.as_view(),
    ),
]

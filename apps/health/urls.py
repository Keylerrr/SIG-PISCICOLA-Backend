from django.urls import path

from .views import (
    CycleHealthStatDetailView,
    CycleHealthStatListCreateView,
    HealthStatTreatmentPlanDetailView,
    HealthStatTreatmentPlanEventDetailView,
    HealthStatTreatmentPlanEventListView,
    HealthStatTreatmentPlanListCreateView,
)

urlpatterns = [
    path(
        "farms/<int:farm_id>/cycles/<int:cycle_id>/health-stats/",
        CycleHealthStatListCreateView.as_view(),
        name="health-stat-list",
    ),
    path(
        "farms/<int:farm_id>/cycles/<int:cycle_id>/health-stats/<int:health_stat_id>/",
        CycleHealthStatDetailView.as_view(),
        name="health-stat-detail",
    ),
    path(
        "farms/<int:farm_id>/cycles/<int:cycle_id>/health-stats/<int:health_stat_id>/treatment-plans/",
        HealthStatTreatmentPlanListCreateView.as_view(),
        name="treatment-plan-list",
    ),
    path(
        "farms/<int:farm_id>/cycles/<int:cycle_id>/health-stats/<int:health_stat_id>/treatment-plans/<int:plan_id>/",
        HealthStatTreatmentPlanDetailView.as_view(),
        name="treatment-plan-detail",
    ),
    path(
        "farms/<int:farm_id>/cycles/<int:cycle_id>/health-stats/<int:health_stat_id>/treatment-plans/<int:plan_id>/treatment-events/",
        HealthStatTreatmentPlanEventListView.as_view(),
        name="treatment-event-list",
    ),
    path(
        "farms/<int:farm_id>/cycles/<int:cycle_id>/health-stats/<int:health_stat_id>/treatment-plans/<int:plan_id>/treatment-events/<int:event_id>/",
        HealthStatTreatmentPlanEventDetailView.as_view(),
        name="treatment-event-detail",
    ),
]

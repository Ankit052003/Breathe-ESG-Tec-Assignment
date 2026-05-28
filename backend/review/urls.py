from django.urls import path

from .views import (
    ActivityActionView,
    ActivityDetailView,
    ActivityListView,
    BatchRawRecordListView,
    DashboardSummaryView,
    FacilityListView,
    HealthView,
    IngestionBatchListView,
    OrganizationListView,
    UploadIngestionView,
)


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("organizations/", OrganizationListView.as_view(), name="organizations"),
    path("facilities/", FacilityListView.as_view(), name="facilities"),
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard"),
    path("ingestions/upload/", UploadIngestionView.as_view(), name="upload-ingestion"),
    path("batches/", IngestionBatchListView.as_view(), name="batches"),
    path(
        "batches/<int:batch_id>/raw-records/",
        BatchRawRecordListView.as_view(),
        name="batch-raw-records",
    ),
    path("activities/", ActivityListView.as_view(), name="activities"),
    path("activities/<int:activity_id>/", ActivityDetailView.as_view(), name="activity"),
    path(
        "activities/<int:activity_id>/<str:action>/",
        ActivityActionView.as_view(),
        name="activity-action",
    ),
]

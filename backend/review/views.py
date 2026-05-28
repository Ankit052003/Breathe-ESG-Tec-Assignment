from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpRequest
from rest_framework import parsers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AuditEvent,
    Facility,
    IngestionBatch,
    NormalizedActivity,
    Organization,
    RawRecord,
    SourceSystem,
)
from .serializers import (
    ActivityDetailSerializer,
    ActivityListSerializer,
    FacilitySerializer,
    IngestionBatchSerializer,
    OrganizationSerializer,
    RawRecordSerializer,
)
from .services import (
    get_actor_name,
    get_demo_organization,
    ingest_rows,
    parse_csv_file,
    parse_date,
    parse_decimal,
    recalculate_activity_emissions,
)


class HealthView(APIView):
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class OrganizationListView(APIView):
    def get(self, request: Request) -> Response:
        organizations = Organization.objects.all()
        return Response(OrganizationSerializer(organizations, many=True).data)


class FacilityListView(APIView):
    def get(self, request: Request) -> Response:
        organization = resolve_organization(request)
        facilities = Facility.objects.filter(organization=organization)
        return Response(FacilitySerializer(facilities, many=True).data)


def resolve_organization(request: Request) -> Organization:
    organization_slug = request.query_params.get("organization")
    if request.data and isinstance(request.data, dict):
        organization_slug = request.data.get("organization", organization_slug)
    return get_demo_organization(organization_slug)


class UploadIngestionView(APIView):
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request: Request) -> Response:
        try:
            organization = resolve_organization(request)
            source_type = str(request.data.get("source_type", "")).strip()
            uploaded_file = request.FILES.get("file")
            if source_type not in SourceSystem.SourceType.values:
                return Response(
                    {"detail": "source_type must be one of: sap, utility, travel."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if uploaded_file is None:
                return Response(
                    {"detail": "CSV file is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            rows = parse_csv_file(uploaded_file)
            if not rows:
                return Response(
                    {"detail": "CSV file has no data rows."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            batch = ingest_rows(
                organization,
                source_type,
                uploaded_file.name,
                rows,
            )
            return Response(
                IngestionBatchSerializer(batch).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class IngestionBatchListView(APIView):
    def get(self, request: Request) -> Response:
        organization = resolve_organization(request)
        batches = IngestionBatch.objects.filter(organization=organization).select_related(
            "source_system"
        )
        return Response(IngestionBatchSerializer(batches, many=True).data)


class BatchRawRecordListView(APIView):
    def get(self, request: Request, batch_id: int) -> Response:
        organization = resolve_organization(request)
        raw_records = RawRecord.objects.filter(
            organization=organization, batch_id=batch_id
        )
        return Response(RawRecordSerializer(raw_records, many=True).data)


def filter_activities(
    request: Request, activities: Any
) -> Any:
    source_type = request.query_params.get("source_type")
    status_filter = request.query_params.get("status")
    scope = request.query_params.get("scope")
    facility = request.query_params.get("facility")
    flagged = request.query_params.get("flagged")
    flag_severity = request.query_params.get("flag_severity")
    search = request.query_params.get("search")

    if source_type:
        activities = activities.filter(source_type=source_type)
    if status_filter:
        activities = activities.filter(status=status_filter)
    if scope:
        activities = activities.filter(scope=scope)
    if facility:
        activities = activities.filter(facility_id=facility)
    if flagged == "true":
        activities = activities.filter(flags__isnull=False)
    if flag_severity:
        activities = activities.filter(flags__severity=flag_severity)
    if search:
        activities = activities.filter(
            Q(source_reference__icontains=search)
            | Q(counterparty__icontains=search)
            | Q(department__icontains=search)
            | Q(location_label__icontains=search)
        )
    return activities.distinct()


class ActivityListView(APIView):
    def get(self, request: Request) -> Response:
        organization = resolve_organization(request)
        activities = (
            NormalizedActivity.objects.filter(organization=organization)
            .select_related("facility", "batch", "raw_record")
            .prefetch_related("flags")
        )
        filtered = filter_activities(request, activities)
        return Response(ActivityListSerializer(filtered[:300], many=True).data)


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def update_activity_from_payload(
    activity: NormalizedActivity, payload: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    date_fields = {"activity_date", "period_start", "period_end"}
    decimal_fields = {"normalized_quantity", "amount"}
    text_fields = {
        "normalized_unit",
        "department",
        "location_label",
        "counterparty",
        "currency",
        "edit_reason",
    }

    for field in date_fields:
        if field in payload:
            old_value = getattr(activity, field)
            new_value = parse_date(str(payload[field])) if payload[field] else None
            setattr(activity, field, new_value)
            changes[field] = {"from": json_value(old_value), "to": json_value(new_value)}

    for field in decimal_fields:
        if field in payload:
            old_value = getattr(activity, field)
            new_value = parse_decimal(str(payload[field])) if payload[field] else None
            setattr(activity, field, new_value)
            changes[field] = {"from": json_value(old_value), "to": json_value(new_value)}

    for field in text_fields:
        if field in payload:
            old_value = getattr(activity, field)
            new_value = str(payload[field]).strip()
            setattr(activity, field, new_value)
            changes[field] = {"from": json_value(old_value), "to": json_value(new_value)}

    if "facility_id" in payload:
        old_value = activity.facility_id
        facility_id = payload["facility_id"]
        if facility_id in ("", None):
            activity.facility = None
            new_value = None
        else:
            activity.facility = Facility.objects.get(
                organization=activity.organization, id=facility_id
            )
            new_value = activity.facility_id
        changes["facility_id"] = {"from": old_value, "to": new_value}

    if {"normalized_quantity", "normalized_unit", "facility_id"} & set(payload.keys()):
        recalculate_activity_emissions(activity)
        changes["emissions_kg_co2e"] = {
            "to": json_value(activity.emissions_kg_co2e),
        }

    if changes:
        edited_fields = dict(activity.edited_fields)
        edited_fields.update({field: change["to"] for field, change in changes.items()})
        activity.edited_fields = edited_fields
    return changes


class ActivityDetailView(APIView):
    def get(self, request: Request, activity_id: int) -> Response:
        organization = resolve_organization(request)
        activity = (
            NormalizedActivity.objects.filter(organization=organization, id=activity_id)
            .select_related("facility", "batch", "raw_record")
            .prefetch_related("flags", "audit_events")
            .first()
        )
        if activity is None:
            return Response({"detail": "Activity not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ActivityDetailSerializer(activity).data)

    @transaction.atomic
    def patch(self, request: Request, activity_id: int) -> Response:
        organization = resolve_organization(request)
        activity = NormalizedActivity.objects.select_for_update().filter(
            organization=organization, id=activity_id
        ).first()
        if activity is None:
            return Response({"detail": "Activity not found."}, status=status.HTTP_404_NOT_FOUND)
        if activity.status not in {
            NormalizedActivity.Status.NORMALIZED,
            NormalizedActivity.Status.NEEDS_REVIEW,
        }:
            return Response(
                {"detail": "Only normalized or needs_review activities can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            changes = update_activity_from_payload(activity, request.data)
        except Facility.DoesNotExist:
            return Response(
                {"detail": "Facility does not exist for this organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not changes:
            return Response(
                {"detail": "No editable fields were supplied."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        activity.save()
        AuditEvent.objects.create(
            organization=organization,
            batch=activity.batch,
            activity=activity,
            action="edited",
            actor_name=get_actor_name(request.headers),
            changes=changes,
        )
        return Response(ActivityDetailSerializer(activity).data)


class ActivityActionView(APIView):
    @transaction.atomic
    def post(self, request: Request, activity_id: int, action: str) -> Response:
        organization = resolve_organization(request)
        activity = NormalizedActivity.objects.select_for_update().filter(
            organization=organization, id=activity_id
        ).first()
        if activity is None:
            return Response({"detail": "Activity not found."}, status=status.HTTP_404_NOT_FOUND)
        if activity.is_locked:
            return Response(
                {"detail": "Locked activities cannot change status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if action == "approve":
            old_status = activity.status
            activity.approve()
        elif action == "reject":
            old_status = activity.status
            activity.reject()
        elif action == "lock":
            old_status = activity.status
            if activity.status != NormalizedActivity.Status.APPROVED:
                return Response(
                    {"detail": "Only approved activities can be locked."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            activity.lock()
        else:
            return Response({"detail": "Unsupported action."}, status=status.HTTP_400_BAD_REQUEST)

        activity.save()
        AuditEvent.objects.create(
            organization=organization,
            batch=activity.batch,
            activity=activity,
            action=action,
            actor_name=get_actor_name(request.headers),
            changes={"status": {"from": old_status, "to": activity.status}},
        )
        return Response(ActivityDetailSerializer(activity).data)


class DashboardSummaryView(APIView):
    def get(self, request: Request) -> Response:
        organization = resolve_organization(request)
        activities = NormalizedActivity.objects.filter(organization=organization)
        status_counts = {
            row["status"]: row["count"]
            for row in activities.values("status").annotate(count=Count("id"))
        }
        source_counts = {
            row["source_type"]: row["count"]
            for row in activities.values("source_type").annotate(count=Count("id"))
        }
        scope_counts = {
            row["scope"]: row["count"]
            for row in activities.values("scope").annotate(count=Count("id"))
        }
        flagged_count = activities.filter(flags__isnull=False).distinct().count()
        failed_rows = RawRecord.objects.filter(
            organization=organization, status=RawRecord.Status.FAILED
        ).count()
        return Response(
            {
                "organization": organization.slug,
                "batches": IngestionBatch.objects.filter(organization=organization).count(),
                "activities": activities.count(),
                "failed_rows": failed_rows,
                "flagged_rows": flagged_count,
                "review_queue_count": activities.filter(
                    status__in=[
                        NormalizedActivity.Status.NORMALIZED,
                        NormalizedActivity.Status.NEEDS_REVIEW,
                    ]
                ).count(),
                "status_counts": status_counts,
                "source_counts": source_counts,
                "scope_counts": scope_counts,
            }
        )

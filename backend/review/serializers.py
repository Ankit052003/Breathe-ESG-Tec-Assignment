from rest_framework import serializers

from .models import (
    AuditEvent,
    Facility,
    IngestionBatch,
    NormalizedActivity,
    Organization,
    RawRecord,
    ReviewFlag,
)


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug"]


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ["id", "code", "name", "meter_number", "service_address", "grid_region"]


class ReviewFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewFlag
        fields = ["id", "severity", "code", "field", "message", "created_at"]


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ["id", "row_number", "source_payload", "status", "parse_errors", "created_at"]


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ["id", "action", "actor_name", "changes", "created_at"]


class IngestionBatchSerializer(serializers.ModelSerializer):
    source_system_name = serializers.CharField(source="source_system.name", read_only=True)

    class Meta:
        model = IngestionBatch
        fields = [
            "id",
            "source_system_name",
            "source_type",
            "filename",
            "status",
            "uploaded_at",
            "total_rows",
            "normalized_rows",
            "failed_rows",
        ]


class ActivityListSerializer(serializers.ModelSerializer):
    facility = FacilitySerializer(read_only=True)
    flags = ReviewFlagSerializer(many=True, read_only=True)
    batch_filename = serializers.CharField(source="batch.filename", read_only=True)

    class Meta:
        model = NormalizedActivity
        fields = [
            "id",
            "source_type",
            "source_reference",
            "activity_type",
            "scope",
            "status",
            "activity_date",
            "period_start",
            "period_end",
            "original_quantity",
            "original_unit",
            "normalized_quantity",
            "normalized_unit",
            "facility",
            "location_label",
            "department",
            "counterparty",
            "currency",
            "amount",
            "emissions_kg_co2e",
            "normalized_payload",
            "edited_fields",
            "edit_reason",
            "created_at",
            "updated_at",
            "batch_filename",
            "flags",
        ]


class ActivityDetailSerializer(ActivityListSerializer):
    raw_record = RawRecordSerializer(read_only=True)
    audit_events = AuditEventSerializer(many=True, read_only=True)

    class Meta(ActivityListSerializer.Meta):
        fields = ActivityListSerializer.Meta.fields + ["raw_record", "audit_events"]


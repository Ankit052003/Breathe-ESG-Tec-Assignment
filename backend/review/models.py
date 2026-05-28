from django.db import models
from django.utils import timezone


class Organization(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Facility(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    meter_number = models.CharField(max_length=80, blank=True)
    service_address = models.CharField(max_length=255, blank=True)
    grid_region = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("organization", "code")]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class SourceSystem(models.Model):
    class SourceType(models.TextChoices):
        SAP = "sap", "SAP"
        UTILITY = "utility", "Utility"
        TRAVEL = "travel", "Travel"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["source_type", "name"]
        unique_together = [("organization", "source_type", "name")]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.name}"


class PlantLookup(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    plant_code = models.CharField(max_length=40)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("organization", "plant_code")]

    def __str__(self) -> str:
        return f"{self.plant_code} -> {self.facility.code}"


class Airport(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=160)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class UnitConversion(models.Model):
    category = models.CharField(max_length=40)
    source_unit = models.CharField(max_length=40)
    target_unit = models.CharField(max_length=40)
    multiplier = models.DecimalField(max_digits=18, decimal_places=8)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("category", "source_unit", "target_unit")]

    def __str__(self) -> str:
        return f"{self.source_unit} -> {self.target_unit}"


class EmissionFactor(models.Model):
    activity_type = models.CharField(max_length=60)
    scope = models.CharField(max_length=20)
    unit = models.CharField(max_length=40)
    kg_co2e_per_unit = models.DecimalField(max_digits=18, decimal_places=8)
    source = models.CharField(max_length=180)
    region = models.CharField(max_length=80, blank=True)
    active = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["activity_type", "region"]
        unique_together = [("activity_type", "scope", "unit", "region")]

    def __str__(self) -> str:
        region = f" {self.region}" if self.region else ""
        return f"{self.activity_type}{region}: {self.kg_co2e_per_unit}/{self.unit}"


class IngestionBatch(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        COMPLETED = "completed", "Completed"
        COMPLETED_WITH_FLAGS = "completed_with_flags", "Completed with flags"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    source_system = models.ForeignKey(SourceSystem, on_delete=models.PROTECT)
    source_type = models.CharField(max_length=20, choices=SourceSystem.SourceType.choices)
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=40, choices=Status.choices)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    total_rows = models.PositiveIntegerField()
    normalized_rows = models.PositiveIntegerField()
    failed_rows = models.PositiveIntegerField()

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.source_type}:{self.filename}"


class RawRecord(models.Model):
    class Status(models.TextChoices):
        PARSED = "parsed", "Parsed"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    batch = models.ForeignKey(
        IngestionBatch, related_name="raw_records", on_delete=models.CASCADE
    )
    row_number = models.PositiveIntegerField()
    source_payload = models.JSONField()
    status = models.CharField(max_length=20, choices=Status.choices)
    parse_errors = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["batch_id", "row_number"]
        unique_together = [("batch", "row_number")]

    def __str__(self) -> str:
        return f"{self.batch_id}:{self.row_number}"


class NormalizedActivity(models.Model):
    class Scope(models.TextChoices):
        SCOPE_1 = "scope_1", "Scope 1"
        SCOPE_2 = "scope_2", "Scope 2"
        SCOPE_3 = "scope_3", "Scope 3"

    class Status(models.TextChoices):
        NORMALIZED = "normalized", "Normalized"
        NEEDS_REVIEW = "needs_review", "Needs review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        LOCKED = "locked", "Locked"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    batch = models.ForeignKey(
        IngestionBatch, related_name="activities", on_delete=models.CASCADE
    )
    raw_record = models.OneToOneField(
        RawRecord, related_name="activity", on_delete=models.CASCADE
    )
    source_type = models.CharField(max_length=20, choices=SourceSystem.SourceType.choices)
    source_reference = models.CharField(max_length=120, blank=True)
    activity_type = models.CharField(max_length=60)
    scope = models.CharField(max_length=20, choices=Scope.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    original_quantity = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    original_unit = models.CharField(max_length=40, blank=True)
    normalized_quantity = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    normalized_unit = models.CharField(max_length=40, blank=True)
    facility = models.ForeignKey(Facility, null=True, blank=True, on_delete=models.SET_NULL)
    location_label = models.CharField(max_length=180, blank=True)
    department = models.CharField(max_length=120, blank=True)
    counterparty = models.CharField(max_length=160, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    emission_factor = models.ForeignKey(
        EmissionFactor, null=True, blank=True, on_delete=models.PROTECT
    )
    emissions_kg_co2e = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    normalized_payload = models.JSONField()
    edited_fields = models.JSONField()
    edit_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self) -> str:
        return f"{self.source_type}:{self.source_reference or self.id}"

    @property
    def is_locked(self) -> bool:
        return self.status == self.Status.LOCKED

    def approve(self) -> None:
        self.status = self.Status.APPROVED
        self.approved_at = timezone.now()

    def reject(self) -> None:
        self.status = self.Status.REJECTED

    def lock(self) -> None:
        self.status = self.Status.LOCKED
        self.locked_at = timezone.now()


class ReviewFlag(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    activity = models.ForeignKey(
        NormalizedActivity, related_name="flags", on_delete=models.CASCADE
    )
    severity = models.CharField(max_length=20, choices=Severity.choices)
    code = models.CharField(max_length=80)
    field = models.CharField(max_length=80, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["severity", "code"]

    def __str__(self) -> str:
        return f"{self.severity}:{self.code}"


class AuditEvent(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    batch = models.ForeignKey(
        IngestionBatch, null=True, blank=True, on_delete=models.CASCADE
    )
    activity = models.ForeignKey(
        NormalizedActivity,
        null=True,
        blank=True,
        related_name="audit_events",
        on_delete=models.CASCADE,
    )
    action = models.CharField(max_length=40)
    actor_name = models.CharField(max_length=120)
    changes = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} by {self.actor_name}"


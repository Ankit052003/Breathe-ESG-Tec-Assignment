import csv
import json
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase

from .models import NormalizedActivity, Organization, RawRecord, ReviewFlag
from .services import ingest_rows


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = PROJECT_ROOT / "sample_data"


def read_sample(filename: str) -> list[dict[str, str]]:
    with (SAMPLE_DIR / filename).open(encoding="utf-8-sig", newline="") as sample_file:
        return list(csv.DictReader(sample_file))


class IngestionWorkflowTests(TestCase):
    def setUp(self) -> None:
        call_command("seed_demo", verbosity=0)
        self.organization = Organization.objects.get(slug="acme-industrial")

    def test_all_sample_sources_create_reviewable_activities_and_flags(self) -> None:
        samples = [
            ("sap", "sap_fuel_procurement.csv"),
            ("utility", "utility_electricity.csv"),
            ("travel", "travel_expenses.csv"),
        ]

        for source_type, filename in samples:
            ingest_rows(self.organization, source_type, filename, read_sample(filename))

        self.assertEqual(NormalizedActivity.objects.count(), 13)
        self.assertEqual(RawRecord.objects.filter(status=RawRecord.Status.FAILED).count(), 3)
        self.assertGreaterEqual(ReviewFlag.objects.filter(severity="warning").count(), 3)
        self.assertGreaterEqual(ReviewFlag.objects.filter(severity="error").count(), 3)
        self.assertTrue(
            NormalizedActivity.objects.filter(scope=NormalizedActivity.Scope.SCOPE_1).exists()
        )
        self.assertTrue(
            NormalizedActivity.objects.filter(scope=NormalizedActivity.Scope.SCOPE_2).exists()
        )
        self.assertTrue(
            NormalizedActivity.objects.filter(scope=NormalizedActivity.Scope.SCOPE_3).exists()
        )

    def test_upload_endpoint_accepts_sample_csvs(self) -> None:
        samples = [
            ("sap", "sap_fuel_procurement.csv"),
            ("utility", "utility_electricity.csv"),
            ("travel", "travel_expenses.csv"),
        ]
        client = Client()

        for source_type, filename in samples:
            content = (SAMPLE_DIR / filename).read_bytes()
            upload = SimpleUploadedFile(filename, content, content_type="text/csv")
            response = client.post(
                "/api/ingestions/upload/",
                data={"source_type": source_type, "file": upload},
            )

            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["source_type"], source_type)

        self.assertEqual(NormalizedActivity.objects.count(), 13)
        self.assertEqual(RawRecord.objects.filter(status=RawRecord.Status.FAILED).count(), 3)

    def test_activity_edit_approve_lock_lifecycle(self) -> None:
        ingest_rows(
            self.organization,
            "sap",
            "sap_fuel_procurement.csv",
            read_sample("sap_fuel_procurement.csv"),
        )
        activity = NormalizedActivity.objects.filter(
            status=NormalizedActivity.Status.NORMALIZED
        ).first()
        self.assertIsNotNone(activity)

        client = Client()
        patch_response = client.patch(
            f"/api/activities/{activity.id}/",
            data=json.dumps(
                {
                    "normalized_quantity": "125",
                    "edit_reason": "Integration test correction",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(patch_response.status_code, 200)

        approve_response = client.post(
            f"/api/activities/{activity.id}/approve/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(approve_response.status_code, 200)

        approved_edit_response = client.patch(
            f"/api/activities/{activity.id}/",
            data=json.dumps({"normalized_quantity": "126"}),
            content_type="application/json",
        )
        self.assertEqual(approved_edit_response.status_code, 400)

        lock_response = client.post(
            f"/api/activities/{activity.id}/lock/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(lock_response.status_code, 200)

        locked_edit_response = client.patch(
            f"/api/activities/{activity.id}/",
            data=json.dumps({"normalized_quantity": "127"}),
            content_type="application/json",
        )
        self.assertEqual(locked_edit_response.status_code, 400)

    def test_facility_and_flag_filters_are_available(self) -> None:
        ingest_rows(
            self.organization,
            "utility",
            "utility_electricity.csv",
            read_sample("utility_electricity.csv"),
        )
        client = Client()

        facilities_response = client.get("/api/facilities/")
        self.assertEqual(facilities_response.status_code, 200)
        self.assertGreaterEqual(len(facilities_response.json()), 2)

        warning_response = client.get("/api/activities/?flag_severity=warning")
        self.assertEqual(warning_response.status_code, 200)
        self.assertGreaterEqual(len(warning_response.json()), 1)

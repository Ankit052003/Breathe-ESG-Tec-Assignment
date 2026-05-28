from __future__ import annotations

import csv
import math
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any, Iterable, TypedDict

from django.db import transaction
from django.db.models import QuerySet

from .models import (
    Airport,
    AuditEvent,
    EmissionFactor,
    Facility,
    IngestionBatch,
    NormalizedActivity,
    Organization,
    PlantLookup,
    RawRecord,
    ReviewFlag,
    SourceSystem,
    UnitConversion,
)


class ParsedValue(TypedDict):
    activity_type: str
    scope: str
    source_reference: str
    activity_date: date | None
    period_start: date | None
    period_end: date | None
    original_quantity: Decimal | None
    original_unit: str
    normalized_quantity: Decimal | None
    normalized_unit: str
    facility: Facility | None
    location_label: str
    department: str
    counterparty: str
    currency: str
    amount: Decimal | None
    emission_factor: EmissionFactor | None
    emissions_kg_co2e: Decimal | None
    normalized_payload: dict[str, Any]


class FlagValue(TypedDict):
    severity: str
    code: str
    field: str
    message: str


DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%Y%m%d",
)

SAP_ALIASES: dict[str, tuple[str, ...]] = {
    "document_number": ("document number", "material document", "belegnummer"),
    "posting_date": ("posting date", "buchungsdatum", "postingdate"),
    "plant_code": ("plant", "werk", "plant code"),
    "cost_center": ("cost center", "kostenstelle"),
    "material_description": ("material description", "materialkurztext", "description"),
    "material_group": ("material group", "materialgruppe"),
    "quantity": ("quantity", "menge"),
    "unit": ("unit", "base unit of measure", "basismengeneinheit", "uom"),
    "currency": ("currency", "waehrung", "wahrung"),
    "amount": ("amount", "betrag", "value"),
    "vendor": ("vendor", "lieferant", "supplier"),
}

UTILITY_ALIASES: dict[str, tuple[str, ...]] = {
    "account_number": ("account number", "account"),
    "meter_number": ("meter number", "meter"),
    "service_address": ("service address", "address"),
    "period_start": ("billing period start", "period start", "start date"),
    "period_end": ("billing period end", "period end", "end date"),
    "usage": ("usage", "usage quantity", "kwh"),
    "unit": ("usage unit", "unit"),
    "peak_demand_kw": ("peak demand kw", "demand kw"),
    "tariff": ("tariff", "rate plan", "rate"),
    "total_cost": ("total cost", "amount", "bill amount"),
    "currency": ("currency",),
}

TRAVEL_ALIASES: dict[str, tuple[str, ...]] = {
    "expense_id": ("expense id", "report entry id", "trip id"),
    "traveler": ("traveler", "employee"),
    "department": ("department", "cost center"),
    "category": ("category", "expense type", "travel category"),
    "transaction_date": ("transaction date", "date"),
    "origin_airport": ("origin airport", "from airport", "origin"),
    "destination_airport": ("destination airport", "to airport", "destination"),
    "distance": ("distance", "flight distance"),
    "distance_unit": ("distance unit", "unit"),
    "hotel_nights": ("hotel nights", "nights"),
    "ground_distance": ("ground distance", "vehicle distance"),
    "currency": ("currency",),
    "amount": ("amount", "transaction amount"),
    "vendor": ("vendor", "merchant", "carrier"),
}


def get_actor_name(request_headers: dict[str, str]) -> str:
    actor = request_headers.get("X-Analyst-Name", "").strip()
    if actor:
        return actor
    return "demo-analyst"


def get_demo_organization(slug: str | None) -> Organization:
    selected_slug = (slug or "acme-industrial").strip()
    organization = Organization.objects.filter(slug=selected_slug).first()
    if organization is None:
        raise ValueError(
            f"Organization '{selected_slug}' does not exist. Run seed_demo first."
        )
    return organization


def parse_csv_file(uploaded_file: Any) -> list[dict[str, str]]:
    content = uploaded_file.read().decode("utf-8-sig")
    reader = csv.DictReader(StringIO(content))
    if reader.fieldnames is None:
        raise ValueError("CSV file must include a header row.")
    return [dict(row) for row in reader]


def canonicalize(value: str) -> str:
    return " ".join(value.replace("_", " ").replace("-", " ").strip().lower().split())


def get_field(row: dict[str, str], aliases: dict[str, tuple[str, ...]], name: str) -> str:
    canonical_row = {canonicalize(key): value for key, value in row.items()}
    for alias in aliases[name]:
        value = canonical_row.get(canonicalize(alias))
        if value is not None:
            return value.strip()
    return ""


def parse_decimal(value: str) -> Decimal | None:
    cleaned = (
        value.strip()
        .replace("$", "")
        .replace("EUR", "")
        .replace("USD", "")
        .replace("INR", "")
        .replace(" ", "")
    )
    if cleaned == "":
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_date(value: str) -> date | None:
    cleaned = value.strip()
    if cleaned == "":
        return None
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    return None


def normalize_quantity(
    category: str, source_unit: str, quantity: Decimal | None, target_unit: str
) -> Decimal | None:
    if quantity is None:
        return None
    source = canonicalize(source_unit)
    target = canonicalize(target_unit)
    if source == target:
        return quantity
    conversion = UnitConversion.objects.filter(
        category=category, source_unit__iexact=source, target_unit__iexact=target
    ).first()
    if conversion is None:
        return None
    return quantity * conversion.multiplier


def find_emission_factor(
    activity_type: str, scope: str, unit: str, region: str
) -> EmissionFactor | None:
    factors: QuerySet[EmissionFactor] = EmissionFactor.objects.filter(
        activity_type=activity_type,
        scope=scope,
        unit__iexact=unit,
        active=True,
    )
    regional = factors.filter(region__iexact=region).first()
    if regional is not None:
        return regional
    return factors.first()


def calculate_emissions(
    quantity: Decimal | None, factor: EmissionFactor | None
) -> Decimal | None:
    if quantity is None or factor is None:
        return None
    return quantity * factor.kg_co2e_per_unit


def create_activity(
    organization: Organization,
    batch: IngestionBatch,
    raw_record: RawRecord,
    source_type: str,
    parsed: ParsedValue,
    flags: list[FlagValue],
) -> NormalizedActivity:
    status = (
        NormalizedActivity.Status.NEEDS_REVIEW
        if flags
        else NormalizedActivity.Status.NORMALIZED
    )
    activity = NormalizedActivity.objects.create(
        organization=organization,
        batch=batch,
        raw_record=raw_record,
        source_type=source_type,
        source_reference=parsed["source_reference"],
        activity_type=parsed["activity_type"],
        scope=parsed["scope"],
        status=status,
        activity_date=parsed["activity_date"],
        period_start=parsed["period_start"],
        period_end=parsed["period_end"],
        original_quantity=parsed["original_quantity"],
        original_unit=parsed["original_unit"],
        normalized_quantity=parsed["normalized_quantity"],
        normalized_unit=parsed["normalized_unit"],
        facility=parsed["facility"],
        location_label=parsed["location_label"],
        department=parsed["department"],
        counterparty=parsed["counterparty"],
        currency=parsed["currency"],
        amount=parsed["amount"],
        emission_factor=parsed["emission_factor"],
        emissions_kg_co2e=parsed["emissions_kg_co2e"],
        normalized_payload=parsed["normalized_payload"],
        edited_fields={},
    )
    ReviewFlag.objects.bulk_create(
        [
            ReviewFlag(
                activity=activity,
                severity=flag["severity"],
                code=flag["code"],
                field=flag["field"],
                message=flag["message"],
            )
            for flag in flags
        ]
    )
    AuditEvent.objects.create(
        organization=organization,
        batch=batch,
        activity=activity,
        action="normalized",
        actor_name="system",
        changes={
            "status": status,
            "flag_count": len(flags),
            "source_type": source_type,
        },
    )
    return activity


def flag(severity: str, code: str, field: str, message: str) -> FlagValue:
    return {"severity": severity, "code": code, "field": field, "message": message}


def lookup_plant_facility(
    organization: Organization, plant_code: str, flags: list[FlagValue]
) -> Facility | None:
    if plant_code == "":
        flags.append(
            flag("error", "missing_plant", "plant_code", "SAP plant code is missing.")
        )
        return None
    lookup = PlantLookup.objects.filter(
        organization=organization, plant_code=plant_code
    ).select_related("facility").first()
    if lookup is None:
        flags.append(
            flag(
                "warning",
                "unknown_plant",
                "plant_code",
                f"SAP plant code '{plant_code}' is not mapped to a facility.",
            )
        )
        return None
    return lookup.facility


def lookup_meter_facility(
    organization: Organization,
    meter_number: str,
    service_address: str,
    flags: list[FlagValue],
) -> Facility | None:
    if meter_number:
        facility = Facility.objects.filter(
            organization=organization, meter_number__iexact=meter_number
        ).first()
        if facility is not None:
            return facility
    if service_address:
        facility = Facility.objects.filter(
            organization=organization, service_address__icontains=service_address[:20]
        ).first()
        if facility is not None:
            return facility
    flags.append(
        flag(
            "warning",
            "unknown_meter",
            "meter_number",
            "Utility meter or service address is not mapped to a facility.",
        )
    )
    return None


def classify_sap_activity(
    material_description: str, material_group: str
) -> tuple[str, str, str, str]:
    combined = f"{material_description} {material_group}".lower()
    if "diesel" in combined:
        return ("stationary_diesel", NormalizedActivity.Scope.SCOPE_1, "fuel", "gallon")
    if "gasoline" in combined or "petrol" in combined:
        return ("stationary_gasoline", NormalizedActivity.Scope.SCOPE_1, "fuel", "gallon")
    return ("procurement_spend", NormalizedActivity.Scope.SCOPE_3, "spend", "usd")


def parse_sap_row(
    organization: Organization, row: dict[str, str]
) -> tuple[ParsedValue, list[FlagValue]]:
    flags: list[FlagValue] = []
    document_number = get_field(row, SAP_ALIASES, "document_number")
    posting_date = parse_date(get_field(row, SAP_ALIASES, "posting_date"))
    plant_code = get_field(row, SAP_ALIASES, "plant_code")
    material_description = get_field(row, SAP_ALIASES, "material_description")
    material_group = get_field(row, SAP_ALIASES, "material_group")
    quantity = parse_decimal(get_field(row, SAP_ALIASES, "quantity"))
    unit = get_field(row, SAP_ALIASES, "unit")
    amount = parse_decimal(get_field(row, SAP_ALIASES, "amount"))
    currency = get_field(row, SAP_ALIASES, "currency").upper()
    vendor = get_field(row, SAP_ALIASES, "vendor")
    department = get_field(row, SAP_ALIASES, "cost_center")

    if posting_date is None:
        flags.append(
            flag("error", "invalid_date", "posting_date", "Posting date is missing or invalid.")
        )
    facility = lookup_plant_facility(organization, plant_code, flags)
    activity_type, scope, category, target_unit = classify_sap_activity(
        material_description, material_group
    )

    if category == "fuel":
        if quantity is None:
            flags.append(
                flag("error", "missing_quantity", "quantity", "Fuel quantity is missing.")
            )
        normalized_quantity = normalize_quantity(category, unit, quantity, target_unit)
        if normalized_quantity is None and quantity is not None:
            flags.append(
                flag(
                    "error",
                    "unknown_unit",
                    "unit",
                    f"Fuel unit '{unit}' cannot be converted to gallons.",
                )
            )
        normalized_unit = target_unit
    else:
        if amount is None:
            flags.append(
                flag("error", "missing_amount", "amount", "Procurement spend is missing.")
            )
        if currency not in {"USD", ""}:
            flags.append(
                flag(
                    "warning",
                    "currency_not_converted",
                    "currency",
                    f"Currency '{currency}' is stored but not converted in the prototype.",
                )
            )
        normalized_quantity = amount
        normalized_unit = target_unit

    factor = find_emission_factor(activity_type, scope, normalized_unit, "")
    if factor is None:
        flags.append(
            flag(
                "warning",
                "missing_factor",
                "emission_factor",
                f"No emission factor exists for {activity_type}/{normalized_unit}.",
            )
        )
    emissions = calculate_emissions(normalized_quantity, factor)

    parsed: ParsedValue = {
        "activity_type": activity_type,
        "scope": scope,
        "source_reference": document_number,
        "activity_date": posting_date,
        "period_start": None,
        "period_end": None,
        "original_quantity": quantity,
        "original_unit": unit,
        "normalized_quantity": normalized_quantity,
        "normalized_unit": normalized_unit,
        "facility": facility,
        "location_label": plant_code,
        "department": department,
        "counterparty": vendor,
        "currency": currency,
        "amount": amount,
        "emission_factor": factor,
        "emissions_kg_co2e": emissions,
        "normalized_payload": {
            "plant_code": plant_code,
            "material_description": material_description,
            "material_group": material_group,
        },
    }
    return parsed, flags


def parse_utility_row(
    organization: Organization, row: dict[str, str]
) -> tuple[ParsedValue, list[FlagValue]]:
    flags: list[FlagValue] = []
    account_number = get_field(row, UTILITY_ALIASES, "account_number")
    meter_number = get_field(row, UTILITY_ALIASES, "meter_number")
    service_address = get_field(row, UTILITY_ALIASES, "service_address")
    period_start = parse_date(get_field(row, UTILITY_ALIASES, "period_start"))
    period_end = parse_date(get_field(row, UTILITY_ALIASES, "period_end"))
    usage = parse_decimal(get_field(row, UTILITY_ALIASES, "usage"))
    unit = get_field(row, UTILITY_ALIASES, "unit")
    tariff = get_field(row, UTILITY_ALIASES, "tariff")
    amount = parse_decimal(get_field(row, UTILITY_ALIASES, "total_cost"))
    currency = get_field(row, UTILITY_ALIASES, "currency").upper()

    if period_start is None or period_end is None:
        flags.append(
            flag(
                "error",
                "invalid_billing_period",
                "billing_period",
                "Billing period start or end date is missing or invalid.",
            )
        )
    elif period_end < period_start:
        flags.append(
            flag(
                "error",
                "reversed_billing_period",
                "billing_period",
                "Billing period end is before billing period start.",
            )
        )
    if usage is None:
        flags.append(
            flag("error", "missing_usage", "usage", "Electricity usage is missing.")
        )

    facility = lookup_meter_facility(organization, meter_number, service_address, flags)
    normalized_quantity = normalize_quantity("electricity", unit, usage, "kwh")
    if normalized_quantity is None and usage is not None:
        flags.append(
            flag(
                "error",
                "unknown_unit",
                "unit",
                f"Electricity unit '{unit}' cannot be converted to kWh.",
            )
        )
    if normalized_quantity is not None and normalized_quantity > Decimal("100000"):
        flags.append(
            flag(
                "warning",
                "extreme_usage",
                "usage",
                "Electricity usage is unusually high for one billing period.",
            )
        )

    factor = find_emission_factor(
        "purchased_electricity",
        NormalizedActivity.Scope.SCOPE_2,
        "kwh",
        facility.grid_region if facility is not None else "",
    )
    emissions = calculate_emissions(normalized_quantity, factor)

    parsed: ParsedValue = {
        "activity_type": "purchased_electricity",
        "scope": NormalizedActivity.Scope.SCOPE_2,
        "source_reference": f"{account_number}:{meter_number}",
        "activity_date": period_end,
        "period_start": period_start,
        "period_end": period_end,
        "original_quantity": usage,
        "original_unit": unit,
        "normalized_quantity": normalized_quantity,
        "normalized_unit": "kwh",
        "facility": facility,
        "location_label": service_address,
        "department": "",
        "counterparty": "Utility provider",
        "currency": currency,
        "amount": amount,
        "emission_factor": factor,
        "emissions_kg_co2e": emissions,
        "normalized_payload": {
            "account_number": account_number,
            "meter_number": meter_number,
            "tariff": tariff,
        },
    }
    return parsed, flags


def airport_distance_miles(origin_code: str, destination_code: str) -> Decimal | None:
    origin = Airport.objects.filter(code__iexact=origin_code).first()
    destination = Airport.objects.filter(code__iexact=destination_code).first()
    if origin is None or destination is None:
        return None
    radius_miles = 3958.8
    lat_1 = math.radians(origin.latitude)
    lat_2 = math.radians(destination.latitude)
    delta_lat = math.radians(destination.latitude - origin.latitude)
    delta_lon = math.radians(destination.longitude - origin.longitude)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_1) * math.cos(lat_2) * math.sin(delta_lon / 2) ** 2
    )
    miles = 2 * radius_miles * math.asin(math.sqrt(haversine))
    return Decimal(str(round(miles, 2)))


def normalize_distance(
    distance: Decimal | None, unit: str, flags: list[FlagValue]
) -> Decimal | None:
    if distance is None:
        return None
    if unit == "":
        return distance
    normalized = normalize_quantity("distance", unit, distance, "mile")
    if normalized is None:
        flags.append(
            flag(
                "error",
                "unknown_distance_unit",
                "distance_unit",
                f"Distance unit '{unit}' cannot be converted to miles.",
            )
        )
    return normalized


def parse_travel_row(
    organization: Organization, row: dict[str, str]
) -> tuple[ParsedValue, list[FlagValue]]:
    flags: list[FlagValue] = []
    expense_id = get_field(row, TRAVEL_ALIASES, "expense_id")
    traveler = get_field(row, TRAVEL_ALIASES, "traveler")
    department = get_field(row, TRAVEL_ALIASES, "department")
    category = get_field(row, TRAVEL_ALIASES, "category")
    transaction_date = parse_date(get_field(row, TRAVEL_ALIASES, "transaction_date"))
    origin_airport = get_field(row, TRAVEL_ALIASES, "origin_airport").upper()
    destination_airport = get_field(row, TRAVEL_ALIASES, "destination_airport").upper()
    distance = parse_decimal(get_field(row, TRAVEL_ALIASES, "distance"))
    distance_unit = get_field(row, TRAVEL_ALIASES, "distance_unit")
    hotel_nights = parse_decimal(get_field(row, TRAVEL_ALIASES, "hotel_nights"))
    ground_distance = parse_decimal(get_field(row, TRAVEL_ALIASES, "ground_distance"))
    amount = parse_decimal(get_field(row, TRAVEL_ALIASES, "amount"))
    currency = get_field(row, TRAVEL_ALIASES, "currency").upper()
    vendor = get_field(row, TRAVEL_ALIASES, "vendor")

    if transaction_date is None:
        flags.append(
            flag(
                "error",
                "invalid_date",
                "transaction_date",
                "Travel transaction date is missing or invalid.",
            )
        )

    lowered_category = category.lower()
    activity_type = "unsupported_travel"
    normalized_quantity: Decimal | None = None
    normalized_unit = ""
    original_quantity: Decimal | None = None
    original_unit = ""
    location_label = ""

    if "flight" in lowered_category or "air" in lowered_category:
        activity_type = "business_travel_air"
        original_quantity = distance
        original_unit = distance_unit
        normalized_unit = "mile"
        normalized_quantity = normalize_distance(distance, distance_unit, flags)
        if normalized_quantity is None:
            if origin_airport == "" or destination_airport == "":
                flags.append(
                    flag(
                        "error",
                        "missing_airport_codes",
                        "airport_codes",
                        "Flight distance is missing and airport codes are incomplete.",
                    )
                )
            else:
                normalized_quantity = airport_distance_miles(
                    origin_airport, destination_airport
                )
                if normalized_quantity is None:
                    flags.append(
                        flag(
                            "warning",
                            "unknown_airport",
                            "airport_codes",
                            "Airport lookup does not contain the supplied route.",
                        )
                    )
        location_label = f"{origin_airport}-{destination_airport}".strip("-")
    elif "hotel" in lowered_category or "lodging" in lowered_category:
        activity_type = "hotel_night"
        original_quantity = hotel_nights
        original_unit = "night"
        normalized_quantity = hotel_nights
        normalized_unit = "night"
        location_label = vendor
        if hotel_nights is None:
            flags.append(
                flag("error", "missing_nights", "hotel_nights", "Hotel nights are missing.")
            )
    elif (
        "taxi" in lowered_category
        or "rental" in lowered_category
        or "ground" in lowered_category
        or "rail" in lowered_category
    ):
        activity_type = "ground_transport"
        original_quantity = ground_distance or distance
        original_unit = distance_unit or "mile"
        normalized_quantity = normalize_distance(original_quantity, original_unit, flags)
        normalized_unit = "mile"
        location_label = vendor
        if original_quantity is None:
            flags.append(
                flag(
                    "error",
                    "missing_ground_distance",
                    "ground_distance",
                    "Ground transport distance is missing.",
                )
            )
    else:
        flags.append(
            flag(
                "error",
                "unsupported_category",
                "category",
                f"Travel category '{category}' is not supported by the prototype.",
            )
        )

    factor = find_emission_factor(
        activity_type,
        NormalizedActivity.Scope.SCOPE_3,
        normalized_unit,
        "",
    )
    if factor is None:
        flags.append(
            flag(
                "warning",
                "missing_factor",
                "emission_factor",
                f"No emission factor exists for {activity_type}/{normalized_unit}.",
            )
        )
    emissions = calculate_emissions(normalized_quantity, factor)

    parsed: ParsedValue = {
        "activity_type": activity_type,
        "scope": NormalizedActivity.Scope.SCOPE_3,
        "source_reference": expense_id,
        "activity_date": transaction_date,
        "period_start": None,
        "period_end": None,
        "original_quantity": original_quantity,
        "original_unit": original_unit,
        "normalized_quantity": normalized_quantity,
        "normalized_unit": normalized_unit,
        "facility": None,
        "location_label": location_label,
        "department": department,
        "counterparty": vendor or traveler,
        "currency": currency,
        "amount": amount,
        "emission_factor": factor,
        "emissions_kg_co2e": emissions,
        "normalized_payload": {
            "traveler": traveler,
            "category": category,
            "origin_airport": origin_airport,
            "destination_airport": destination_airport,
        },
    }
    return parsed, flags


def parse_row_by_source(
    organization: Organization, source_type: str, row: dict[str, str]
) -> tuple[ParsedValue, list[FlagValue]]:
    if source_type == SourceSystem.SourceType.SAP:
        return parse_sap_row(organization, row)
    if source_type == SourceSystem.SourceType.UTILITY:
        return parse_utility_row(organization, row)
    if source_type == SourceSystem.SourceType.TRAVEL:
        return parse_travel_row(organization, row)
    raise ValueError(f"Unsupported source type '{source_type}'.")


def has_error(flags: Iterable[FlagValue]) -> bool:
    return any(flag_value["severity"] == ReviewFlag.Severity.ERROR for flag_value in flags)


@transaction.atomic
def ingest_rows(
    organization: Organization,
    source_type: str,
    filename: str,
    rows: list[dict[str, str]],
) -> IngestionBatch:
    source_system = SourceSystem.objects.filter(
        organization=organization, source_type=source_type
    ).first()
    if source_system is None:
        raise ValueError(
            f"Source system '{source_type}' is not configured for {organization.slug}."
        )

    batch = IngestionBatch.objects.create(
        organization=organization,
        source_system=source_system,
        source_type=source_type,
        filename=filename,
        status=IngestionBatch.Status.RECEIVED,
        total_rows=len(rows),
        normalized_rows=0,
        failed_rows=0,
    )
    AuditEvent.objects.create(
        organization=organization,
        batch=batch,
        action="batch_received",
        actor_name="system",
        changes={"source_type": source_type, "filename": filename, "rows": len(rows)},
    )

    failed_rows = 0
    flagged_rows = 0
    for index, row in enumerate(rows, start=2):
        parsed, flags = parse_row_by_source(organization, source_type, row)
        raw_status = RawRecord.Status.FAILED if has_error(flags) else RawRecord.Status.PARSED
        if flags:
            flagged_rows += 1
        if raw_status == RawRecord.Status.FAILED:
            failed_rows += 1
        raw_record = RawRecord.objects.create(
            organization=organization,
            batch=batch,
            row_number=index,
            source_payload=row,
            status=raw_status,
            parse_errors=[
                flag_value for flag_value in flags if flag_value["severity"] == "error"
            ],
        )
        create_activity(organization, batch, raw_record, source_type, parsed, flags)

    batch.normalized_rows = len(rows)
    batch.failed_rows = failed_rows
    batch.status = (
        IngestionBatch.Status.COMPLETED_WITH_FLAGS
        if flagged_rows > 0
        else IngestionBatch.Status.COMPLETED
    )
    batch.save(update_fields=["normalized_rows", "failed_rows", "status"])
    AuditEvent.objects.create(
        organization=organization,
        batch=batch,
        action="batch_completed",
        actor_name="system",
        changes={
            "status": batch.status,
            "normalized_rows": batch.normalized_rows,
            "failed_rows": batch.failed_rows,
            "flagged_rows": flagged_rows,
        },
    )
    return batch


def recalculate_activity_emissions(activity: NormalizedActivity) -> None:
    factor = find_emission_factor(
        activity.activity_type,
        activity.scope,
        activity.normalized_unit,
        activity.facility.grid_region if activity.facility is not None else "",
    )
    activity.emission_factor = factor
    activity.emissions_kg_co2e = calculate_emissions(
        activity.normalized_quantity, factor
    )

from decimal import Decimal

from django.core.management.base import BaseCommand

from review.models import (
    Airport,
    EmissionFactor,
    Facility,
    Organization,
    PlantLookup,
    SourceSystem,
    UnitConversion,
)


class Command(BaseCommand):
    help = "Seed the demo tenant, lookup tables, and prototype emission factors."

    def handle(self, *args: object, **options: object) -> None:
        organization, _ = Organization.objects.update_or_create(
            slug="acme-industrial",
            defaults={"name": "Acme Industrial"},
        )

        bengaluru, _ = Facility.objects.update_or_create(
            organization=organization,
            code="BLR-MFG",
            defaults={
                "name": "Bengaluru Manufacturing Plant",
                "meter_number": "BLR-EL-01",
                "service_address": "42 Peenya Industrial Area, Bengaluru",
                "grid_region": "US average",
            },
        )
        pune, _ = Facility.objects.update_or_create(
            organization=organization,
            code="PUN-DC",
            defaults={
                "name": "Pune Distribution Center",
                "meter_number": "PUN-EL-02",
                "service_address": "8 Chakan Logistics Park, Pune",
                "grid_region": "US average",
            },
        )

        for source_type, name, description in [
            (
                SourceSystem.SourceType.SAP,
                "SAP ECC export",
                "CSV exported from an SAP ALV/material document style report.",
            ),
            (
                SourceSystem.SourceType.UTILITY,
                "Utility portal export",
                "CSV export of monthly meter usage and billing period data.",
            ),
            (
                SourceSystem.SourceType.TRAVEL,
                "Corporate travel report",
                "Concur-like expense export for flights, hotels, and ground travel.",
            ),
        ]:
            SourceSystem.objects.update_or_create(
                organization=organization,
                source_type=source_type,
                name=name,
                defaults={"description": description},
            )

        PlantLookup.objects.update_or_create(
            organization=organization,
            plant_code="1000",
            defaults={"facility": bengaluru},
        )
        PlantLookup.objects.update_or_create(
            organization=organization,
            plant_code="2000",
            defaults={"facility": pune},
        )

        conversions = [
            ("fuel", "l", "gallon", "0.26417205", "Liters to US gallons."),
            ("fuel", "liter", "gallon", "0.26417205", "Liters to US gallons."),
            ("fuel", "litre", "gallon", "0.26417205", "Litres to US gallons."),
            ("fuel", "gal", "gallon", "1", "US gallons alias."),
            ("electricity", "mwh", "kwh", "1000", "Megawatt-hours to kWh."),
            ("distance", "km", "mile", "0.62137119", "Kilometers to miles."),
            ("distance", "kilometer", "mile", "0.62137119", "Kilometers to miles."),
        ]
        for category, source_unit, target_unit, multiplier, notes in conversions:
            UnitConversion.objects.update_or_create(
                category=category,
                source_unit=source_unit,
                target_unit=target_unit,
                defaults={"multiplier": Decimal(multiplier), "notes": notes},
            )

        factors = [
            (
                "stationary_diesel",
                "scope_1",
                "gallon",
                "10.21",
                "",
                "EPA GHG Emission Factors Hub, diesel fuel kg CO2 per gallon.",
            ),
            (
                "stationary_gasoline",
                "scope_1",
                "gallon",
                "8.89",
                "",
                "EPA GHG Emission Factors Hub, gasoline kg CO2 per gallon.",
            ),
            (
                "purchased_electricity",
                "scope_2",
                "kwh",
                "0.637",
                "US average",
                "EPA eGRID/equivalencies national delivered electricity proxy.",
            ),
            (
                "procurement_spend",
                "scope_3",
                "usd",
                "0.35",
                "",
                "Prototype spend-based factor for purchased goods screening.",
            ),
            (
                "business_travel_air",
                "scope_3",
                "mile",
                "0.18",
                "",
                "Prototype passenger-mile factor for air travel screening.",
            ),
            (
                "hotel_night",
                "scope_3",
                "night",
                "30",
                "",
                "Prototype hotel stay factor per room-night.",
            ),
            (
                "ground_transport",
                "scope_3",
                "mile",
                "0.30",
                "",
                "Prototype passenger-mile factor for taxi/rental/rail rows.",
            ),
        ]
        for activity_type, scope, unit, factor, region, source in factors:
            EmissionFactor.objects.update_or_create(
                activity_type=activity_type,
                scope=scope,
                unit=unit,
                region=region,
                defaults={
                    "kg_co2e_per_unit": Decimal(factor),
                    "source": source,
                    "active": True,
                },
            )

        airports = [
            ("BLR", "Kempegowda International Airport", "13.1986", "77.7066"),
            ("BOM", "Chhatrapati Shivaji Maharaj International Airport", "19.0896", "72.8656"),
            ("DEL", "Indira Gandhi International Airport", "28.5562", "77.1000"),
            ("JFK", "John F. Kennedy International Airport", "40.6413", "-73.7781"),
            ("LHR", "London Heathrow Airport", "51.4700", "-0.4543"),
            ("SFO", "San Francisco International Airport", "37.6213", "-122.3790"),
        ]
        for code, name, latitude, longitude in airports:
            Airport.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                },
            )

        if int(options.get("verbosity", 1)) > 0:
            self.stdout.write(
                self.style.SUCCESS("Seeded demo organization, lookups, and factors.")
            )

# Data Model

## Shape of the System

The prototype uses source-specific ingestion adapters that preserve every uploaded row as a `RawRecord`, then create one analyst-reviewable `NormalizedActivity`. This split is intentional: auditors and analysts need the untouched source payload, while calculations and workflow need one consistent activity table.

## Tables

### Organization

Tenant boundary. Every facility, source system, batch, raw row, normalized activity, and audit event belongs to an organization. The demo seed creates `acme-industrial`, but the schema is ready for multiple clients without mixing data.

### Facility

Operational location inside an organization. It stores a local code, service address, utility meter number, and grid region. SAP rows attach through plant-code lookup; utility rows attach through meter number or service address.

### SourceSystem

Configured upstream source for a tenant. The prototype seeds three source types:

- `sap`: SAP ECC / S/4HANA style export.
- `utility`: electricity portal export.
- `travel`: corporate travel / expense report.

### PlantLookup

Maps SAP plant codes to tenant facilities. This exists because SAP plant codes are usually opaque outside SAP and should not be treated as facility names.

### Airport

Small airport lookup for travel rows. It lets the prototype infer flight distance when a travel export has airport codes but no distance. Unknown airports are flagged instead of guessed.

### UnitConversion

Stores deterministic conversions used during normalization:

- fuel liters to gallons
- MWh to kWh
- kilometers to miles

Conversions are stored as data so the calculation path can be inspected instead of hidden in one parser.

### EmissionFactor

Prototype factor table keyed by activity type, scope, unit, and optional region. The seed includes screening factors for diesel, gasoline, electricity, procurement spend, flights, hotel nights, and ground transport. These factors are deliberately simple and documented as a tradeoff.

### IngestionBatch

One uploaded file. It records source type, filename, received/completed status, total rows, normalized rows, and failed rows.

### RawRecord

The exact parsed CSV row, row number, parse status, and parse errors. This is the source-of-truth layer for audit traceability.

### NormalizedActivity

The central review row. It stores:

- tenant, batch, raw record, source type, and source reference
- activity type and GHG Protocol scope
- activity date or billing period
- original quantity/unit and normalized quantity/unit
- facility, location, department, vendor/carrier/supplier
- currency and spend amount
- emission factor and estimated kgCO2e
- normalized payload for source-specific context
- review status: `normalized`, `needs_review`, `approved`, `rejected`, `locked`
- edited fields and edit reason

Scope mapping used in the prototype:

- Scope 1: onsite/company fuel combustion from SAP fuel rows.
- Scope 2: purchased electricity from utility rows.
- Scope 3: procurement spend and business travel rows.

### ReviewFlag

Validation and suspicion findings attached to a normalized activity. Examples:

- unknown SAP plant
- unknown unit
- invalid billing period
- unknown utility meter
- extreme electricity usage
- missing flight distance or unknown airport
- unsupported travel category

Rows with flags remain reviewable. Severe parse problems mark the raw record as failed and the normalized activity as `needs_review`.

### AuditEvent

Append-only event log for import, normalization, edit, approval, rejection, and lock actions. Each event stores actor name and JSON changes. Edits and status changes are blocked after an activity reaches `locked`.

## Why This Model

The model optimizes for analyst review and audit defense rather than generic CRUD. The raw layer preserves provenance, the normalized layer enables one dashboard across very different sources, and the audit layer explains how a row moved from source data to approved emissions activity.

## Review Lifecycle

Analysts can edit only `normalized` and `needs_review` rows. After a row is `approved` or `rejected`, normalized values are no longer editable through the API. Only approved rows can be locked, and locked rows reject all edit and status-change attempts. This keeps approval meaningful: the approved values are the values that can later be locked for audit.

## Production Extensions

Production would need stricter tenant auth, row-level permissions, background ingestion jobs, versioned emission factors, stronger currency conversion, bulk workflow controls, object storage for original files, and source connector credentials. Those are outside the four-day prototype scope.

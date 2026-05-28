# Decisions

## Overall Scope

I built a narrow analyst-review workflow: upload realistic CSV exports, normalize rows, flag suspicious data, edit before sign-off, approve/reject, and lock rows for audit. I did not build full connector infrastructure because the assignment grades data judgment more heavily than feature breadth.

## SAP

Decision: support an SAP ALV/local-file style CSV export for fuel and procurement rows.

Why: SAP can expose data through IDoc, BAPI, OData, and report exports, but enterprise onboarding often starts with exported reports before formal integration access exists. A CSV export is realistic for a prototype and still forces SAP-specific problems: German headers, plant codes, mixed dates, inconsistent units, and material descriptions.

Handled:

- German header aliases such as `Belegnummer`, `Buchungsdatum`, `Werk`, `Menge`, and `Basismengeneinheit`.
- Plant-code lookup.
- Mixed date formats.
- Fuel rows normalized to gallons.
- Procurement rows normalized as spend-based Scope 3 screening rows.

Ignored:

- IDoc segment parsing.
- BAPI/OData authentication.
- SAP material master enrichment.
- Currency conversion.

## Utility Electricity

Decision: support a utility portal CSV export instead of PDF parsing or API pull.

Why: facility teams commonly download electricity usage data from portals, including Green Button-style usage exports. CSV is more credible than asking analysts to hand key bills and more feasible than PDF parsing in four days.

Handled:

- Meter number and service address lookup.
- Billing period start/end that do not need to align to calendar months.
- kWh and MWh normalization to kWh.
- Tariff/rate plan stored as metadata.
- Invalid billing periods and extreme usage flags.

Ignored:

- PDF bill extraction.
- Interval-level Green Button XML parsing.
- Demand charge calculation.
- Utility-specific tariff math.

## Corporate Travel

Decision: support a Concur-like expense/travel CSV report.

Why: Concur-style report entries expose transaction date, expense type, currency, amount, vendor, and configured fields. For carbon accounting, the hard part is that flights, hotels, and ground transport need different activity quantities. The prototype models that split directly.

Handled:

- Flight rows using distance if supplied, otherwise airport-code distance inference for a small lookup.
- Hotel rows using nights.
- Ground transport rows using distance.
- Unsupported categories flagged for analyst review.

Ignored:

- Real Concur/Navan API auth.
- Multi-leg itineraries.
- Cabin class and radiative forcing factors.
- Hotel country-specific factors.

## Auth And Tenancy

Decision: implement tenant-aware data models and demo-tenant API behavior, but no login UI.

Why: The grading criteria require multi-tenancy in the data model. Building production auth would take time away from ingestion realism and review workflow. API calls default to the seeded `acme-industrial` tenant.

## Review Locking

Decision: allow edits only while rows are `normalized` or `needs_review`.

Why: If an analyst could change an approved row before locking it, approval would no longer mean a specific reviewed value. The prototype keeps approval and locking defensible by blocking edits after approval, rejection, or lock.

## PM Questions

- Which SAP module/report is the source of truth for fuel and procurement during onboarding?
- Are client facility identifiers already mapped to SAP plant codes and utility meter numbers?
- Which countries and grid regions matter for electricity factors?
- Should analysts be allowed to edit normalized quantities, or should edits create adjustment rows?
- What evidence package do auditors expect for each approved row?
- Which travel platform fields are guaranteed: airport codes, distance, cabin class, hotel country, vehicle distance?

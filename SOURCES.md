# Sources And Sample Data

## SAP Fuel And Procurement

Researched formats:

- SAP Help, SAP GUI export to spreadsheet/local file: https://help.sap.com/docs/ABAP_PLATFORM_NEW/b1c834a22d05483b8a75710743b5ff26/e18dd05de0b24f46a701edc9607431bc.html
- SAP Help, material document OData service showing material-document access by posting date, plant, and storage location: https://help.sap.com/docs/SAP_S4HANA_CLOUD/3f57e7df4a114edabffe8b2d581a59ed/78f5a8461d554cc38b3af2d07d6f9c8e.html
- SAP Help, material-document item fields including plant, base unit, and quantity: https://help.sap.com/docs/SAP_S4HANA_CLOUD/3f57e7df4a114edabffe8b2d581a59ed/8c451658745b1f60e10000000a44147b.html

What I learned:

- SAP data can arrive through formal APIs, IDocs, BAPIs, or exported operational reports.
- Plant code, posting date, material document number, quantity, unit, material description, amount, currency, and vendor are realistic line-level fields.
- SAP exports may be localized; German labels are common in some client configurations.
- Plant codes are not human-friendly facility names and need lookup data.

Sample file: `sample_data/sap_fuel_procurement.csv`

The sample uses German-style headers including `Belegnummer`, `Buchungsdatum`, `Werk`, `Menge`, and `Basismengeneinheit`. It includes liters, gallons, a procurement row in EUR, an unknown plant code, and a missing fuel quantity.

What would break in production:

- IDoc/BAPI/OData integration would need a connector instead of CSV upload.
- Real SAP units may use ISO or SAP internal unit codes.
- Procurement emissions should not rely only on spend.
- Currency conversion and material master enrichment are not implemented.

## Utility Electricity

Researched formats:

- Green Button Download My Data overview: https://www.greenbuttonalliance.org/green-button-download-my-data-dmd
- Green Button standard overview: https://www.greenbuttonalliance.org/green-button
- Green Button Connect My Data overview: https://www.greenbuttondata.org/cmd.html

What I learned:

- Utility usage data can be downloaded from portals as utility-specific CSVs or shared through Green Button-style XML standards.
- Electricity records need meter/account identity, usage quantity, units, and time period.
- Usage intervals vary; monthly billing periods do not necessarily align to calendar months.
- Demand and tariff data matter for cost review even if they are not directly used for Scope 2 emissions.

Sample file: `sample_data/utility_electricity.csv`

The sample includes account number, meter number, service address, billing start/end, usage, kWh/MWh units, peak demand, tariff, cost, and currency. It includes a reversed billing period, an unknown meter, and an unusually high usage row.

What would break in production:

- Green Button XML/ESPI interval parsing is not implemented.
- Utility bills with multiple meters, taxes, riders, and adjustments need richer bill-line modeling.
- Location-based electricity factors should use real grid subregions and reporting year.
- Market-based Scope 2 instruments are not modeled.

## Corporate Travel

Researched formats:

- SAP Concur report entry data fields: https://help.sap.com/docs/CONCUR_EXPENSE/bb83754b1c5541808d50c09901e11475/1519c0a1377f45df83a7498e8c22f741.html
- SAP Concur developer expense configuration reference: https://preview.developer.concur.com/api-reference/expense/expense-config/v4.expense.config.html

What I learned:

- Concur-style entries include transaction date, expense type, currency, exchange rate, vendor, description, and configurable fields.
- Carbon treatment depends on expense category: flights need distance and airports, hotels need nights and country, ground transport needs distance or vehicle detail.
- Distance is not guaranteed in expense rows, so airport-code inference and analyst review are necessary.

Sample file: `sample_data/travel_expenses.csv`

The sample includes flights, hotels, taxi/ground transport, and an unsupported meal row. One flight has airport codes but no distance, one has an unknown airport code, the hotel uses nights, and taxi travel uses kilometers.

What would break in production:

- Multi-leg trips and cabin class are not modeled.
- Hotel factors should vary by country and year.
- Ground transport needs vehicle type, fuel type, or supplier-specific data for better accuracy.
- Real APIs need OAuth, pagination, retry behavior, and field mapping per client.

## Accounting And Factors

Reference standards and factor sources:

- GHG Protocol Corporate Standard: https://ghgprotocol.org/corporate-standard
- GHG Protocol Scope 3 Standard: https://ghgprotocol.org/standards/scope-3-standard
- EPA GHG Emission Factors Hub: https://www.epa.gov/climateleadership/ghg-emission-factors-hub
- EPA eGRID: https://www.epa.gov/egrid

The seeded factors are screening values for prototype workflow validation, not production reporting factors.

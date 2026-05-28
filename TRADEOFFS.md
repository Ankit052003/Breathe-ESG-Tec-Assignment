# Tradeoffs

## 1. No PDF Utility Bill Parsing

I chose utility portal CSV ingestion instead of PDF bill parsing. PDF parsing would consume most of the prototype time and still be brittle across utility templates. The current model stores billing periods, meters, usage, tariffs, and cost, so a future PDF parser could feed the same normalized activity model.

## 2. No Real SAP Or Travel API Connectors

I did not implement SAP OData/BAPI/IDoc or Concur/Navan API authentication. Real connector work depends on tenant credentials, network access, source permissions, and exact customer configuration. The prototype focuses on adapter boundaries and realistic exported row shapes, which are the parts that can be defended without fake credentials.

## 3. No Production Emissions-Factor Engine

The app uses seeded screening factors, not a full versioned factor library. Production would require factor geography, year, source versioning, market-based vs location-based Scope 2 methods, supplier-specific procurement factors, and travel class/country adjustments. The current `EmissionFactor` table is intentionally simple but points to where that engine would attach.


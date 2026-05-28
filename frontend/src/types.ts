export type SourceType = "sap" | "utility" | "travel";

export type Facility = {
  id: number;
  code: string;
  name: string;
  meter_number: string;
  service_address: string;
  grid_region: string;
};

export type ReviewFlag = {
  id: number;
  severity: "info" | "warning" | "error";
  code: string;
  field: string;
  message: string;
  created_at: string;
};

export type RawRecord = {
  id: number;
  row_number: number;
  source_payload: Record<string, string>;
  status: string;
  parse_errors: ReviewFlag[];
  created_at: string;
};

export type AuditEvent = {
  id: number;
  action: string;
  actor_name: string;
  changes: Record<string, unknown>;
  created_at: string;
};

export type Activity = {
  id: number;
  source_type: SourceType;
  source_reference: string;
  activity_type: string;
  scope: "scope_1" | "scope_2" | "scope_3";
  status: "normalized" | "needs_review" | "approved" | "rejected" | "locked";
  activity_date: string | null;
  period_start: string | null;
  period_end: string | null;
  original_quantity: string | null;
  original_unit: string;
  normalized_quantity: string | null;
  normalized_unit: string;
  facility: Facility | null;
  location_label: string;
  department: string;
  counterparty: string;
  currency: string;
  amount: string | null;
  emissions_kg_co2e: string | null;
  normalized_payload: Record<string, unknown>;
  edited_fields: Record<string, unknown>;
  edit_reason: string;
  created_at: string;
  updated_at: string;
  batch_filename: string;
  flags: ReviewFlag[];
  raw_record?: RawRecord;
  audit_events?: AuditEvent[];
};

export type Batch = {
  id: number;
  source_system_name: string;
  source_type: SourceType;
  filename: string;
  status: string;
  uploaded_at: string;
  total_rows: number;
  normalized_rows: number;
  failed_rows: number;
};

export type Dashboard = {
  organization: string;
  batches: number;
  activities: number;
  failed_rows: number;
  flagged_rows: number;
  review_queue_count: number;
  status_counts: Record<string, number>;
  source_counts: Record<string, number>;
  scope_counts: Record<string, number>;
};

export type Filters = {
  source_type: string;
  status: string;
  scope: string;
  facility: string;
  flagged: boolean;
  flag_severity: string;
  search: string;
};

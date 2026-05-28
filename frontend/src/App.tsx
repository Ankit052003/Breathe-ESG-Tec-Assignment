import {
  AlertTriangle,
  BarChart3,
  Building2,
  CheckCircle2,
  Database,
  Factory,
  FileUp,
  FileWarning,
  LockKeyhole,
  Plane,
  PlugZap,
  RefreshCcw,
  Save,
  Search,
  ShieldCheck,
  XCircle
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent, ReactNode } from "react";

import {
  activityAction,
  getActivities,
  getActivity,
  getBatches,
  getDashboard,
  getFacilities,
  updateActivity,
  uploadIngestion
} from "./api";
import type { Activity, Batch, Dashboard, Facility, Filters, SourceType } from "./types";

const sourceOptions: { value: SourceType; label: string }[] = [
  { value: "sap", label: "SAP" },
  { value: "utility", label: "Utility" },
  { value: "travel", label: "Travel" }
];

const sourceMeta: Record<
  SourceType,
  { label: string; caption: string; icon: ReactNode; tone: string }
> = {
  sap: {
    label: "SAP",
    caption: "Fuel + procurement",
    icon: <Factory size={19} />,
    tone: "sap"
  },
  utility: {
    label: "Utility",
    caption: "Electricity meters",
    icon: <PlugZap size={19} />,
    tone: "utility"
  },
  travel: {
    label: "Travel",
    caption: "Flights + hotels",
    icon: <Plane size={19} />,
    tone: "travel"
  }
};

const emptyFilters: Filters = {
  source_type: "",
  status: "",
  scope: "",
  facility: "",
  flagged: false,
  flag_severity: "",
  search: ""
};

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function numberValue(value: string | number | null): string {
  if (value === null) {
    return "-";
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return String(value);
  }
  return numeric.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function dateValue(value: string | null): string {
  if (!value) {
    return "-";
  }
  return value;
}

function statusTone(status: string): string {
  if (status === "locked" || status === "approved") {
    return "good";
  }
  if (status === "needs_review") {
    return "warn";
  }
  if (status === "rejected") {
    return "bad";
  }
  return "neutral";
}

function sourceTone(sourceType: string): string {
  if (sourceType === "sap" || sourceType === "utility" || sourceType === "travel") {
    return sourceType;
  }
  return "neutral";
}

function initialEditValues(activity: Activity): Record<string, string> {
  return {
    normalized_quantity: activity.normalized_quantity || "",
    normalized_unit: activity.normalized_unit || "",
    activity_date: activity.activity_date || "",
    period_start: activity.period_start || "",
    period_end: activity.period_end || "",
    department: activity.department || "",
    location_label: activity.location_label || "",
    counterparty: activity.counterparty || "",
    amount: activity.amount || "",
    currency: activity.currency || "",
    edit_reason: activity.edit_reason || ""
  };
}

function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [sourceType, setSourceType] = useState<SourceType>("sap");
  const [file, setFile] = useState<File | null>(null);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function refresh(): Promise<void> {
    setLoading(true);
    setError("");
    try {
      const [nextDashboard, nextBatches, nextFacilities, nextActivities] = await Promise.all([
        getDashboard(),
        getBatches(),
        getFacilities(),
        getActivities(filters)
      ]);
      setDashboard(nextDashboard);
      setBatches(nextBatches);
      setFacilities(nextFacilities);
      setActivities(nextActivities);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [
    filters.source_type,
    filters.status,
    filters.scope,
    filters.facility,
    filters.flagged,
    filters.flag_severity,
    filters.search
  ]);

  async function openActivity(activityId: number): Promise<void> {
    setError("");
    try {
      const detail = await getActivity(activityId);
      setSelectedActivity(detail);
      setEditValues(initialEditValues(detail));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Activity load failed");
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (file === null) {
      setError("Choose a CSV file first.");
      return;
    }
    setUploading(true);
    setError("");
    setNotice("");
    try {
      const batch = await uploadIngestion(sourceType, file);
      setNotice(
        `${label(batch.source_type)} upload completed: ${batch.normalized_rows} rows, ${batch.failed_rows} failed.`
      );
      setFile(null);
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function saveActivity(): Promise<void> {
    if (selectedActivity === null) {
      return;
    }
    setError("");
    try {
      const updated = await updateActivity(selectedActivity.id, editValues);
      setSelectedActivity(updated);
      setEditValues(initialEditValues(updated));
      setNotice(`Activity ${updated.id} saved.`);
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Save failed");
    }
  }

  async function changeStatus(action: "approve" | "reject" | "lock"): Promise<void> {
    if (selectedActivity === null) {
      return;
    }
    setError("");
    try {
      const updated = await activityAction(selectedActivity.id, action);
      setSelectedActivity(updated);
      setNotice(`Activity ${updated.id} ${action}d.`);
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Status change failed");
    }
  }

  function updateFilter(name: keyof Filters, value: string | boolean): void {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function updateEdit(name: string, value: string): void {
    setEditValues((current) => ({ ...current, [name]: value }));
  }

  const latestBatches = useMemo(() => batches.slice(0, 5), [batches]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="title-cluster">
          <p className="eyebrow">Breathe ESG prototype</p>
          <h1>Analyst review workspace</h1>
          <div className="workflow-strip" aria-label="Review lifecycle">
            <span>Ingest</span>
            <span>Normalize</span>
            <span>Review</span>
            <span>Lock</span>
          </div>
        </div>
        <div className="topbar-actions">
          <span className="tenant-badge">
            <Building2 size={16} />
            acme-industrial
          </span>
          <button className="icon-button" type="button" onClick={() => void refresh()}>
            <RefreshCcw size={18} />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {notice ? <div className="alert success">{notice}</div> : null}

      <section className="summary-grid">
        <Metric icon={<Database size={19} />} label="Batches" value={dashboard?.batches ?? 0} />
        <Metric icon={<BarChart3 size={19} />} label="Rows" value={dashboard?.activities ?? 0} />
        <Metric
          icon={<FileWarning size={19} />}
          label="Failed"
          value={dashboard?.failed_rows ?? 0}
          tone="bad"
        />
        <Metric
          icon={<AlertTriangle size={19} />}
          label="Flagged"
          value={dashboard?.flagged_rows ?? 0}
          tone="warn"
        />
        <Metric
          icon={<CheckCircle2 size={19} />}
          label="Approved"
          value={dashboard?.status_counts.approved ?? 0}
          tone="good"
        />
        <Metric
          icon={<ShieldCheck size={19} />}
          label="Locked"
          value={dashboard?.status_counts.locked ?? 0}
        />
      </section>

      <section className="insight-grid">
        <SourceMix dashboard={dashboard} />
        <ReviewProgress dashboard={dashboard} />
      </section>

      <section className="workspace-grid">
        <div className="left-column">
          <section className="surface">
            <div className="section-head">
              <h2>Upload</h2>
              <FileUp size={18} />
            </div>
            <form className="upload-form" onSubmit={(event) => void handleUpload(event)}>
              <div className="source-picker" aria-label="Source type">
                {sourceOptions.map((option) => {
                  const meta = sourceMeta[option.value];
                  return (
                    <button
                      className={`source-card ${meta.tone} ${
                        sourceType === option.value ? "active" : ""
                      }`}
                      key={option.value}
                      type="button"
                      onClick={() => setSourceType(option.value)}
                    >
                      <span className="source-icon">{meta.icon}</span>
                      <span>
                        <strong>{meta.label}</strong>
                        <small>{meta.caption}</small>
                      </span>
                    </button>
                  );
                })}
              </div>
              <label>
                <span>CSV file</span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    setFile(event.target.files?.[0] ?? null)
                  }
                />
              </label>
              <button className="primary-button" type="submit" disabled={uploading}>
                <FileUp size={18} />
                <span>{uploading ? "Uploading" : "Upload"}</span>
              </button>
              {file ? <p className="file-selected">{file.name}</p> : null}
            </form>
          </section>

          <section className="surface">
            <div className="section-head">
              <h2>Recent batches</h2>
            </div>
            <div className="batch-list">
              {latestBatches.length === 0 ? (
                <p className="empty">No batches yet.</p>
              ) : (
                latestBatches.map((batch) => (
                  <div className="batch-row" key={batch.id}>
                    <div>
                      <strong>{batch.filename}</strong>
                      <span>{label(batch.source_type)} - {batch.source_system_name}</span>
                    </div>
                    <span className={`pill ${statusTone(batch.status)}`}>{label(batch.status)}</span>
                    <span>{batch.normalized_rows}/{batch.total_rows}</span>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        <section className="surface review-surface">
          <div className="section-head review-head">
            <h2>Review queue</h2>
            <div className="loading-slot">{loading ? "Loading" : ""}</div>
          </div>

          <div className="filters">
            <label className="search-box">
              <Search size={16} />
              <input
                value={filters.search}
                placeholder="Search reference, counterparty, department"
                onChange={(event) => updateFilter("search", event.target.value)}
              />
            </label>
            <select
              value={filters.source_type}
              onChange={(event) => updateFilter("source_type", event.target.value)}
            >
              <option value="">All sources</option>
              {sourceOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={filters.status}
              onChange={(event) => updateFilter("status", event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="normalized">Normalized</option>
              <option value="needs_review">Needs review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="locked">Locked</option>
            </select>
            <select
              value={filters.scope}
              onChange={(event) => updateFilter("scope", event.target.value)}
            >
              <option value="">All scopes</option>
              <option value="scope_1">Scope 1</option>
              <option value="scope_2">Scope 2</option>
              <option value="scope_3">Scope 3</option>
            </select>
            <select
              value={filters.facility}
              onChange={(event) => updateFilter("facility", event.target.value)}
            >
              <option value="">All facilities</option>
              {facilities.map((facility) => (
                <option key={facility.id} value={facility.id}>
                  {facility.code}
                </option>
              ))}
            </select>
            <select
              value={filters.flag_severity}
              onChange={(event) => updateFilter("flag_severity", event.target.value)}
            >
              <option value="">All flag severity</option>
              <option value="warning">Warnings</option>
              <option value="error">Errors</option>
            </select>
            <label className="flag-toggle">
              <input
                type="checkbox"
                checked={filters.flagged}
                onChange={(event) => updateFilter("flagged", event.target.checked)}
              />
              <span>Flags only</span>
            </label>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ref</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Scope</th>
                  <th>Activity</th>
                  <th>Facility / Dept</th>
                  <th>Quantity</th>
                  <th>kgCO2e</th>
                  <th>Flags</th>
                </tr>
              </thead>
              <tbody>
                {activities.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="empty-cell">
                      No rows match the current filters.
                    </td>
                  </tr>
                ) : (
                  activities.map((activity) => (
                    <tr
                      key={activity.id}
                      className={selectedActivity?.id === activity.id ? "selected" : ""}
                      onClick={() => void openActivity(activity.id)}
                    >
                      <td>{activity.source_reference || `#${activity.id}`}</td>
                      <td>
                        <span className={`source-chip ${sourceTone(activity.source_type)}`}>
                          {label(activity.source_type)}
                        </span>
                      </td>
                      <td>
                        <span className={`pill ${statusTone(activity.status)}`}>
                          {label(activity.status)}
                        </span>
                      </td>
                      <td>{label(activity.scope)}</td>
                      <td>{label(activity.activity_type)}</td>
                      <td>
                        {activity.facility?.code || activity.department || activity.location_label || "-"}
                      </td>
                      <td>
                        {numberValue(activity.normalized_quantity)} {activity.normalized_unit}
                      </td>
                      <td>{numberValue(activity.emissions_kg_co2e)}</td>
                      <td>
                        {activity.flags.length > 0 ? (
                          <span className="flag-count">
                            <AlertTriangle size={14} />
                            {activity.flags.length}
                          </span>
                        ) : (
                          "-"
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </section>

      <ActivityDetail
        activity={selectedActivity}
        editValues={editValues}
        updateEdit={updateEdit}
        saveActivity={saveActivity}
        changeStatus={changeStatus}
      />
    </main>
  );
}

function Metric(props: { icon: ReactNode; label: string; value: number; tone?: string }) {
  return (
    <div className={`metric ${props.tone || ""}`}>
      <div className="metric-icon">{props.icon}</div>
      <span>{props.label}</span>
      <strong>{props.value.toLocaleString()}</strong>
    </div>
  );
}

function SourceMix(props: { dashboard: Dashboard | null }) {
  const sourceRows = [
    { key: "sap", label: "SAP", icon: <Factory size={18} /> },
    { key: "utility", label: "Utility", icon: <PlugZap size={18} /> },
    { key: "travel", label: "Travel", icon: <Plane size={18} /> }
  ];
  const total = Math.max(props.dashboard?.activities ?? 0, 1);

  return (
    <section className="surface insight-panel">
      <div className="section-head">
        <h2>Source mix</h2>
        <Database size={18} />
      </div>
      <div className="source-mix">
        {sourceRows.map((source) => {
          const count = props.dashboard?.source_counts[source.key] ?? 0;
          const width = `${Math.round((count / total) * 100)}%`;
          return (
            <div className="mix-row" key={source.key}>
              <div className="mix-label">
                {source.icon}
                <span>{source.label}</span>
              </div>
              <div className="mix-track">
                <div className={`mix-fill ${source.key}`} style={{ width }} />
              </div>
              <strong>{count}</strong>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ReviewProgress(props: { dashboard: Dashboard | null }) {
  const total = Math.max(props.dashboard?.activities ?? 0, 1);
  const approved = props.dashboard?.status_counts.approved ?? 0;
  const locked = props.dashboard?.status_counts.locked ?? 0;
  const reviewQueue = props.dashboard?.review_queue_count ?? 0;
  const flagged = props.dashboard?.flagged_rows ?? 0;

  return (
    <section className="surface insight-panel">
      <div className="section-head">
        <h2>Review progress</h2>
        <ShieldCheck size={18} />
      </div>
      <div className="progress-stack">
        <ProgressRow label="In review" value={reviewQueue} total={total} tone="review" />
        <ProgressRow label="Flagged" value={flagged} total={total} tone="flagged" />
        <ProgressRow label="Approved" value={approved} total={total} tone="approved" />
        <ProgressRow label="Locked" value={locked} total={total} tone="locked" />
      </div>
    </section>
  );
}

function ProgressRow(props: { label: string; value: number; total: number; tone: string }) {
  const width = `${Math.round((props.value / props.total) * 100)}%`;
  return (
    <div className="progress-row">
      <div className="progress-label">
        <span>{props.label}</span>
        <strong>{props.value.toLocaleString()}</strong>
      </div>
      <div className="progress-track">
        <div className={`progress-fill ${props.tone}`} style={{ width }} />
      </div>
    </div>
  );
}

function ActivityDetail(props: {
  activity: Activity | null;
  editValues: Record<string, string>;
  updateEdit: (name: string, value: string) => void;
  saveActivity: () => Promise<void>;
  changeStatus: (action: "approve" | "reject" | "lock") => Promise<void>;
}) {
  const { activity, editValues, updateEdit, saveActivity, changeStatus } = props;

  if (activity === null) {
    return (
      <section className="surface detail-surface">
        <div className="section-head">
          <h2>Activity detail</h2>
        </div>
        <p className="empty">Select a row to review source payload, flags, edits, and audit history.</p>
      </section>
    );
  }

  const editable = activity.status === "normalized" || activity.status === "needs_review";
  const locked = activity.status === "locked";

  return (
    <section className="surface detail-surface">
      <div className="section-head detail-head">
        <div>
          <h2>{activity.source_reference || `Activity ${activity.id}`}</h2>
          <p>{label(activity.activity_type)} - {label(activity.scope)}</p>
        </div>
        <span className={`pill ${statusTone(activity.status)}`}>{label(activity.status)}</span>
      </div>

      <div className="evidence-strip">
        <div>
          <span>Source</span>
          <strong>{label(activity.source_type)}</strong>
        </div>
        <div>
          <span>Batch</span>
          <strong>{activity.batch_filename}</strong>
        </div>
        <div>
          <span>Flags</span>
          <strong>{activity.flags.length}</strong>
        </div>
        <div>
          <span>Raw row</span>
          <strong>{activity.raw_record?.row_number ?? "-"}</strong>
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-block">
          <h3>Normalized row</h3>
          <dl>
            <dt>Date</dt>
            <dd>{dateValue(activity.activity_date)}</dd>
            <dt>Period</dt>
            <dd>{dateValue(activity.period_start)} to {dateValue(activity.period_end)}</dd>
            <dt>Original</dt>
            <dd>{numberValue(activity.original_quantity)} {activity.original_unit}</dd>
            <dt>Normalized</dt>
            <dd>{numberValue(activity.normalized_quantity)} {activity.normalized_unit}</dd>
            <dt>Emissions</dt>
            <dd>{numberValue(activity.emissions_kg_co2e)} kgCO2e</dd>
            <dt>Facility</dt>
            <dd>{activity.facility?.name || activity.location_label || "-"}</dd>
            <dt>Counterparty</dt>
            <dd>{activity.counterparty || "-"}</dd>
          </dl>
        </div>

        <div className="detail-block">
          <h3>Flags</h3>
          {activity.flags.length === 0 ? (
            <p className="empty">No flags.</p>
          ) : (
            <ul className="flag-list">
              {activity.flags.map((flag) => (
                <li key={flag.id} className={flag.severity}>
                  <strong>{label(flag.code)}</strong>
                  <span>{flag.message}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="detail-block edit-block">
          <h3>Edit before sign-off</h3>
          {!editable ? (
            <p className="review-note">
              This row has already left review. Only normalized or needs_review rows can be edited.
            </p>
          ) : null}
          <div className="edit-grid">
            <label>
              <span>Quantity</span>
              <input
                disabled={!editable}
                value={editValues.normalized_quantity || ""}
                onChange={(event) => updateEdit("normalized_quantity", event.target.value)}
              />
            </label>
            <label>
              <span>Unit</span>
              <input
                disabled={!editable}
                value={editValues.normalized_unit || ""}
                onChange={(event) => updateEdit("normalized_unit", event.target.value)}
              />
            </label>
            <label>
              <span>Activity date</span>
              <input
                disabled={!editable}
                value={editValues.activity_date || ""}
                onChange={(event) => updateEdit("activity_date", event.target.value)}
              />
            </label>
            <label>
              <span>Period start</span>
              <input
                disabled={!editable}
                value={editValues.period_start || ""}
                onChange={(event) => updateEdit("period_start", event.target.value)}
              />
            </label>
            <label>
              <span>Period end</span>
              <input
                disabled={!editable}
                value={editValues.period_end || ""}
                onChange={(event) => updateEdit("period_end", event.target.value)}
              />
            </label>
            <label>
              <span>Department</span>
              <input
                disabled={!editable}
                value={editValues.department || ""}
                onChange={(event) => updateEdit("department", event.target.value)}
              />
            </label>
            <label className="wide">
              <span>Edit reason</span>
              <input
                disabled={!editable}
                value={editValues.edit_reason || ""}
                onChange={(event) => updateEdit("edit_reason", event.target.value)}
              />
            </label>
          </div>
          <div className="action-row">
            <button type="button" onClick={() => void saveActivity()} disabled={!editable}>
              <Save size={17} />
              <span>Save</span>
            </button>
            <button type="button" onClick={() => void changeStatus("approve")} disabled={locked}>
              <CheckCircle2 size={17} />
              <span>Approve</span>
            </button>
            <button type="button" onClick={() => void changeStatus("reject")} disabled={locked}>
              <XCircle size={17} />
              <span>Reject</span>
            </button>
            <button
              type="button"
              onClick={() => void changeStatus("lock")}
              disabled={locked || activity.status !== "approved"}
            >
              <LockKeyhole size={17} />
              <span>Lock</span>
            </button>
          </div>
        </div>

        <div className="detail-block raw-block">
          <h3>Raw source payload</h3>
          <pre>{JSON.stringify(activity.raw_record?.source_payload || {}, null, 2)}</pre>
        </div>

        <div className="detail-block audit-block">
          <h3>Audit trail</h3>
          {activity.audit_events?.length ? (
            <ol>
              {activity.audit_events.map((event) => (
                <li key={event.id}>
                  <strong>{label(event.action)}</strong>
                  <span>{event.actor_name} - {new Date(event.created_at).toLocaleString()}</span>
                  <code>{JSON.stringify(event.changes)}</code>
                </li>
              ))}
            </ol>
          ) : (
            <p className="empty">No audit events.</p>
          )}
        </div>
      </div>
    </section>
  );
}

export default App;

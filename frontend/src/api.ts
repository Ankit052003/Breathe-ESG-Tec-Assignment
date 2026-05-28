import type { Activity, Batch, Dashboard, Facility, Filters, SourceType } from "./types";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        `Could not reach the API at ${API_BASE_URL}. Start the Django backend or set VITE_API_BASE_URL to the deployed backend URL.`
      );
    }
    throw error;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail || "Request failed");
  }
  return response.json() as Promise<T>;
}

export async function getDashboard(): Promise<Dashboard> {
  return request<Dashboard>("/api/dashboard/");
}

export async function getBatches(): Promise<Batch[]> {
  return request<Batch[]>("/api/batches/");
}

export async function getFacilities(): Promise<Facility[]> {
  return request<Facility[]>("/api/facilities/");
}

export async function getActivities(filters: Filters): Promise<Activity[]> {
  const params = new URLSearchParams();
  if (filters.source_type) {
    params.set("source_type", filters.source_type);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.scope) {
    params.set("scope", filters.scope);
  }
  if (filters.facility) {
    params.set("facility", filters.facility);
  }
  if (filters.flagged) {
    params.set("flagged", "true");
  }
  if (filters.flag_severity) {
    params.set("flag_severity", filters.flag_severity);
  }
  if (filters.search) {
    params.set("search", filters.search);
  }
  const query = params.toString();
  return request<Activity[]>(`/api/activities/${query ? `?${query}` : ""}`);
}

export async function getActivity(activityId: number): Promise<Activity> {
  return request<Activity>(`/api/activities/${activityId}/`);
}

export async function uploadIngestion(
  sourceType: SourceType,
  file: File
): Promise<Batch> {
  const formData = new FormData();
  formData.append("source_type", sourceType);
  formData.append("file", file);
  return request<Batch>("/api/ingestions/upload/", {
    method: "POST",
    body: formData
  });
}

export async function updateActivity(
  activityId: number,
  payload: Record<string, string>
): Promise<Activity> {
  return request<Activity>(`/api/activities/${activityId}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-Analyst-Name": "demo-analyst"
    },
    body: JSON.stringify(payload)
  });
}

export async function activityAction(
  activityId: number,
  action: "approve" | "reject" | "lock"
): Promise<Activity> {
  return request<Activity>(`/api/activities/${activityId}/${action}/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Analyst-Name": "demo-analyst"
    },
    body: "{}"
  });
}

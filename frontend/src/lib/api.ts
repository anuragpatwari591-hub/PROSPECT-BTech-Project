import type {
  ActivityResponse, ContributorsResponse, HistoryResponse, Metric, Project, Recommendation, RiskModel, RiskResponse,
  Run, SimulationResponse,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public extra: Record<string, unknown> = {}) {
    super(message);
  }
}

export async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json();
    const { code = "HTTP_ERROR", message = response.statusText, ...extra } = body?.error ?? {};
    return new ApiError(response.status, code, message, extra);
  } catch {
    return new ApiError(response.status, "HTTP_ERROR", `Request failed with status ${response.status}.`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Cannot reach the PROSPECT server. Check that the backend is running.");
  }
  if (!response.ok) throw await parseError(response);
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export const api = {
  listProjects: () => request<Project[]>("/api/projects"),
  createProject: (repository_url: string) =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify({ repository_url }) }),
  deleteProject: (id: number) => request<void>(`/api/projects/${id}`, { method: "DELETE" }),
  analyze: (id: number, force = false) => request<Run>(`/api/projects/${id}/analyze?force=${force}`, { method: "POST" }),
  run: (id: number, runId: number) => request<Run>(`/api/projects/${id}/runs/${runId}`),
  metrics: (id: number) => request<{ run: Run; metrics: Metric[] }>(`/api/projects/${id}/metrics`),
  risk: (id: number) => request<RiskResponse>(`/api/projects/${id}/risk`),
  recommendations: (id: number) => request<Recommendation[]>(`/api/projects/${id}/recommendations`),
  history: (id: number) => request<HistoryResponse>(`/api/projects/${id}/history`),
  activity: (id: number) => request<ActivityResponse>(`/api/projects/${id}/activity`),
  contributors: (id: number) => request<ContributorsResponse>(`/api/projects/${id}/contributors`),
  riskModel: () => request<RiskModel>("/api/risk-model"),
  simulate: (id: number, overrides: Record<string, number>) =>
    request<SimulationResponse>(`/api/projects/${id}/simulate`, { method: "POST", body: JSON.stringify({ overrides }) }),
  reportUrl: (id: number) => `${BASE}/api/projects/${id}/report`,
};

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type RunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface RiskSummary { run_id: number; analyzed_at: string | null; risk_score: number; health_score: number; risk_level: RiskLevel }

export interface Run {
  id: number; project_id: number; status: RunStatus; started_at: string; finished_at: string | null;
  error_code: string | null; error_message: string | null; used_cache: boolean; api_calls: number;
  data_truncated: boolean; collection_notes: string[] | null;
}

export interface Project {
  id: number; name: string; owner: string; repo: string; url: string; description: string | null;
  stars: number | null; forks: number | null; is_archived: boolean; default_branch: string | null;
  last_collected_at: string | null; created_at: string; latest: RiskSummary | null; active_run: Run | null;
}

export interface Metric {
  key: string; name: string; value: number | null; unit: string; note: string | null; definition: string;
  formula: string; source: string; interpretation: string; limitations: string;
}

export interface Factor {
  id: number; dimension: string; signal_key: string; metric_key: string; metric_value: number | null;
  score: number; contribution: number; severity: "low" | "medium" | "high" | "critical"; explanation: string;
}

export interface Dimension {
  key: string; label: string; weight: number; effective_weight: number; score: number | null;
  contribution: number; status: "scored" | "not_applicable";
}

export interface DormancyOutput {
  status: "ok" | "unreliable" | "model_unavailable" | "not_applicable" | "error"; message: string;
  probability_dormant_180d?: number; contributions?: { feature: string; value: number; log_odds_contribution: number }[];
  test_metrics?: Record<string, number | number[] | number[][]>; model_version?: string;
}

export interface AnomalyOutput {
  status: "ok" | "insufficient_data"; message?: string; active_weeks: number;
  anomalies: { week_ending: string; score: number; reasons: { feature: string; value: number; typical: number; robust_z: number }[] }[];
}

export interface RiskResponse {
  run: Run; risk_score: number; health_score: number; risk_level: RiskLevel; coverage: number; engine_version: string;
  dimensions: Dimension[]; factors: Factor[]; top_factors: Factor[]; disclaimer: string;
  ml: { anomaly?: AnomalyOutput; dormancy?: DormancyOutput } | null;
}

export interface Recommendation { id: number; risk_factor_id: number | null; signal_key: string; priority: "HIGH" | "MEDIUM" | "LOW"; title: string; detail: string }

export interface HistoryPoint { run_id: number; analyzed_at: string; risk_score: number; health_score: number; risk_level: RiskLevel; key_metrics: Record<string, number | null> }
export interface HistoryResponse { points: HistoryPoint[]; changes: Record<string, { from_run_id: number; from_score: number; delta: number } | null> }

export interface WeekRow { week_ending: string; commits: number; issues_opened: number; issues_closed: number; prs_opened: number; prs_merged: number }
export interface ActivityResponse { run_id: number; weeks: WeekRow[]; anomaly: AnomalyOutput | null }

export interface ContributorsResponse {
  run_id: number; window_days: number; total_commits: number; authors: number;
  top_authors: { author: string; commits: number; share: number }[]; other_commits: number;
  all_time_top: { login: string; contributions: number }[]; note: string;
}

export interface SimulationResponse {
  label: string; run_id: number; scenario_id: number; baseline_score: number; simulated_score: number; difference: number;
  baseline_level: RiskLevel; simulated_level: RiskLevel; applied: Record<string, number>;
  dimensions: { key: string; label: string; baseline: number | null; simulated: number | null; status: string }[];
}

export interface RiskModel { simulatable_metrics: Record<string, { min: number; max: number }> }

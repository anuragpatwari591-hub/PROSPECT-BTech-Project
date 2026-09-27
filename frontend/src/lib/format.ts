import type { RiskLevel } from "./types";

export const LEVEL_COLOR: Record<RiskLevel, string> = {
  LOW: "var(--color-risk-low)", MEDIUM: "var(--color-risk-medium)",
  HIGH: "var(--color-risk-high)", CRITICAL: "var(--color-risk-critical)",
};
export const SEVERITY_COLOR: Record<string, string> = {
  low: LEVEL_COLOR.LOW, medium: LEVEL_COLOR.MEDIUM, high: LEVEL_COLOR.HIGH, critical: LEVEL_COLOR.CRITICAL,
};
export const DIMENSION_COLOR: Record<string, string> = {
  activity: "var(--color-dim-activity)", issues: "var(--color-dim-issues)", pull_requests: "var(--color-dim-prs)",
  contributors: "var(--color-dim-contributors)", releases: "var(--color-dim-releases)",
};

export function formatValue(value: number | null | undefined, unit = ""): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (unit.startsWith("ratio")) return `${Math.round(value * 100)}%`;
  const text = Number.isInteger(value) || Math.abs(value) >= 100 ? Math.round(value).toLocaleString("en-US") : value.toFixed(1);
  if (unit === "%") return `${value > 0 ? "+" : ""}${text}%`;
  return unit && !["commits", "issues", "PRs", "people", "releases"].includes(unit) ? `${text} ${unit}` : text;
}

/**
 * Parse a timestamp from the API. The backend always stores UTC, but SQLite (used by the Windows desktop build)
 * returns datetimes without a timezone marker, e.g. "2026-09-26T11:10:53". JavaScript would read such a string as
 * LOCAL time, shifting it by the user's UTC offset (5 h 30 min in India). Treat marker-less timestamps as UTC.
 */
export function parseApiDate(iso: string): Date {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/i.test(iso);
  return new Date(iso.includes("T") && !hasZone ? `${iso}Z` : iso);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "never";
  return parseApiDate(iso).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function relativeTime(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "never";
  const minutes = Math.round((now - parseApiDate(iso).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} days ago`;
}

export function levelFor(score: number): RiskLevel {
  if (score >= 75) return "CRITICAL";
  if (score >= 50) return "HIGH";
  if (score >= 25) return "MEDIUM";
  return "LOW";
}

export const METRIC_LABELS: Record<string, string> = {
  days_since_last_commit: "Days since last commit", activity_trend_pct: "Activity trend (%)",
  active_weeks_ratio: "Weeks with commits (0–1)", issue_close_ratio_90d: "Issues closed ÷ opened",
  median_open_issue_age_days: "Median open issue age (days)", median_pr_turnaround_days: "Median PR turnaround (days)",
  pr_turnaround_trend_pct: "PR turnaround trend (%)", stale_open_pr_ratio: "Stale open PRs (0–1)",
  median_pr_size_lines: "Median PR size (lines)", top_contributor_share: "Top contributor share (0–1)",
  bus_factor_estimate: "Commit-share bus factor", contributors_90d: "Active contributors (90 days)",
  days_since_last_release: "Days since last release",
};

function Metric({ label, value }) {
  return (
    <div className="metric-tile">
      <span className="metric-value">{value ?? "N/A"}</span>
      <span className="metric-label">{label}</span>
    </div>
  );
}

export default function MetricsPanel({ metrics }) {
  return (
    <div className="panel">
      <h3>Repository Metrics</h3>
      <div className="metric-grid">
        <Metric label="Days since last push" value={metrics.days_since_last_push} />
        <Metric label="Contributors sampled" value={metrics.contributor_count} />
        <Metric label="Top contributor share" value={`${metrics.top_contributor_pct}%`} />
        <Metric label="Open issues" value={metrics.open_issue_count} />
        <Metric label="Closed issues" value={metrics.closed_issue_count} />
        <Metric label="Stale open issues (>90d)" value={metrics.stale_open_issue_count} />
        <Metric label="Open pull requests" value={metrics.open_pr_count} />
        <Metric label="Merged pull requests" value={metrics.merged_pr_count} />
        <Metric label="Closed (unmerged) PRs" value={metrics.closed_unmerged_pr_count} />
        <Metric label="Stale open PRs (>45d)" value={metrics.stale_open_pr_count} />
        <Metric label="Releases" value={metrics.release_count} />
        <Metric label="Days since last release" value={metrics.days_since_last_release} />
      </div>
    </div>
  );
}

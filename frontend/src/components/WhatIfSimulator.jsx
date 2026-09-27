import { useState } from "react";
import { runWhatIf } from "../api.js";

const FIELDS = [
  { key: "days_since_last_push", label: "Days since last push", min: 0, max: 1000, step: 1 },
  { key: "contributor_count", label: "Contributor count", min: 0, max: 100, step: 1 },
  { key: "top_contributor_pct", label: "Top contributor share (%)", min: 0, max: 100, step: 1 },
  { key: "open_issue_count", label: "Open issues", min: 0, max: 500, step: 1 },
  { key: "stale_open_issue_count", label: "Stale open issues (>90d)", min: 0, max: 500, step: 1 },
  { key: "open_pr_count", label: "Open pull requests", min: 0, max: 200, step: 1 },
  { key: "stale_open_pr_count", label: "Stale open PRs (>45d)", min: 0, max: 200, step: 1 },
  { key: "release_count", label: "Release count", min: 0, max: 200, step: 1 },
  { key: "days_since_last_release", label: "Days since last release", min: 0, max: 1000, step: 1 },
];

export default function WhatIfSimulator({ analysisId, metrics }) {
  const initial = Object.fromEntries(
    FIELDS.map((f) => [f.key, metrics[f.key] ?? 0])
  );
  const [values, setValues] = useState(initial);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (key, raw) => {
    setValues((prev) => ({ ...prev, [key]: Number(raw) }));
  };

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const overrides = { ...values };
      if (overrides.days_since_last_release === 0 && metrics.release_count === 0 && values.release_count === 0) {
        overrides.days_since_last_release = null;
      }
      const sim = await runWhatIf(analysisId, overrides);
      setResult(sim);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setValues(initial);
    setResult(null);
  };

  return (
    <div className="panel whatif-panel">
      <h3>What-If Risk Simulator</h3>
      <p className="panel-subtitle">
        Adjust hypothetical metrics and re-run the exact same risk algorithm &mdash;
        nothing is fetched from GitHub again.
      </p>

      <div className="whatif-grid">
        {FIELDS.map((f) => (
          <label className="whatif-field" key={f.key}>
            <span>
              {f.label}: <strong>{values[f.key]}</strong>
            </span>
            <input
              type="range"
              min={f.min}
              max={f.max}
              step={f.step}
              value={values[f.key]}
              onChange={(e) => handleChange(f.key, e.target.value)}
            />
          </label>
        ))}
      </div>

      <div className="whatif-actions">
        <button onClick={handleRun} disabled={loading}>
          {loading ? "Simulating…" : "Run Simulation"}
        </button>
        <button className="secondary" onClick={handleReset} disabled={loading}>
          Reset
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <div className="whatif-result">
          <div>
            <span className="muted">Simulated Risk Score</span>
            <div className="whatif-score">{result.risk_score} / 100</div>
          </div>
          <div>
            <span className="muted">Simulated Classification</span>
            <div className="whatif-classification">{result.classification}</div>
          </div>
          <div>
            <span className="muted">Change vs Actual</span>
            <div
              className={
                result.risk_score <= result.extra.base_risk_score
                  ? "whatif-delta improved"
                  : "whatif-delta worsened"
              }
            >
              {result.risk_score > result.extra.base_risk_score ? "+" : ""}
              {(result.risk_score - result.extra.base_risk_score).toFixed(1)} pts
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

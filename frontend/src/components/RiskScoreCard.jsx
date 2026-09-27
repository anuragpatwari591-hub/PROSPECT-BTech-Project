const CLASS_INFO = {
  LOW: { color: "#2e7d32", label: "Low Risk" },
  MEDIUM: { color: "#f9a825", label: "Medium Risk" },
  HIGH: { color: "#ef6c00", label: "High Risk" },
  CRITICAL: { color: "#c62828", label: "Critical Risk" },
};

export default function RiskScoreCard({ analysis }) {
  const info = CLASS_INFO[analysis.classification] || CLASS_INFO.MEDIUM;

  return (
    <div className="risk-score-card">
      <div className="repo-title">
        <h2>{analysis.repo_full_name}</h2>
        {analysis.description && <p className="repo-desc">{analysis.description}</p>}
        <a href={analysis.repo_url} target="_blank" rel="noreferrer">
          {analysis.repo_url}
        </a>
      </div>

      <div className="score-row">
        <div className="score-gauge" style={{ "--gauge-color": info.color }}>
          <svg viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" className="gauge-track" />
            <circle
              cx="60"
              cy="60"
              r="52"
              className="gauge-fill"
              style={{
                stroke: info.color,
                strokeDasharray: `${(analysis.risk_score / 100) * 326.7} 326.7`,
              }}
            />
          </svg>
          <div className="gauge-label">
            <span className="gauge-score">{analysis.risk_score}</span>
            <span className="gauge-max">/ 100</span>
          </div>
        </div>

        <div className="score-details">
          <span className="classification-badge" style={{ backgroundColor: info.color }}>
            {info.label}
          </span>
          <div className="health-row">
            <span>Health Score</span>
            <strong>{analysis.health_score} / 100</strong>
          </div>
          <div className="stat-row">
            <span>⭐ {analysis.stars} stars</span>
            <span>⑂ {analysis.forks} forks</span>
            {analysis.primary_language && <span>{analysis.primary_language}</span>}
          </div>
          {analysis.is_simulation && (
            <div className="simulation-tag">
              What-If Simulation — base risk score was {analysis.extra?.base_risk_score}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

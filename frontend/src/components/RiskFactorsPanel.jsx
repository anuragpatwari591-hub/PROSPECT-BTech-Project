function barColor(pct) {
  if (pct >= 75) return "#c62828";
  if (pct >= 50) return "#ef6c00";
  if (pct >= 25) return "#f9a825";
  return "#2e7d32";
}

export default function RiskFactorsPanel({ factors }) {
  return (
    <div className="panel">
      <h3>Explainable Risk Factors</h3>
      <p className="panel-subtitle">
        Every point is produced by a fixed, documented rule &mdash; nothing here is a
        black box.
      </p>
      <div className="factor-list">
        {factors.map((f) => (
          <div className="factor-item" key={f.key}>
            <div className="factor-header">
              <span className="factor-label">{f.label}</span>
              <span className="factor-points">
                {f.points} / {f.max_points} pts
              </span>
            </div>
            <div className="factor-bar-track">
              <div
                className="factor-bar-fill"
                style={{ width: `${f.pct_of_max}%`, backgroundColor: barColor(f.pct_of_max) }}
              />
            </div>
            <ul className="factor-reasons">
              {f.reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
              {f.reasons.length === 0 && <li className="muted">No contributing signals.</li>}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

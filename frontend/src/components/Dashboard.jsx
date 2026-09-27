import RiskScoreCard from "./RiskScoreCard.jsx";
import MetricsPanel from "./MetricsPanel.jsx";
import RiskFactorsPanel from "./RiskFactorsPanel.jsx";
import RecommendationsPanel from "./RecommendationsPanel.jsx";
import WhatIfSimulator from "./WhatIfSimulator.jsx";
import { reportUrl } from "../api.js";

export default function Dashboard({ analysis }) {
  return (
    <div className="dashboard">
      <RiskScoreCard analysis={analysis} />

      {analysis.id && !analysis.is_simulation && (
        <div className="report-actions">
          <a className="download-btn" href={reportUrl(analysis.id)} target="_blank" rel="noreferrer">
            ⬇ Download PDF Report
          </a>
        </div>
      )}

      <div className="dashboard-grid">
        <RiskFactorsPanel factors={analysis.factors} />
        <div className="dashboard-side">
          <MetricsPanel metrics={analysis.metrics} />
          <RecommendationsPanel recommendations={analysis.recommendations} />
        </div>
      </div>

      {analysis.id && !analysis.is_simulation && (
        <WhatIfSimulator analysisId={analysis.id} metrics={analysis.metrics} />
      )}
    </div>
  );
}

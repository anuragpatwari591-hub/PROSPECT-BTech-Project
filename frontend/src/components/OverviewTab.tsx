import { formatValue, SEVERITY_COLOR } from "../lib/format";
import type { Metric, Recommendation, RiskResponse } from "../lib/types";
import { Panel, Tip } from "./ui";

const CARDS = ["commits_90d", "open_issues", "prs_merged_90d", "median_pr_turnaround_days", "contributors_90d", "activity_trend_pct"];

export function MetricCard({ metric }: { metric: Metric }) {
  return (
    <div className="rounded-lg border border-line bg-panel px-4 py-3">
      <Tip label={<span className="text-xs text-ink-soft">{metric.name}</span>}>
        {metric.definition} <br /><br />Formula: {metric.formula}
      </Tip>
      <p className="mt-1 text-2xl font-bold">{formatValue(metric.value, metric.unit)}</p>
      {metric.note && <p className="mt-0.5 text-xs text-ink-faint">{metric.note}</p>}
    </div>
  );
}

export function OverviewTab({ risk, metrics, recommendations, onOpenFactors }: {
  risk: RiskResponse; metrics: Metric[]; recommendations: Recommendation[]; onOpenFactors: () => void;
}) {
  const byKey = Object.fromEntries(metrics.map((m) => [m.key, m]));
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {CARDS.filter((k) => byKey[k]).map((k) => <MetricCard key={k} metric={byKey[k]} />)}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Why this score" aside={<button type="button" className="font-semibold text-accent" onClick={onOpenFactors}>All factors</button>}>
          {risk.top_factors.length === 0 ? (
            <p className="text-sm text-ink-soft">No signal adds risk points. Every measured signal is within its healthy range.</p>
          ) : (
            <ol className="space-y-4">
              {risk.top_factors.map((f) => (
                <li key={f.id} className="flex gap-3">
                  <span className="mt-1 h-3 w-3 shrink-0 rounded-full" style={{ background: SEVERITY_COLOR[f.severity] }} aria-hidden />
                  <div>
                    <p className="text-sm font-semibold">+{f.contribution.toFixed(1)} points <span className="font-normal text-ink-soft">from {byKey[f.metric_key]?.name ?? f.signal_key}</span></p>
                    <p className="text-sm text-ink-soft">{f.explanation}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Panel>

        <Panel title="Recommended actions" aside={`${recommendations.length} triggered`}>
          {recommendations.length === 0 ? (
            <p className="text-sm text-ink-soft">No factor scored 50 or more, so no action is recommended.</p>
          ) : (
            <ul className="space-y-4">
              {recommendations.map((r) => (
                <li key={r.id}>
                  <p className="text-sm font-semibold">
                    <span className={`mr-2 rounded px-1.5 py-0.5 text-xs ${r.priority === "HIGH" ? "bg-[#f6e3e5] text-[color:var(--color-risk-critical)]" : "bg-[#f7efdc] text-[#80601c]"}`}>
                      {r.priority === "HIGH" ? "High priority" : "Medium priority"}
                    </span>
                    {r.title}
                  </p>
                  <p className="mt-1 text-sm text-ink-soft">{r.detail}</p>
                  <p className="mt-1 text-xs text-ink-faint">Triggered by {r.signal_key}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      {(risk.run.collection_notes?.length ?? 0) > 0 && (
        <Panel title="Data notes">
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink-soft">
            {risk.run.collection_notes!.map((n) => <li key={n}>{n}</li>)}
          </ul>
        </Panel>
      )}
    </div>
  );
}

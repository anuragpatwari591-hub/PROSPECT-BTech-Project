import { DIMENSION_COLOR, formatValue, SEVERITY_COLOR } from "../lib/format";
import type { Metric, RiskResponse } from "../lib/types";
import { Panel, Tip } from "./ui";

export function FactorsTab({ risk, metrics }: { risk: RiskResponse; metrics: Metric[] }) {
  const defs = Object.fromEntries(metrics.map((m) => [m.key, m]));
  return (
    <div className="space-y-5">
      {risk.dimensions.map((d) => {
        const factors = risk.factors.filter((f) => f.dimension === d.key);
        return (
          <Panel key={d.key} title={d.label}
            aside={d.status === "scored"
              ? <span><span className="font-semibold text-ink">{d.contribution.toFixed(1)} pts</span> · dimension score {formatValue(d.score)} · weight {Math.round(d.weight * 100)}%</span>
              : "Not scored — no data for this dimension"}>
            <div className="mb-4 h-1.5 w-full rounded bg-line-soft">
              <div className="h-1.5 rounded" style={{ width: `${d.score ?? 0}%`, background: DIMENSION_COLOR[d.key] }} />
            </div>
            {factors.length === 0 ? (
              <p className="text-sm text-ink-soft">None of this dimension's metrics could be measured for this repository (for example, the project publishes no GitHub Releases). Its weight was redistributed.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="text-xs text-ink-soft">
                    <tr className="border-b border-line-soft">
                      <th className="py-2 pr-3 font-medium">Signal</th><th className="py-2 pr-3 font-medium">Metric value</th>
                      <th className="py-2 pr-3 font-medium">Signal score</th><th className="py-2 pr-3 font-medium">Points</th>
                      <th className="py-2 font-medium">Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {factors.map((f) => {
                      const def = defs[f.metric_key];
                      return (
                        <tr key={f.id} className="border-b border-line-soft align-top last:border-0">
                          <td className="py-3 pr-3">
                            {def ? <Tip label={<span className="font-semibold">{def.name}</span>}>{def.definition} Limitations: {def.limitations}</Tip>
                                 : <span className="font-semibold">{f.metric_key}</span>}
                          </td>
                          <td className="py-3 pr-3 whitespace-nowrap">{formatValue(f.metric_value, def?.unit)}</td>
                          <td className="py-3 pr-3">
                            <div className="flex items-center gap-2">
                              <div className="h-2 w-16 rounded bg-line-soft"><div className="h-2 rounded" style={{ width: `${f.score}%`, background: SEVERITY_COLOR[f.severity] }} /></div>
                              <span className="w-8 text-right">{f.score.toFixed(0)}</span>
                            </div>
                          </td>
                          <td className="py-3 pr-3 font-semibold">{f.contribution.toFixed(1)}</td>
                          <td className="py-3 text-ink-soft">{f.explanation}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        );
      })}
    </div>
  );
}

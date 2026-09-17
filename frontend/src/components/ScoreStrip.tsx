import { DIMENSION_COLOR, formatValue } from "../lib/format";
import type { RiskResponse } from "../lib/types";
import { LevelBadge, Tip } from "./ui";

/** The headline: the score itself, and a strip showing exactly which dimensions the points come from. */
export function ScoreStrip({ risk }: { risk: RiskResponse }) {
  const scored = risk.dimensions.filter((d) => d.status === "scored");
  const skipped = risk.dimensions.filter((d) => d.status !== "scored");
  return (
    <div className="rounded-lg border border-line bg-panel p-5 sm:p-6">
      <div className="flex flex-wrap items-end gap-x-10 gap-y-4">
        <div>
          <p className="text-sm text-ink-soft">Risk score</p>
          <p className="text-6xl leading-none font-bold tracking-tight" data-testid="risk-score">{risk.risk_score.toFixed(0)}</p>
        </div>
        <div className="space-y-2 pb-1">
          <LevelBadge level={risk.risk_level} size="lg" />
          <p className="text-sm text-ink-soft">
            Health score <span className="font-semibold text-ink">{risk.health_score.toFixed(0)}</span>
            <span className="mx-2 text-line">|</span>
            <Tip label={<span>Data coverage {Math.round(risk.coverage * 100)}%</span>}>
              Share of the model's weight that had data. Dimensions without data are left out and the remaining weights are rescaled.
            </Tip>
          </p>
        </div>
      </div>

      <div className="mt-6">
        <p className="mb-2 text-sm font-semibold">Where the {risk.risk_score.toFixed(0)} points come from</p>
        <div className="flex h-9 w-full overflow-hidden rounded-md bg-line-soft" role="img"
             aria-label={scored.map((d) => `${d.label} ${d.contribution.toFixed(1)} points`).join(", ")}>
          {scored.map((d) => (
            <div key={d.key} title={`${d.label}: ${d.contribution.toFixed(1)} points`}
                 style={{ width: `${d.contribution}%`, background: DIMENSION_COLOR[d.key] }}
                 className="h-full border-r-2 border-white last:border-r-0" />
          ))}
        </div>
        <div className="mt-1 flex justify-between text-xs text-ink-faint"><span>0</span><span>100</span></div>
        <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3 lg:grid-cols-5">
          {scored.map((d) => (
            <div key={d.key} className="flex items-start gap-2">
              <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: DIMENSION_COLOR[d.key] }} aria-hidden />
              <div>
                <dt className="text-xs text-ink-soft">{d.label}</dt>
                <dd className="text-sm"><span className="font-semibold">{d.contribution.toFixed(1)}</span> pts
                  <span className="text-ink-faint"> · score {formatValue(d.score)} × {Math.round(d.effective_weight * 100)}%</span></dd>
              </div>
            </div>
          ))}
        </dl>
        {skipped.length > 0 && (
          <p className="mt-3 text-xs text-ink-soft">Not scored (no data): {skipped.map((d) => d.label).join(", ")}.</p>
        )}
      </div>
      <p className="mt-4 border-t border-line-soft pt-3 text-xs text-ink-soft">{risk.disclaimer}</p>
    </div>
  );
}

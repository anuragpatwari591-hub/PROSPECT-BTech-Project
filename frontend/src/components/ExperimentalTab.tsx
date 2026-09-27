import type { RiskResponse } from "../lib/types";
import { Message, Panel } from "./ui";

const FEATURE_LABELS: Record<string, string> = {
  log_commits_30d: "Commits, last 30 days (log)", log_commits_90d: "Commits, last 90 days (log)",
  log_commits_180d: "Commits, last 180 days (log)", active_weeks_ratio_26w: "Share of weeks with commits (26 w)",
  days_since_last_commit: "Days since last commit", recent_rate_ratio: "Recent vs 6-month commit rate",
  authors_90d: "Authors, last 90 days", top_author_share_180d: "Top author share (180 days)",
};

export function ExperimentalTab({ risk }: { risk: RiskResponse }) {
  const d = risk.ml?.dormancy;
  const t = d?.test_metrics;
  return (
    <div className="space-y-5">
      <Message tone="warning" title="Experimental — not used in the risk score">
        This model estimates the chance that a currently active repository has no commits in the next 180 days. It was trained on commit histories of 76 public repositories.
        On held-out repositories it ranked projects well, but it did not clearly beat a simple “no commit for 60 days” rule. Treat it as a research output.
      </Message>
      <Panel title="Dormancy estimate (next 180 days)">
        {!d || !["ok", "unreliable"].includes(d.status) ? (
          <p className="text-sm text-ink-soft">{d?.message ?? "No model output for this analysis."}</p>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[12rem_minmax(0,1fr)]">
            <div>
              <p className="text-5xl font-bold">{(d.probability_dormant_180d ?? 0) < 0.005 ? "<1" : Math.round((d.probability_dormant_180d ?? 0) * 100)}%</p>
              <p className="mt-1 text-sm text-ink-soft">{d.message}</p>
              {t && <p className="mt-3 text-xs text-ink-faint">Test set: ROC-AUC {String(t.roc_auc)}, PR-AUC {String(t.pr_auc)}, precision {String(t.precision)}, recall {String(t.recall)}.</p>}
            </div>
            <div>
              <p className="mb-2 text-sm font-semibold">What pushed the estimate up or down</p>
              <ul className="space-y-1.5">
                {d.contributions?.map((c) => {
                  const width = Math.min(100, Math.abs(c.log_odds_contribution) * 25);
                  const up = c.log_odds_contribution > 0;
                  return (
                    <li key={c.feature} className="grid grid-cols-[minmax(0,16rem)_minmax(0,1fr)_3.5rem] items-center gap-3 text-sm">
                      <span className="truncate text-ink-soft" title={FEATURE_LABELS[c.feature]}>{FEATURE_LABELS[c.feature] ?? c.feature}</span>
                      <div className="relative h-2 rounded bg-line-soft">
                        <div className="absolute top-0 h-2 rounded" style={{ width: `${width / 2}%`, left: up ? "50%" : `${50 - width / 2}%`, background: up ? "var(--color-risk-high)" : "var(--color-risk-low)" }} />
                        <div className="absolute top-[-3px] left-1/2 h-3.5 w-px bg-ink-faint" />
                      </div>
                      <span className="text-right tabular-nums">{up ? "+" : ""}{c.log_odds_contribution.toFixed(2)}</span>
                    </li>
                  );
                })}
              </ul>
              <p className="mt-2 text-xs text-ink-faint">Contributions to the log-odds of a logistic regression (coefficient × standardised feature). Features are correlated, so individual values should not be read as causes.</p>
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}

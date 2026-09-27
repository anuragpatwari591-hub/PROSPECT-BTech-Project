import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, ApiError } from "../lib/api";
import { formatValue, LEVEL_COLOR, METRIC_LABELS } from "../lib/format";
import type { Metric, SimulationResponse } from "../lib/types";
import { useAsync } from "../lib/useAsync";
import { Button, LevelBadge, Message, Panel, Skeleton } from "./ui";

const SHORT_DIMENSION: Record<string, string> = {
  activity: "Activity", issues: "Issues", pull_requests: "PRs", contributors: "Contributors", releases: "Releases",
};

function stepFor(max: number) {
  if (max <= 1) return 0.01;
  if (max <= 10) return 0.1;
  return 1;
}

export function SimulatorTab({ projectId, metrics }: { projectId: number; metrics: Metric[] }) {
  const model = useAsync(() => api.riskModel(), []);
  const current = useMemo(() => Object.fromEntries(metrics.map((m) => [m.key, m.value])), [metrics]);
  const [values, setValues] = useState<Record<string, number>>({});
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (model.loading) return <Skeleton className="h-96" />;
  if (model.error || !model.data) return <Message tone="error" title="Simulator unavailable">{model.error?.message}</Message>;
  const ranges = model.data.simulatable_metrics;
  // Practical slider ranges: the API accepts wider values, but these cover realistic what-if questions.
  const uiMax: Record<string, number> = { days_since_last_commit: 365, median_open_issue_age_days: 730, median_pr_turnaround_days: 30,
    median_pr_size_lines: 3000, bus_factor_estimate: 10, contributors_90d: 30, days_since_last_release: 730, issue_close_ratio_90d: 2 };
  const changed = Object.fromEntries(Object.entries(values).filter(([k, v]) => v !== current[k]));

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.simulate(projectId, changed));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Simulation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <Panel title="Change metrics" aside={<button type="button" className="font-semibold text-accent" onClick={() => { setValues({}); setResult(null); }}>Reset</button>}>
        <p className="mb-4 text-sm text-ink-soft">Move a slider to ask “what if this metric were different?”. Metrics with no current value start at the middle of their range.</p>
        <div className="space-y-4">
          {Object.entries(ranges).map(([key, range]) => {
            const max = Math.min(range.max, uiMax[key] ?? range.max);
            const base = current[key];
            const value = values[key] ?? base ?? (range.min + max) / 2;
            return (
              <div key={key}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <label htmlFor={`sim-${key}`} className="font-medium">{METRIC_LABELS[key] ?? key}</label>
                  <span className="whitespace-nowrap">
                    <span className="text-ink-faint">now {formatValue(base)}</span>
                    {key in changed && <span className="ml-2 font-semibold text-accent">→ {formatValue(value)}</span>}
                  </span>
                </div>
                <input id={`sim-${key}`} type="range" min={range.min} max={max} step={stepFor(max)} value={value}
                  onChange={(e) => setValues((v) => ({ ...v, [key]: Number(e.target.value) }))}
                  className="mt-1 w-full accent-[#2a4d8f]" />
              </div>
            );
          })}
        </div>
        <Button className="mt-5 w-full" onClick={run} disabled={busy || Object.keys(changed).length === 0}>
          {busy ? "Simulating…" : `Simulate ${Object.keys(changed).length || ""} change${Object.keys(changed).length === 1 ? "" : "s"}`}
        </Button>
        {error && <p className="mt-2 text-sm text-[color:var(--color-risk-critical)]" role="alert">{error}</p>}
      </Panel>

      <div className="space-y-5">
        <div className="rounded-lg border-2 border-dashed border-[color:var(--color-risk-medium)] bg-[#fbf6ea] px-4 py-3 text-sm">
          <p className="font-bold">Simulation / estimate</p>
          <p className="text-ink-soft">Results show how the rule-based score responds to hypothetical values. They do not predict what will happen to the project.</p>
        </div>
        {!result ? (
          <Message title="No simulation yet">Change one or more metrics and select Simulate.</Message>
        ) : (
          <Panel title="Current versus simulated">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div><p className="text-xs text-ink-soft">Current</p><p className="text-4xl font-bold">{result.baseline_score.toFixed(0)}</p><LevelBadge level={result.baseline_level} /></div>
              <div><p className="text-xs text-ink-soft">Simulated</p><p className="text-4xl font-bold" style={{ color: LEVEL_COLOR[result.simulated_level] }}>{result.simulated_score.toFixed(0)}</p><LevelBadge level={result.simulated_level} /></div>
              <div><p className="text-xs text-ink-soft">Difference</p><p className="text-4xl font-bold" data-testid="sim-diff">{result.difference > 0 ? "+" : ""}{result.difference.toFixed(1)}</p><p className="text-xs text-ink-faint">points</p></div>
            </div>
            <div className="mt-5 h-64">
              <ResponsiveContainer>
                <BarChart data={result.dimensions.filter((d) => d.status === "scored")} margin={{ left: -20 }}>
                  <CartesianGrid vertical={false} stroke="var(--color-line-soft)" />
                  <XAxis dataKey="key" tickFormatter={(k: string) => SHORT_DIMENSION[k] ?? k} tick={{ fontSize: 11 }} interval={0} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar isAnimationActive={false} dataKey="baseline" name="Current" fill="var(--color-ink-faint)" radius={[2, 2, 0, 0]} />
                  <Bar isAnimationActive={false} dataKey="simulated" name="Simulated" fill="var(--color-accent)" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-xs text-ink-faint">Dimension scores (0–100). Changed: {Object.entries(result.applied).map(([k, v]) => `${METRIC_LABELS[k] ?? k} = ${v}`).join("; ")}.</p>
          </Panel>
        )}
      </div>
    </div>
  );
}

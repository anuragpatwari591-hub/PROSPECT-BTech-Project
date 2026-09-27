import { CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { formatDate, formatValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { LevelBadge, Message, Panel, Skeleton } from "./ui";

export function HistoryTab({ projectId, runId }: { projectId: number; runId: number }) {
  const { data, error, loading } = useAsync(() => api.history(projectId), [projectId, runId]);
  if (loading) return <Skeleton className="h-80" />;
  if (error || !data) return <Message tone="error" title="History could not be loaded">{error?.message}</Message>;
  const points = data.points.map((p) => ({ ...p, label: formatDate(p.analyzed_at) }));
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {(["7d", "30d", "90d"] as const).map((k) => {
          const c = data.changes[k];
          return (
            <div key={k} className="rounded-lg border border-line bg-panel px-4 py-3">
              <p className="text-xs text-ink-soft">Change over {k.replace("d", " days")}</p>
              {c ? <p className="mt-1 text-2xl font-bold">{c.delta > 0 ? "+" : ""}{c.delta.toFixed(1)} <span className="text-sm font-normal text-ink-soft">vs run #{c.from_run_id}</span></p>
                 : <p className="mt-1 text-sm text-ink-soft">No stored analysis from {k.replace("d", " days")} ago yet.</p>}
            </div>
          );
        })}
      </div>
      <Panel title="Risk score over time" aside={`${points.length} completed ${points.length === 1 ? "analysis" : "analyses"}`}>
        {points.length < 2 ? (
          <p className="text-sm text-ink-soft">A trend line appears after the second analysis. History is built from real, stored analyses only; missing periods are never filled in.</p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={points} margin={{ left: -20, right: 12 }}>
                <ReferenceArea y1={75} y2={100} fill="var(--color-risk-critical)" fillOpacity={0.05} />
                <ReferenceArea y1={50} y2={75} fill="var(--color-risk-high)" fillOpacity={0.05} />
                <CartesianGrid vertical={false} stroke="var(--color-line-soft)" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={30} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line isAnimationActive={false} dataKey="risk_score" name="Risk score" stroke="var(--color-ink)" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Panel>
      <Panel title="Previous analyses">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-xs text-ink-soft"><tr className="border-b border-line-soft">
              <th className="py-2 pr-3 font-medium">Run</th><th className="py-2 pr-3 font-medium">Analysed</th><th className="py-2 pr-3 font-medium">Risk</th>
              <th className="py-2 pr-3 font-medium">Level</th><th className="py-2 pr-3 font-medium">Commits 90d</th><th className="py-2 pr-3 font-medium">Open issues</th>
              <th className="py-2 pr-3 font-medium">PR turnaround</th><th className="py-2 font-medium">Contributors</th>
            </tr></thead>
            <tbody>
              {[...points].reverse().map((p) => (
                <tr key={p.run_id} className="border-b border-line-soft last:border-0">
                  <td className="py-2 pr-3">#{p.run_id}</td><td className="py-2 pr-3">{p.label}</td>
                  <td className="py-2 pr-3 font-semibold">{p.risk_score.toFixed(1)}</td><td className="py-2 pr-3"><LevelBadge level={p.risk_level} /></td>
                  <td className="py-2 pr-3">{formatValue(p.key_metrics.commits_90d)}</td><td className="py-2 pr-3">{formatValue(p.key_metrics.open_issues)}</td>
                  <td className="py-2 pr-3">{formatValue(p.key_metrics.median_pr_turnaround_days, "days")}</td><td className="py-2">{formatValue(p.key_metrics.contributors_90d)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { formatValue } from "../lib/format";
import type { Metric } from "../lib/types";
import { useAsync } from "../lib/useAsync";
import { Message, Panel, Skeleton } from "./ui";

export function ContributorsTab({ projectId, runId, metrics }: { projectId: number; runId: number; metrics: Metric[] }) {
  const { data, error, loading } = useAsync(() => api.contributors(projectId), [projectId, runId]);
  if (loading) return <Skeleton className="h-80" />;
  if (error || !data) return <Message tone="error" title="Contributor data could not be loaded">{error?.message}</Message>;
  const m = Object.fromEntries(metrics.map((x) => [x.key, x.value]));
  const chart = data.top_authors.map((a) => ({ ...a, pct: Math.round(a.share * 100) }));
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat label="Active contributors (90 days)" value={formatValue(m.contributors_90d)} />
        <Stat label="Top contributor share" value={formatValue(m.top_contributor_share, "ratio")} />
        <Stat label="Commit-share bus factor" value={formatValue(m.bus_factor_estimate)}
              hint="Fewest authors who together made half of the recent commits." />
      </div>
      <Panel title="Share of commits, last 90 days" aside={`${data.total_commits} commits by ${data.authors} authors`}>
        {chart.length === 0 ? <p className="text-sm text-ink-soft">No commits in the last 90 days.</p> : (
          <div style={{ height: Math.max(160, chart.length * 30) }}>
            <ResponsiveContainer>
              <BarChart data={chart} layout="vertical" margin={{ left: 10, right: 30 }}>
                <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="author" width={130} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v, _n, p) => [`${v}% (${(p.payload as { commits: number }).commits} commits)`, "Share"]} />
                <Bar isAnimationActive={false} dataKey="pct" fill="var(--color-dim-contributors)" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        {data.other_commits > 0 && <p className="mt-2 text-xs text-ink-soft">{data.other_commits} further commits by other authors.</p>}
        <p className="mt-3 text-xs text-ink-faint">{data.note} Authors without a linked GitHub account appear as anonymised "unlinked" IDs.</p>
      </Panel>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel px-4 py-3">
      <p className="text-xs text-ink-soft">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {hint && <p className="text-xs text-ink-faint">{hint}</p>}
    </div>
  );
}

import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { Message, Panel, Skeleton } from "./ui";

const FEATURE_LABEL: Record<string, string> = {
  commits: "commits", issues_opened: "issues opened", issues_closed: "issues closed", prs_opened: "PRs opened", prs_merged: "PRs merged",
};
const AXIS = { fontSize: 11, fill: "var(--color-ink-faint)" };
const shortDate = (d: string) => new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

export function ActivityTab({ projectId, runId }: { projectId: number; runId: number }) {
  const { data, error, loading } = useAsync(() => api.activity(projectId), [projectId, runId]);
  if (loading) return <Skeleton className="h-80" />;
  if (error || !data) return <Message tone="error" title="Activity could not be loaded">{error?.message}</Message>;
  const anomaly = data.anomaly;
  return (
    <div className="space-y-5">
      <Panel title="Commits per week" aside="Last 52 weeks, bots excluded">
        <div className="h-56">
          <ResponsiveContainer>
            <BarChart data={data.weeks} margin={{ left: -20, right: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--color-line-soft)" />
              <XAxis dataKey="week_ending" tickFormatter={shortDate} tick={AXIS} minTickGap={24} />
              <YAxis tick={AXIS} allowDecimals={false} />
              <Tooltip labelFormatter={(l) => `Week ending ${shortDate(String(l))}`} />
              <Bar isAnimationActive={false} dataKey="commits" name="Commits" fill="var(--color-dim-activity)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Issues per week">
          <div className="h-52">
            <ResponsiveContainer>
              <LineChart data={data.weeks} margin={{ left: -20, right: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--color-line-soft)" />
                <XAxis dataKey="week_ending" tickFormatter={shortDate} tick={AXIS} minTickGap={24} />
                <YAxis tick={AXIS} allowDecimals={false} />
                <Tooltip labelFormatter={(l) => `Week ending ${shortDate(String(l))}`} /><Legend wrapperStyle={{ fontSize: 12 }} />
                <Line isAnimationActive={false} dataKey="issues_opened" name="Opened" stroke="var(--color-risk-high)" dot={false} strokeWidth={2} />
                <Line isAnimationActive={false} dataKey="issues_closed" name="Closed" stroke="var(--color-dim-issues)" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Pull requests per week">
          <div className="h-52">
            <ResponsiveContainer>
              <LineChart data={data.weeks} margin={{ left: -20, right: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--color-line-soft)" />
                <XAxis dataKey="week_ending" tickFormatter={shortDate} tick={AXIS} minTickGap={24} />
                <YAxis tick={AXIS} allowDecimals={false} />
                <Tooltip labelFormatter={(l) => `Week ending ${shortDate(String(l))}`} /><Legend wrapperStyle={{ fontSize: 12 }} />
                <Line isAnimationActive={false} dataKey="prs_opened" name="Opened" stroke="var(--color-ink-faint)" dot={false} strokeWidth={2} />
                <Line isAnimationActive={false} dataKey="prs_merged" name="Merged" stroke="var(--color-dim-prs)" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>
      <Panel title="Unusual weeks" aside="Experimental · Isolation Forest">
        {!anomaly || anomaly.status !== "ok" ? (
          <p className="text-sm text-ink-soft">{anomaly?.message ?? "Not enough activity to look for unusual weeks."}</p>
        ) : anomaly.anomalies.length === 0 ? (
          <p className="text-sm text-ink-soft">No week stood out from this repository's own normal pattern.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {anomaly.anomalies.map((a) => (
              <li key={a.week_ending}>
                <span className="font-semibold">Week ending {shortDate(a.week_ending)}:</span>{" "}
                <span className="text-ink-soft">{a.reasons.map((r) => `${FEATURE_LABEL[r.feature] ?? r.feature} ${r.value} (typical ${r.typical})`).join("; ")}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-xs text-ink-faint">Informational only. Unusual weeks are not part of the risk score.</p>
      </Panel>
    </div>
  );
}

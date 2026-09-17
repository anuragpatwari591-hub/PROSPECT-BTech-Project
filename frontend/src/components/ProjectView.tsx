import { lazy, Suspense, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { formatDate, relativeTime } from "../lib/format";
import type { Metric, Project, Recommendation, RiskResponse } from "../lib/types";
import { ExperimentalTab } from "./ExperimentalTab";
import { FactorsTab } from "./FactorsTab";
import { OverviewTab } from "./OverviewTab";
import { ScoreStrip } from "./ScoreStrip";
import { Button, Message, Skeleton } from "./ui";

// Chart-heavy tabs are loaded on demand to keep the first page load small.
const ActivityTab = lazy(() => import("./ActivityTab").then((m) => ({ default: m.ActivityTab })));
const ContributorsTab = lazy(() => import("./ContributorsTab").then((m) => ({ default: m.ContributorsTab })));
const HistoryTab = lazy(() => import("./HistoryTab").then((m) => ({ default: m.HistoryTab })));
const SimulatorTab = lazy(() => import("./SimulatorTab").then((m) => ({ default: m.SimulatorTab })));

const TABS = [
  ["overview", "Overview"], ["factors", "Risk factors"], ["activity", "Activity"], ["contributors", "Contributors"],
  ["simulator", "What-if"], ["history", "History"], ["experimental", "Experimental ML"],
] as const;
type Tab = (typeof TABS)[number][0];

interface Bundle { risk: RiskResponse; metrics: Metric[]; recommendations: Recommendation[] }

export function ProjectView({ project, onChanged, onDeleted }: { project: Project; onChanged: () => void; onDeleted: () => void }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [loadError, setLoadError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [runId, setRunId] = useState<number | null>(project.active_run?.id ?? null);
  const [runMessage, setRunMessage] = useState<{ tone: "error" | "warning"; title: string; body: string } | null>(null);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let current = true;
    setLoading(true);
    Promise.all([api.risk(project.id), api.metrics(project.id), api.recommendations(project.id)])
      .then(([risk, metrics, recommendations]) => { if (current) { setBundle({ risk, metrics: metrics.metrics, recommendations }); setLoadError(null); } })
      .catch((err: ApiError) => { if (current) { setBundle(null); setLoadError(err); } })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [project.id, refresh]);

  useEffect(() => { setRunId(project.active_run?.id ?? null); setRunMessage(null); setTab("overview"); }, [project.id, project.active_run?.id]);

  // Poll the background analysis run until it finishes.
  useEffect(() => {
    if (runId === null) return;
    const timer = setInterval(async () => {
      try {
        const run = await api.run(project.id, runId);
        if (run.status === "COMPLETED" || run.status === "FAILED") {
          setRunId(null);
          if (run.status === "FAILED") setRunMessage({ tone: "error", title: "Analysis failed", body: run.error_message ?? "Unknown error." });
          setRefresh((r) => r + 1);
          onChanged();
        }
      } catch { /* transient polling error: try again on next tick */ }
    }, 2000);
    return () => clearInterval(timer);
  }, [runId, project.id, onChanged]);

  async function startAnalysis(force: boolean) {
    setRunMessage(null);
    try {
      const run = await api.analyze(project.id, force);
      setRunId(run.id);
      onChanged();
    } catch (err) {
      const e = err as ApiError;
      if (e.code === "ANALYSIS_IN_PROGRESS" && typeof e.extra.run_id === "number") setRunId(e.extra.run_id);
      else setRunMessage({ tone: "error", title: "Could not start analysis", body: e.message });
    }
  }

  async function remove() {
    if (!window.confirm(`Delete ${project.name} and all of its stored analyses?`)) return;
    await api.deleteProject(project.id);
    onDeleted();
  }

  const running = runId !== null;
  const noAnalysis = loadError?.code === "NO_COMPLETED_ANALYSIS";

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="truncate text-2xl font-bold tracking-tight">{project.name}</h2>
          <p className="mt-1 text-sm text-ink-soft">
            <a href={project.url} target="_blank" rel="noreferrer noopener" className="underline decoration-line underline-offset-4 hover:text-ink">{project.url.replace("https://", "")}</a>
            {project.stars !== null && <> · {project.stars.toLocaleString("en-US")} stars</>}
            {project.is_archived && <> · <span className="font-semibold text-[color:var(--color-risk-high)]">archived</span></>}
            {bundle && <> · analysed <span title={formatDate(bundle.risk.run.finished_at)}>{relativeTime(bundle.risk.run.finished_at)}</span></>}
          </p>
          {project.description && <p className="mt-1 max-w-2xl text-sm text-ink-soft">{project.description}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => startAnalysis(bundle !== null)} disabled={running}>
            {running ? "Analysing…" : bundle ? "Re-analyse" : "Run analysis"}
          </Button>
          {bundle && <a href={api.reportUrl(project.id)} className="inline-flex items-center rounded-md border border-line bg-panel px-3.5 py-2 text-sm font-semibold hover:border-ink-faint" download>Download PDF report</a>}
          <Button variant="ghost" onClick={remove}>Delete</Button>
        </div>
      </header>

      {running && (
        <Message title="Analysis in progress">
          Collecting commits, issues, pull requests and releases from GitHub, then computing metrics and risk. Large repositories can take a minute.
        </Message>
      )}
      {runMessage && <Message tone={runMessage.tone} title={runMessage.title}>{runMessage.body}</Message>}

      {loading && !bundle ? (
        <div className="space-y-4"><Skeleton className="h-56" /><Skeleton className="h-32" /></div>
      ) : noAnalysis ? (
        !running && <Message title="This repository has not been analysed yet" action={<Button onClick={() => startAnalysis(false)}>Run first analysis</Button>}>
          The first analysis uses roughly 20–50 GitHub API requests.
        </Message>
      ) : loadError ? (
        <Message tone="error" title="Could not load the analysis">{loadError.message}</Message>
      ) : bundle && (
        <>
          <ScoreStrip risk={bundle.risk} />
          {bundle.risk.run.data_truncated && (
            <Message tone="warning" title="Some data was truncated">This repository is larger than the collection limits, so some counts are lower bounds. See Data notes on the overview.</Message>
          )}
          <nav className="-mx-1 flex gap-1 overflow-x-auto border-b border-line px-1" role="tablist" aria-label="Analysis sections">
            {TABS.map(([key, label]) => (
              <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}
                className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-semibold transition-colors ${tab === key ? "border-ink text-ink" : "border-transparent text-ink-soft hover:text-ink"}`}>
                {label}
              </button>
            ))}
          </nav>
          <div role="tabpanel"><Suspense fallback={<Skeleton className="h-80" />}>
            {tab === "overview" && <OverviewTab risk={bundle.risk} metrics={bundle.metrics} recommendations={bundle.recommendations} onOpenFactors={() => setTab("factors")} />}
            {tab === "factors" && <FactorsTab risk={bundle.risk} metrics={bundle.metrics} />}
            {tab === "activity" && <ActivityTab projectId={project.id} runId={bundle.risk.run.id} />}
            {tab === "contributors" && <ContributorsTab projectId={project.id} runId={bundle.risk.run.id} metrics={bundle.metrics} />}
            {tab === "simulator" && <SimulatorTab projectId={project.id} metrics={bundle.metrics} />}
            {tab === "history" && <HistoryTab projectId={project.id} runId={bundle.risk.run.id} />}
            {tab === "experimental" && <ExperimentalTab risk={bundle.risk} />}
          </Suspense></div>
        </>
      )}
    </div>
  );
}

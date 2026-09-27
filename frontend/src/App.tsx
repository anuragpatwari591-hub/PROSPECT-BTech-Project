import { useCallback, useEffect, useState } from "react";
import { ProjectView } from "./components/ProjectView";
import { AddProjectForm, ProjectList } from "./components/Sidebar";
import { Message, Skeleton } from "./components/ui";
import { api } from "./lib/api";
import { useAsync } from "./lib/useAsync";

export default function App() {
  const projects = useAsync(() => api.listProjects(), []);
  const [selected, setSelected] = useState<number | null>(null);
  const { reload } = projects;

  useEffect(() => {
    const list = projects.data ?? [];
    if (list.length && (selected === null || !list.some((p) => p.id === selected))) setSelected(list[0].id);
    if (!list.length && selected !== null && !projects.loading) setSelected(null);
  }, [projects.data, projects.loading, selected]);

  const onChanged = useCallback(() => reload(), [reload]);
  const project = projects.data?.find((p) => p.id === selected) ?? null;

  return (
    <div className="flex min-h-full flex-col lg:flex-row">
      <aside className="border-b border-line bg-panel lg:sticky lg:top-0 lg:h-screen lg:w-80 lg:shrink-0 lg:overflow-y-auto lg:border-r lg:border-b-0">
        <div className="space-y-6 p-5">
          <div>
            <p className="text-xl font-bold tracking-tight">PROSPECT</p>
            <p className="text-xs text-ink-soft">Explainable risk analysis for GitHub repositories</p>
          </div>
          <AddProjectForm onCreated={(p) => { reload(); setSelected(p.id); }} onExisting={(id) => setSelected(id)} />
          <div>
            <p className="mb-2 text-sm font-semibold">Repositories</p>
            {projects.loading && !projects.data ? <Skeleton className="h-20" /> :
              <ProjectList projects={projects.data ?? []} selected={selected} onSelect={setSelected} />}
          </div>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-5 lg:p-8">
        <div className="mx-auto max-w-6xl">
          {projects.error ? (
            <Message tone="error" title="Cannot load repositories">{projects.error.message}</Message>
          ) : project ? (
            <ProjectView key={project.id} project={project} onChanged={onChanged} onDeleted={() => { setSelected(null); reload(); }} />
          ) : !projects.loading && (
            <div className="mx-auto mt-16 max-w-xl">
              <h1 className="text-3xl font-bold tracking-tight">Find out where a software project is at risk, and why.</h1>
              <p className="mt-3 text-ink-soft">Add a public GitHub repository. PROSPECT collects its commits, issues, pull requests and releases, turns them into documented metrics, and shows exactly which signals raise the risk score, with actions to take.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

import { useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import { LEVEL_COLOR } from "../lib/format";
import type { Project } from "../lib/types";
import { Button } from "./ui";

const URL_PATTERN = /^(https?:\/\/(www\.)?github\.com\/)?[A-Za-z0-9-]+\/[A-Za-z0-9._-]+(\.git)?\/?$/;

export function AddProjectForm({ onCreated, onExisting }: { onCreated: (p: Project) => void; onExisting: (id: number) => void }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = url.trim();
    if (!URL_PATTERN.test(value)) {
      setError("Use the form https://github.com/owner/repository.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      onCreated(await api.createProject(value));
      setUrl("");
    } catch (err) {
      if (err instanceof ApiError && err.code === "PROJECT_EXISTS" && typeof err.extra.project_id === "number") {
        onExisting(err.extra.project_id);
        setUrl("");
      } else {
        setError(err instanceof ApiError ? err.message : "Could not add the repository.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-2">
      <label htmlFor="repo-url" className="block text-sm font-semibold">Add a GitHub repository</label>
      <input
        id="repo-url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://github.com/owner/repo"
        aria-invalid={Boolean(error)} aria-describedby={error ? "repo-url-error" : undefined}
        className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm placeholder:text-ink-faint focus:border-accent focus:outline-none"
      />
      {error && <p id="repo-url-error" className="text-xs text-[color:var(--color-risk-critical)]">{error}</p>}
      <Button type="submit" disabled={busy || !url.trim()} className="w-full">{busy ? "Checking repository…" : "Add repository"}</Button>
    </form>
  );
}

export function ProjectList({ projects, selected, onSelect }: { projects: Project[]; selected: number | null; onSelect: (id: number) => void }) {
  if (!projects.length) {
    return <p className="text-sm text-ink-soft">No repositories yet. Add one above to run the first analysis.</p>;
  }
  return (
    <ul className="space-y-1" aria-label="Repositories">
      {projects.map((p) => {
        const active = p.id === selected;
        return (
          <li key={p.id}>
            <button
              type="button" onClick={() => onSelect(p.id)} aria-current={active ? "true" : undefined}
              className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left transition-colors ${active ? "bg-accent-soft" : "hover:bg-line-soft"}`}
            >
              <span className="h-8 w-1 shrink-0 rounded-full" style={{ background: p.latest ? LEVEL_COLOR[p.latest.risk_level] : "var(--color-line)" }} aria-hidden />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold">{p.name}</span>
                <span className="block text-xs text-ink-soft">
                  {p.active_run ? "Analysing…" : p.latest ? `Risk ${p.latest.risk_score.toFixed(0)} · ${p.latest.risk_level.toLowerCase()}` : "Not analysed yet"}
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

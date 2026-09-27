import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ScoreStrip } from "../components/ScoreStrip";
import { AddProjectForm } from "../components/Sidebar";
import type { RiskResponse } from "../lib/types";

afterEach(() => vi.restoreAllMocks());

const risk: RiskResponse = {
  run: { id: 1, project_id: 1, status: "COMPLETED", started_at: "", finished_at: "", error_code: null, error_message: null, used_cache: false, api_calls: 10, data_truncated: false, collection_notes: [] },
  risk_score: 46.2, health_score: 53.8, risk_level: "MEDIUM", coverage: 0.85, engine_version: "rules-1.0",
  dimensions: [
    { key: "activity", label: "Activity risk", weight: 0.25, effective_weight: 0.294, score: 20, contribution: 5.9, status: "scored" },
    { key: "contributors", label: "Contributor dependency risk", weight: 0.2, effective_weight: 0.235, score: 90, contribution: 21.2, status: "scored" },
    { key: "releases", label: "Release risk", weight: 0.15, effective_weight: 0, score: null, contribution: 0, status: "not_applicable" },
  ],
  factors: [], top_factors: [], disclaimer: "Rule-based heuristic score.", ml: null,
};

it("shows the score, level and where the points come from", () => {
  render(<ScoreStrip risk={risk} />);
  expect(screen.getByTestId("risk-score")).toHaveTextContent("46");
  expect(screen.getByText("Medium risk")).toBeInTheDocument();
  expect(screen.getByRole("img")).toHaveAccessibleName(/Contributor dependency risk 21.2 points/);
  expect(screen.getByText(/Not scored \(no data\): Release risk/)).toBeInTheDocument();
  expect(screen.getByText("Rule-based heuristic score.")).toBeInTheDocument();
});

it("validates the repository URL before calling the API", async () => {
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  render(<AddProjectForm onCreated={vi.fn()} onExisting={vi.fn()} />);
  await userEvent.type(screen.getByLabelText("Add a GitHub repository"), "https://gitlab.com/a/b");
  await userEvent.click(screen.getByRole("button", { name: "Add repository" }));
  expect(screen.getByText(/Use the form/)).toBeInTheDocument();
  expect(fetchSpy).not.toHaveBeenCalled();
});

it("selects the existing project when the repository is already registered", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: { code: "PROJECT_EXISTS", message: "exists", project_id: 7 } }), { status: 409 }));
  const onExisting = vi.fn();
  render(<AddProjectForm onCreated={vi.fn()} onExisting={onExisting} />);
  await userEvent.type(screen.getByLabelText("Add a GitHub repository"), "pallets/flask");
  await userEvent.click(screen.getByRole("button", { name: "Add repository" }));
  expect(onExisting).toHaveBeenCalledWith(7);
});

import { useEffect, useState } from "react";
import { analyzeRepo, fetchHistory, fetchHistoryItem, deleteHistoryItem } from "./api.js";
import RepoInput from "./components/RepoInput.jsx";
import Dashboard from "./components/Dashboard.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";

export default function App() {
  const [view, setView] = useState("analyze"); // "analyze" | "history"
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);

  const loadHistory = async () => {
    try {
      const items = await fetchHistory();
      setHistory(items);
    } catch (e) {
      // history is a secondary feature; don't block the main flow on failure
      console.error("Failed to load history", e);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleAnalyze = async (repoUrl) => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeRepo(repoUrl);
      setAnalysis(result);
      setView("analyze");
      loadHistory();
    } catch (e) {
      setError(e.message);
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectHistory = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchHistoryItem(id);
      setAnalysis(result);
      setView("analyze");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteHistory = async (id) => {
    try {
      await deleteHistoryItem(id);
      if (analysis?.id === id) setAnalysis(null);
      loadHistory();
    } catch (e) {
      console.error("Failed to delete history item", e);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">P</span>
          <div>
            <h1>PROSPECT</h1>
            <p>Predictive Software Project Risk &amp; Engineering Control System</p>
          </div>
        </div>
        <nav className="app-nav">
          <button
            className={view === "analyze" ? "nav-btn active" : "nav-btn"}
            onClick={() => setView("analyze")}
          >
            Analyze
          </button>
          <button
            className={view === "history" ? "nav-btn active" : "nav-btn"}
            onClick={() => setView("history")}
          >
            History ({history.length})
          </button>
        </nav>
      </header>

      <main className="app-main">
        {view === "analyze" && (
          <>
            <RepoInput onAnalyze={handleAnalyze} loading={loading} />
            {error && <div className="error-banner">{error}</div>}
            {analysis && <Dashboard analysis={analysis} onUpdate={setAnalysis} />}
            {!analysis && !loading && !error && (
              <div className="empty-state">
                <p>Enter a public GitHub repository URL above to run a risk analysis.</p>
                <p className="empty-state-hint">
                  Example: <code>https://github.com/facebook/react</code>
                </p>
              </div>
            )}
          </>
        )}

        {view === "history" && (
          <HistoryPanel
            history={history}
            onSelect={handleSelectHistory}
            onDelete={handleDeleteHistory}
          />
        )}
      </main>

      <footer className="app-footer">
        <span>PROSPECT &mdash; deterministic, rule-based risk scoring. No ML, no guesswork.</span>
      </footer>
    </div>
  );
}

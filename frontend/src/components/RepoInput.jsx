import { useState } from "react";

export default function RepoInput({ onAnalyze, loading }) {
  const [value, setValue] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    onAnalyze(trimmed);
  };

  return (
    <form className="repo-input" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="https://github.com/owner/repo"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={loading}
      />
      <button type="submit" disabled={loading || !value.trim()}>
        {loading ? "Analyzing…" : "Analyze Repository"}
      </button>
    </form>
  );
}

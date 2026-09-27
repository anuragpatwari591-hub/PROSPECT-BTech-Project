const CLASS_COLOR = {
  LOW: "#2e7d32",
  MEDIUM: "#f9a825",
  HIGH: "#ef6c00",
  CRITICAL: "#c62828",
};

export default function HistoryPanel({ history, onSelect, onDelete }) {
  if (history.length === 0) {
    return (
      <div className="empty-state">
        <p>No analyses yet. Run one from the Analyze tab.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3>Analysis History</h3>
      <table className="history-table">
        <thead>
          <tr>
            <th>Repository</th>
            <th>Risk Score</th>
            <th>Classification</th>
            <th>Date</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {history.map((item) => (
            <tr key={item.id}>
              <td className="history-repo" onClick={() => onSelect(item.id)}>
                {item.repo_full_name}
              </td>
              <td>{item.risk_score}</td>
              <td>
                <span
                  className="classification-pill"
                  style={{ backgroundColor: CLASS_COLOR[item.classification] || "#888" }}
                >
                  {item.classification}
                </span>
              </td>
              <td>{new Date(item.created_at).toLocaleString()}</td>
              <td>
                <button className="link-btn" onClick={() => onDelete(item.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

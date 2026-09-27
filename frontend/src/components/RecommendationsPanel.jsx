export default function RecommendationsPanel({ recommendations }) {
  return (
    <div className="panel">
      <h3>Recommendations</h3>
      <ul className="recommendation-list">
        {recommendations.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>
    </div>
  );
}

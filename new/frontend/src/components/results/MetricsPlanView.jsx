export default function MetricsPlanView({ results }) {
  const plan = results?.metrics_plan_dict

  if (!plan) {
    return <pre className="code-view">{results?.metrics_plan_raw || 'Ожидание…'}</pre>
  }

  return (
    <div className="metrics-plan">
      {Object.entries(plan).map(([col, metrics]) => (
        <div key={col} className="metric-row">
          <strong>{col}</strong>
          <div className="metric-tags">
            {metrics.map((m) => <span key={m} className="tag">{m}</span>)}
          </div>
        </div>
      ))}
    </div>
  )
}

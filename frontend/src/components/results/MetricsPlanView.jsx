import { useActiveTable } from '../../hooks/useActiveTable'
import DatasetSwitcher from './DatasetSwitcher'

export default function MetricsPlanView({ results }) {
  const tables = results?.tables || []
  const { items, active, activeId, setActiveId } = useActiveTable(tables)
  const plan = active?.metrics_plan_dict || (tables.length <= 1 ? results?.metrics_plan_dict : null)
  const fallback = active?.metrics_plan_raw || results?.metrics_plan_raw

  if (!plan || !Object.keys(plan).length) {
    return (
      <>
        <DatasetSwitcher items={items} value={activeId} onChange={setActiveId} />
        <pre className="code-view">{fallback || 'Ожидание…'}</pre>
      </>
    )
  }

  return (
    <div className="metrics-plan">
      <DatasetSwitcher items={items} value={activeId} onChange={setActiveId} />
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

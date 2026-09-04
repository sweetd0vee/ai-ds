import { useActiveTable } from '../../hooks/useActiveTable'
import DatasetSwitcher from './DatasetSwitcher'

export default function MetricsResultsView({ results }) {
  const tables = results?.tables || []
  const { items, active, activeId, setActiveId } = useActiveTable(tables)
  const text = active?.metrics_results_raw || (tables.length <= 1 ? results?.metrics_results_raw : '')
  return (
    <>
      <DatasetSwitcher items={items} value={activeId} onChange={setActiveId} />
      <pre className="code-view">{text || 'Ожидание…'}</pre>
    </>
  )
}

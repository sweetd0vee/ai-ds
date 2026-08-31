import { PREVIEW_ROWS } from '../../constants'
import { useActiveTable } from '../../hooks/useActiveTable'
import DatasetSwitcher from './DatasetSwitcher'
import PreviewTable from './PreviewTable'

export default function PreviewView({ results, pending }) {
  const tables = results?.tables || []
  const { items, active, activeId, setActiveId } = useActiveTable(tables)

  const preview = active?.preview || (!items.length ? results?.preview : null)
  const columns = active?.columns || (!items.length ? results?.columns : active?.columns)
  const rows = active?.rows
  const cols = active?.cols

  return (
    <>
      <DatasetSwitcher items={items} value={activeId} onChange={setActiveId} />
      {(rows != null && cols != null) && (
        <p className="preview-meta">
          {rows} строк × {cols} столбцов · первые {PREVIEW_ROWS} записей
          {active?.label && items.length > 1 ? ` · ${active.label}` : ''}
        </p>
      )}
      <PreviewTable preview={preview} columns={columns} pending={pending} />
    </>
  )
}

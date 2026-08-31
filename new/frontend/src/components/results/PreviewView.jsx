import { useEffect, useMemo, useState } from 'react'
import { PREVIEW_ROWS } from '../../constants'
import DatasetSwitcher from './DatasetSwitcher'
import PreviewTable from './PreviewTable'

export default function PreviewView({ results, pending }) {
  const tables = results?.tables || []
  const items = useMemo(() => {
    const list = []
    if (results?.table_count > 1 && results?.preview) {
      const mode = results.analysis_source
      const label = mode === 'join' ? 'Объединённая' : mode === 'union' ? 'Склеенная' : 'Для анализа'
      list.push({
        id: '__analysis__',
        name: results.filename || 'Анализ',
        label,
        rows: results.shape?.[0],
        cols: results.shape?.[1],
        preview: results.preview,
        columns: results.columns,
      })
    }
    tables.forEach((table) => list.push({
      ...table,
      label: table.sheet ? `${table.filename} / ${table.sheet}` : table.name,
    }))
    return list
  }, [results, tables])

  const [activeId, setActiveId] = useState(items[0]?.id)

  useEffect(() => {
    if (!items.some((item) => item.id === activeId)) {
      setActiveId(items[0]?.id)
    }
  }, [items, activeId])

  const active = items.find((item) => item.id === activeId) || items[0]
  const preview = active?.preview || (!items.length ? results?.preview : null)
  const columns = active?.columns || results?.columns
  const rows = active?.rows ?? results?.shape?.[0]
  const cols = active?.cols ?? results?.shape?.[1]

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

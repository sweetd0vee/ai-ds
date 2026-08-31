import { useEffect, useMemo, useState } from 'react'
import DatasetSwitcher from './DatasetSwitcher'

const KIND_LABELS = {
  numeric: 'Число',
  categorical: 'Категория',
  datetime: 'Дата',
  boolean: 'Булев',
  identifier: 'ID',
  textual: 'Текст',
}

function formatStructureStats(col) {
  const text = col.description || ''
  const filled = text.match(/(\d+)\s+значений?/)
  const unique = text.match(/(\d+)\s+(уникальных|категорий)/)
  const parts = []
  if (filled) parts.push(`${filled[1]} зап.`)
  if (unique) parts.push(`${unique[1]} ${unique[2] === 'категорий' ? 'кат.' : 'уник.'}`)
  return parts.length ? parts.join(' · ') : '—'
}

function ColumnsTable({ columns, datetimeCandidates }) {
  return (
    <>
      <div className="structure-toolbar">
        <span className="structure-count">{columns.length} столбцов</span>
        {datetimeCandidates.length > 0 && (
          <span className="structure-dates">
            Даты: {datetimeCandidates.join(', ')}
          </span>
        )}
      </div>
      <div className="table-scroll table-scroll--structure">
        <table className="structure-table">
          <thead>
            <tr>
              <th className="structure-th-idx">#</th>
              <th>Столбец</th>
              <th>Тип</th>
              <th>Сводка</th>
            </tr>
          </thead>
          <tbody>
            {columns.map((col, i) => (
              <tr key={col.name}>
                <td className="structure-idx">{i + 1}</td>
                <td className="structure-name" title={col.name}>{col.name}</td>
                <td>
                  <span className={`kind-badge kind-${col.kind || 'textual'}`}>
                    {KIND_LABELS[col.kind] || col.type}
                  </span>
                </td>
                <td className="structure-stats">{formatStructureStats(col)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

export default function StructureView({ results }) {
  const analysisStructure = results?.data_structure || results?.parsed_data_structure
  const tables = results?.tables || []

  const items = useMemo(() => {
    const list = []
    if (tables.length > 1 && analysisStructure?.columns?.length) {
      list.push({
        id: '__analysis__',
        label: results.analysis_source === 'join' ? 'Объединённая' : 'Для анализа',
        rows: results.shape?.[0],
        cols: results.shape?.[1],
        structure: analysisStructure,
      })
    }
    tables.forEach((table) => {
      list.push({
        id: table.id,
        label: table.sheet ? `${table.filename} / ${table.sheet}` : table.name,
        rows: table.rows,
        cols: table.cols,
        structure: table.structure || (tables.length === 1 ? analysisStructure : null),
      })
    })
    return list
  }, [tables, analysisStructure, results])

  const [activeId, setActiveId] = useState(items[0]?.id)
  useEffect(() => {
    if (!items.some((item) => item.id === activeId)) {
      setActiveId(items[0]?.id)
    }
  }, [items, activeId])

  const active = items.find((item) => item.id === activeId) || items[0]
  const structure = active?.structure || analysisStructure
  const columns = structure?.columns || []
  const datetimeCandidates = structure?.datetime_candidates || []

  if (!columns.length && !tables.length) {
    return <pre className="code-view">{results?.data_structure_raw || 'Ожидание…'}</pre>
  }

  return (
    <div className="structure-view">
      <DatasetSwitcher items={items} value={activeId} onChange={setActiveId} />
      {columns.length ? (
        <ColumnsTable columns={columns} datetimeCandidates={datetimeCandidates} />
      ) : (
        <pre className="code-view">{results?.data_structure_raw || 'Ожидание структуры…'}</pre>
      )}
    </div>
  )
}

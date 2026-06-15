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

export default function StructureView({ results }) {
  const structure = results?.data_structure || results?.parsed_data_structure
  const columns = structure?.columns || []
  const datetimeCandidates = structure?.datetime_candidates || []

  if (!columns.length) {
    return <pre className="code-view">{results?.data_structure_raw || 'Ожидание…'}</pre>
  }

  return (
    <div className="structure-view">
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
    </div>
  )
}

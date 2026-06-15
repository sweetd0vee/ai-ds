export default function PreviewTable({ preview, columns }) {
  if (!preview?.length) {
    return (
      <div className="table-scroll table-scroll--empty">
        <div className="empty">Данные загружаются…</div>
      </div>
    )
  }

  const cols = columns || Object.keys(preview[0] || {})

  return (
    <div className="table-scroll table-scroll--preview">
      <table>
        <thead>
          <tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {preview.map((row, i) => (
            <tr key={i}>{cols.map((c) => <td key={c}>{row[c] ?? ''}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

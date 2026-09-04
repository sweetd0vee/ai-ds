import { Loader2 } from 'lucide-react'

export default function PreviewTable({ preview, columns, pending = false }) {
  if (!preview?.length) {
    return (
      <div className="table-scroll table-scroll--empty">
        <div className={`empty${pending ? ' empty--loading' : ''}`}>
          {pending && <Loader2 size={18} className="spin" />}
          {pending ? 'Данные загружаются…' : 'Нет строк для предпросмотра'}
        </div>
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

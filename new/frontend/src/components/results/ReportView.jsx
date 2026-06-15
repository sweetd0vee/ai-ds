import AnalysisView from './AnalysisView'
import { AnalysisInline, parseReportSections } from './textFormat'

function ReportSectionBody({ title, body }) {
  const upper = title.toUpperCase()
  const clean = body.includes('---JSON---') ? body.split('---JSON---')[0].trim() : body.trim()

  if (!clean) return <p className="analysis-paragraph muted">Данные недоступны.</p>

  if (upper.includes('ИНТЕРПРЕТАЦИЯ') || (upper.includes('АНАЛИЗ') && !upper.includes('МЕТРИК'))) {
    return <AnalysisView text={clean} />
  }

  const lines = clean.split('\n').map((l) => l.trim()).filter(Boolean)
  const bulletSection = upper.includes('РЕКОМЕНДАЦИИ')
    || upper.includes('ВИЗУАЛИЗАЦ')
    || upper.includes('МЕТРИК')

  if (bulletSection || (lines.length > 0 && lines.every((l) => l.startsWith('•')))) {
    return (
      <ul className="report-list">
        {lines.map((line, i) => (
          <li key={i}><AnalysisInline text={line.replace(/^•\s*/, '')} /></li>
        ))}
      </ul>
    )
  }

  const blocks = clean.split(/\n\s*\n/).filter(Boolean)

  return (
    <div className="report-section-body">
      {blocks.map((block, bi) => {
        const blines = block.split('\n').map((l) => l.trim()).filter(Boolean)

        if (blines.length > 1 && blines.every((l) => l.startsWith('•'))) {
          return (
            <ul key={bi} className="report-list">
              {blines.map((l, i) => (
                <li key={i}><AnalysisInline text={l.replace(/^•\s*/, '')} /></li>
              ))}
            </ul>
          )
        }

        return blines.map((line, li) => {
          const kv = line.match(/^([^:]{2,48}):\s*(.+)$/)
          if (kv && !line.startsWith('http')) {
            return (
              <p key={`${bi}-${li}`} className="report-kv">
                <strong>{kv[1]}:</strong>{' '}
                <AnalysisInline text={kv[2]} />
              </p>
            )
          }
          if (line === line.toUpperCase() && line.length < 72 && !line.includes('  ')) {
            return <h5 key={`${bi}-${li}`} className="report-mini-heading">{line}</h5>
          }
          if (line.startsWith('•')) {
            return (
              <p key={`${bi}-${li}`} className="report-bullet">
                • <AnalysisInline text={line.replace(/^•\s*/, '')} />
              </p>
            )
          }
          return (
            <p key={`${bi}-${li}`} className="analysis-paragraph">
              <AnalysisInline text={line} />
            </p>
          )
        })
      })}
    </div>
  )
}

export default function ReportView({ text }) {
  if (!text?.trim()) {
    return <div className="text-view">Ожидание…</div>
  }

  const sections = parseReportSections(text)

  if (!sections.length) {
    return (
      <div className="report-view-formatted">
        <p className="analysis-paragraph"><AnalysisInline text={text} /></p>
      </div>
    )
  }

  return (
    <div className="report-view-formatted">
      {sections.map((section, i) => (
        <section key={i} className="report-section">
          <h3 className="report-section-title">{section.title}</h3>
          <ReportSectionBody title={section.title} body={section.body} />
        </section>
      ))}
    </div>
  )
}

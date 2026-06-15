const FEATURE_RE = /^\*\*([^*]+)\*\*\s*[—–:-]\s*(.+)$/

export function AnalysisInline({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return <span key={i}>{part}</span>
  })
}

export function parseReportSections(text) {
  const sections = []
  let current = null
  let body = []

  for (const line of text.replace(/\r\n/g, '\n').split('\n')) {
    const stripped = line.trim()
    if (stripped === 'ИТОГОВЫЙ АНАЛИТИЧЕСКИЙ ОТЧЁТ' || /^=+$/.test(stripped)) continue
    if (stripped.startsWith('— Отчёт сформирован')) continue

    const m = stripped.match(/^(\d+)\.\s+(.+)$/)
    if (m) {
      if (current) sections.push({ title: current, body: body.join('\n').trim() })
      current = m[2]
      body = []
    } else {
      body.push(line)
    }
  }

  if (current) sections.push({ title: current, body: body.join('\n').trim() })
  return sections
}

export function normalizeAnalysisText(text) {
  return text.replace(/\r\n/g, '\n').replace(/  \n/g, '\n').trim()
}

export function matchFeatureLine(line) {
  return line.match(FEATURE_RE)
}

export function FeatureLine({ name, description }) {
  return (
    <>
      <strong className="analysis-feature-name">{name}</strong>
      <span className="analysis-feature-sep"> — </span>
      <span className="analysis-feature-desc"><AnalysisInline text={description} /></span>
    </>
  )
}

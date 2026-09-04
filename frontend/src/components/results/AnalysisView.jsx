import {
  AnalysisInline,
  FeatureLine,
  matchFeatureLine,
  normalizeAnalysisText,
} from './textFormat'

export default function AnalysisView({ text }) {
  if (!text?.trim()) {
    return <div className="text-view">Ожидание…</div>
  }

  const blocks = normalizeAnalysisText(text).split(/\n\s*\n/).filter(Boolean)

  return (
    <div className="analysis-view">
      {blocks.map((block, bi) => {
        const lines = block.split('\n').map((l) => l.trim()).filter(Boolean)
        const features = lines.filter((l) => matchFeatureLine(l))

        if (features.length >= 2 || (features.length === 1 && lines.length === 1)) {
          return (
            <ul key={bi} className="analysis-features">
              {lines.map((line, li) => {
                const m = matchFeatureLine(line)
                if (!m) {
                  return (
                    <li key={li} className="analysis-feature analysis-feature--text">
                      <AnalysisInline text={line} />
                    </li>
                  )
                }
                return (
                  <li key={li} className="analysis-feature">
                    <FeatureLine name={m[1]} description={m[2]} />
                  </li>
                )
              })}
            </ul>
          )
        }

        const sub = block.match(/^([А-ЯA-ZЁ][^:]{1,48}):\s*(.*)$/s)
        if (sub && !block.includes('**')) {
          return (
            <div key={bi} className="analysis-block">
              <h4 className="analysis-subheading">{sub[1]}</h4>
              {sub[2] && <p className="analysis-paragraph"><AnalysisInline text={sub[2]} /></p>}
            </div>
          )
        }

        return (
          <div key={bi} className="analysis-block">
            {lines.map((line, li) => {
              const m = matchFeatureLine(line)
              if (m) {
                return (
                  <div key={li} className="analysis-feature analysis-feature--row">
                    <FeatureLine name={m[1]} description={m[2]} />
                  </div>
                )
              }
              return (
                <p key={li} className="analysis-paragraph">
                  <AnalysisInline text={line} />
                </p>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

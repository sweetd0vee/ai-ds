import { AnalysisInline } from './textFormat'

const PRIORITY_LABELS = {
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

function HypothesisCard({ item, selected, onToggle }) {
  const priority = item.priority || 'medium'

  return (
    <article
      className={`hypothesis-card hypothesis-card--${priority} ${selected ? 'hypothesis-card--selected' : 'hypothesis-card--unchecked'}`}
    >
      <header className="hypothesis-card-header">
        <label className="hypothesis-check">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggle(item.id)}
            aria-label={`Выбрать гипотезу ${item.id}`}
          />
        </label>
        <span className="hypothesis-id">#{item.id}</span>
        <h4 className="hypothesis-title">{item.title}</h4>
        {item.kind_label || item.kind ? (
          <span className="hypothesis-kind">{item.kind_label || item.kind}</span>
        ) : null}
        <span className={`hypothesis-priority hypothesis-priority--${priority}`}>
          {item.priority_label || PRIORITY_LABELS[priority] || priority}
        </span>
      </header>

      {item.statement && (
        <section className="hypothesis-section">
          <h5>Формулировка</h5>
          <p><AnalysisInline text={item.statement} /></p>
        </section>
      )}

      {item.rationale && (
        <section className="hypothesis-section">
          <h5>Основание</h5>
          <p><AnalysisInline text={item.rationale} /></p>
        </section>
      )}

      {item.columns?.length > 0 && (
        <section className="hypothesis-section">
          <h5>Столбцы</h5>
          <div className="hypothesis-columns">
            {item.columns.map((col) => (
              <span key={col} className="hypothesis-column-tag">{col}</span>
            ))}
          </div>
        </section>
      )}

      {item.verification && (
        <section className="hypothesis-section hypothesis-section--verify">
          <h5>Как проверить</h5>
          <p><AnalysisInline text={item.verification} /></p>
        </section>
      )}
    </article>
  )
}

function HypothesesFallback({ text }) {
  if (!text?.trim()) {
    return <div className="text-view">Ожидание…</div>
  }

  return (
    <div className="hypotheses-fallback">
      <p className="hypotheses-intro muted">
        Модель вернула ответ в нестандартном формате. Показан исходный текст — перезапустите
        анализ или обновите страницу, если парсер уже исправлен на сервере:
      </p>
      <pre className="code-view hypotheses-raw">{text}</pre>
    </div>
  )
}

export default function HypothesesView({
  results,
  selectedIds,
  onToggle,
  onSelectAll,
  onSelectNone,
}) {
  const hypotheses = results?.hypotheses
  const raw = results?.hypotheses_raw

  if (!hypotheses?.length && !raw?.trim()) {
    return <div className="text-view">Ожидание…</div>
  }

  if (!hypotheses?.length) {
    return <HypothesesFallback text={raw} />
  }

  const selectedCount = selectedIds?.size ?? 0
  const allSelected = selectedCount === hypotheses.length && hypotheses.length > 0

  return (
    <div className="hypotheses-view">
      <div className="hypotheses-intro-block">
        <h3 className="hypotheses-heading">Проверяемые гипотезы</h3>
        <p className="hypotheses-intro">
          Ниже — проверяемые гипотезы, которые Python сначала подтвердил цифрами
          (ядро рынка, выбросы, редкие категории, различия групп), а затем модель сформулировала ясным языком.
        </p>
        <div className="hypotheses-select-bar">
          <button
            type="button"
            className="hypotheses-select-btn"
            onClick={allSelected ? onSelectNone : onSelectAll}
          >
            {allSelected ? 'Снять все' : 'Выбрать все'}
          </button>
          <span className="hypotheses-select-count">
            Выбрано {selectedCount} из {hypotheses.length}
          </span>
        </div>
      </div>

      <div className="hypotheses-list">
        {hypotheses.map((item) => (
          <HypothesisCard
            key={item.id ?? item.title}
            item={item}
            selected={Boolean(selectedIds?.has(item.id))}
            onToggle={onToggle}
          />
        ))}
      </div>
    </div>
  )
}

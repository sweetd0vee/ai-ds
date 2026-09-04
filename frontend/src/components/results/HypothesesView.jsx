import { useState } from 'react'
import { Loader2, Plus } from 'lucide-react'
import { addHypothesis } from '../../api'
import { AnalysisInline } from './textFormat'

const PRIORITY_LABELS = {
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
}

const EMPTY_FORM = {
  title: '',
  statement: '',
  columns: '',
  priority: 'medium',
}

function parseColumnInput(value) {
  return value
    .split(/[,;]/)
    .map((part) => part.trim())
    .filter(Boolean)
}

function HypothesisCard({ item, selected, onToggle }) {
  const priority = item.priority || 'medium'
  const isAuditor = item.source === 'auditor' || item.kind === 'auditor'

  return (
    <article
      className={`hypothesis-card hypothesis-card--${priority} ${isAuditor ? 'hypothesis-card--auditor' : ''} ${selected ? 'hypothesis-card--selected' : 'hypothesis-card--unchecked'}`}
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
          <span className={`hypothesis-kind ${isAuditor ? 'hypothesis-kind--auditor' : ''}`}>
            {item.kind_label || item.kind}
          </span>
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
    return null
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

function AddHypothesisForm({ jobId, datasetColumns, onAdded }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const updateField = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }))
    if (error) setError(null)
  }

  const toggleColumn = (name) => {
    const key = String(name)
    const selected = new Set(parseColumnInput(form.columns))
    if (selected.has(key)) selected.delete(key)
    else selected.add(key)
    setForm((prev) => ({ ...prev, columns: [...selected].join(', ') }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const statement = form.statement.trim()
    if (!jobId || !statement || submitting) return

    setSubmitting(true)
    setError(null)
    try {
      const data = await addHypothesis(jobId, {
        title: form.title.trim(),
        statement,
        columns: parseColumnInput(form.columns),
        priority: form.priority,
      })
      setForm(EMPTY_FORM)
      onAdded?.(data)
    } catch (err) {
      setError(err.message || 'Не удалось добавить гипотезу')
    } finally {
      setSubmitting(false)
    }
  }

  const selectedColumns = new Set(parseColumnInput(form.columns))
  const canSubmit = Boolean(form.statement.trim()) && !submitting

  return (
    <form className="hypothesis-composer" onSubmit={handleSubmit}>
      <div className="hypothesis-composer-header">
        <h3>Добавить свою гипотезу</h3>
        <p>
          Сформулируйте гипотезу по этим данным — она попадёт в список и позже сможет
          проверяться скриптом.
        </p>
      </div>

      <label className="hypothesis-composer-field">
        <span>Заголовок</span>
        <input
          type="text"
          value={form.title}
          onChange={updateField('title')}
          placeholder="Краткое название"
          maxLength={160}
        />
      </label>

      <label className="hypothesis-composer-field">
        <span>Формулировка</span>
        <textarea
          value={form.statement}
          onChange={updateField('statement')}
          placeholder="Например: просрочка чаще встречается в сегменте X при ставке выше Y"
          rows={3}
          required
        />
      </label>

      <div className="hypothesis-composer-row">
        <label className="hypothesis-composer-field">
          <span>Столбцы</span>
          <input
            type="text"
            value={form.columns}
            onChange={updateField('columns')}
            placeholder="Через запятую, необязательно"
            list="hypothesis-column-options"
          />
        </label>
        <label className="hypothesis-composer-field hypothesis-composer-field--priority">
          <span>Приоритет</span>
          <select value={form.priority} onChange={updateField('priority')}>
            <option value="high">Высокий</option>
            <option value="medium">Средний</option>
            <option value="low">Низкий</option>
          </select>
        </label>
      </div>

      {datasetColumns.length > 0 && (
        <div className="hypothesis-composer-chips" aria-label="Столбцы датасета">
          {datasetColumns.slice(0, 24).map((name) => (
            <button
              key={name}
              type="button"
              className={`hypothesis-column-tag ${selectedColumns.has(name) ? 'hypothesis-column-tag--active' : ''}`}
              onClick={() => toggleColumn(name)}
            >
              {name}
            </button>
          ))}
        </div>
      )}

      <datalist id="hypothesis-column-options">
        {datasetColumns.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>

      {error && <p className="hypothesis-composer-error">{error}</p>}

      <div className="hypothesis-composer-actions">
        <button type="submit" className="hypothesis-composer-submit" disabled={!canSubmit}>
          {submitting ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}
          {submitting ? 'Добавление…' : 'Добавить в список'}
        </button>
      </div>
    </form>
  )
}

export default function HypothesesView({
  results,
  selectedIds,
  onToggle,
  onSelectAll,
  onSelectNone,
  jobId,
  canAdd = false,
  onAdded,
}) {
  const hypotheses = results?.hypotheses
  const raw = results?.hypotheses_raw
  const datasetColumns = (results?.columns || []).map(String)
  const hasList = Boolean(hypotheses?.length)
  const hasRaw = Boolean(raw?.trim())
  const waiting = !hasList && !hasRaw && !canAdd

  if (waiting) {
    return <div className="text-view">Ожидание…</div>
  }

  const selectedCount = selectedIds?.size ?? 0
  const allSelected = hasList && selectedCount === hypotheses.length

  return (
    <div className="hypotheses-view">
      {canAdd && (
        <AddHypothesisForm
          jobId={jobId}
          datasetColumns={datasetColumns}
          onAdded={onAdded}
        />
      )}

      {hasList ? (
        <>
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
        </>
      ) : hasRaw ? (
        <HypothesesFallback text={raw} />
      ) : (
        <p className="hypotheses-empty muted">
          Пока нет гипотез. Добавьте свою формулировку в поле выше.
        </p>
      )}
    </div>
  )
}

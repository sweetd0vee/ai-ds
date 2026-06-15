const ISSUE_LABELS = {
  high_missing: 'Много пропусков',
  moderate_missing: 'Есть пропуски',
  constant: 'Константа',
  near_unique: 'Почти все уникальны',
  likely_identifier: 'Похоже на ID',
}

const KIND_LABELS = {
  numeric: 'Числовые',
  categorical: 'Категории',
  datetime: 'Даты',
  boolean: 'Булевы',
  identifier: 'Идентификаторы',
  textual: 'Текст',
}

const GRADE_CLASS = { good: 'grade-good', fair: 'grade-fair', poor: 'grade-poor' }

const NOTABLE_STRENGTHS = new Set(['сильная', 'умеренная'])

function StrengthBadge({ strength }) {
  const cls = strength === 'сильная' ? 'strength-strong' : 'strength-moderate'
  return <span className={`strength-badge ${cls}`}>{strength}</span>
}

function CoefficientHelp({ help }) {
  if (!help) return null
  return (
    <div className="coeff-help-grid">
      {Object.entries(help).map(([key, item]) => (
        <div key={key} className="coeff-help-card">
          <h5>{item.name}</h5>
          <p className="coeff-help-range">Диапазон: {item.range}</p>
          <p className="coeff-help-text">{item.meaning}</p>
          <p className="coeff-help-thresholds">{item.thresholds}</p>
        </div>
      ))}
    </div>
  )
}

function CorrelationTable({ title, description, columns, rows, valueKey, valueClass }) {
  if (!rows?.length) return null

  return (
    <div className="insights-block">
      <h4>{title}</h4>
      {description && <p className="insights-desc">{description}</p>}
      <div className="insights-table-wrap">
        <table className="insights-table">
          <thead>
            <tr>
              {columns.map((col) => <th key={col}>{col}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                {row.cells.map((cell, i) => (
                  <td
                    key={i}
                    className={i === valueKey ? valueClass?.(row.raw) : undefined}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function filterNotable(pairs, getStrength) {
  return (pairs || []).filter((p) => NOTABLE_STRENGTHS.has(getStrength(p)))
}

export default function InsightsView({ results }) {
  const quality = results?.quality_report
  const correlations = results?.correlations

  if (!quality) {
    return (
      <pre className="code-view">
        {results?.quality_report_raw || 'Ожидание анализа качества…'}
      </pre>
    )
  }

  const summary = quality.summary || {}
  const gradeClass = GRADE_CLASS[summary.overall_grade] || 'grade-fair'
  const kinds = summary.column_kinds || {}

  const numericRows = filterNotable(correlations?.numeric_pairs, (p) => p.strength).map((p) => ({
    key: `${p.col_a}-${p.col_b}`,
    raw: p,
    cells: [
      p.col_a,
      p.col_b,
      p.pearson,
      p.direction,
      <StrengthBadge key="s" strength={p.strength} />,
    ],
  }))

  const categoricalRows = filterNotable(correlations?.categorical_pairs, (p) => p.strength).map((p) => ({
    key: `${p.col_a}-${p.col_b}`,
    raw: p,
    cells: [p.col_a, p.col_b, p.cramers_v, <StrengthBadge key="s" strength={p.strength} />],
  }))

  const mixedRows = filterNotable(correlations?.categorical_numeric, (p) => p.strength).map((p) => ({
    key: `${p.categorical}-${p.numeric}`,
    raw: p,
    cells: [p.categorical, p.numeric, p.eta, <StrengthBadge key="s" strength={p.strength} />],
  }))

  const hasCorrelations = numericRows.length || categoricalRows.length || mixedRows.length
  const flaggedColumns = quality.columns?.filter((c) => c.issues?.length) || []
  const topMissing = summary.top_missing_columns || []

  return (
    <div className="insights-view">
      <div className={`quality-score-card ${gradeClass}`}>
        <div className="quality-score-value">{summary.overall_score ?? '—'}</div>
        <div className="quality-score-meta">
          <span className="quality-score-label">Оценка качества данных</span>
          <span className="quality-score-grade">{summary.overall_grade_label || '—'}</span>
          <p className="quality-score-hint">
            Учитываются пропуски, дубликаты, константы и столбцы-ID.
            Чем выше — тем надёжнее выводы анализа.
          </p>
        </div>
      </div>

      <div className="insights-stats">
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.rows ?? 0}</span>
          <span className="insight-stat-label">строк</span>
        </div>
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.columns ?? 0}</span>
          <span className="insight-stat-label">столбцов</span>
        </div>
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.fill_rate_pct ?? 0}%</span>
          <span className="insight-stat-label">заполненность ячеек</span>
        </div>
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.complete_rows_pct ?? 0}%</span>
          <span className="insight-stat-label">строк без пропусков</span>
        </div>
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.duplicate_pct ?? 0}%</span>
          <span className="insight-stat-label">дубликатов строк</span>
        </div>
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.usable_columns ?? 0}</span>
          <span className="insight-stat-label">столбцов для анализа</span>
        </div>
      </div>

      {Object.keys(kinds).length > 0 && (
        <div className="insights-block">
          <h4>Состав данных</h4>
          <div className="kind-chips">
            {Object.entries(kinds).map(([kind, count]) => (
              <span key={kind} className="kind-chip">
                {KIND_LABELS[kind] || kind}: <strong>{count}</strong>
              </span>
            ))}
          </div>
          <p className="insights-desc">
            Идентификаторов: {summary.identifier_columns ?? 0}, констант: {summary.constant_columns ?? 0},
            {' '}столбцов с &gt;50% пропусков: {summary.columns_with_high_missing ?? 0},
            {' '}с умеренными пропусками (10–50%): {summary.moderate_missing_columns ?? 0}.
          </p>
        </div>
      )}

      {topMissing.length > 0 && (
        <div className="insights-block">
          <h4>Где больше всего пропусков</h4>
          <div className="insights-table-wrap">
            <table className="insights-table">
              <thead>
                <tr>
                  <th>Столбец</th>
                  <th>Тип</th>
                  <th>Пропуски</th>
                </tr>
              </thead>
              <tbody>
                {topMissing.map((col) => (
                  <tr key={col.name}>
                    <td>{col.name}</td>
                    <td>{KIND_LABELS[col.kind] || col.kind}</td>
                    <td>{col.missing_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {flaggedColumns.length > 0 ? (
        <div className="insights-block">
          <h4>Замечания по столбцам</h4>
          <div className="insights-table-wrap">
            <table className="insights-table">
              <thead>
                <tr>
                  <th>Столбец</th>
                  <th>Тип</th>
                  <th>Пропуски</th>
                  <th>Уникальных</th>
                  <th>Замечания</th>
                </tr>
              </thead>
              <tbody>
                {flaggedColumns.map((col) => (
                  <tr key={col.name}>
                    <td>{col.name}</td>
                    <td>{KIND_LABELS[col.kind] || col.kind}</td>
                    <td>{col.missing_pct}%</td>
                    <td>{col.nunique}</td>
                    <td>
                      <div className="issue-tags">
                        {col.issues.map((issue) => (
                          <span key={issue} className="issue-tag">
                            {ISSUE_LABELS[issue] || issue}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <p className="insights-ok">Критичных проблем с качеством не обнаружено.</p>
      )}

      <div className="insights-block">
        <h4>Связи между столбцами</h4>
        <p className="insights-desc">
          {correlations?.filter_note || 'Показаны только сильные и умеренные связи.'}
          {' '}Слабые корреляции скрыты, чтобы не перегружать отчёт шумом.
        </p>
        <CoefficientHelp help={correlations?.help} />
      </div>

      <CorrelationTable
        title="Числовые корреляции (Pearson r)"
        description="Линейная связь между двумя числовыми признаками."
        columns={['Столбец A', 'Столбец B', 'r', 'Направление', 'Сила']}
        rows={numericRows}
        valueKey={2}
        valueClass={(p) => (p.pearson > 0 ? 'corr-pos' : 'corr-neg')}
      />

      <CorrelationTable
        title="Категориальные связи (Cramér's V)"
        description="Насколько тесно связаны два категориальных столбца."
        columns={['Столбец A', 'Столбец B', 'V', 'Сила']}
        rows={categoricalRows}
      />

      <CorrelationTable
        title="Категория → число (η)"
        description="Влияет ли категория на уровень числового показателя."
        columns={['Категория', 'Число', 'η', 'Сила']}
        rows={mixedRows}
      />

      {!hasCorrelations && (
        <p className="insights-muted">
          Сильных и умеренных связей между столбцами не найдено.
          Это нормально для малых или слабо связанных данных.
        </p>
      )}
    </div>
  )
}

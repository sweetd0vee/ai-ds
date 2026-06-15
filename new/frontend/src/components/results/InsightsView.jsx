const ISSUE_LABELS = {
  high_missing: 'Много пропусков',
  moderate_missing: 'Есть пропуски',
  constant: 'Константа',
  near_unique: 'Почти все уникальны',
  likely_identifier: 'Похоже на ID',
}

const GRADE_CLASS = { good: 'grade-good', fair: 'grade-fair', poor: 'grade-poor' }

function CorrelationTable({ title, columns, rows, valueKey, valueClass }) {
  if (!rows?.length) return null

  return (
    <div className="insights-block">
      <h4>{title}</h4>
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

  const numericRows = correlations?.numeric_pairs?.map((p) => ({
    key: `${p.col_a}-${p.col_b}`,
    raw: p,
    cells: [p.col_a, p.col_b, p.pearson, p.strength],
  }))

  const categoricalRows = correlations?.categorical_pairs?.map((p) => ({
    key: `${p.col_a}-${p.col_b}`,
    raw: p,
    cells: [p.col_a, p.col_b, p.cramers_v, p.strength],
  }))

  const mixedRows = correlations?.categorical_numeric?.map((p) => ({
    key: `${p.categorical}-${p.numeric}`,
    raw: p,
    cells: [p.categorical, p.numeric, p.eta, p.strength],
  }))

  const hasCorrelations = numericRows?.length || categoricalRows?.length || mixedRows?.length

  return (
    <div className="insights-view">
      <div className={`quality-score-card ${gradeClass}`}>
        <div className="quality-score-value">{summary.overall_score ?? '—'}</div>
        <div className="quality-score-meta">
          <span className="quality-score-label">Оценка качества</span>
          <span className="quality-score-grade">{summary.overall_grade_label || '—'}</span>
        </div>
      </div>

      <div className="insights-stats">
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.rows ?? 0}</span>
          <span className="insight-stat-label">строк</span>
        </div>
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.duplicate_pct ?? 0}%</span>
          <span className="insight-stat-label">дубликатов</span>
        </div>
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.avg_missing_pct ?? 0}%</span>
          <span className="insight-stat-label">пропусков в среднем</span>
        </div>
        <div className="insight-stat">
          <span className="insight-stat-value">{summary.columns_with_high_missing ?? 0}</span>
          <span className="insight-stat-label">столбцов с &gt;50% пропусков</span>
        </div>
      </div>

      {quality.columns?.some((c) => c.issues?.length) ? (
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
                {quality.columns
                  .filter((c) => c.issues?.length)
                  .map((col) => (
                    <tr key={col.name}>
                      <td>{col.name}</td>
                      <td>{col.kind}</td>
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

      <CorrelationTable
        title="Числовые корреляции (Pearson)"
        columns={['Столбец A', 'Столбец B', 'r', 'Сила']}
        rows={numericRows}
        valueKey={2}
        valueClass={(p) => (p.pearson > 0 ? 'corr-pos' : 'corr-neg')}
      />

      <CorrelationTable
        title="Категориальные связи (Cramér&apos;s V)"
        columns={['Столбец A', 'Столбец B', 'V', 'Сила']}
        rows={categoricalRows}
      />

      <CorrelationTable
        title="Категория → число (η)"
        columns={['Категория', 'Число', 'η', 'Сила']}
        rows={mixedRows}
      />

      {!hasCorrelations && (
        <p className="insights-muted">Связи между столбцами не обнаружены или данных недостаточно.</p>
      )}
    </div>
  )
}

const CARDINALITY_HINT = {
  '1:1': 'Каждой записи слева соответствует не больше одной справа',
  '1:N': 'Одна запись слева связана с несколькими справа',
  'N:1': 'Несколько записей слева ссылаются на одну справа',
  'N:M': 'Множественная связь, ключ не уникален ни с одной стороны',
  union: 'Одинаковые столбцы — таблицы можно склеить по строкам',
}

function scorePct(score) {
  if (score == null) return '—'
  return `${Math.round(Number(score) * 100)}%`
}

function JoinPlan({ plan, tablesById }) {
  if (!plan || plan.mode === 'single') return null

  const modeLabel = {
    join: 'Объединение по ключам (left join)',
    union: 'Склейка строк (одинаковая схема)',
    largest: 'Анализ самой большой таблицы',
  }[plan.mode] || plan.mode

  return (
    <div className="insights-block">
      <h4>Как собрана таблица для анализа</h4>
      <p className="insights-desc">
        {modeLabel}. Основа: <strong>{tablesById[plan.primary] || plan.primary}</strong>
        {plan.rows_after != null && (
          <> · итог {plan.rows_after} строк × {plan.cols_after} столбцов</>
        )}
      </p>
      {(plan.steps || []).length > 0 && (
        <ol className="relation-steps">
          {plan.steps.map((step, i) => (
            <li key={i}>
              {step.action === 'join' ? (
                <>
                  JOIN <strong>{step.from}</strong>.{step.left_column} → <strong>{step.to}</strong>.{step.right_column}
                  {step.match_pct != null && (
                    <> · совпало {step.matched_rows}/{step.left_rows} ({step.match_pct}%)</>
                  )}
                </>
              ) : (
                <>UNION <strong>{step.table}</strong>: {step.rows} строк</>
              )}
            </li>
          ))}
        </ol>
      )}
      {(plan.unmatched || []).length > 0 && (
        <p className="insights-muted">
          Не вошли в объединение: {plan.unmatched.map((id) => tablesById[id] || id).join(', ')}
        </p>
      )}
      {plan.note && <p className="insights-muted">{plan.note}</p>}
    </div>
  )
}

export default function RelationsView({ results }) {
  const relations = results?.relations
  const tables = results?.tables || []
  const links = relations?.links || []
  const plan = results?.join_plan
  const tablesById = Object.fromEntries(tables.map((t) => [t.id, t.name]))

  if (!relations && tables.length < 2) {
    return (
      <p className="insights-muted">
        Загрузите несколько таблиц, чтобы найти ключи и связи между ними.
      </p>
    )
  }

  return (
    <div className="relations-view">
      <div className="relation-summary">
        <p>{relations?.summary || 'Связи между таблицами'}</p>
      </div>

      {tables.length > 0 && (
        <div className="relation-nodes">
          {tables.map((table) => (
            <article key={table.id} className="relation-node">
              <strong title={table.name}>{table.name}</strong>
              <span>{table.rows} строк × {table.cols} столбцов</span>
            </article>
          ))}
        </div>
      )}

      <JoinPlan plan={plan} tablesById={tablesById} />

      {links.length === 0 ? (
        <p className="insights-muted">
          Общих ключей не найдено: нет пересечения значений и нет похожих имён столбцов.
        </p>
      ) : (
        <div className="insights-block">
          <h4>Найденные связи</h4>
          <div className="relation-cards">
            {links.map((link, i) => (
              <article key={`${link.left_table}-${link.right_table}-${i}`} className="relation-card">
                <div className="relation-card-head">
                  <span className={`relation-kind relation-kind--${link.kind}`}>
                    {link.kind === 'union' ? 'схема' : 'ключ'}
                  </span>
                  <span className="relation-score">уверенность {scorePct(link.score)}</span>
                </div>
                {link.kind === 'union' ? (
                  <h5>
                    {tablesById[link.left_table] || link.left_table}
                    {' ≈ '}
                    {tablesById[link.right_table] || link.right_table}
                  </h5>
                ) : (
                  <h5>
                    {tablesById[link.left_table] || link.left_table}.{link.left_column}
                    {' ↔ '}
                    {tablesById[link.right_table] || link.right_table}.{link.right_column}
                  </h5>
                )}
                <p className="insights-desc">{link.reason}</p>
                <div className="relation-meta">
                  {link.cardinality_label && (
                    <span title={CARDINALITY_HINT[link.cardinality] || ''}>
                      {link.cardinality_label}
                    </span>
                  )}
                  {link.matched_values != null && link.kind === 'join' && (
                    <span>пересечение {link.matched_values}</span>
                  )}
                  {link.coverage_left != null && link.kind === 'join' && (
                    <span>покрытие {link.coverage_left}% / {link.coverage_right}%</span>
                  )}
                </div>
                {(link.examples || []).length > 0 && (
                  <p className="relation-examples">
                    Примеры: {(link.examples || []).slice(0, 6).join(', ')}
                  </p>
                )}
              </article>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

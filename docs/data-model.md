# Модель данных

## Объект Job

Память + `job_state.json` + SSE/REST.

### Ответ API (`JobStatusResponse`)

```typescript
interface JobStatusResponse {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'unknown'
  step: string
  progress: number
  message: string
  error: string | null
  filename: string
  filenames?: string[]
  graph_count: number
  analyst_model: string
  results: Results | null
}
```

На диске у Job ещё есть `file_paths`, `analysis_path`, timestamps — в HTTP-снимок они не входят.

---

## Объект `results`

Ключи появляются постепенно. При нескольких таблицах детализация часто лежит в `tables[i]`, а корневые поля дублируют **первую** таблицу или склеенный текст.

| Ключ | Этап | Смысл |
|------|------|--------|
| `preview`, `columns`, `shape` | preparing | Превью первой таблицы |
| `tables` | preparing+ | Мета + позже structure/quality/discovery/plots на таблицу |
| `table_count` | preparing | Число таблиц |
| `relations`, `relations_raw` | preparing | Join/union-кандидаты, без merge |
| `graph_count` | preparing | Запрошенный лимит PNG |
| `data_structure`, `data_structure_raw` | structure | Типы столбцов (одна таблица) |
| `quality_report`, `quality_report_raw` | insights | Балл качества |
| `correlations`, `correlations_raw` | insights | Пары связей |
| `insights_report_raw` | insights+discovery | Текст для вкладки «Инсайты» |
| `discovery`, `discovery_brief`, `discovery_raw` | discovery | Аномалии, роли, highlights |
| `hypotheses` | discovery | Python-гипотезы (+ связи таблиц) |
| `metrics_plan_raw`, `metrics_plan_dict` | metrics | План `{column: [metric]}` |
| `calculation_code` | metrics | Псевдокод вкладки «Код» |
| `metrics_results_raw` | metrics | Текст расчёта |
| `analysis_summary` | metrics_analysis | Комментарий LLM или Python-бриф |
| `hypotheses_raw` | analysis | Сейчас обычно пусто (LLM гипотез нет) |
| `hypotheses_python` | analysis | Копия python-списка |
| `viz_code`, `viz_output` | viz | Описание и лог графиков |
| `plot_files`, `plot_details` | viz | Имена PNG и метаданные |
| `final_report` | final_report | Итоговый текст |

---

## `data_structure`

```json
{
  "columns": [
    {
      "name": "price",
      "type": "float64",
      "kind": "numeric",
      "description": "1500 значений, 42 уникальных"
    }
  ],
  "datetime_candidates": ["created_at"]
}
```

`kind`: `numeric` | `categorical` | `datetime` | `boolean` | `identifier` | `textual`

---

## `quality_report`

```json
{
  "summary": {
    "overall_score": 78,
    "overall_grade": "good",
    "overall_grade_label": "Хорошее",
    "rows": 10000,
    "duplicate_pct": 0.5,
    "avg_missing_pct": 3.2,
    "columns_with_high_missing": 1
  },
  "columns": [
    {
      "name": "age",
      "kind": "numeric",
      "missing_pct": 12.5,
      "nunique": 87,
      "issues": ["moderate_missing"]
    }
  ]
}
```

Коды `issues`: `high_missing` (>50%), `moderate_missing` (10–50%), `constant`, `near_unique`, `likely_identifier`.

---

## `correlations`

Три списка: `numeric_pairs` (pearson), `categorical_pairs` (cramers_v), `categorical_numeric` (eta). У пары есть `strength` (текст силы).

---

## `discovery` (сжато)

Ключи: `roles`, `derived`, `highlights`, `concentration`, `outliers`, `implausible`, `label_duplicates`, `group_profiles`, `tests`, `hypotheses`, `kind_labels`.

Роли столбцов: `geo`, `money`, `currency`, `area`, `numeric`, `categorical`, `datetime`, `identifier`.

---

## Элемент `hypotheses[]`

```json
{
  "id": 1,
  "kind": "numeric_outlier",
  "kind_label": "Выбросы",
  "title": "Выбросы в «price»",
  "statement": "если … то …",
  "rationale": "цифры из расчёта",
  "columns": ["price"],
  "verification": "как проверить",
  "priority": "high",
  "priority_label": "высокий",
  "source": "python"
}
```

`kind`: `geo_outlier`, `numeric_outlier`, `rare_category`, `group_difference`, `quality`, `concentration`, `correlation`, `derived`, `implausible`, `table_relation`.  
`source`: `python` | `auditor` (ручная) | исторически `llm`.

---

## `tables[]` (элемент)

id, name, filename, sheet, rows, cols, columns, preview; после анализа — `structure`, `quality_report`, `discovery`, `metrics_plan_dict`, `plot_files`, `plot_details`, текстовые `*_raw`.

---

## Файлы задачи

```
data/jobs/{job_id}/
├── job_state.json
├── analysis_df.pkl
├── inputs/
│   └── 00_orders.csv
└── output/
    ├── relations.txt
    ├── data_structure.xlsx
    ├── quality_report.txt
    ├── correlations.txt
    ├── quality_insights.xlsx
    ├── discovery_insights.txt
    ├── generated_calculation_code.py
    ├── generated_visualization_code.py
    ├── analysis_summary_report.txt / .docx
    ├── hypotheses_report.docx / .xlsx
    ├── final_report.txt / .docx
    ├── plots_report.docx
    └── plot_001.png …
```

---

## Настройки клиента

Ключ localStorage: `ds-app-settings`

```json
{ "theme": "light", "analystModel": "qwen3.8:27b" }
```

На сервер не синхронизируется. Модель применяется к **следующему** запуску.

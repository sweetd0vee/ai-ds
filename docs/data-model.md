# Модель данных

## Объект Job

Хранится в памяти, на диске (`job_state.json`) и передаётся в SSE/REST.

### Ответ API (`JobStatusResponse`)

```typescript
interface JobStatusResponse {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'unknown'
  step: string           // ID этапа пайплайна
  progress: number       // 0–100
  message: string        // Сообщение для UI
  error: string | null
  filename: string
  filenames?: string[]
  graph_count: number
  analyst_model: string
  results: Results | null
}
```

---

## Объект `results`

Накапливается по мере прохождения пайплайна. Ключи появляются не все сразу.

### Таблица полей

| Ключ | Тип | Этап появления | Описание |
|------|-----|----------------|----------|
| `preview` | `list[dict]` | preparing | Первые 20 строк анализируемой таблицы |
| `columns` | `list[str]` | preparing | Имена столбцов |
| `shape` | `[int, int]` | preparing | [строки, столбцы] |
| `tables` | `list[object]` | preparing | Исходные таблицы: id, name, preview, structure |
| `table_count` | `int` | preparing | Число загруженных таблиц |
| `relations` | `object` | preparing | Найденные join/union связи |
| `join_plan` | `object` | preparing | Как собрана таблица для анализа |
| `relations_raw` | `str` | preparing | Текст отчёта о связях |
| `graph_count` | `int` | preparing | Запрошенное число графиков |
| `data_structure_raw` | `str` | structure | Текстовое описание структуры |
| `data_structure` | `object` | structure | JSON структуры |
| `parsed_data_structure` | `object` | structure | Дубликат `data_structure` |
| `quality_report` | `object` | data_insights | Структурированный отчёт качества |
| `quality_report_raw` | `str` | data_insights | Текст + JSON |
| `correlations` | `object` | data_insights | Пары и коэффициенты |
| `correlations_raw` | `str` | data_insights | Текст + JSON |
| `insights_report_raw` | `str` | data_insights | Объединённый текст для UI |
| `metrics_plan_raw` | `str` | metrics_plan | Текст плана |
| `metrics_plan_dict` | `dict` | metrics_plan | `{column: [metrics]}` |
| `calculation_code` | `str` | metrics_calculation | Справочный псевдокод |
| `metrics_results_raw` | `str` | metrics_calculation | Результаты расчёта |
| `code_warnings_metrics` | `list` | metrics_calculation | Предупреждения (пусто в Python-first) |
| `analysis_summary` | `str` | metrics_analysis | LLM-интерпретация |
| `hypotheses_raw` | `str` | hypotheses | Сырой ответ LLM |
| `hypotheses` | `list[dict]` | hypotheses | Распарсенные гипотезы |
| `viz_code` | `str` | viz_generation | Описание логики графиков |
| `viz_output` | `str` | viz_generation | Лог построения |
| `code_warnings_viz` | `list` | viz_generation | Предупреждения визуализации |
| `plot_files` | `list[str]` | viz_generation | Имена PNG |
| `plot_details` | `list[dict]` | viz_generation | Метаданные графиков (тип, столбцы, описание) |
| `final_report` | `str` | final_report | Итоговый TXT-отчёт |

---

## `data_structure` (детально)

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

### Значения `kind`

`numeric` | `categorical` | `datetime` | `boolean` | `identifier` | `textual`

---

## `quality_report` (детально)

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

### Коды `issues`

| Код | Смысл |
|-----|-------|
| `high_missing` | >50% пропусков |
| `moderate_missing` | 10–50% пропусков |
| `constant` | Одно значение |
| `near_unique` | Почти все уникальны |
| `likely_identifier` | Похоже на ID |

---

## `correlations` (детально)

```json
{
  "numeric_pairs": [
    {
      "col_a": "price",
      "col_b": "quantity",
      "pearson": 0.72,
      "strength": "сильная"
    }
  ],
  "categorical_pairs": [
    {
      "col_a": "region",
      "col_b": "category",
      "cramers_v": 0.45,
      "strength": "умеренная"
    }
  ],
  "categorical_numeric": [
    {
      "categorical": "region",
      "numeric": "revenue",
      "eta": 0.38,
      "strength": "умеренная"
    }
  ]
}
```

---

## `hypotheses[]` (элемент)

```json
{
  "id": "H1",
  "title": "Сезонность продаж",
  "statement": "Продажи выше в Q4",
  "rationale": "На основе корреляции date-revenue",
  "columns": ["date", "revenue"],
  "verification": "Группировка по кварталам, t-test",
  "priority": "high"
}
```

---

## Файловая структура задачи

```
data/jobs/{job_id}/
├── input.csv              # или input.xlsx
├── job_state.json         # полный Job + results
└── output/
    ├── data_structure.xlsx
    ├── quality_report.txt
    ├── correlations.txt
    ├── quality_insights.xlsx
    ├── generated_calculation_code.py
    ├── generated_visualization_code.py
    ├── analysis_summary_report.txt
    ├── analysis_summary_report.docx
    ├── hypotheses_report.txt
    ├── hypotheses_report.docx
    ├── final_report.txt
    ├── final_report.docx
    ├── plots_report.docx
    └── plot_001.png … plot_NNN.png
```

---

## Настройки клиента (localStorage)

Ключ: `ds-app-settings`

```json
{
  "theme": "light",
  "analystModel": "qwen3:8b"
}
```

Не синхронизируется с сервером. Модель применяется только к **следующему** запуску анализа.

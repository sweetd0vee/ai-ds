# Backend — модули и логика

Путь: `new/backend/app/`

## Точка входа

### `main.py`

- Создаёт `FastAPI(title="Электронный Data Scientist API")`.
- CORS из `settings.cors_origins`.
- Создаёт `JOBS_DIR` при старте.
- Подключает роутер с префиксом `/api`.

### `config.py`

```python
class Settings:
    analyst_model: str = "qwen3:8b"
    coder_model: str = "qwen3-coder:latest"  # не используется
    analyst_models: list[str]  # whitelist для POST /analyze
    cors_origins: list[str]
```

Пути:
- `BASE_DIR` — корень backend
- `DATA_DIR` — `backend/data`
- `JOBS_DIR` — `backend/data/jobs`
- `PREVIEW_ROWS = 20`

---

## Хранение задач (`jobs.py`)

### Dataclass `Job`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | str | UUID |
| `file_path` | str | Путь к input-файлу |
| `output_dir` | str | Папка output |
| `filename` | str | Исходное имя файла |
| `graph_count` | int | Лимит графиков |
| `analyst_model` | str | Модель Ollama |
| `status` | str | pending / running / completed / failed / unknown |
| `step` | str | Текущий этап пайплайна |
| `progress` | int | 0–100 |
| `message` | str | Сообщение для UI |
| `error` | str \| None | Текст ошибки |
| `results` | dict | Накопленные артефакты |

### `JobStore`

| Метод | Назначение |
|-------|------------|
| `create(...)` | Новая задача + запись на диск |
| `get(job_id)` | Из памяти или `_load_from_disk` |
| `update(job_id, step, progress, message, partial={})` | Merge в `results`, SSE notify |
| `complete(job_id, results)` | status=completed, progress=100 |
| `fail(job_id, error, partial)` | status=failed |
| `subscribe` / `unsubscribe` | Очереди SSE-слушателей |

Сериализация: `json.dumps(convert_numpy_types(asdict(job)))`.

---

## Ядро анализа

### `core/data_analysis.py`

| Функция | Описание |
|---------|----------|
| `classify_column(series, name)` | Определяет `kind` столбца |
| `analyze_data_structure(df)` | Полная структура + raw text |
| `build_metrics_plan(df, structure)` | Словарь метрик по столбцам |
| `compute_metrics(df, plan)` | Расчёт значений |
| `format_metrics_results(results)` | Текстовое представление |
| `format_calculation_code_reference(plan)` | Псевдокод для UI |

### `core/data_insights.py`

| Функция | Описание |
|---------|----------|
| `build_quality_report(df, structure)` | Балл, грейд, issues по столбцам |
| `compute_correlations(df, structure)` | Три типа пар столбцов |
| `format_quality_report` / `format_correlations` | Текст + JSON |

### `core/visualization.py`

`generate_visualizations(df, output_dir, max_plots)`:

- Выбирает типы графиков по составу данных.
- Сохраняет `plot_001.png`, `plot_002.png`, …
- Возвращает `(files, code_reference, log)`.

### `core/reports.py`

`build_final_report(...)` — сборка 8 секций итогового TXT из всех артефактов.

### `core/hypotheses.py`

| Функция | Описание |
|---------|----------|
| `parse_hypotheses(raw)` | JSON из ответа LLM |
| `format_hypotheses_text(hypotheses)` | Текст для TXT-экспорта |

---

## LLM (`core/llm.py`, `core/prompts.py`)

### Клиент

```python
get_llm_analyst(model)  # кэш Ollama per model
chain_invoke(prompt, output_key, llm, partial={})  # asyncio.to_thread
```

Параметры Ollama: `temperature=0.4`, `num_predict=1200`, `num_ctx=8192`.

### Активные промпты

| Константа | Назначение |
|-----------|------------|
| `DATA_ANALYZE` | Интерпретация метрик, качества, корреляций |
| `DATA_HYPOTHESES` | JSON-массив гипотез |

### Legacy-промпты (не используются)

`STRUCT_ANALYZE`, `M_PLAN`, `CODE_GEN`, `VIZ_GEN`, `FINAL_REP`.

---

## Экспорт документов

| Модуль | Функция | Формат |
|--------|---------|--------|
| `structure_export.py` | `build_structure_xlsx` | XLSX с цветными типами |
| `analysis_export.py` | `build_analysis_docx` | DOCX анализа (`**bold**`, списки) |
| `hypotheses_export.py` | `build_hypotheses_docx` | DOCX гипотез с приоритетами |
| `report_export.py` | `build_report_docx` | DOCX итогового отчёта по секциям |

---

## Вспомогательные модули

| Модуль | Назначение |
|--------|------------|
| `loaders.py` | `load_dataframe` — CSV/XLSX |
| `preprocess.py` | Даты, fillna (legacy path) |
| `sandbox.py` | `run_sandbox_code` для `/run-code` |
| `utils.py` | `convert_numpy_types`, `extract_python_code`, `static_code_analysis` |

---

## HTTP-слой (`api/routes.py`)

Singleton `job_store = JobStore()`.

Основные обработчики:
- `analyze` — валидация файла, `store.create`, `background_tasks.add_task(run_analysis_pipeline)`
- `stream_job` — async generator SSE
- `download_file` — whitelist имён + on-demand DOCX/XLSX

---

## Зависимости (`requirements.txt`)

Ключевые пакеты: `fastapi`, `uvicorn`, `pandas`, `numpy`, `matplotlib`, `seaborn`, `openpyxl`, `python-docx`, `langchain`, `langchain-community`, `langchain-classic`.

---

## Логирование

`pipeline.py` использует `logger.exception` при падении задачи. Глобальная настройка логов — по умолчанию стандартный уровень uvicorn.

# Backend — модули и логика

Путь: `backend/app/`

Карта «куда править» — [onboarding.md](onboarding.md). Алгоритм шагов — [pipeline.md](pipeline.md).

## Точка входа

### `main.py`

- `FastAPI(title="Электронный Data Scientist API")`
- CORS из `settings.cors_origins`
- создаёт `JOBS_DIR`
- роутер с префиксом `/api`

### `config.py`

```python
class Settings:
    ollama_base_url: str   # OLLAMA_BASE_URL, default http://127.0.0.1:11434
    analyst_model: str     # ANALYST_MODEL, default qwen3.8:27b
    analyst_models: list   # whitelist для POST /analyze
    cors_origins: list     # CORS_ORIGINS (5190, 5173, 8080, …)
```

Пути: `BASE_DIR` → `DATA_DIR` (`backend/data`) → `JOBS_DIR` (`data/jobs`). `PREVIEW_ROWS = 20`.

Dev-сервер: `run_dev.py`, порт `API_PORT` (8021), reload только каталога `app/`.

---

## Хранение задач (`jobs.py`)

### Dataclass `Job`

| Поле | Смысл |
|------|--------|
| `id` | UUID |
| `file_path` / `file_paths` | Первый файл / все сохранённые пути |
| `filenames` | Исходные имена |
| `output_dir` | Папка артефактов |
| `analysis_path` | `analysis_df.pkl` для песочницы |
| `graph_count` | Лимит графиков |
| `analyst_model` | Модель Ollama |
| `status` | pending / running / completed / failed / unknown |
| `step`, `progress`, `message`, `error` | Для UI |
| `results` | Накопленный JSON пайплайна |
| `created_at`, `updated_at` | ISO UTC |

### `JobStore`

| Метод | Назначение |
|-------|------------|
| `create` | Новая задача + запись на диск |
| `get` / `list_all` | Память или `job_state.json` |
| `update` | step/progress/message, merge `results`, SSE |
| `complete` / `fail` | Терминальные статусы |
| `patch_results` | Ручные правки (добавление гипотезы) |
| `delete` / `delete_all` | Удаление папки job |
| `subscribe` / `unsubscribe` | Очереди SSE |

Сериализация: `json.dumps(convert_numpy_types(asdict(job)))`.

---

## Ядро анализа (`core/`)

| Модуль | Роль |
|--------|------|
| `pipeline.py` | `run_analysis_pipeline`: шаги по порядку, fail на исключении |
| `pipeline_steps.py` | `PipelineContext` + `step_*` |
| `pipeline_helpers.py` | `analyze_one_table`, графики всех таблиц, LLM, сохранение файлов |
| `loaders.py` | CSV/XLSX → список таблиц |
| `data_analysis.py` | kind столбца, план и расчёт метрик |
| `data_insights.py` | качество, корреляции |
| `scientific_discovery.py` | роли, выбросы, концентрация, python-гипотезы |
| `relations.py` | join/union **без merge**, гипотезы о связях |
| `visualization.py` | PNG по приоритету столбцов и discovery |
| `plot_insights.py` | метаданные графика (тип, столбцы, текст) |
| `reports.py` | итоговый TXT |
| `hypotheses.py` | нормализация / парсинг / `append_auditor_hypothesis` |
| `preprocess.py` | `pd.to_datetime` по кандидатам |
| `sandbox.py` | `exec` пользовательского кода |
| `utils.py` | numpy→json, AST-проверки кода песочницы |
| `llm.py` | кэш Ollama, `chain_invoke`, `think=False` |
| `prompts.py` | `DATA_ANALYZE` (живой), `DATA_HYPOTHESES` (не вызывается) |

### Экспорт

| Модуль | Файл |
|--------|------|
| `structure_export.py` | `data_structure.xlsx` |
| `quality_export.py` | `quality_insights.xlsx` |
| `analysis_export.py` | DOCX анализа |
| `hypotheses_export.py` | DOCX/XLSX гипотез |
| `report_export.py` | DOCX итогового отчёта |
| `plots_export.py` | DOCX с PNG |

---

## LLM

`get_llm_analyst(model)`: `temperature=0.3`, `num_predict=700`, `num_ctx=4096`, без thinking-токенов Qwen.

Единственный вызов в пайплайне: `run_llm_analysis` → `DATA_ANALYZE`. На вход — бриф инсайтов и связей, не сырые метрики целиком. Ошибка → fallback на Python-текст.

---

## HTTP (`api/routes.py`, `api/artifacts.py`)

Singleton `job_store = JobStore()`.

Кратко:

- `POST /analyze` — файлы на диск, `add_task(run_analysis_pipeline)`
- `GET /jobs`, `GET /jobs/{id}`, SSE stream
- `DELETE /jobs`, `DELETE /jobs/{id}`
- plots, download (whitelist + on-demand сборка в `artifacts.py`)
- `POST .../run-code` — sandbox
- `POST .../hypotheses` — гипотеза аудитора после завершения анализа
- `POST .../hypotheses/export` — выбранные id в xlsx/docx

Полный контракт — [api-reference.md](api-reference.md).

---

## Зависимости

`requirements.txt`: fastapi, uvicorn, pandas, numpy, matplotlib, seaborn, openpyxl, python-docx, langchain, langchain-community, langchain-classic.

Логи: `logging.basicConfig(INFO)` в `main.py`; `logger.exception` при падении пайплайна.

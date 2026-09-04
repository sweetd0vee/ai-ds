# Онбординг: что это за продукт и как в нём работать

Документ для человека, который впервые открыл репозиторий. Здесь — смысл системы, как устроен код, куда смотреть и что менять. Технические детали лежат в соседних файлах; этот текст — карта.

## Что делает продукт

**Электронный Data Scientist** — локальный веб-инструмент. Пользователь загружает CSV/Excel (одну или несколько таблиц), система сама:

1. Читает таблицы и **не объединяет** их.
2. Определяет типы столбцов, качество, корреляции, аномалии.
3. Считает статистики и строит графики на **Python**.
4. Формулирует **гипотезы из расчётов**, а не «из головы» модели.
5. Просит LLM только коротко **прокомментировать** уже посчитанные факты.
6. Собирает отчёт (TXT/DOCX) и отдаёт всё в браузер по мере готовности.

Это не чат с данными и не Jupyter. Это фиксированный конвейер: одни и те же шаги для любого файла.

Рабочая версия — `backend/` и `frontend/` в корне репозитория. `old/` и корневой `DOCUMENTATION.md` — legacy Streamlit, где LLM ещё писала и исполняла Python. Сейчас так **не работает**.

## Как думать о системе

Три сущности:

| Сущность | Где живёт | Зачем |
|----------|-----------|--------|
| **Job** | `backend/app/jobs.py` + диск `data/jobs/{uuid}/` | Одна сессия анализа: статус, прогресс, накопленные `results` |
| **Pipeline** | `core/pipeline.py` → `pipeline_steps.py` | Последовательность шагов, которые наполняют Job |
| **UI** | `frontend/src/` | Загрузка файла, подписка на прогресс, вкладки по ключам `results` |

Фронтенд **не считает** метрики и **не знает** алгоритмов. Он показывает то, что сервер положил в `job.results`, и скачивает файлы из `output/`.

```
Браузер                    FastAPI                      Диск / Ollama
───────                    ───────                      ────────────
файл + «Запустить»
        POST /api/analyze  → создаёт Job
        ← job_id
        GET  .../stream    ← SSE: step, progress, results
                           → pipeline шагает
                           → пишет PNG/DOCX/TXT
                           → один раз зовёт Ollama
вкладки обновляются
```

## Что запускать и где лежит код

Локально (два терминала):

- API: `backend` → `python run_dev.py` → **http://127.0.0.1:8021**
- UI: `frontend` → `npm run dev` → **http://localhost:5190** (проксирует `/api` на 8021)

Пошаговая установка — [getting-started.md](getting-started.md).

```
ai-ds/
├── docs/                          ← вы здесь
├── datasets/                      ← тестовые CSV/XLSX
├── backend/app/
│   ├── main.py                    точка входа FastAPI
│   ├── config.py                  Ollama, CORS, модели
│   ├── jobs.py                    Job + SSE + job_state.json
│   ├── models.py                  Pydantic-схемы API
│   ├── api/routes.py              HTTP
│   ├── api/artifacts.py           скачивание / пересборка файлов
│   └── core/                      вся аналитика
├── frontend/src/
│   ├── App.jsx                    состояние приложения
│   ├── api.js                     fetch + SSE
│   ├── constants.js               шаги степпера и вкладки
│   └── components/                UI
└── old/                           не трогать, если чините текущий продукт
```

## Путь одного анализа по коду

Именно этот путь стоит прочитать сверху вниз, если нужно понять «что происходит».

### 1. Кнопка «Запустить анализ»

`App.jsx` → `onAnalyze` → `startAnalysis()` в `api.js` → `POST /api/analyze`.

В запросе: файлы (`files`), `graph_count` (10/15/20/30), `analyst_model` из настроек.

### 2. Сервер создаёт задачу

`api/routes.py` → `start_analysis`:

- проверяет расширение (`.csv` / `.xlsx`), число файлов (до 10), модель из whitelist;
- `job_store.create(...)` — UUID;
- сохраняет файлы в `data/jobs/{id}/inputs/`;
- в фоне: `background_tasks.add_task(run_analysis_pipeline, job.id, job_store)`.

Ответ клиенту — сразу `{ job_id }`. Анализ ещё идёт.

### 3. UI слушает прогресс

`useJobStream` открывает `GET /api/jobs/{id}/stream` (SSE) и параллельно поллит статус раз в 2 с.

Каждое сообщение — полный снимок Job: `status`, `step`, `progress`, `message`, `results`. Вкладки справа загораются, как только в `results` появляется нужный ключ (`sectionMeta.js`).

### 4. Пайплайн

`core/pipeline.py` — тонкий оркестратор. Логика шагов — `pipeline_steps.py`. Тяжёлый pandas/matplotlib крутится в `asyncio.to_thread`, чтобы не блокировать HTTP.

Порядок вызовов:

```
step_prepare
step_structure
step_insights
step_discovery
step_metrics
step_analysis_and_visualizations   ← графики ∥ LLM
step_final_report
store.complete
```

Полная таблица этапов, входы/выходы и файлы на диске — [pipeline.md](pipeline.md).

### 5. Что видит пользователь

`ResultsPanel.jsx` по `activeSection` рендерит вкладку. Список вкладок — `RESULT_SECTIONS` в `constants.js`. Если таблиц несколько, внутри вкладки есть `DatasetSwitcher`.

## Python считает, LLM комментирует

Это главное архитектурное правило текущей версии.

| Делает Python | Делает LLM (Ollama) |
|---------------|---------------------|
| Типы столбцов | Короткий текст «Анализ» по уже посчитанным инсайтам |
| Качество, корреляции | — |
| Выбросы, ядро/хвост категорий, гипотезы | — |
| Метрики, графики, итоговый отчёт | — |

Промпт гипотез `DATA_HYPOTHESES` в `prompts.py` **сейчас не вызывается**. Гипотезы собирает `scientific_discovery.py` (+ связи таблиц из `relations.py`). Если Ollama недоступна, пайплайн не падает: в «Анализ» подставляется Python-бриф.

Менять цифры и правила — в Python-модулях. Менять тон комментария — в `prompts.py` (`DATA_ANALYZE`) и `llm.py`.

## Карта: «хочу изменить X»

| Задача | Куда идти |
|--------|-----------|
| Новый шаг пайплайна / другой порядок | `core/pipeline.py`, `pipeline_steps.py`, `constants.js` (`PIPELINE_STEPS`) |
| Тип столбца определяется неправильно | `core/data_analysis.py` (`classify_column`) |
| Другие статистики | `data_analysis.py` (`NUMERIC_METRICS` и `compute_metrics`) |
| Балл качества, корреляции | `core/data_insights.py` |
| Другие гипотезы / аномалии | `core/scientific_discovery.py` |
| Поиск join-ключей между файлами | `core/relations.py` |
| Другие графики | `core/visualization.py` |
| Текст итогового отчёта | `core/reports.py` |
| Текст LLM | `core/prompts.py`, `core/llm.py` |
| Новый HTTP-метод | `api/routes.py`, `models.py`, `frontend/src/api.js` |
| Новая вкладка результатов | `constants.js` → `ResultsPanel.jsx` → компонент в `components/results/` + `sectionMeta.js` |
| Степпер слева не совпадает с бэком | `constants.js` `PIPELINE_STEPS` должен совпадать с `store.update(..., step=...)` |
| Тема, модель по умолчанию | `frontend/src/settings.js`, `backend/app/config.py` |
| Порт API / UI | `run_dev.py` (`API_PORT`), `vite.config.js` (`VITE_DEV_PORT`, `VITE_API_PORT`) |
| Песочница «выполнить код» | `core/sandbox.py`, `POST /jobs/{id}/run-code` |

## Как устроена аналитика одной таблицы

На шаге структуры для **каждой** таблицы вызывается `structure_and_analyze` (`pipeline_helpers.py`):

1. `analyze_data_structure(df)` — kind каждого столбца.
2. Даты приводятся к datetime.
3. `build_quality_report` + `compute_correlations`.
4. `discover_insights` — роли столбцов (geo/money/…), выбросы, концентрация, подозрительные значения, профили групп, гипотезы.
5. `build_metrics_plan` + `compute_metrics`.

Дальше пайплайн только **склеивает** тексты таблиц, рисует графики, зовёт LLM и собирает отчёт. Повторять pandas-логику в `pipeline_steps.py` не нужно — она уже внутри `analyze_one_table`.

Несколько таблиц:

- Excel: каждый лист = отдельная таблица.
- Несколько файлов = несколько таблиц.
- `detect_relations` ищет ключи join/union **для отчёта**, join не выполняется.
- Бюджет графиков делится между таблицами (`split_graph_count`).

## Состояние Job и файлы на диске

Пока пайплайн идёт, `store.update(..., partial=ctx.state)` мержит ключи в `job.results` и пушит SSE.

На диске:

```
backend/data/jobs/{job_id}/
├── job_state.json          полный Job (переживает рестарт сервера)
├── analysis_df.pkl         обработанные DataFrame (для песочницы)
├── inputs/                 исходные файлы
└── output/                 PNG, DOCX, XLSX, TXT
```

После рестарта uvicorn задачи поднимаются из `job_state.json`. История в UI — `GET /api/jobs`.

Контракт полей `results` — [data-model.md](data-model.md).

## Frontend: что за что отвечает

| Файл | Роль |
|------|------|
| `App.jsx` | Файлы, запуск, история, hero vs режим анализа |
| `hooks/useJobStream.js` | SSE + fallback-поллинг |
| `hooks/useSettings.js` | Тема и модель в localStorage |
| `hooks/useActiveTable.js` | Какая таблица выбрана на вкладке |
| `ProgressPanel.jsx` | Левая колонка: прогресс, степпер |
| `results/ResultsPanel.jsx` | Правая колонка: нав + тело вкладки |
| `results/sectionMeta.js` | Есть ли данные на вкладке, текст для «Копировать» |

Стили разнесены: `App.css` + `styles/*.css`. Темы — CSS-переменные (`index.css`, `data-theme`).

## Типичный рабочий цикл разработчика

1. Запустить Ollama (`ollama serve`, модель из настроек должна быть в `ollama list`).
2. Поднять backend и frontend.
3. Прогнать маленький файл из `datasets/`.
4. Смотреть:
   - степпер и вкладки в UI;
   - логи uvicorn;
   - `data/jobs/<последний-uuid>/output/` и `job_state.json`.
5. OpenAPI: http://127.0.0.1:8021/docs

Отладка шага: поставить лог или breakpoint в соответствующей `step_*` в `pipeline_steps.py`. Падение любого шага → `store.fail`, UI показывает ошибку, частичные `results` сохраняются.

Тестов в репозитории почти нет: проверка — ручной прогон и просмотр артефактов.

## Чего не делать

- Не править `old/` и `DOCUMENTATION.md`, ожидая эффект в текущем UI.
- Не добавлять `exec` LLM-кода в основной пайплайн — это сознательно убрали.
- Не джойнить таблицы «для удобства» без явной задачи: продукт анализирует их по отдельности.
- Не класть секреты в репозиторий; Ollama — локальный HTTP без ключа.
- Sandbox `/run-code` — `exec` с ограниченным контекстом. Это локальный инструмент, не публичный SaaS.

## Куда читать дальше

1. [pipeline.md](pipeline.md) — каждый этап: функции, прогресс, артефакты.
2. [architecture.md](architecture.md) — слои, Job, SSE, параллелизм.
3. [api-reference.md](api-reference.md) — все HTTP-методы.
4. [backend.md](backend.md) / [frontend.md](frontend.md) — модули.
5. [data-model.md](data-model.md) — форма JSON в `results`.
6. [getting-started.md](getting-started.md) — установка с нуля.

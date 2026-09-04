# Frontend — UI и клиентская логика

Путь: `frontend/src/`

Dev: порт **5190**, прокси `/api` → `127.0.0.1:8021`.

## Структура

```
src/
├── App.jsx                 состояние приложения, hero/analysis
├── App.css
├── main.jsx
├── index.css               дизайн-токены, темы
├── api.js
├── settings.js             тема + модель, localStorage
├── constants.js            PIPELINE_STEPS, RESULT_SECTIONS
├── hooks/
│   ├── useJobStream.js
│   ├── useSettings.js
│   └── useActiveTable.js
├── components/
│   ├── AppHeader.jsx
│   ├── UploadSection.jsx
│   ├── PipelineStepper.jsx
│   ├── ProgressPanel.jsx
│   ├── StatsCards.jsx
│   ├── ErrorAlert.jsx
│   ├── SettingsModal.jsx
│   ├── HistoryModal.jsx
│   ├── CodeSandbox.jsx
│   └── results/
│       ├── ResultsPanel.jsx
│       ├── ResultsNav.jsx
│       ├── ResultsToolbar.jsx
│       ├── DatasetSwitcher.jsx
│       ├── sectionMeta.js
│       ├── PreviewView.jsx / PreviewTable.jsx
│       ├── StructureView.jsx
│       ├── RelationsView.jsx
│       ├── InsightsView.jsx
│       ├── MetricsPlanView.jsx
│       ├── MetricsResultsView.jsx
│       ├── AnalysisView.jsx
│       ├── HypothesesView.jsx
│       ├── ReportView.jsx
│       ├── PlotsGallery.jsx
│       ├── PlotLightbox.jsx
│       └── …
└── styles/                 layout, results, progress, …
```

---

## Режимы

**Hero** (`!job && !loading`): крупная зона загрузки.

**Анализ** (`job || loading`): слева `ProgressPanel` (загрузка-док, степпер, статистика), справа `ResultsPanel`.

---

## Поток в `App.jsx`

```
файлы → onAnalyze → startAnalysis
                   → jobId
                   → startStream (SSE)
                   → job.results → вкладки
```

Ещё: история (`HistoryModal` → `GET /jobs` → `getJobStatus`), настройки, таймер `elapsed`.

---

## Хуки

**`useJobStream`** — SSE + поллинг 2 с, `loading=false` на completed/failed.

**`useSettings`** — `ds-app-settings` в localStorage; live preview темы.

**`useActiveTable`** — какая таблица выбрана, когда `results.tables.length > 1`.

---

## Вкладки

`RESULT_SECTIONS` в `constants.js`:

| ID | Компонент | Откуда данные |
|----|-----------|----------------|
| `preview` | `PreviewView` | `preview` / `tables` |
| `structure` | `StructureView` | `data_structure` / `tables[].structure` |
| `relations` | `RelationsView` | `relations` |
| `insights` | `InsightsView` | качество + discovery |
| `metrics_plan` | `MetricsPlanView` | `metrics_plan_dict` |
| `calculation_code` | `CodeSandbox` | `calculation_code` + `run-code` |
| `metrics` | `MetricsResultsView` | `metrics_results_raw` |
| `analysis` | `AnalysisView` | `analysis_summary` |
| `hypotheses` | `HypothesesView` | `hypotheses` |
| `viz_code` | `<pre>` | `viz_code` |
| `report` | `ReportView` | `final_report` |
| `plots` | `PlotsGallery` + lightbox | `plot_files` / по таблице |

Точка «есть данные»: `sectionHasData` в `sectionMeta.js`.

Тулбар: копировать, скачать XLSX/DOCX, экспорт выбранных гипотез, zip графиков — `ResultsToolbar.jsx` + `api.js`.

---

## Темы

8 штук в `settings.js` (`light`, `ocean`, `dark`, `dracula`, …). Атрибуты `data-theme` и `data-theme-mode` на документе.

Модель LLM из настроек уходит **только в следующий** `POST /analyze`.

---

## API-клиент

База `/api`. Разбор ошибок FastAPI — `parseApiDetail`. Скачивание — blob, не прямая `<a href>` для DOCX (иначе легко сломать имя файла).

---

## Степпер

`PIPELINE_STEPS` должен совпадать с `store.update(..., step=...)` на бэке. Логика: done / active / error по индексу текущего `job.step`.

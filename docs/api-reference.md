# Справочник API

Базовый URL: `/api`  
Код: `app/api/routes.py`, скачивание — `app/api/artifacts.py`  
OpenAPI: http://127.0.0.1:8021/docs (dev) или :8020 (Docker)

Ошибки FastAPI: `{"detail": "строка"}` или `{"detail": [{"msg": "..."}]}`.  
Идентификатор задачи — UUID v4. JSON, кроме файлов и SSE.

---

## `GET /api/health`

`{"status":"ok"}`

---

## `GET /api/config`

```json
{
  "analyst_models": ["qwen3.8:27b", "qwen3:4b", "..."],
  "default_analyst_model": "qwen3.8:27b"
}
```

---

## `POST /api/analyze`

`multipart/form-data`

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `files` | да* | До 10 файлов `.csv` / `.xlsx` |
| `file` | да* | Один файл (старый клиент) |
| `graph_count` | нет | 10, 15, 20 или 30 (default 20) |
| `analyst_model` | нет | Должна быть в `analyst_models` |

\* Нужен хотя бы один из `files` / `file`.

**200:**

```json
{
  "job_id": "uuid",
  "filename": "orders.csv +1",
  "filenames": ["orders.csv", "customers.csv"],
  "message": "Анализ запущен",
  "graph_count": 20
}
```

**400:** формат, модель, число графиков, больше 10 файлов.

Файлы пишутся в `data/jobs/{id}/inputs/`, стартует `run_analysis_pipeline`. Таблицы **не** объединяются.

---

## `GET /api/jobs`

Список задач с диска (история UI), новые сверху.

**200:** `{ "jobs": [ JobListItem, ... ] }` — id, имена файлов, status, progress, модель, timestamps, rows/cols из `results.shape` если есть.

---

## `DELETE /api/jobs`

Удаляет все папки в `JOBS_DIR`. `{ "deleted": N }`

---

## `DELETE /api/jobs/{job_id}`

Удаляет одну задачу. **404**, если не найдена.

---

## `GET /api/jobs/{job_id}`

Снимок Job. Форма — [data-model.md](data-model.md#ответ-api-jobstatusresponse). **404** если нет.

---

## `GET /api/jobs/{job_id}/stream`

`Content-Type: text/event-stream`

```
data: {"job_id":"...","status":"running","step":"metrics_plan",...}

```

Первое событие — snapshot. Далее — на каждое изменение. Keepalive 30 с. Закрытие на `completed` / `failed`.

---

## `GET /api/jobs/{job_id}/plots/{filename}`

PNG. Имя должно начинаться с `plot_` и заканчиваться `.png` (в т.ч. `orders__plot_001.png`).

---

## `POST /api/jobs/{job_id}/run-code`

```json
{ "code": "print(df.shape)" }
```

```json
{ "success": true, "output": "...", "error": null, "warnings": [] }
```

В `exec`: `df` (из pickle или файла), `pd`, `np`, при нескольких таблицах — словарь кадров. Не для публичного интернета.

---

## `POST /api/jobs/{job_id}/hypotheses`

Добавить гипотезу аудитора. Тело: `statement` обязателен; `title`, `rationale`, `verification`, `columns`, `priority`.

**409**, если анализ ещё `running`/`pending`. Ответ — обновлённый Job.

---

## `POST /api/jobs/{job_id}/hypotheses/export`

```json
{ "ids": [1, 2, 3], "format": "xlsx" }
```

`format`: `xlsx` | `docx`. Нужен непустой `ids`, если список гипотез не пустой. Файл пишется в `output/` и отдаётся как download.

---

## `GET /api/jobs/{job_id}/download/{filename}`

Whitelist в `ALLOWED_DOWNLOADS` (`artifacts.py`):

| Файл | Содержание |
|------|------------|
| `final_report.txt` / `.docx` | Итоговый отчёт |
| `analysis_summary_report.txt` / `.docx` | Текст анализа |
| `hypotheses_report.docx` / `.xlsx` | Гипотезы |
| `quality_report.txt`, `correlations.txt` | Качество / связи столбцов |
| `quality_insights.xlsx` | Качество |
| `data_structure.xlsx` | Типы столбцов |
| `relations.txt` | Связи таблиц |
| `plots_report.docx` | Графики + подписи |
| `generated_calculation_code.py` | Псевдокод метрик |
| `generated_visualization_code.py` | Описание графиков |

Если DOCX/XLSX нет (старый job), сервер пересобирает из `results`.

---

## Пример curl

```bash
curl -X POST http://127.0.0.1:8021/api/analyze \
  -F "files=@data.csv" \
  -F "graph_count=20" \
  -F "analyst_model=qwen3.8:27b"

curl http://127.0.0.1:8021/api/jobs/{job_id}
curl -O http://127.0.0.1:8021/api/jobs/{job_id}/download/final_report.docx
```

# Справочник API

Базовый URL: `/api`  
Префикс роутера: `app/api/routes.py`  
Интерактивная документация: http://localhost:8000/docs

## Общие соглашения

- Формат ошибок FastAPI: `{"detail": "строка"}` или `{"detail": [{"msg": "..."}]}`.
- Все ответы JSON, кроме файлов и SSE.
- Идентификатор задачи — UUID v4.

---

## `GET /api/health`

Проверка доступности сервера.

**Ответ 200:**
```json
{ "status": "ok" }
```

---

## `GET /api/config`

Список моделей для настроек UI.

**Ответ 200:**
```json
{
  "analyst_models": ["qwen3:8b", "qwen3:4b", "..."],
  "default_analyst_model": "qwen3:8b"
}
```

---

## `POST /api/analyze`

Запуск нового анализа.

**Content-Type:** `multipart/form-data`

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `file` | file | да | `.csv` или `.xlsx` |
| `graph_count` | int | нет | `10`, `15`, `20` или `30` (default: 20) |
| `analyst_model` | string | нет | Должна быть в `analyst_models` |

**Ответ 200:**
```json
{
  "job_id": "uuid",
  "filename": "data.csv",
  "message": "Анализ запущен",
  "graph_count": 20
}
```

**Ошибки:** 400 — неверный формат/модель/количество графиков.

**Побочные эффекты:**
- Создаётся `data/jobs/{job_id}/input.{ext}`
- Запускается `run_analysis_pipeline` в фоне

---

## `GET /api/jobs/{job_id}`

Текущее состояние задачи (REST, без стриминга).

**Ответ 200:** см. [Модель Job](data-model.md#ответ-api-jobstatusresponse)

**Ошибки:** 404 — задача не найдена.

---

## `GET /api/jobs/{job_id}/stream`

Server-Sent Events — поток обновлений задачи.

**Headers ответа:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`

**Формат события:**
```
data: {"job_id":"...","status":"running","step":"metrics_plan",...}

```

**Поведение:**
1. Первое событие — текущий snapshot.
2. Далее — при каждом изменении задачи.
3. Keepalive каждые 30 с: `: keepalive\n\n`
4. Поток закрывается при `completed` или `failed`.

**Использование во frontend:** `EventSource('/api/jobs/{id}/stream')`.

---

## `GET /api/jobs/{job_id}/plots/{filename}`

Отдача PNG-графика.

**Ограничения:** `filename` должен соответствовать `plot_*.png`.

**Ответ:** `image/png` (FileResponse).

---

## `POST /api/jobs/{job_id}/run-code`

Песочница: выполнение пользовательского Python на датасете задачи.

**Тело запроса:**
```json
{ "code": "print(df.shape)" }
```

**Ответ 200:**
```json
{
  "success": true,
  "output": "stdout текст",
  "error": null,
  "warnings": ["предупреждения static_code_analysis"]
}
```

**Контекст `exec`:**
- `df` — препроцессированный DataFrame
- `pd`, `np`
- `metrics_plan`, `compute_metrics`, `format_metrics_results`

---

## `GET /api/jobs/{job_id}/download/{filename}`

Скачивание артефакта анализа.

### Разрешённые файлы

| Файл | Описание |
|------|----------|
| `final_report.txt` / `.docx` | Итоговый отчёт |
| `analysis_summary_report.txt` / `.docx` | LLM-анализ метрик |
| `hypotheses_report.txt` / `.docx` | Гипотезы |
| `quality_report.txt` | Качество данных |
| `correlations.txt` | Корреляции |
| `data_structure.xlsx` | Структура столбцов |
| `generated_calculation_code.py` | Справочный код метрик |
| `generated_visualization_code.py` | Описание визуализации |

### Генерация по запросу

Если DOCX/XLSX отсутствует (старые задачи), сервер пересобирает:

- `data_structure.xlsx` ← `build_structure_xlsx`
- `analysis_summary_report.docx` ← `build_analysis_docx`
- `hypotheses_report.docx` ← `build_hypotheses_docx`
- `final_report.docx` ← `build_report_docx`

---

## Пример полного цикла (curl)

```bash
# 1. Запуск
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@data.csv" \
  -F "graph_count=20" \
  -F "analyst_model=qwen3:8b"

# 2. Статус
curl http://localhost:8000/api/jobs/{job_id}

# 3. Скачать отчёт
curl -O http://localhost:8000/api/jobs/{job_id}/download/final_report.docx
```

# Электронный Data Scientist — FastAPI + React

Новая версия проекта: асинхронный бэкенд на **FastAPI** и фронтенд на **React**.

> **Полная документация:** [docs/README.md](../docs/README.md) — архитектура, пайплайн, API, code review.

Актуальный пайплайн — **Python-first** (метрики и графики на Python, LLM только для интерпретации и гипотез). Legacy Streamlit-версия: `ins_temp3.py`, `DOCUMENTATION.md`.

## Структура

```
new/
├── backend/          # FastAPI API + пайплайн анализа
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes.py
│   │   └── core/     # промпты, парсеры, pipeline (из ins_temp3.py)
│   └── requirements.txt
├── frontend/         # React (Vite)
│   ├── src/App.jsx
│   └── package.json
└── README.md
```

## Требования

- Python 3.11+
- Node.js 18+
- **Ollama** запущена локально
- Модели:
  ```bash
  ollama pull qwen3:8b
  ollama pull qwen3-coder
  ```

## Установка

### 1. Backend

```bash
cd "/Users/sweetd0ve/электронный DS/new/backend"

# Можно использовать существующий venv из корня проекта:
source "../../venv/bin/activate"

pip install -r requirements.txt
```

### 2. Frontend

```bash
cd "/Users/sweetd0ve/электронный DS/new/frontend"
npm install
```

## Запуск

Нужны **два терминала**.

### Терминал 1 — Backend (порт 8000)

```bash
cd "/Users/sweetd0ve/электронный DS/new/backend"
source "../../venv/bin/activate"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка: http://localhost:8000/api/health

### Терминал 2 — Frontend (порт 5173)

```bash
cd "/Users/sweetd0ve/электронный DS/new/frontend"
npm run dev
```

Откройте: **http://localhost:5173**

## Как пользоваться

1. Перетащите или выберите файл `.csv` / `.xlsx`
2. Выберите количество графиков (10–30, меньше = быстрее)
3. Нажмите **«Запустить анализ»**
4. Следите за прогрессом в реальном времени (SSE)
5. Результаты появятся во вкладках:
   - Данные, Структура, План метрик
   - Код и результаты метрик
   - Анализ, Код графиков, Отчёт, Графики

## API

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/health` | Проверка сервера |
| POST | `/api/analyze` | Загрузка файла, старт анализа → `{ job_id }` |
| GET | `/api/jobs/{job_id}` | Статус и результаты |
| GET | `/api/jobs/{job_id}/stream` | SSE — обновления в реальном времени |
| GET | `/api/jobs/{job_id}/plots/{filename}` | PNG-график |
| GET | `/api/jobs/{job_id}/download/{filename}` | Скачать отчёт / код |

## Оптимизация скорости

Пайплайн распараллелен:
- **Параллель 1:** сохранение отчёта анализа + генерация кода графиков
- **Параллель 2:** построение графиков + итоговый отчёт (LLM)

По умолчанию 20 графиков (вместо 30) — быстрее на ~30%.

## Пайплайн (как в ins_temp3.py)

1. Анализ структуры данных (LLM `qwen3:8b`)
2. План метрик
3. Генерация кода расчёта (`qwen3-coder`)
4. Выполнение кода в Python REPL
5. Анализ метрик
6. Генерация кода визуализации (30 графиков)
7. Построение графиков
8. Итоговый отчёт (.txt + .docx)

Артефакты сохраняются в `backend/data/jobs/{job_id}/output/`.

## Старая версия (Streamlit)

По-прежнему доступна:

```bash
cd "/Users/sweetd0ve/электронный DS"
source venv/bin/activate
python -m streamlit run ins_temp3.py
```

## Устранение проблем

| Проблема | Решение |
|----------|---------|
| `ModuleNotFoundError: langchain_*` | Активируйте venv и `pip install -r requirements.txt` |
| Ollama connection error | Запустите `ollama serve` |
| CORS ошибки | Backend на :8000, frontend на :5173 (прокси в vite.config.js) |
| Долгий анализ | Нормально — LLM генерирует код и 30 графиков |

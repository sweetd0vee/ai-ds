# Электронный Data Scientist — FastAPI + React

Новая версия проекта: асинхронный бэкенд на **FastAPI** и фронтенд на **React**.

> **Полная документация:** [docs/README.md](../docs/README.md) — архитектура, пайплайн, API, code review.

Актуальный пайплайн — **Python-first** (метрики и графики на Python, LLM только для интерпретации и гипотез). Legacy Streamlit-версия: `old/ins_temp3.py`, `DOCUMENTATION.md`.

## Структура

```
ai-ds/
├── datasets/             # тестовые CSV/XLSX (sample_30x100.csv)
├── docs/                 # полная техническая документация
├── new/                  # актуальная версия (FastAPI + React)
│   ├── backend/          # FastAPI API + пайплайн анализа
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/routes.py
│   │   │   └── core/     # промпты, парсеры, pipeline
│   │   ├── run_dev.py    # запуск dev-сервера (порт 8021)
│   │   ├── docker/       # Dockerfile для API
│   │   └── requirements.txt
│   ├── frontend/         # React (Vite)
│   │   ├── src/App.jsx
│   │   ├── docker/       # Dockerfile, nginx
│   │   └── package.json
│   ├── docker/           # полный стек UI + API
│   └── README.md
├── old/                  # legacy Streamlit (ins_temp2.py, ins_temp3.py)
├── requirements.txt      # зависимости legacy-версии
└── DOCUMENTATION.md
```

## Требования

- Python 3.11+
- Node.js 18+
- **Ollama** — [скачать для Windows](https://ollama.com/download/windows)
- Модели (в PowerShell или cmd):

```powershell
ollama pull qwen3.8:27b
ollama pull qwen3-coder
```

## Установка

Все команды ниже — из корня репозитория (`ai-ds`). Путь к проекту в примерах:

`C:\Users\audit\Work\Arina\2026\ai-ds`

### 1. Backend

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\backend

# Виртуальное окружение (один раз) — нужен Python 3.11+
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> На Windows команда `python` может указывать на 3.9 — используйте `py -3.12`.  
> Если PowerShell блокирует активацию venv: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`  
> В **cmd** вместо Activate.ps1: `venv\Scripts\activate.bat`

Альтернатива — зависимости в `vendor/` (как в `run_dev.py`):

```powershell
py -3.12 -m pip install -r requirements.txt --target .\vendor
```

### 2. Frontend

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\frontend
npm install
```

## Запуск

Нужны **два терминала** (PowerShell или cmd).

### Терминал 1 — Backend (порт 8021)

**Вариант A** — через `run_dev.py` (рекомендуется):

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\backend
.\venv\Scripts\Activate.ps1
python run_dev.py
```

**Вариант B** — напрямую через uvicorn:

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8021
```

Проверка: http://localhost:8021/api/health

### Терминал 2 — Frontend (порт 5190)

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\frontend
npm run dev
```

Откройте: **http://localhost:5190**

Тестовые датасеты: `datasets\` (9 файлов, от 60 до 2000 строк) — см. `datasets\README.md`

## Как пользоваться

1. Перетащите или выберите один или несколько файлов `.csv` / `.xlsx` (листы Excel тоже считаются таблицами)
2. Выберите количество графиков (10–30, меньше = быстрее)
3. Нажмите **«Запустить анализ»**
4. Следите за прогрессом в реальном времени (SSE)
5. Результаты появятся во вкладках:
   - Данные, Структура, **Связи таблиц**, Качество, План метрик
   - Код и результаты метрик
   - Анализ, Гипотезы, Код графиков, Отчёт, Графики

Если загружено несколько таблиц, сервис ищет общие ключи (по именам столбцов и пересечению значений) и показывает их во вкладке **Связи таблиц**. Таблицы не объединяются автоматически.

## API

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/health` | Проверка сервера |
| POST | `/api/analyze` | Загрузка одного или нескольких файлов, старт анализа → `{ job_id }` |
| GET | `/api/jobs/{job_id}` | Статус и результаты |
| GET | `/api/jobs/{job_id}/stream` | SSE — обновления в реальном времени |
| GET | `/api/jobs/{job_id}/plots/{filename}` | PNG-график |
| GET | `/api/jobs/{job_id}/download/{filename}` | Скачать отчёт / код |

## Оптимизация скорости

Пайплайн распараллелен:
- **Параллель 1:** построение графиков + сохранение DOCX анализа и гипотез
- Графики и отчёты качества считаются на Python без LLM

По умолчанию 20 графиков (вместо 30) — быстрее на ~30%.

## Пайплайн (Python-first)

1. Анализ структуры данных (Python)
2. Качество данных и корреляции (Python)
3. План метрик (Python)
4. Расчёт метрик (Python)
5. Интерпретация метрик (LLM `qwen3.8:27b`)
6. Формулирование гипотез (LLM)
7. Построение графиков (Python, до 30 PNG)
8. Итоговый отчёт (Python, .txt + .docx)

Подробности: [docs/pipeline.md](../docs/pipeline.md)

## Docker

Production-стек в контейнерах: UI :8080, API :8020. См. [docs/docker.md](../docs/docker.md) или `new/docker/README.md`.

Артефакты сохраняются в `new\backend\data\jobs\{job_id}\output\`.

## Старая версия (Streamlit)

По-прежнему доступна в папке `old/`:

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run old\ins_temp3.py
```

## Устранение проблем

| Проблема | Решение |
|----------|---------|
| `No matching distribution found for langchain-classic` | venv создан на Python 3.9 — пересоздайте: `py -3.12 -m venv venv` |
| `ModuleNotFoundError: langchain_*` | Активируйте venv и `pip install -r requirements.txt` |
| Ollama connection error / model 404 | Ollama должна быть запущена; на Windows используйте `127.0.0.1`, не `localhost` (уже в настройках). Проверка: `ollama list` |
| `Activate.ps1` заблокирован | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` или используйте cmd + `activate.bat` |
| `Not Found` при загрузке файла | Убедитесь, что backend на :8021, frontend на :5190; перезапустите оба сервера |
| CORS ошибки | Backend на :8021, frontend на :5190 (прокси в vite.config.js) |
| Порт занят | Backend: `set API_PORT=8821 && python run_dev.py`; frontend: `set VITE_DEV_PORT=5280 && npm run dev` |
| Долгий анализ | Нормально — LLM генерирует код и 30 графиков |

# Быстрый старт

## Требования

| Компонент | Версия |
|-----------|--------|
| Python | 3.11+ (рекомендуется 3.12+) |
| Node.js | 18+ |
| Ollama | Установлена и запущена |
| Модель LLM | Минимум `qwen3:8b` |

Путь к проекту в примерах: `C:\Users\audit\Work\Arina\2026\ai-ds`

## Установка Ollama и моделей

```powershell
# Установите Ollama с https://ollama.com/download/windows
ollama serve   # если не запущена как служба

ollama pull qwen3:8b
# Опционально — другие модели из списка настроек backend:
ollama pull qwen3:4b
ollama pull llama3.2
```

## Установка backend

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\backend

py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> На Windows `python` может указывать на 3.9 — используйте `py -3.12`.  
> Если PowerShell блокирует активацию venv: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Альтернатива — зависимости в `vendor/` (как в `run_dev.py`):

```powershell
py -3.12 -m pip install -r requirements.txt --target .\vendor
```

## Установка frontend

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\frontend
npm install
```

## Запуск (два терминала)

### Терминал 1 — API (порт 8010)

**Вариант A** — через `run_dev.py` (рекомендуется):

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\backend
.\venv\Scripts\Activate.ps1
python run_dev.py
```

**Вариант B** — напрямую через uvicorn:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

Проверка:

- Health: http://localhost:8010/api/health → `{"status":"ok"}`
- Swagger: http://localhost:8010/docs

Другой порт: `set API_PORT=8800` и `python run_dev.py`.

### Терминал 2 — UI (порт 5173)

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\frontend
npm run dev
```

Откройте: **http://localhost:5173**

Vite проксирует `/api` на `localhost:8010` (`vite.config.js`).

## Первый анализ

1. На главном экране перетащите файл `.csv` или `.xlsx`.
2. Выберите количество графиков (10 / 15 / 20 / 30).
3. В шестерёнке настроек при необходимости смените LLM-модель.
4. Нажмите **«Запустить анализ»**.
5. Слева — прогресс и степпер, справа — вкладки с результатами.
6. По завершении скачайте DOCX/XLSX с панели инструментов вкладки.

Тестовые датасеты: `datasets\` (9 файлов) — см. `datasets\README.md`.

## Docker (production-стек)

Полный стек в контейнерах — UI на :8080, API на :8020. Подробности: [docker.md](docker.md).

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\docker
.\up.ps1
```

## Production-сборка frontend

```powershell
cd new/frontend
npm run build    # → dist/
npm run preview  # локальный просмотр dist/
```

Для production раздавайте `dist/` через nginx и проксируйте `/api` на backend (см. `new/frontend/docker/nginx.conf`).

## Типичные проблемы

| Симптом | Решение |
|---------|---------|
| «Сервер недоступен» | Запустите backend: `python run_dev.py` на :8010 |
| Ошибка LLM / timeout | `ollama serve`, `ollama list`, наличие выбранной модели |
| Ollama connection error | На Windows используйте `127.0.0.1`, не `localhost` (уже в `config.py`) |
| Пустой анализ | Убедитесь, что в файле есть данные и заголовки столбцов |
| Кодировка CSV | Backend пробует utf-8 → latin1 → cp1251 автоматически |
| Порт занят | Backend — :8010; закройте старый Vite на :5173 |

## Переменные и пути

| Параметр | Значение по умолчанию | Файл / env |
|----------|----------------------|------------|
| `JOBS_DIR` | `backend/data/jobs` | `app/config.py` |
| `PREVIEW_ROWS` | `20` | `app/config.py` |
| `analyst_model` | `qwen3:8b` | `app/config.py` / `ANALYST_MODEL` |
| `ollama_base_url` | `http://127.0.0.1:11434` | `OLLAMA_BASE_URL` |
| CORS origins | `localhost:5173`, `:8080` | `CORS_ORIGINS` |
| Dev API port | `8010` | `API_PORT` в `run_dev.py` |

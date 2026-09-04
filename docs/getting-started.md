# Быстрый старт

## Требования

| Компонент | Версия |
|-----------|--------|
| Python | 3.11+ (лучше 3.12+) |
| Node.js | 18+ |
| Ollama | Установлена и запущена |
| Модель | По умолчанию `qwen3.8:27b` (или другая из whitelist backend) |

Путь в примерах: `C:\Users\audit\Work\Arina\2026\ai-ds`

## Ollama

```powershell
# https://ollama.com/download/windows
ollama serve

ollama pull qwen3.8:27b
```

Список допустимых имён моделей задан в `backend/app/config.py` (`analyst_models`). Имя в UI должно совпадать с `ollama list`.

## Backend

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\backend

py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

На Windows `python` часто указывает на 3.9 — используйте `py -3.12`.  
Если PowerShell блокирует venv: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Альтернатива — пакеты в `vendor/` (так умеет `run_dev.py`):

```powershell
py -3.12 -m pip install -r requirements.txt --target .\vendor
```

## Frontend

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\frontend
npm install
```

## Запуск (два терминала)

### Терминал 1 — API (порт **8021**)

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\backend
.\venv\Scripts\Activate.ps1
python run_dev.py
```

Проверка:

- Health: http://127.0.0.1:8021/api/health → `{"status":"ok"}`
- Swagger: http://127.0.0.1:8021/docs

Другой порт: `$env:API_PORT=8821; python run_dev.py` — тогда у Vite задайте тот же `VITE_API_PORT`.

### Терминал 2 — UI (порт **5190**)

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\frontend
npm run dev
```

Откройте **http://localhost:5190**

Vite проксирует `/api` на `127.0.0.1:8021` (`vite.config.js`). Если порты разъехались, UI получит 404 / «сервер недоступен».

## Первый анализ

1. Перетащите `.csv` или `.xlsx` (можно несколько).
2. Выберите число графиков (10 / 15 / 20 / 30).
3. В шестерёнке при необходимости смените модель.
4. **Запустить анализ**.
5. Слева — прогресс, справа — вкладки.
6. После завершения — скачивание с панели вкладки; прошлые запуски — иконка истории.

Тестовые файлы: `datasets\`.

## Docker

UI :8080, API :8020 — [docker.md](docker.md).

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\docker
.\up.ps1
```

## Сборка frontend

```powershell
cd frontend
npm run build
npm run preview
```

## Типичные проблемы

| Симптом | Что проверить |
|---------|----------------|
| «Сервер недоступен» | `python run_dev.py`, порт 8021 |
| LLM timeout / пустой анализ | `ollama serve`, `ollama list`, имя модели |
| Ollama connection error | `127.0.0.1`, не `localhost` (уже в `config.py`) |
| Кодировка CSV | utf-8 → latin1 → cp1251 |
| Порт занят | `run_dev.py` подскажет; `netstat -ano \| findstr :8021` |
| UI на 5173, API на 8010 | Это старые порты из устаревших заметок. Сейчас 5190 / 8021 |

## Переменные

| Параметр | По умолчанию | Где |
|----------|--------------|-----|
| `JOBS_DIR` | `backend/data/jobs` | `config.py` |
| `PREVIEW_ROWS` | `20` | `config.py` |
| `analyst_model` | `qwen3.8:27b` | `ANALYST_MODEL` / `config.py` |
| `ollama_base_url` | `http://127.0.0.1:11434` | `OLLAMA_BASE_URL` |
| CORS | 5190, 5180, 5173, 8080, … | `CORS_ORIGINS` |
| Dev API | `8021` | `API_PORT` |
| Dev UI | `5190` | `VITE_DEV_PORT` |

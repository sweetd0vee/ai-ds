# Docker — развёртывание

Сборка и запуск **backend (FastAPI)** и **frontend (React + nginx)** в контейнерах.

Подробные README по частям: `docker/README.md`, `backend/docker/README.md`, `frontend/docker/README.md`.

## Требования

- Docker Desktop 4.x+ (Windows/macOS) или Docker Engine + Compose v2 (Linux)
- **Ollama на хосте** — контейнеры обращаются к ней по `host.docker.internal:11434`

```powershell
ollama pull qwen3.8:27b
```

## Быстрый старт (весь стек)

Запустите Docker Desktop и дождитесь статуса *Running*.

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\docker
.\up.ps1
```

Или двойной клик по `up.bat`. Вручную:

```powershell
copy .env.example .env
docker compose build --progress=plain
docker compose up -d
```

Откройте **http://localhost:8080** — UI проксирует `/api` на backend.

Остановка: `docker compose down`

## Порты: Docker vs локальная разработка

Можно запускать оба варианта одновременно:

| | Локально (`run_dev.py` / `npm run dev`) | Docker |
|---|------------------------------------------|--------|
| UI | http://localhost:5173 | http://localhost:8080 |
| API | http://localhost:8010 | http://localhost:8020 |

Внутри контейнера backend слушает **8010**; на хост пробрасывается как **8020** (`API_HOST_PORT`).

## Переменные окружения

Файл `docker/.env` (из `.env.example`):

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `UI_PORT` | `8080` | Порт UI на хосте |
| `API_HOST_PORT` | `8020` | Порт API на хосте |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | URL Ollama на хосте |
| `ANALYST_MODEL` | `qwen3:8b` | Модель анализа |
| `CODER_MODEL` | `qwen3-coder:latest` | Зарезервировано (не используется в Python-first пайплайне) |
| `CORS_ORIGINS` | `http://localhost:8080,...` | Разрешённые origins для API |

## Данные задач

Артефакты анализа (`data/jobs/`) хранятся в Docker volume `backend-jobs` и не теряются при пересоздании контейнера.

## Сборка образов отдельно

### Backend

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\backend
docker build -f docker/Dockerfile -t ai-ds-backend:latest .
```

Только API: `cd docker` → `copy .env.example .env` → `docker compose up -d`  
Проверка: http://localhost:8020/api/health

### Frontend

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\frontend
docker build -f docker/Dockerfile -t ai-ds-frontend:latest .
```

Запуск UI + backend: `cd docker` → `docker compose up -d`

## Linux без Docker Desktop

Если `host.docker.internal` недоступен:

```env
OLLAMA_BASE_URL=http://172.17.0.1:11434
```

В compose-файлах проекта уже добавлено `extra_hosts: host.docker.internal:host-gateway`.

## Устранение проблем

| Симптом | Решение |
|---------|---------|
| Команда зависает | Docker Desktop не запущен |
| `error during connect` | Запустите Docker Desktop |
| Долгая первая сборка | 10–20 мин — нормально (образы Python/Node, pip-пакеты) |
| Порт занят | Измените `UI_PORT` / `API_HOST_PORT` в `.env` |
| LLM timeout | Ollama на хосте: `ollama serve`, проверьте `ollama list` |

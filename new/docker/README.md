# Docker — Электронный Data Scientist

Сборка и запуск **backend (FastAPI)** и **frontend (React + nginx)**.

## Требования

- Docker Desktop 4.x+ (или Docker Engine + Compose v2)
- **Ollama на хосте** — контейнеры ходят в неё по `host.docker.internal:11434`

```powershell
ollama pull qwen3:8b
ollama pull qwen3-coder
```

## Быстрый старт (весь стек)

**Сначала запустите Docker Desktop** и дождитесь статуса *Running*.

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\docker
.\up.ps1
```

Или двойной клик по `up.bat`.

Вручную:

```powershell
copy .env.example .env
docker compose build --progress=plain
docker compose up -d
```

> Если в PowerShell появляется `>>` и команда не выполняется — нажмите **Ctrl+C** и запустите `.\up.ps1`.

Откройте **http://localhost:8080** — UI проксирует `/api` на backend.

Порты **не совпадают** с локальной разработкой — можно запускать оба варианта одновременно:

| | Локально (`npm run dev` / `run_dev.py`) | Docker |
|---|------------------------------------------|--------|
| UI | http://localhost:5173 | http://localhost:8080 |
| API | http://localhost:8010 | http://localhost:8020 |

Остановка:

```powershell
docker compose down
```

## Сборка образов отдельно

### Backend

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\backend
docker build -f docker/Dockerfile -t ai-ds-backend:latest .
```

Запуск только API:

```powershell
cd docker
copy .env.example .env
docker compose up -d
```

API: http://localhost:8020/api/health

### Frontend

Сначала соберите backend-образ (нужен для `depends_on` в compose фронтенда):

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\backend
docker build -f docker/Dockerfile -t ai-ds-backend:latest .
```

Сборка UI:

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\frontend
docker build -f docker/Dockerfile -t ai-ds-frontend:latest .
```

Запуск UI + backend:

```powershell
cd docker
docker compose up -d
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `UI_PORT` | `8080` | Порт UI на хосте |
| `API_HOST_PORT` | `8020` | Порт API на хосте (внутри контейнера — 8010) |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | URL Ollama на хосте |
| `ANALYST_MODEL` | `qwen3:8b` | Модель анализа |
| `CODER_MODEL` | `qwen3-coder:latest` | Модель кода |
| `CORS_ORIGINS` | `http://localhost:8080,...` | Разрешённые origins для API |

## Данные задач

Артефакты анализа (`data/jobs/`) хранятся в Docker volume `backend-jobs` и не теряются при пересоздании контейнера.

## Linux без Docker Desktop

Если `host.docker.internal` недоступен, укажите IP хоста:

```env
OLLAMA_BASE_URL=http://172.17.0.1:11434
```

или добавьте в `docker-compose.yml`:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

(уже включено в наши compose-файлы)

## Устранение проблем

| Симптом | Решение |
|---------|---------|
| Команда зависает, нет вывода | Docker Desktop не запущен — откройте и подождите *Running* |
| В терминале `>>` | Нажмите **Ctrl+C**, запустите `.\up.ps1` |
| `error during connect` | То же — запустите Docker Desktop |
| Долгая сборка | Первый `docker compose build` качает Python/Node образы и pip-пакеты — 10–20 мин нормально |
| Порт занят | Измените `UI_PORT` / `API_HOST_PORT` в `.env` |

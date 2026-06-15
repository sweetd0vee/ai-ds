# Docker — Backend

FastAPI API. На хосте порт **8020** (локальная разработка — **8010**).

## Сборка образа

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\backend
docker build -f docker/Dockerfile -t ai-ds-backend:latest .
```

## Запуск только API

```powershell
cd docker
copy .env.example .env
docker compose build --progress=plain
docker compose up -d
```

Проверка: http://localhost:8020/api/health

Ollama должна работать на хосте (`ollama serve`), модели — `qwen3:8b`, `qwen3-coder`.

Полный стек (UI + API): см. `new/docker/README.md`.

# Docker — Frontend

Production-сборка: `npm run build` → **nginx** (порт 80 в контейнере).

Прокси `/api` → сервис `backend:8010` (имя контейнера в compose).

## Сборка образа

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\frontend
docker build -f docker/Dockerfile -t ai-ds-frontend:latest .
```

## Запуск с backend

```powershell
# сначала образ backend
cd ..\backend
docker build -f docker/Dockerfile -t ai-ds-backend:latest .

cd ..\frontend\docker
docker compose up -d
```

UI: http://localhost:8080

Полный стек удобнее поднимать из `docker/` — см. `docker/README.md`.

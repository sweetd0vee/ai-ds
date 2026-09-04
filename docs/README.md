# Документация «Электронный Data Scientist»

Актуальная версия — `new/`: FastAPI + React, Python-first пайплайн.

## С чего начать

Если вы новый разработчик и не понимаете, что происходит в коде, читайте **по порядку**:

1. [Онбординг](onboarding.md) — смысл продукта, путь клика по файлам, куда что менять
2. [Быстрый старт](getting-started.md) — установка и запуск
3. [Пайплайн](pipeline.md) — полный алгоритм шагов анализа

## Справочники

| Документ | Описание |
|----------|----------|
| [Обзор](overview.md) | Назначение, стек, отличия от legacy |
| [Архитектура](architecture.md) | Слои, Job, SSE, параллелизм |
| [Справочник API](api-reference.md) | HTTP-эндпоинты |
| [Backend](backend.md) | Модули сервера |
| [Frontend](frontend.md) | UI и клиент |
| [Модель данных](data-model.md) | Job, `results`, файлы на диске |
| [Docker](docker.md) | Контейнеры |
| [Code Review](code-review.md) | Риски и долг |

## Версии

| Путь | Статус | Описание |
|------|--------|----------|
| `new/` | **Активная** | FastAPI + React |
| `old/ins_temp3.py` | Legacy | Streamlit + LLM пишет Python (`DOCUMENTATION.md` в корне) |

Документы в этой папке описывают **только `new/`**, если не сказано иное.

## Быстрые ссылки

- Backend: `new/backend/app/`
- Frontend: `new/frontend/src/`
- OpenAPI: http://127.0.0.1:8021/docs
- UI (dev): http://localhost:5190
- UI (Docker): http://localhost:8080

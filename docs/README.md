# Документация «Электронный Data Scientist»

Полная техническая документация актуальной версии проекта (`new/`): FastAPI backend + React frontend.

## Содержание

| Документ | Описание |
|----------|----------|
| [Обзор проекта](overview.md) | Назначение, возможности, стек, отличия от legacy-версии |
| [Быстрый старт](getting-started.md) | Установка, запуск, первый анализ |
| [Docker](docker.md) | Сборка и запуск в контейнерах |
| [Архитектура](architecture.md) | Компоненты системы, потоки данных, хранение задач |
| [Пайплайн анализа](pipeline.md) | Пошаговая логика обработки данных (ядро системы) |
| [Справочник API](api-reference.md) | HTTP-эндпоинты, форматы запросов и ответов |
| [Backend](backend.md) | Модули сервера, алгоритмы, LLM, экспорт |
| [Frontend](frontend.md) | UI, компоненты, темы, взаимодействие с API |
| [Модель данных](data-model.md) | Структура `Job`, `results`, артефакты на диске |
| [Code Review](code-review.md) | Оценка качества кода, риски, рекомендации |
| [Ближайшие доработки](roadmap-presentation.html) | Презентация на 3 слайда (HTML). PPTX: [roadmap-near-term.pptx](roadmap-near-term.pptx) |

## Версии проекта

| Путь | Статус | Описание |
|------|--------|----------|
| `new/` | **Активная** | FastAPI + React, Python-first пайплайн |
| `old/ins_temp3.py` | Legacy | Streamlit + LLM-heavy пайплайн (см. `DOCUMENTATION.md` в корне) |

Документация в этой папке описывает **только `new/`**, если не указано иное.

## Быстрые ссылки

- Backend: `new/backend/app/`
- Frontend: `new/frontend/src/`
- OpenAPI (при запущенном сервере): http://localhost:8010/docs
- UI в разработке: http://localhost:5173
- UI в Docker: http://localhost:8080
- Docker-инструкции: `new/docker/README.md`

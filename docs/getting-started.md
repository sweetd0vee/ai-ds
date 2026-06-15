# Быстрый старт

## Требования

| Компонент | Версия |
|-----------|--------|
| Python | 3.11+ (рекомендуется 3.12+) |
| Node.js | 18+ |
| Ollama | Установлена и запущена |
| Модель LLM | Минимум `qwen3:8b` |

## Установка Ollama и моделей

```bash
# Установите Ollama с https://ollama.com, затем:
ollama serve   # если не запущена как служба

ollama pull qwen3:8b
# Опционально — другие модели из списка настроек backend:
ollama pull qwen3:4b
ollama pull llama3.2
```

## Установка backend

```bash
cd "/Users/sweetd0ve/электронный DS/new/backend"

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

Альтернатива — использовать venv из корня проекта:

```bash
source "/Users/sweetd0ve/электронный DS/venv/bin/activate"
cd new/backend
pip install -r requirements.txt
```

## Установка frontend

```bash
cd "/Users/sweetd0ve/электронный DS/new/frontend"
npm install
```

## Запуск (два терминала)

### Терминал 1 — API (порт 8000)

```bash
cd "/Users/sweetd0ve/электронный DS/new/backend"
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка:

- Health: http://localhost:8000/api/health → `{"status":"ok"}`
- Swagger: http://localhost:8000/docs

### Терминал 2 — UI (порт 5173)

```bash
cd "/Users/sweetd0ve/электронный DS/new/frontend"
npm run dev
```

Откройте: **http://localhost:5173**

Vite проксирует `/api` на `localhost:8000`, CORS в dev не требуется.

## Первый анализ

1. На главном экране перетащите файл `.csv` или `.xlsx`.
2. Выберите количество графиков (10 / 15 / 20 / 30).
3. В шестерёнке настроек при необходимости смените LLM-модель.
4. Нажмите **«Запустить анализ»**.
5. Слева — прогресс и степпер, справа — вкладки с результатами.
6. По завершении скачайте DOCX/XLSX/графики с панели инструментов вкладки.

## Production-сборка frontend

```bash
cd new/frontend
npm run build    # → dist/
npm run preview  # локальный просмотр dist/
```

Для production нужно раздавать `dist/` через nginx/статику и проксировать `/api` на backend.

## Типичные проблемы

| Симптом | Решение |
|---------|---------|
| «Сервер недоступен» | Запустите uvicorn на :8000 |
| Ошибка LLM / timeout | Проверьте `ollama serve`, `ollama list`, наличие выбранной модели |
| Пустой анализ | Убедитесь, что в файле есть данные и заголовки столбцов |
| Кодировка CSV | Backend пробует utf-8 → latin1 → cp1251 автоматически |

## Переменные и пути

| Параметр | Значение по умолчанию | Файл |
|----------|----------------------|------|
| `JOBS_DIR` | `backend/data/jobs` | `app/config.py` |
| `PREVIEW_ROWS` | `20` | `app/config.py` |
| `analyst_model` | `qwen3:8b` | `app/config.py` |
| CORS origins | `localhost:5173` | `app/config.py` |

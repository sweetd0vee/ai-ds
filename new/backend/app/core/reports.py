"""Формирование итогового отчёта без LLM."""

from __future__ import annotations

import json

from .hypotheses import format_hypotheses_text


def build_final_report(
    filename: str,
    shape: tuple[int, int] | list[int],
    metrics_results_raw: str,
    analysis_summary: str,
    plot_files: list[str],
    graph_count: int,
    quality_report_raw: str = "",
    correlations_raw: str = "",
    hypotheses: list[dict] | None = None,
    discovery_raw: str = "",
) -> str:
    rows, cols = int(shape[0]), int(shape[1])
    n_plots = len(plot_files)

    metrics_brief = _metrics_highlights(metrics_results_raw)

    sections = [
        "ИТОГОВЫЙ АНАЛИТИЧЕСКИЙ ОТЧЁТ",
        "=" * 40,
        "",
        "1. ОБЩАЯ ХАРАКТЕРИСТИКА ДАННЫХ",
        f"Файл: {filename}",
        f"Размер: {rows} строк × {cols} столбцов.",
        f"Визуализация: построено {n_plots} графиков (запрошено {graph_count}).",
        "",
        "2. КАЧЕСТВО ДАННЫХ",
        _section_excerpt(quality_report_raw, "---JSON---"),
        "",
        "3. ИНСАЙТЫ, АНОМАЛИИ И ОСНОВНАЯ ОБЛАСТЬ",
        _section_excerpt(discovery_raw, "---JSON---", limit=4000) if discovery_raw else "  Инсайты недоступны.",
        "",
        "4. СВЯЗИ МЕЖДУ СТОЛБЦАМИ",
        _section_excerpt(correlations_raw, "---JSON---"),
        "",
        "5. КЛЮЧЕВЫЕ НАБЛЮДЕНИЯ ПО МЕТРИКАМ",
        metrics_brief,
        "",
        "6. ИНТЕРПРЕТАЦИЯ АНАЛИЗА",
        analysis_summary.strip(),
        "",
        "7. ГИПОТЕЗЫ ДЛЯ ПРОВЕРКИ",
        format_hypotheses_text(hypotheses or []),
        "",
        "8. ВИЗУАЛИЗАЦИИ",
    ]

    if plot_files:
        sections.extend(f"  • {name}" for name in plot_files)
    else:
        sections.append("  Графики не были построены (недостаточно подходящих признаков).")

    sections.extend([
        "",
        "9. РЕКОМЕНДАЦИИ",
        _recommendations(metrics_results_raw, rows, cols, quality_report_raw),
        "",
        "— Отчёт сформирован автоматически на основе расчётных метрик и анализа.",
    ])

    return "\n".join(sections)


def _section_excerpt(text: str, stop_at: str, limit: int = 2000) -> str:
    if not text or not text.strip():
        return "  Данные недоступны."
    excerpt = text.split(stop_at)[0].strip() if stop_at in text else text.strip()
    if len(excerpt) > limit:
        excerpt = excerpt[:limit] + "…"
    return excerpt


def _metrics_highlights(metrics_results_raw: str) -> str:
    try:
        data = json.loads(metrics_results_raw)
    except (json.JSONDecodeError, TypeError):
        return metrics_results_raw[:1500] if metrics_results_raw else "Метрики недоступны."

    lines: list[str] = []
    for col, metrics in list(data.items())[:12]:
        if not isinstance(metrics, dict):
            continue
        parts = []
        for key in ("count", "mean", "median", "std", "nunique", "min", "max", "mode"):
            if key in metrics and metrics[key] is not None:
                val = metrics[key]
                if isinstance(val, float):
                    val = round(val, 4)
                parts.append(f"{key}={val}")
        if parts:
            lines.append(f"• {col}: {', '.join(parts[:6])}")
    return "\n".join(lines) if lines else "Сводка метрик недоступна."


def _recommendations(
    metrics_results_raw: str,
    rows: int,
    cols: int,
    quality_report_raw: str = "",
) -> str:
    tips = [
        "Проверьте столбцы с большим числом пропусков — возможна предобработка (imputation или удаление).",
        "Сравните распределения числовых признаков с выбросами на boxplot-графиках.",
        "Для категориальных признаков с высокой кардинальностью рассмотрите группировку редких категорий.",
    ]

    try:
        if "---JSON---" in quality_report_raw:
            quality = json.loads(quality_report_raw.split("---JSON---", 1)[1].strip())
            summary = quality.get("summary", {})
            score = summary.get("overall_score")
            if score is not None and score < 50:
                tips.insert(0, "Качество данных низкое — выводы стоит трактовать с осторожностью до очистки.")
            dup = summary.get("duplicate_pct", 0)
            if dup and dup > 5:
                tips.insert(0, f"Обнаружены дубликаты строк ({dup}%) — проверьте дедупликацию.")
    except (json.JSONDecodeError, TypeError, IndexError):
        pass

    try:
        data = json.loads(metrics_results_raw)
        for col, metrics in data.items():
            if not isinstance(metrics, dict):
                continue
            count = metrics.get("count")
            if count is not None and rows > 0 and count < rows * 0.7:
                tips.insert(0, f"Столбец «{col}»: заметны пропуски ({count}/{rows} заполнено).")
                break
    except (json.JSONDecodeError, TypeError):
        pass

    if cols > 20:
        tips.append("При большом числе признаков имеет смысл отобрать ключевые для моделирования.")

    return "\n".join(f"• {t}" for t in tips[:6])

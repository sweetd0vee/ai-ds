"""Названия и выводы по автоматически построенным графикам."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

_PLOT_SUFFIXES = (
    "_mean_bar",
    "_timeseries",
    "_crosstab",
    "_scatter",
    "_box",
    "_count",
    "_hist",
    "_heatmap",
    "_bar",
)


def _parse_filename(filename: str) -> dict[str, Any]:
    base = filename
    if base.startswith("plot_"):
        base = base[5:]
    if base.endswith(".png"):
        base = base[:-4]

    if base == "corr_heatmap":
        return {"kind": "heatmap"}
    if base == "missing_bar":
        return {"kind": "missing"}

    for suffix in _PLOT_SUFFIXES:
        if base.endswith(suffix):
            stem = base[: -len(suffix)]
            kind = suffix[1:]
            parts = stem.split("_") if stem else []
            parsed: dict[str, Any] = {"kind": kind, "parts": parts}
            if kind == "scatter" and len(parts) >= 2:
                parsed["col_x"], parsed["col_y"] = parts[0], parts[1]
            elif kind in ("mean_bar", "box") and len(parts) >= 2:
                parsed["numeric"], parsed["categorical"] = parts[0], "_".join(parts[1:])
            elif kind == "timeseries" and len(parts) >= 2:
                parsed["metric"], parsed["date_col"] = parts[0], "_".join(parts[1:])
            elif kind in ("count", "hist") and parts:
                parsed["column"] = "_".join(parts)
            elif kind == "crosstab" and len(parts) >= 2:
                parsed["col_a"], parsed["col_b"] = parts[0], "_".join(parts[1:])
            return parsed
    return {"kind": "unknown", "parts": base.split("_")}


def _strength_phrase(value: float, *, kind: str = "pearson") -> str:
    abs_v = abs(value)
    if abs_v >= 0.7:
        return "сильная"
    if abs_v >= 0.4:
        return "умеренная"
    if abs_v >= 0.2:
        return "слабая"
    return "очень слабая"


def _find_numeric_pair(correlations: dict | None, col_a: str, col_b: str) -> dict | None:
    for pair in (correlations or {}).get("numeric_pairs") or []:
        a, b = pair.get("col_a"), pair.get("col_b")
        if {a, b} == {col_a, col_b}:
            return pair
    return None


def _find_cat_numeric(correlations: dict | None, cat: str, num: str) -> dict | None:
    for link in (correlations or {}).get("categorical_numeric") or []:
        if link.get("categorical") == cat and link.get("numeric") == num:
            return link
    return None


def _find_cat_pair(correlations: dict | None, col_a: str, col_b: str) -> dict | None:
    for pair in (correlations or {}).get("categorical_pairs") or []:
        a, b = pair.get("col_a"), pair.get("col_b")
        if {a, b} == {col_a, col_b}:
            return pair
    return None


def _title_from_parsed(parsed: dict[str, Any], label: str = "") -> str:
    kind = parsed.get("kind")
    if kind == "heatmap":
        return "Тепловая карта корреляций числовых признаков"
    if kind == "missing":
        return "Пропущенные значения по столбцам"
    if kind == "scatter":
        x, y = parsed.get("col_x", ""), parsed.get("col_y", "")
        return f"Зависимость {y} от {x}"
    if kind == "mean_bar":
        return f"Среднее {parsed.get('numeric', '')} по {parsed.get('categorical', '')}"
    if kind == "box":
        return f"Распределение {parsed.get('numeric', '')} по {parsed.get('categorical', '')}"
    if kind == "timeseries":
        return f"Динамика {parsed.get('metric', '')} по периодам"
    if kind == "count":
        return f"Распределение категорий: {parsed.get('column', '')}"
    if kind == "hist":
        return f"Распределение: {parsed.get('column', '')}"
    if kind == "crosstab":
        return f"Совместное распределение {parsed.get('col_a', '')} × {parsed.get('col_b', '')}"
    if label:
        return label.replace(" vs ", " и ").replace(" x ", " × ").capitalize()
    parts = parsed.get("parts") or []
    return " ".join(parts) if parts else "График"


def _conclusion_heatmap(df: pd.DataFrame, correlations: dict | None) -> str:
    pairs = (correlations or {}).get("numeric_pairs") or []
    if not pairs:
        cols = (correlations or {}).get("numeric_columns") or []
        if cols:
            return (
                f"На карте показаны попарные корреляции {len(cols)} числовых признаков. "
                "Сравните оттенки ячеек: тёмно-красный — сильная прямая связь, "
                "тёмно-синий — сильная обратная связь."
            )
        return "Тепловая карта показывает линейные связи между числовыми столбцами."

    lines = ["На графике выделены наиболее заметные линейные связи между числовыми признаками:"]
    for pair in pairs[:4]:
        a, b = pair.get("col_a"), pair.get("col_b")
        r = pair.get("pearson") or 0
        direction = "прямая" if r >= 0 else "обратная"
        lines.append(
            f"• {a} и {b}: r = {r:.2f} ({_strength_phrase(r)} {direction} связь)."
        )
    return "\n".join(lines)


def _conclusion_scatter(df: pd.DataFrame, col_x: str, col_y: str, correlations: dict | None) -> str:
    pair = _find_numeric_pair(correlations, col_x, col_y)
    sub = df[[col_x, col_y]].apply(pd.to_numeric, errors="coerce").dropna()
    if sub.empty:
        return f"График иллюстрирует совместное поведение столбцов {col_x} и {col_y}."

    r = pair.get("pearson") if pair else sub[col_x].corr(sub[col_y])
    if r is None or pd.isna(r):
        r = 0.0
    direction = "рост" if r >= 0 else "снижение"
    strength = _strength_phrase(float(r))
    lines = [
        f"Точки показывают {len(sub)} наблюдений. Коэффициент Пирсона r = {r:.2f} "
        f"({strength} {'прямая' if r >= 0 else 'обратная'} связь): при увеличении {col_x} "
        f"наблюдается {direction} {col_y}."
    ]
    if len(sub) >= 5:
        slope_note = "Красная линия — линейный тренд; отклонения точек указывают на выбросы или нелинейность."
        lines.append(slope_note)
    return " ".join(lines)


def _group_stats(df: pd.DataFrame, cat: str, num: str) -> tuple[str, float, float] | None:
    sub = df[[cat, num]].copy()
    sub[num] = pd.to_numeric(sub[num], errors="coerce")
    sub = sub.dropna()
    if sub.empty:
        return None
    top_cats = sub[cat].astype(str).value_counts().head(10).index
    sub = sub[sub[cat].astype(str).isin(top_cats)]
    grouped = sub.groupby(sub[cat].astype(str), observed=True)[num].mean().sort_values(ascending=False)
    if grouped.empty:
        return None
    best = grouped.index[0]
    worst = grouped.index[-1]
    return best, float(grouped.iloc[0]), float(grouped.iloc[-1])


def _conclusion_mean_bar(df: pd.DataFrame, cat: str, num: str, correlations: dict | None) -> str:
    stats = _group_stats(df, cat, num)
    link = _find_cat_numeric(correlations, cat, num)
    eta = (link or {}).get("eta")
    if not stats:
        return f"Столбчатая диаграмма сравнивает средние значения {num} по группам {cat}."

    best, best_val, worst_val = stats
    grouped = df[[cat, num]].copy()
    grouped[num] = pd.to_numeric(grouped[num], errors="coerce")
    grouped = grouped.dropna()
    means = grouped.groupby(grouped[cat].astype(str), observed=True)[num].mean().sort_values(ascending=False)
    worst_cat = means.index[-1]

    lines = [
        f"Наибольшее среднее {num} — у «{best}» ({best_val:.2f}), "
        f"наименьшее — у «{worst_cat}» ({worst_val:.2f})."
    ]
    if eta is not None:
        lines.append(
            f"Корреляционное отношение η = {eta:.2f} ({_strength_phrase(eta, kind='eta')}): "
            f"категория {cat} заметно объясняет различия в {num}."
        )
    else:
        lines.append(f"Сравнение групп по {cat} помогает выявить сегменты с аномально высокими или низкими {num}.")
    return " ".join(lines)


def _conclusion_box(df: pd.DataFrame, cat: str, num: str, correlations: dict | None) -> str:
    sub = df[[cat, num]].copy()
    sub[num] = pd.to_numeric(sub[num], errors="coerce")
    sub = sub.dropna()
    if sub.empty:
        return f"Boxplot показывает разброс и выбросы {num} внутри групп {cat}."

    medians = sub.groupby(sub[cat].astype(str), observed=True)[num].median().sort_values(ascending=False)
    best, worst = medians.index[0], medians.index[-1]
    lines = [
        f"Медиана {num} наиболее высока в группе «{best}», наименьшая — в «{worst}». "
        "Усы и точки вне коробки отражают разброс и возможные выбросы."
    ]
    link = _find_cat_numeric(correlations, cat, num)
    if link and link.get("eta") is not None:
        lines.append(f"Связь категории с числом: η = {link['eta']:.2f}.")
    return " ".join(lines)


def _conclusion_timeseries(df: pd.DataFrame, metric: str, date_col: str) -> str:
    sub = df[[date_col, metric]].copy()
    sub[date_col] = pd.to_datetime(sub[date_col], errors="coerce")
    sub[metric] = pd.to_numeric(sub[metric], errors="coerce")
    sub = sub.dropna().sort_values(date_col)
    if len(sub) < 4:
        return f"График отражает изменение {metric} во времени (столбец даты: {date_col})."

    mid = len(sub) // 2
    first_mean = float(sub[metric].iloc[:mid].mean())
    second_mean = float(sub[metric].iloc[mid:].mean())
    if second_mean > first_mean * 1.05:
        trend = "наблюдается рост показателя во второй половине периода"
    elif second_mean < first_mean * 0.95:
        trend = "во второй половине периода показатель снижается"
    else:
        trend = "существенного тренда не видно — значения колеблются вокруг среднего"
    return (
        f"Временной ряд по {metric}: среднее в первой половине периода {first_mean:.2f}, "
        f"во второй — {second_mean:.2f}; {trend}."
    )


def _conclusion_count(df: pd.DataFrame, column: str) -> str:
    if column not in df.columns:
        return f"Диаграмма показывает частоту категорий в столбце {column}."
    vc = df[column].astype(str).value_counts()
    total = int(vc.sum())
    top = vc.index[0]
    top_n = int(vc.iloc[0])
    share = top_n / total * 100 if total else 0
    n_cats = len(vc)
    return (
        f"В столбце {column} — {n_cats} уникальных категорий. "
        f"Доминирует «{top}»: {top_n} записей ({share:.1f}% выборки)."
    )


def _conclusion_hist(df: pd.DataFrame, column: str) -> str:
    if column not in df.columns:
        return f"Гистограмма показывает распределение значений {column}."
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return f"Распределение значений столбца {column}."
    mean = float(series.mean())
    median = float(series.median())
    std = float(series.std())
    skew = "симметричное" if abs(mean - median) < std * 0.15 else (
        "правостороннее (есть высокие выбросы)" if mean > median else "левостороннее (есть низкие выбросы)"
    )
    return (
        f"Распределение {column}: среднее {mean:.2f}, медиана {median:.2f}, σ = {std:.2f}. "
        f"Форма распределения — {skew}."
    )


def _conclusion_missing(df: pd.DataFrame) -> str:
    miss = df.isna().sum()
    miss = miss[miss > 0].sort_values(ascending=False)
    if miss.empty:
        return "Пропусков в данных не обнаружено — столбцы заполнены полностью."
    top_col = miss.index[0]
    top_n = int(miss.iloc[0])
    pct = top_n / len(df) * 100 if len(df) else 0
    return (
        f"Пропуски есть в {len(miss)} столбцах. Больше всего — в «{top_col}» "
        f"({top_n} ячеек, {pct:.1f}% строк). Рекомендуется проверить источник и стратегию заполнения."
    )


def _conclusion_crosstab(df: pd.DataFrame, col_a: str, col_b: str, correlations: dict | None) -> str:
    pair = _find_cat_pair(correlations, col_a, col_b)
    v = (pair or {}).get("cramers_v")
    lines = [f"Таблица сопряжённости для {col_a} и {col_b} показывает, как часто встречаются их сочетания."]
    if v is not None:
        lines.append(
            f"Cramér's V = {v:.2f} ({_strength_phrase(v)} связь): знание {col_a} помогает предсказывать {col_b}."
        )
    return " ".join(lines)


def build_plot_conclusion(
    parsed: dict[str, Any],
    df: pd.DataFrame | None,
    correlations: dict | None,
) -> str:
    kind = parsed.get("kind")
    if df is None or df.empty:
        return "График построен автоматически на основе структуры и связей в данных."

    try:
        if kind == "heatmap":
            return _conclusion_heatmap(df, correlations)
        if kind == "missing":
            return _conclusion_missing(df)
        if kind == "scatter":
            return _conclusion_scatter(df, parsed.get("col_x", ""), parsed.get("col_y", ""), correlations)
        if kind == "mean_bar":
            return _conclusion_mean_bar(df, parsed.get("categorical", ""), parsed.get("numeric", ""), correlations)
        if kind == "box":
            return _conclusion_box(df, parsed.get("categorical", ""), parsed.get("numeric", ""), correlations)
        if kind == "timeseries":
            return _conclusion_timeseries(df, parsed.get("metric", ""), parsed.get("date_col", ""))
        if kind == "count":
            return _conclusion_count(df, parsed.get("column", ""))
        if kind == "hist":
            return _conclusion_hist(df, parsed.get("column", ""))
        if kind == "crosstab":
            return _conclusion_crosstab(df, parsed.get("col_a", ""), parsed.get("col_b", ""), correlations)
    except Exception:
        pass
    return "График отражает закономерности в данных; используйте его для уточнения гипотез и поиска аномалий."


def build_plot_detail(
    filename: str,
    *,
    label: str = "",
    df: pd.DataFrame | None = None,
    correlations: dict | None = None,
) -> dict[str, str]:
    parsed = _parse_filename(filename)
    title = _title_from_parsed(parsed, label)
    conclusion = build_plot_conclusion(parsed, df, correlations)
    return {
        "filename": filename,
        "title": title,
        "conclusion": conclusion,
    }


def rebuild_plot_details(
    plot_files: list[str],
    *,
    df: pd.DataFrame | None = None,
    correlations: dict | None = None,
    viz_output: str = "",
) -> list[dict[str, str]]:
    """Восстановить метаданные для задач без сохранённого plot_details."""
    labels_by_hint: dict[str, str] = {}
    for line in (viz_output or "").splitlines():
        line = line.strip().lstrip("- ")
        if not line or line.startswith("Построено") or line.startswith("Стратегия"):
            continue
        label = re.sub(r"\s*\(score=[\d.]+\)\s*$", "", line).strip()
        if not label:
            continue
        key = label.replace(" ", "_").replace(" vs ", "_").replace(" x ", "_").lower()
        labels_by_hint[key] = label

    details: list[dict[str, str]] = []
    for filename in plot_files:
        parsed = _parse_filename(filename)
        hint = "_".join(parsed.get("parts") or [])
        label = labels_by_hint.get(hint, "")
        details.append(
            build_plot_detail(filename, label=label, df=df, correlations=correlations)
        )
    return details

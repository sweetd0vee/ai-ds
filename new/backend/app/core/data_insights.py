"""Отчёт о качестве данных и связи между столбцами (без LLM)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .data_analysis import classify_column
from .utils import convert_numpy_types

TOP_NUMERIC_PAIRS = 15
TOP_CATEGORICAL_PAIRS = 10
TOP_CAT_NUMERIC = 10
MAX_CAT_CARDINALITY = 40
MAX_CAT_COLS = 8


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _strength_label(value: float, *, strong: float = 0.7, moderate: float = 0.4) -> str:
    abs_v = abs(value)
    if abs_v >= strong:
        return "сильная"
    if abs_v >= moderate:
        return "умеренная"
    if abs_v >= 0.2:
        return "слабая"
    return "очень слабая"


def _is_notable_strength(strength: str) -> bool:
    return strength in ("сильная", "умеренная")


CORRELATION_HELP = {
    "pearson": {
        "name": "Коэффициент Пирсона (r)",
        "range": "от −1 до +1",
        "meaning": (
            "Линейная связь двух числовых столбцов. +1 — рост одного сопровождается ростом другого, "
            "−1 — рост одного сопровождается падением другого, 0 — линейной связи нет."
        ),
        "thresholds": "Сильная: |r| ≥ 0.7. Умеренная: 0.4 ≤ |r| < 0.7. Слабые связи скрыты.",
    },
    "cramers_v": {
        "name": "Cramér's V",
        "range": "от 0 до 1",
        "meaning": (
            "Сила связи между двумя категориальными столбцами. Чем выше V, тем предсказуемее "
            "значения одного столбца по другому (например, регион и канал продаж)."
        ),
        "thresholds": "Сильная: V ≥ 0.5. Умеренная: 0.3 ≤ V < 0.5. Слабые связи скрыты.",
    },
    "eta": {
        "name": "Корреляционное отношение (η)",
        "range": "от 0 до 1",
        "meaning": (
            "Насколько категориальный столбец объясняет разброс числового. "
            "Высокое η — средние/медианы числа заметно различаются между группами."
        ),
        "thresholds": "Сильная: η ≥ 0.5. Умеренная: 0.3 ≤ η < 0.5. Слабые связи скрыты.",
    },
}


def _column_kind(df: pd.DataFrame, col: str, parsed_structure: dict | None) -> str:
    if parsed_structure:
        for item in parsed_structure.get("columns", []):
            if item.get("name") == col:
                return item.get("kind") or classify_column(df, col)
    return classify_column(df, col)


def _chi2_statistic(table: np.ndarray) -> float:
    observed = table.astype(float)
    n = observed.sum()
    if n == 0:
        return 0.0
    row_sum = observed.sum(axis=1, keepdims=True)
    col_sum = observed.sum(axis=0, keepdims=True)
    expected = row_sum @ col_sum / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum((observed - expected) ** 2 / expected)
    return float(chi2) if np.isfinite(chi2) else 0.0


def _cramers_v(series_a: pd.Series, series_b: pd.Series) -> float | None:
    a = series_a.dropna().astype(str)
    b = series_b.dropna().astype(str)
    aligned = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(aligned) < 5:
        return None
    if aligned["a"].nunique() < 2 or aligned["b"].nunique() < 2:
        return None
    table = pd.crosstab(aligned["a"], aligned["b"]).values
    chi2 = _chi2_statistic(table)
    n = table.sum()
    min_dim = min(table.shape) - 1
    if min_dim <= 0 or n == 0:
        return None
    return _safe_float(np.sqrt(chi2 / (n * min_dim)))


def _correlation_ratio(categories: pd.Series, values: pd.Series) -> float | None:
    cats = categories.astype(str)
    nums = pd.to_numeric(values, errors="coerce")
    frame = pd.DataFrame({"cat": cats, "val": nums}).dropna()
    if len(frame) < 5 or frame["cat"].nunique() < 2:
        return None
    grand_mean = frame["val"].mean()
    ss_total = ((frame["val"] - grand_mean) ** 2).sum()
    if ss_total <= 0:
        return None
    ss_between = sum(
        len(group) * (group.mean() - grand_mean) ** 2
        for _, group in frame.groupby("cat")["val"]
    )
    return _safe_float(np.sqrt(ss_between / ss_total))


def build_quality_report(df: pd.DataFrame, parsed_structure: dict | None = None) -> dict:
    rows, col_count = df.shape
    duplicate_rows = int(df.duplicated().sum()) if rows else 0
    duplicate_pct = round(duplicate_rows / rows * 100, 2) if rows else 0.0

    columns: list[dict] = []
    issue_counts = {"high_missing": 0, "constant": 0, "near_unique": 0}

    for col in df.columns:
        series = df[col]
        non_null = int(series.notna().sum())
        missing = rows - non_null
        missing_pct = round(missing / rows * 100, 2) if rows else 0.0
        nunique = int(series.nunique(dropna=True))
        unique_pct = round(nunique / non_null * 100, 2) if non_null else 0.0
        kind = _column_kind(df, col, parsed_structure)

        issues: list[str] = []
        if missing_pct >= 50:
            issues.append("high_missing")
            issue_counts["high_missing"] += 1
        elif missing_pct >= 10:
            issues.append("moderate_missing")
        if non_null > 0 and nunique == 1:
            issues.append("constant")
            issue_counts["constant"] += 1
        if non_null > 10 and unique_pct >= 95 and kind not in ("identifier",):
            issues.append("near_unique")
            issue_counts["near_unique"] += 1
        if kind == "identifier":
            issues.append("likely_identifier")

        columns.append({
            "name": col,
            "kind": kind,
            "non_null": non_null,
            "missing": missing,
            "missing_pct": missing_pct,
            "nunique": nunique,
            "unique_pct": unique_pct,
            "issues": issues,
        })

    avg_missing = round(sum(c["missing_pct"] for c in columns) / col_count, 2) if col_count else 0.0
    moderate_missing = sum(1 for c in columns if "moderate_missing" in c.get("issues", []))
    identifier_count = sum(
        1 for c in columns if c["kind"] == "identifier" or "likely_identifier" in c.get("issues", [])
    )

    kind_counts: dict[str, int] = {}
    for col in columns:
        kind_counts[col["kind"]] = kind_counts.get(col["kind"], 0) + 1

    complete_rows = int(df.dropna(how="any").shape[0]) if rows else 0
    complete_rows_pct = round(complete_rows / rows * 100, 2) if rows else 0.0
    rows_with_missing = rows - complete_rows

    total_cells = rows * col_count if rows and col_count else 0
    filled_cells = sum(c["non_null"] for c in columns)
    fill_rate_pct = round(filled_cells / total_cells * 100, 2) if total_cells else 100.0

    top_missing = sorted(
        [c for c in columns if c["missing_pct"] > 0],
        key=lambda c: c["missing_pct"],
        reverse=True,
    )[:5]

    score = 100.0
    score -= min(avg_missing * 0.6, 30)
    score -= min(duplicate_pct * 0.5, 20)
    score -= min(issue_counts["high_missing"] * 5, 15)
    score -= min(issue_counts["constant"] * 3, 10)
    score -= min(issue_counts["near_unique"] * 2, 10)
    score = max(0, round(score))

    if score >= 75:
        grade = "good"
        grade_label = "хорошее"
    elif score >= 50:
        grade = "fair"
        grade_label = "удовлетворительное"
    else:
        grade = "poor"
        grade_label = "низкое"

    return convert_numpy_types({
        "summary": {
            "rows": rows,
            "columns": col_count,
            "duplicate_rows": duplicate_rows,
            "duplicate_pct": duplicate_pct,
            "avg_missing_pct": avg_missing,
            "overall_score": score,
            "overall_grade": grade,
            "overall_grade_label": grade_label,
            "columns_with_high_missing": issue_counts["high_missing"],
            "constant_columns": issue_counts["constant"],
            "near_unique_columns": issue_counts["near_unique"],
            "moderate_missing_columns": moderate_missing,
            "identifier_columns": identifier_count,
            "complete_rows": complete_rows,
            "complete_rows_pct": complete_rows_pct,
            "rows_with_missing": rows_with_missing,
            "fill_rate_pct": fill_rate_pct,
            "column_kinds": kind_counts,
            "usable_columns": max(0, col_count - issue_counts["constant"] - identifier_count),
            "top_missing_columns": [
                {"name": c["name"], "missing_pct": c["missing_pct"], "kind": c["kind"]}
                for c in top_missing
            ],
        },
        "columns": columns,
    })


def compute_correlations(df: pd.DataFrame, parsed_structure: dict | None = None) -> dict:
    numeric_cols: list[str] = []
    categorical_cols: list[str] = []

    for col in df.columns:
        kind = _column_kind(df, col, parsed_structure)
        if kind == "numeric":
            numeric_cols.append(col)
        elif kind in ("categorical", "boolean") and df[col].nunique(dropna=True) <= MAX_CAT_CARDINALITY:
            categorical_cols.append(col)

    numeric_pairs: list[dict] = []
    if len(numeric_cols) >= 2:
        numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        corr = numeric_df.corr(method="pearson", min_periods=10)
        for i, col_a in enumerate(numeric_cols):
            for col_b in numeric_cols[i + 1:]:
                r = _safe_float(corr.loc[col_a, col_b])
                if r is None:
                    continue
                numeric_pairs.append({
                    "col_a": col_a,
                    "col_b": col_b,
                    "pearson": round(r, 4),
                    "strength": _strength_label(r),
                    "direction": "положительная" if r > 0 else "отрицательная",
                })
        numeric_pairs.sort(key=lambda x: abs(x["pearson"]), reverse=True)
        numeric_pairs = [p for p in numeric_pairs if _is_notable_strength(p["strength"])][:TOP_NUMERIC_PAIRS]

    cat_cols_limited = sorted(
        categorical_cols,
        key=lambda c: df[c].nunique(dropna=True),
    )[:MAX_CAT_COLS]

    categorical_pairs: list[dict] = []
    for i, col_a in enumerate(cat_cols_limited):
        for col_b in cat_cols_limited[i + 1:]:
            v = _cramers_v(df[col_a], df[col_b])
            if v is None:
                continue
            categorical_pairs.append({
                "col_a": col_a,
                "col_b": col_b,
                "cramers_v": round(v, 4),
                "strength": _strength_label(v, strong=0.5, moderate=0.3),
            })
    categorical_pairs.sort(key=lambda x: x["cramers_v"], reverse=True)
    categorical_pairs = [p for p in categorical_pairs if _is_notable_strength(p["strength"])][:TOP_CATEGORICAL_PAIRS]

    cat_numeric: list[dict] = []
    if numeric_cols and cat_cols_limited:
        for cat_col in cat_cols_limited:
            for num_col in numeric_cols:
                eta = _correlation_ratio(df[cat_col], df[num_col])
                if eta is None:
                    continue
                cat_numeric.append({
                    "categorical": cat_col,
                    "numeric": num_col,
                    "eta": round(eta, 4),
                    "strength": _strength_label(eta, strong=0.5, moderate=0.3),
                })
        cat_numeric.sort(key=lambda x: x["eta"], reverse=True)
        cat_numeric = [p for p in cat_numeric if _is_notable_strength(p["strength"])][:TOP_CAT_NUMERIC]

    return convert_numpy_types({
        "numeric_columns": numeric_cols,
        "categorical_columns": cat_cols_limited,
        "numeric_pairs": numeric_pairs,
        "categorical_pairs": categorical_pairs,
        "categorical_numeric": cat_numeric,
        "help": CORRELATION_HELP,
        "filter_note": "Показаны только сильные и умеренные связи; слабые отфильтрованы.",
    })


def format_quality_report(report: dict) -> str:
    summary = report.get("summary", {})
    kinds = summary.get("column_kinds") or {}
    kind_line = ", ".join(
        f"{k}: {v}" for k, v in sorted(kinds.items(), key=lambda x: -x[1])
    )

    lines = [
        "ОТЧЁТ О КАЧЕСТВЕ ДАННЫХ",
        "=" * 36,
        f"Оценка: {summary.get('overall_score', 0)}/100 ({summary.get('overall_grade_label', '—')})",
        f"Строк: {summary.get('rows', 0)}, столбцов: {summary.get('columns', 0)}",
        f"Заполненность ячеек: {summary.get('fill_rate_pct', 0)}%",
        f"Строк без пропусков: {summary.get('complete_rows', 0)} ({summary.get('complete_rows_pct', 0)}%)",
        f"Дубликаты: {summary.get('duplicate_rows', 0)} ({summary.get('duplicate_pct', 0)}%)",
        f"Средний % пропусков: {summary.get('avg_missing_pct', 0)}%",
        f"Столбцов для анализа: {summary.get('usable_columns', 0)}",
    ]
    if kind_line:
        lines.append(f"Состав: {kind_line}")
    lines.extend(["", "Столбцы с замечаниями:"])

    flagged = [c for c in report.get("columns", []) if c.get("issues")]
    if not flagged:
        lines.append("  • Критичных проблем не обнаружено.")
    else:
        for col in flagged:
            issues = ", ".join(col["issues"])
            lines.append(
                f"  • {col['name']} ({col['kind']}): пропуски {col['missing_pct']}%, "
                f"уникальных {col['nunique']} — {issues}"
            )

    top_missing = summary.get("top_missing_columns") or []
    if top_missing:
        lines.extend(["", "Топ пропусков:"])
        for col in top_missing:
            lines.append(f"  • {col['name']}: {col['missing_pct']}%")

    lines.append("")
    lines.append("---JSON---")
    lines.append(json.dumps(report, ensure_ascii=False, indent=2))
    return "\n".join(lines)


def format_correlations(data: dict) -> str:
    lines = [
        "СВЯЗИ МЕЖДУ СТОЛБЦАМИ",
        "=" * 36,
        data.get("filter_note", "Показаны только сильные и умеренные связи."),
        "",
    ]

    help_block = data.get("help") or CORRELATION_HELP
    lines.append("Справка:")
    for item in help_block.values():
        lines.append(f"  • {item['name']}: {item['thresholds']}")
    lines.append("")

    num_pairs = data.get("numeric_pairs", [])
    if num_pairs:
        lines.append("")
        lines.append("Числовые пары (Pearson):")
        for p in num_pairs:
            lines.append(
                f"  • {p['col_a']} ↔ {p['col_b']}: r={p['pearson']} "
                f"({p['strength']}, {p['direction']})"
            )
    else:
        lines.append("")
        lines.append("Числовые корреляции: недостаточно числовых столбцов.")

    cat_pairs = data.get("categorical_pairs", [])
    if cat_pairs:
        lines.append("")
        lines.append("Категориальные пары (Cramér's V):")
        for p in cat_pairs:
            lines.append(
                f"  • {p['col_a']} ↔ {p['col_b']}: V={p['cramers_v']} ({p['strength']})"
            )

    cat_num = data.get("categorical_numeric", [])
    if cat_num:
        lines.append("")
        lines.append("Категория → число (η, корреляционное отношение):")
        for p in cat_num:
            lines.append(
                f"  • {p['categorical']} → {p['numeric']}: η={p['eta']} ({p['strength']})"
            )

    if not num_pairs and not cat_pairs and not cat_num:
        lines.append("  Значимых связей не найдено.")

    lines.append("")
    lines.append("---JSON---")
    lines.append(json.dumps(data, ensure_ascii=False, indent=2))
    return "\n".join(lines)

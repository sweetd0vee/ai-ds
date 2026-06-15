"""Анализ структуры данных, план метрик и их расчёт без LLM."""

from __future__ import annotations

import json
import logging
import warnings

import numpy as np
import pandas as pd

from .utils import convert_numpy_types

logger = logging.getLogger(__name__)

DATE_NAME_HINTS = (
    "date", "time", "dt", "timestamp", "created", "updated", "birth",
    "день", "дата", "время", "год", "month", "period",
)

NUMERIC_METRICS = [
    "count", "mean", "median", "mode", "std", "var", "min", "max",
    "quantile_25", "quantile_75", "quantile_90", "quantile_95",
    "skew", "kurtosis", "mad", "iqr",
]

CATEGORICAL_METRICS = ["count", "nunique", "mode", "mode_count", "mode_rel_freq"]

DATETIME_METRICS = [
    "count", "min_date", "max_date", "date_range_days", "unique_dates", "dates_per_month",
]

IDENTIFIER_METRICS = ["count", "nunique"]


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


def _column_name_suggests_datetime(name: str) -> bool:
    lower = name.lower()
    return any(hint in lower for hint in DATE_NAME_HINTS)


def _is_id_column(name: str, series: pd.Series) -> bool:
    lower = name.lower()
    if not any(token in lower for token in ("id", "index", "idx", "key", "номер", "код")):
        return False
    non_null = series.notna().sum()
    if non_null == 0:
        return False
    return series.nunique(dropna=True) >= 0.9 * non_null


def _looks_like_datetime(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        return True
    if pd.api.types.is_numeric_dtype(series.dtype):
        return False

    sample = series.dropna().astype(str).head(200)
    if sample.empty:
        return False

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")

    if parsed.notna().mean() < 0.8:
        return False

    # Отсекаем чисто числовые строки вроде "12345"
    str_sample = sample.head(20)
    if str_sample.str.fullmatch(r"-?\d+(\.\d+)?").mean() > 0.8:
        return False

    return True


def classify_column(df: pd.DataFrame, col: str) -> str:
    """Возвращает: numeric | categorical | datetime | boolean | identifier | textual."""
    series = df[col]

    if pd.api.types.is_bool_dtype(series.dtype):
        return "boolean"

    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        return "datetime"

    if pd.api.types.is_numeric_dtype(series.dtype):
        if _is_id_column(col, series):
            return "identifier"
        nunique = series.nunique(dropna=True)
        non_null = series.notna().sum()
        if non_null and nunique <= min(15, max(2, int(0.1 * non_null))):
            return "categorical"
        return "numeric"

    if _column_name_suggests_datetime(col) and _looks_like_datetime(series):
        return "datetime"

    if _looks_like_datetime(series):
        return "datetime"

    if _is_id_column(col, series):
        return "identifier"

    coerced = pd.to_numeric(series, errors="coerce")
    if coerced.notna().sum() >= 0.9 * max(series.notna().sum(), 1):
        return "numeric"

    nunique = series.nunique(dropna=True)
    non_null = series.notna().sum()
    if non_null and nunique / non_null > 0.9 and nunique > 50:
        return "textual"

    return "categorical"


def _human_type(kind: str, dtype) -> str:
    mapping = {
        "numeric": f"числовой ({dtype})",
        "categorical": f"категориальный ({dtype})",
        "datetime": f"дата/время ({dtype})",
        "boolean": f"булевый ({dtype})",
        "identifier": f"идентификатор ({dtype})",
        "textual": f"текстовый ({dtype})",
    }
    return mapping.get(kind, str(dtype))


def _describe_column(df: pd.DataFrame, col: str, kind: str) -> str:
    series = df[col]
    non_null = int(series.notna().sum())
    nunique = int(series.nunique(dropna=True))

    if kind == "numeric":
        return f"Числовой столбец: {non_null} значений, {nunique} уникальных"
    if kind == "categorical":
        return f"Категориальный столбец: {non_null} значений, {nunique} категорий"
    if kind == "datetime":
        return f"Столбец даты/времени: {non_null} значений"
    if kind == "boolean":
        return f"Булевый столбец: {non_null} значений"
    if kind == "identifier":
        return f"Идентификатор: {non_null} значений, {nunique} уникальных"
    return f"Текстовый столбец: {non_null} значений, {nunique} уникальных"


def detect_datetime_candidates(df: pd.DataFrame) -> list[str]:
    candidates = []
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series.dtype):
            candidates.append(col)
        elif pd.api.types.is_numeric_dtype(series.dtype):
            continue
        elif _column_name_suggests_datetime(col) and _looks_like_datetime(series):
            candidates.append(col)
        elif _looks_like_datetime(series):
            candidates.append(col)
    return candidates


def analyze_data_structure(df: pd.DataFrame) -> tuple[dict, str]:
    columns = []
    kinds: dict[str, str] = {}

    for col in df.columns:
        kind = classify_column(df, col)
        kinds[col] = kind
        columns.append({
            "name": col,
            "type": _human_type(kind, df[col].dtype),
            "description": _describe_column(df, col, kind),
            "kind": kind,
        })

    datetime_candidates = detect_datetime_candidates(df)
    parsed = {"columns": columns, "datetime_candidates": datetime_candidates}
    return parsed, format_structure_raw(parsed)


def format_structure_raw(parsed: dict) -> str:
    blocks = ["---COLUMNS_START---"]
    for col in parsed.get("columns", []):
        blocks.extend([
            f"Столбец: {col['name']}",
            f"Тип: {col['type']}",
            f"Описание: {col['description']}",
            "",
        ])
    blocks.append("---COLUMNS_END---")
    blocks.append("---DATETIME_CANDIDATES_START---")
    blocks.append(", ".join(parsed.get("datetime_candidates", [])))
    blocks.append("---DATETIME_CANDIDATES_END---")
    return "\n".join(blocks)


def build_metrics_plan(df: pd.DataFrame, parsed_structure: dict | None = None) -> tuple[dict, str]:
    plan: dict[str, list[str]] = {}
    columns = parsed_structure.get("columns", []) if parsed_structure else []

    if columns:
        col_kinds = {c["name"]: c.get("kind") or classify_column(df, c["name"]) for c in columns}
    else:
        col_kinds = {col: classify_column(df, col) for col in df.columns}

    for col, kind in col_kinds.items():
        if col not in df.columns:
            continue
        if kind == "numeric":
            plan[col] = list(NUMERIC_METRICS)
        elif kind == "datetime":
            plan[col] = list(DATETIME_METRICS)
        elif kind == "identifier":
            plan[col] = list(IDENTIFIER_METRICS)
        elif kind in ("categorical", "boolean", "textual"):
            plan[col] = list(CATEGORICAL_METRICS)
        else:
            plan[col] = list(CATEGORICAL_METRICS)

    return plan, format_metrics_plan_raw(plan)


def format_metrics_plan_raw(plan: dict[str, list[str]]) -> str:
    blocks = ["---METRICS_START---"]
    for col, metrics in plan.items():
        blocks.extend([
            f"Столбец: {col}",
            f"Метрики: {', '.join(metrics)}",
            "",
        ])
    blocks.append("---METRICS_END---")
    return "\n".join(blocks)


def _compute_categorical(series: pd.Series, metrics: list[str]) -> dict:
    s = series.dropna()
    result: dict = {}
    total = len(series)

    for metric in metrics:
        if metric == "count":
            result[metric] = int(s.count())
        elif metric == "nunique":
            result[metric] = int(s.nunique())
        elif metric == "mode":
            mode_vals = s.mode()
            result[metric] = str(mode_vals.iloc[0]) if not mode_vals.empty else None
        elif metric == "mode_count":
            mode_vals = s.mode()
            if mode_vals.empty:
                result[metric] = None
            else:
                result[metric] = int((s == mode_vals.iloc[0]).sum())
        elif metric == "mode_rel_freq":
            mode_vals = s.mode()
            if mode_vals.empty or total == 0:
                result[metric] = None
            else:
                result[metric] = float((s == mode_vals.iloc[0]).sum() / total)
        else:
            result[metric] = None

    return result


def _compute_numeric(series: pd.Series, metrics: list[str]) -> dict:
    numeric = pd.to_numeric(series, errors="coerce")
    s = numeric.dropna()
    result: dict = {}

    if s.empty:
        return {metric: None for metric in metrics}

    for metric in metrics:
        try:
            if metric == "count":
                result[metric] = int(s.count())
            elif metric == "mean":
                result[metric] = _safe_float(s.mean())
            elif metric == "median":
                result[metric] = _safe_float(s.median())
            elif metric == "mode":
                mode_vals = s.mode()
                result[metric] = _safe_float(mode_vals.iloc[0]) if not mode_vals.empty else None
            elif metric == "std":
                result[metric] = _safe_float(s.std())
            elif metric == "var":
                result[metric] = _safe_float(s.var())
            elif metric == "min":
                result[metric] = _safe_float(s.min())
            elif metric == "max":
                result[metric] = _safe_float(s.max())
            elif metric == "quantile_25":
                result[metric] = _safe_float(s.quantile(0.25))
            elif metric == "quantile_75":
                result[metric] = _safe_float(s.quantile(0.75))
            elif metric == "quantile_90":
                result[metric] = _safe_float(s.quantile(0.90))
            elif metric == "quantile_95":
                result[metric] = _safe_float(s.quantile(0.95))
            elif metric == "skew":
                result[metric] = _safe_float(s.skew())
            elif metric == "kurtosis":
                result[metric] = _safe_float(s.kurtosis())
            elif metric == "mad":
                result[metric] = _safe_float((s - s.mean()).abs().mean())
            elif metric == "iqr":
                result[metric] = _safe_float(s.quantile(0.75) - s.quantile(0.25))
            else:
                result[metric] = None
        except Exception as exc:
            logger.debug("Метрика %s не рассчитана: %s", metric, exc)
            result[metric] = None

    return result


def _compute_datetime(series: pd.Series, metrics: list[str]) -> dict:
    dt = pd.to_datetime(series, errors="coerce")
    s = dt.dropna()
    result: dict = {}

    for metric in metrics:
        try:
            if metric == "count":
                result[metric] = int(s.count())
            elif metric == "min_date":
                result[metric] = s.min().isoformat() if not s.empty else None
            elif metric == "max_date":
                result[metric] = s.max().isoformat() if not s.empty else None
            elif metric == "date_range_days":
                result[metric] = int((s.max() - s.min()).days) if len(s) >= 2 else None
            elif metric == "unique_dates":
                result[metric] = int(s.dt.normalize().nunique()) if not s.empty else None
            elif metric == "dates_per_month":
                if len(s) < 2:
                    result[metric] = None
                else:
                    temp = pd.Series(1, index=s)
                    result[metric] = temp.resample("ME").count().tolist()
            else:
                result[metric] = None
        except Exception as exc:
            logger.debug("Datetime-метрика %s не рассчитана: %s", metric, exc)
            result[metric] = None

    return result


def _infer_compute_kind(metrics: list[str]) -> str:
    datetime_metrics = {"min_date", "max_date", "date_range_days", "unique_dates", "dates_per_month"}
    numeric_metrics = {
        "mean", "std", "median", "var", "skew", "kurtosis", "mad", "iqr",
        "quantile_25", "quantile_75", "quantile_90", "quantile_95",
    }
    if datetime_metrics.intersection(metrics):
        return "datetime"
    if numeric_metrics.intersection(metrics):
        return "numeric"
    return "categorical"


def compute_metrics(df: pd.DataFrame, metrics_plan: dict[str, list[str]]) -> dict:
    results: dict[str, dict] = {}

    for col, metrics in metrics_plan.items():
        if col not in df.columns:
            continue

        series = df[col]
        kind = _infer_compute_kind(metrics)

        if kind == "numeric":
            results[col] = _compute_numeric(series, metrics)
        elif kind == "datetime":
            results[col] = _compute_datetime(series, metrics)
        else:
            results[col] = _compute_categorical(series, metrics)

    return convert_numpy_types(results)


def format_metrics_results(metrics_results: dict) -> str:
    return json.dumps(convert_numpy_types(metrics_results), ensure_ascii=False, indent=2)


_SUMMARY_METRIC_ORDER = (
    "count", "nunique", "mean", "median", "std", "min", "max",
    "mode", "mode_count", "mode_rel_freq",
    "quantile_25", "quantile_75", "quantile_90", "quantile_95",
    "skew", "kurtosis", "mad", "iqr", "var",
    "min_date", "max_date", "date_range_days", "unique_dates", "dates_per_month",
)


def _format_metric_value(key: str, value) -> str:
    if isinstance(value, float):
        if key == "mode_rel_freq":
            return f"{key}={value:.1%}"
        return f"{key}={round(value, 4)}"
    if isinstance(value, list):
        if len(value) <= 4:
            return f"{key}={value}"
        return f"{key}=[{value[0]}, …, {value[-1]}] ({len(value)} знач.)"
    return f"{key}={value}"


def format_metrics_summary(metrics_results: dict) -> str:
    """Краткое текстовое представление рассчитанных метрик."""
    lines: list[str] = []

    for col, metrics in metrics_results.items():
        if not isinstance(metrics, dict):
            continue

        parts: list[str] = []
        seen: set[str] = set()
        for key in _SUMMARY_METRIC_ORDER:
            if key not in metrics or metrics[key] is None:
                continue
            parts.append(_format_metric_value(key, metrics[key]))
            seen.add(key)

        for key, value in metrics.items():
            if key in seen or value is None:
                continue
            parts.append(_format_metric_value(key, value))

        if parts:
            lines.append(f"• {col}: {', '.join(parts)}")

    return "\n".join(lines) if lines else "Метрики не рассчитаны."


def format_calculation_code_reference(metrics_plan: dict[str, list[str]]) -> str:
    """Стартовый код для песочницы на вкладке «Код»."""
    cols = len(metrics_plan)
    first_col = next(iter(metrics_plan), "column")
    return f"""# Песочница Python — данные и план метрик уже загружены на сервере
# Доступно: df, pd, np, metrics_plan ({cols} столбцов)
# Функции: compute_metrics(), format_metrics_summary(), format_metrics_results()

rows, cols_count = df.shape
print(f"Датасет: {{rows}} строк × {{cols_count}} столбцов")

missing = df.isna().sum()
cols_with_na = missing[missing > 0]
if not cols_with_na.empty:
    print(f"Столбцов с пропусками: {{len(cols_with_na)}}")
    for col, cnt in cols_with_na.nlargest(5).items():
        print(f"  {{col}}: {{cnt}} ({{cnt / rows:.1%}})")
else:
    print("Пропусков нет")

print()
print("=" * 60)
print("Метрики по плану")
print("=" * 60)

metrics_results = compute_metrics(df, metrics_plan)
print(format_metrics_summary(metrics_results))

# Полный JSON (раскомментируйте при необходимости):
# print(format_metrics_results(metrics_results))

# Дополнительные эксперименты:
# print(df.describe(include="all").T)
# print(df["{first_col}"].value_counts().head(10))
"""

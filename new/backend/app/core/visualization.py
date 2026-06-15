"""Автоматическая визуализация без LLM — приоритет информативным графикам."""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ds_mpl_config"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .data_analysis import classify_column
from .plot_insights import build_plot_detail

logger = logging.getLogger(__name__)

sns.set_theme(style="whitegrid", palette="tab10")
plt.rcParams.update({"figure.figsize": (10, 6), "figure.dpi": 100, "savefig.dpi": 100})

BUSINESS_KEYWORDS = (
    "revenue", "profit", "margin", "price", "cost", "sales", "amount",
    "quantity", "score", "rating", "nps", "total", "sum", "avg", "mean",
    "доход", "выруч", "прибыл", "марж", "цена", "сумм", "колич", "оценк",
)

SKIP_NAME_HINTS = (
    "id", "index", "idx", "key", "sku", "uuid", "hash", "код", "номер",
)


@dataclass
class PlotCandidate:
    score: float
    label: str
    plot_fn: Callable[[], str | None]


def _column_groups(df: pd.DataFrame, parsed_structure: dict | None = None) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {
        "numeric": [],
        "categorical": [],
        "datetime": [],
        "boolean": [],
        "identifier": [],
        "textual": [],
    }
    kind_map = {}
    if parsed_structure:
        for item in parsed_structure.get("columns", []):
            if item.get("name"):
                kind_map[item["name"]] = item.get("kind")

    for col in df.columns:
        kind = kind_map.get(col) or classify_column(df, col)
        groups.get(kind, groups["categorical"]).append(col)
    return groups


def _is_low_value_column(name: str, series: pd.Series, kind: str) -> bool:
    lower = name.lower()
    if any(h in lower for h in SKIP_NAME_HINTS):
        return True
    if kind == "identifier":
        return True
    non_null = max(int(series.notna().sum()), 1)
    nunique = series.nunique(dropna=True)
    if nunique <= 1:
        return True
    if kind in ("categorical", "boolean") and nunique > 25:
        return True
    if kind == "numeric":
        nums = pd.to_numeric(series, errors="coerce").dropna()
        if nums.empty:
            return True
        if nunique >= 0.95 * non_null:
            return True
    return False


def _column_importance(name: str, series: pd.Series, kind: str) -> float:
    if _is_low_value_column(name, series, kind):
        return 0.0
    score = 10.0
    lower = name.lower()
    if any(k in lower for k in BUSINESS_KEYWORDS):
        score += 35.0
    non_null = max(int(series.notna().sum()), 1)
    nunique = series.nunique(dropna=True)
    if kind in ("categorical", "boolean"):
        if 2 <= nunique <= 12:
            score += 20.0
        elif nunique <= 20:
            score += 10.0
    if kind == "numeric":
        nums = pd.to_numeric(series, errors="coerce").dropna()
        if len(nums) > 1:
            mean = abs(float(nums.mean()))
            std = float(nums.std())
            if mean > 1e-9:
                score += min(25.0, (std / mean) * 15.0)
            elif std > 0:
                score += 10.0
    if kind == "datetime":
        score += 15.0
    return score


def _safe_filename(*parts: str) -> str:
    name = "_".join(parts)
    for ch in ' /\\:*?"<>|':
        name = name.replace(ch, "_")
    return f"plot_{name}.png"[:120]


def _save_fig(output_dir: Path, filename: str) -> str:
    path = output_dir / filename
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return filename


def _try_plot(fn: Callable[[], str | None]) -> str | None:
    try:
        return fn()
    except Exception:
        logger.exception("Plot failed")
        plt.close("all")
        return None


def _rank_columns(df: pd.DataFrame, cols: list[str], kind: str) -> list[str]:
    scored = [
        (col, _column_importance(col, df[col], kind))
        for col in cols
        if col in df.columns and not _is_low_value_column(col, df[col], kind)
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [col for col, s in scored if s > 0]


def _collect_candidates(
    df: pd.DataFrame,
    output_dir: Path,
    groups: dict[str, list[str]],
    correlations: dict | None,
) -> list[PlotCandidate]:
    candidates: list[PlotCandidate] = []
    numeric = _rank_columns(df, groups["numeric"], "numeric")
    categorical = _rank_columns(df, groups["categorical"] + groups["boolean"], "categorical")
    datetime_cols = _rank_columns(df, groups["datetime"], "datetime")
    corr = correlations or {}

    # 1. Тепловая карта корреляций (компактная, только осмысленные числовые)
    heatmap_cols = [c for c in corr.get("numeric_columns", numeric) if c in numeric][:12]
    if len(heatmap_cols) >= 3:

        def corr_heatmap(cols=heatmap_cols):
            sub = df[cols].apply(pd.to_numeric, errors="coerce")
            corr_mat = sub.corr()
            if corr_mat.shape[0] < 3:
                return None
            fig, ax = plt.subplots(figsize=(max(8, len(cols) * 0.7), max(6, len(cols) * 0.6)))
            annot = len(cols) <= 10
            sns.heatmap(corr_mat, annot=annot, fmt=".2f", cmap="RdBu_r", center=0, ax=ax, vmin=-1, vmax=1)
            ax.set_title("Корреляции ключевых числовых признаков")
            return _save_fig(output_dir, _safe_filename("corr", "heatmap"))

        candidates.append(PlotCandidate(98.0, "correlation heatmap", corr_heatmap))

    # 2. Scatter + тренд для самых сильных числовых пар (не более 3)
    scatter_count = 0
    used_scatter_cols: set[str] = set()
    for pair in corr.get("numeric_pairs", [])[:12]:
        if scatter_count >= 3:
            break
        col_a, col_b = pair.get("col_a"), pair.get("col_b")
        pearson = abs(pair.get("pearson") or 0)
        if not col_a or not col_b or col_a not in df.columns or col_b not in df.columns:
            continue
        if pearson < 0.35:
            continue
        if col_a in used_scatter_cols and col_b in used_scatter_cols:
            continue
        scatter_count += 1
        used_scatter_cols.update([col_a, col_b])
        score = 70.0 + min(28.0, pearson * 35.0)

        def scatter_pair(a=col_a, b=col_b, r=pair.get("pearson")):
            sub = df[[a, b]].apply(pd.to_numeric, errors="coerce").dropna()
            if len(sub) < 5:
                return None
            fig, ax = plt.subplots()
            sns.regplot(data=sub, x=a, y=b, ax=ax, scatter_kws={"alpha": 0.5, "s": 35}, line_kws={"color": "crimson"})
            ax.set_title(f"{b} vs {a} (r={r:.2f})")
            return _save_fig(output_dir, _safe_filename(a, b, "scatter"))

        candidates.append(PlotCandidate(score, f"scatter {col_a} vs {col_b}", scatter_pair))

    # 3. Среднее/сумма числового по категории (eta из анализа связей, не более 4)
    cat_num_count = 0
    for link in corr.get("categorical_numeric", [])[:12]:
        if cat_num_count >= 4:
            break
        cat_col, num_col = link.get("categorical"), link.get("numeric")
        eta = link.get("eta") or 0
        if not cat_col or not num_col:
            continue
        if cat_col not in df.columns or num_col not in df.columns:
            continue
        if eta < 0.15:
            continue
        score = 75.0 + min(22.0, eta * 40.0)

        def bar_cat_num(c=cat_col, n=num_col, e=eta):
            sub = df[[c, n]].copy()
            sub[n] = pd.to_numeric(sub[n], errors="coerce")
            sub = sub.dropna()
            if sub.empty:
                return None
            top_cats = sub[c].astype(str).value_counts().head(10).index
            sub = sub[sub[c].astype(str).isin(top_cats)]
            agg = sub.groupby(sub[c].astype(str), observed=True)[n].mean().sort_values(ascending=False)
            if agg.empty:
                return None
            fig, ax = plt.subplots(figsize=(11, 5))
            colors = sns.color_palette("tab10", len(agg))
            agg.plot(kind="bar", ax=ax, color=colors)
            ax.set_title(f"Среднее {n} по {c} (η={e:.2f})")
            ax.set_xlabel(c)
            ax.set_ylabel(f"Среднее {n}")
            ax.tick_params(axis="x", rotation=45)
            return _save_fig(output_dir, _safe_filename(n, c, "mean_bar"))

        candidates.append(PlotCandidate(score, f"mean {num_col} by {cat_col}", bar_cat_num))
        cat_num_count += 1

    # 4. Boxplot: числовой по категории (для топ-пар, если bar ещё не покрыл)
    seen_pairs: set[tuple[str, str]] = set()
    for link in corr.get("categorical_numeric", [])[:6]:
        cat_col, num_col = link.get("categorical"), link.get("numeric")
        if not cat_col or not num_col:
            continue
        key = (cat_col, num_col)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        eta = link.get("eta") or 0
        if eta < 0.2:
            continue
        score = 68.0 + min(20.0, eta * 30.0)

        def box_cat_num(c=cat_col, n=num_col, e=eta):
            sub = df[[c, n]].copy()
            sub[n] = pd.to_numeric(sub[n], errors="coerce")
            sub = sub.dropna()
            top_cats = sub[c].astype(str).value_counts().head(8).index
            sub = sub[sub[c].astype(str).isin(top_cats)]
            if sub[c].astype(str).nunique() < 2:
                return None
            fig, ax = plt.subplots(figsize=(11, 5))
            sns.boxplot(data=sub, x=c, y=n, ax=ax, palette="Set2")
            ax.set_title(f"Распределение {n} по {c}")
            ax.tick_params(axis="x", rotation=45)
            return _save_fig(output_dir, _safe_filename(n, c, "box"))

        candidates.append(PlotCandidate(score - 5, f"box {num_col} by {cat_col}", box_cat_num))

    # 5. Временной ряд: агрегат важной метрики по дате
    if datetime_cols and numeric:
        date_col = datetime_cols[0]
        metric_col = numeric[0]
        score = 72.0 + _column_importance(metric_col, df[metric_col], "numeric") * 0.2

        def ts_metric(d=date_col, m=metric_col):
            sub = df[[d, m]].copy()
            sub[d] = pd.to_datetime(sub[d], errors="coerce")
            sub[m] = pd.to_numeric(sub[m], errors="coerce")
            sub = sub.dropna().sort_values(d)
            if len(sub) < 4:
                return None
            freq = "W" if sub[d].nunique() > 60 else "ME"
            rolled = sub.set_index(d)[m].resample(freq).mean()
            if rolled.dropna().empty:
                return None
            fig, ax = plt.subplots()
            rolled.plot(ax=ax, marker="o", color="teal", linewidth=2)
            ax.set_title(f"Динамика среднего {m} по периодам")
            ax.set_xlabel("Период")
            ax.set_ylabel(m)
            ax.tick_params(axis="x", rotation=45)
            return _save_fig(output_dir, _safe_filename(m, d, "timeseries"))

        candidates.append(PlotCandidate(score, f"timeseries {metric_col}", ts_metric))

    # 6. Частоты категорий (только информативные, низкая кардинальность)
    for col in categorical[:4]:
        nunique = df[col].nunique(dropna=True)
        if nunique < 2 or nunique > 15:
            continue
        score = 55.0 + _column_importance(col, df[col], "categorical") * 0.5

        def cat_count(c=col):
            vc = df[c].astype(str).value_counts().head(12)
            if len(vc) < 2:
                return None
            fig, ax = plt.subplots(figsize=(10, max(4, len(vc) * 0.4)))
            colors = sns.color_palette("tab10", len(vc))
            vc.sort_values().plot(kind="barh", ax=ax, color=colors)
            ax.set_title(f"Распределение категорий: {c}")
            ax.set_xlabel("Количество")
            return _save_fig(output_dir, _safe_filename(c, "count"))

        candidates.append(PlotCandidate(score, f"count {col}", cat_count))

    # 7. Гистограмма — только для топ-2 числовых с вариативностью
    for col in numeric[:2]:
        score = 48.0 + _column_importance(col, df[col], "numeric") * 0.4

        def hist_num(c=col):
            series = pd.to_numeric(df[c], errors="coerce").dropna()
            if len(series) < 5 or series.nunique() < 3:
                return None
            fig, ax = plt.subplots()
            sns.histplot(series, bins=min(25, max(8, series.nunique() // 3)), kde=True, ax=ax, color="steelblue")
            ax.set_title(f"Распределение: {c}")
            ax.set_xlabel(c)
            return _save_fig(output_dir, _safe_filename(c, "hist"))

        candidates.append(PlotCandidate(score, f"hist {col}", hist_num))

    # 8. Пропуски — только если есть заметные дыры
    miss = df.isna().sum()
    miss = miss[miss > 0]
    if not miss.empty and miss.max() >= max(3, 0.03 * len(df)):

        def missing_plot():
            top = miss.sort_values(ascending=False).head(15)
            fig, ax = plt.subplots(figsize=(10, 5))
            colors = sns.color_palette("Oranges_r", len(top))
            top.plot(kind="bar", ax=ax, color=colors)
            ax.set_title("Пропущенные значения по столбцам")
            ax.set_ylabel("Количество")
            ax.tick_params(axis="x", rotation=45)
            return _save_fig(output_dir, _safe_filename("missing", "bar"))

        candidates.append(PlotCandidate(45.0, "missing values", missing_plot))

    # 9. Crosstab двух категорий (если есть связь)
    for pair in corr.get("categorical_pairs", [])[:3]:
        col_a, col_b = pair.get("col_a"), pair.get("col_b")
        v = pair.get("cramers_v") or 0
        if not col_a or not col_b or v < 0.2:
            continue
        score = 60.0 + min(18.0, v * 30.0)

        def crosstab_plot(a=col_a, b=col_b, cv=v):
            sub = df[[a, b]].dropna()
            if sub.empty:
                return None
            top_a = sub[a].astype(str).value_counts().head(6).index
            top_b = sub[b].astype(str).value_counts().head(6).index
            sub = sub[sub[a].astype(str).isin(top_a) & sub[b].astype(str).isin(top_b)]
            ct = pd.crosstab(sub[a].astype(str), sub[b].astype(str))
            if ct.size < 4:
                return None
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.heatmap(ct, annot=True, fmt="d", cmap="YlGnBu", ax=ax)
            ax.set_title(f"Совместное распределение {a} × {b}")
            return _save_fig(output_dir, _safe_filename(a, b, "crosstab"))

        candidates.append(PlotCandidate(score, f"crosstab {col_a} x {col_b}", crosstab_plot))

    return candidates


def generate_visualizations(
    df: pd.DataFrame,
    output_dir: Path,
    graph_count: int,
    *,
    correlations: dict | None = None,
    parsed_structure: dict | None = None,
) -> tuple[list[str], str, str, list[dict]]:
    """Возвращает (список png, справочный код, лог выполнения, метаданные графиков)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    groups = _column_groups(df, parsed_structure)

    if correlations is None:
        from .data_insights import compute_correlations
        correlations = compute_correlations(df, parsed_structure)

    candidates = _collect_candidates(df, output_dir, groups, correlations)
    candidates.sort(key=lambda c: c.score, reverse=True)

    plot_files: list[str] = []
    plot_details: list[dict] = []
    actions: list[str] = []
    used_labels: set[str] = set()

    for cand in candidates:
        if len(plot_files) >= graph_count:
            break
        if cand.label in used_labels:
            continue
        name = _try_plot(cand.plot_fn)
        if name:
            plot_files.append(name)
            plot_details.append(
                build_plot_detail(
                    name,
                    label=cand.label,
                    df=df,
                    correlations=correlations,
                )
            )
            actions.append(f"{cand.label} (score={cand.score:.0f})")
            used_labels.add(cand.label)

    plot_files = sorted(set(plot_files))[:graph_count]
    details_by_name = {item["filename"]: item for item in plot_details}
    plot_details = [details_by_name[name] for name in plot_files if name in details_by_name]
    code_ref = format_viz_code_reference(plot_files, graph_count)
    log = (
        f"Построено графиков: {len(plot_files)} из {graph_count}\n"
        f"Стратегия: приоритет связям и бизнес-метрикам\n"
        + "\n".join(f"- {a}" for a in actions)
    )
    return plot_files, code_ref, log, plot_details


def format_viz_code_reference(plot_files: list[str], graph_count: int) -> str:
    lines = [
        "# Автоматическая визуализация (app/core/visualization.py, без LLM)",
        f"# Запрошено графиков: {graph_count}, построено: {len(plot_files)}",
        "# Приоритет: корреляции, связи категория×число, временные ряды, затем распределения",
        "",
        "from app.core.visualization import generate_visualizations",
        "",
        "plot_files, viz_code, log, plot_details = generate_visualizations(",
        "    df, output_dir, graph_count,",
        "    correlations=correlations,",
        "    parsed_structure=parsed_structure,",
        ")",
        "print(log)",
        "",
        "# Созданные файлы:",
    ]
    lines.extend(f"#   {name}" for name in plot_files)
    return "\n".join(lines)

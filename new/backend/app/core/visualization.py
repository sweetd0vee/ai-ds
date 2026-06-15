"""Автоматическая визуализация без LLM."""

from __future__ import annotations

import logging
import os
import tempfile
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

logger = logging.getLogger(__name__)

sns.set_theme(style="whitegrid", palette="tab10")
plt.rcParams.update({"figure.figsize": (10, 6), "figure.dpi": 100, "savefig.dpi": 100})


def _column_groups(df: pd.DataFrame) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {
        "numeric": [],
        "categorical": [],
        "datetime": [],
        "boolean": [],
        "identifier": [],
        "textual": [],
    }
    for col in df.columns:
        kind = classify_column(df, col)
        groups.get(kind, groups["categorical"]).append(col)
    return groups


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


def generate_visualizations(
    df: pd.DataFrame,
    output_dir: Path,
    graph_count: int,
) -> tuple[list[str], str, str]:
    """Возвращает (список png, справочный код, лог выполнения)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    groups = _column_groups(df)
    numeric = groups["numeric"]
    categorical = groups["categorical"] + groups["boolean"]
    datetime_cols = groups["datetime"]
    plot_files: list[str] = []
    actions: list[str] = []

    def add(fn: Callable[[], str | None], label: str) -> bool:
        if len(plot_files) >= graph_count:
            return False
        name = _try_plot(fn)
        if name:
            plot_files.append(name)
            actions.append(label)
        return len(plot_files) < graph_count

    # 1. Пропуски
    if len(df.columns) > 0:
        def missing_plot():
            miss = df.isna().sum()
            miss = miss[miss > 0].sort_values(ascending=False).head(20)
            if miss.empty:
                return None
            fig, ax = plt.subplots()
            miss.plot(kind="bar", ax=ax, color=sns.color_palette("tab10", len(miss)))
            ax.set_title("Пропущенные значения по столбцам")
            ax.set_ylabel("Количество")
            ax.tick_params(axis="x", rotation=45)
            return _save_fig(output_dir, _safe_filename("missing_values", "bar"))

        add(missing_plot, "missing_values bar")

    # 2. Корреляции
    if len(numeric) >= 2:
        def corr_plot():
            corr = df[numeric].select_dtypes(include=[np.number]).corr()
            if corr.shape[0] < 2:
                return None
            fig, ax = plt.subplots(figsize=(max(8, len(numeric)), max(6, len(numeric))))
            sns.heatmap(corr, annot=len(numeric) <= 8, fmt=".2f", cmap="viridis", ax=ax)
            ax.set_title("Корреляция числовых признаков")
            return _save_fig(output_dir, _safe_filename("corr", "heatmap"))

        add(corr_plot, "correlation heatmap")

    # 3. Гистограммы числовых
    for col in numeric:
        if len(plot_files) >= graph_count:
            break

        def hist_plot(c=col):
            series = pd.to_numeric(df[c], errors="coerce").dropna()
            if series.empty:
                return None
            fig, ax = plt.subplots()
            ax.hist(series, bins=min(30, max(10, series.nunique() // 2)), color="steelblue", edgecolor="white")
            ax.set_title(f"Распределение: {c}")
            ax.set_xlabel(c)
            return _save_fig(output_dir, _safe_filename(c, "hist"))

        add(hist_plot, f"{col} histogram")

    # 4. Boxplot числовых
    for col in numeric:
        if len(plot_files) >= graph_count:
            break

        def box_plot(c=col):
            series = pd.to_numeric(df[c], errors="coerce").dropna()
            if series.empty:
                return None
            fig, ax = plt.subplots()
            sns.boxplot(y=series, ax=ax, color="coral")
            ax.set_title(f"Boxplot: {c}")
            return _save_fig(output_dir, _safe_filename(c, "boxplot"))

        add(box_plot, f"{col} boxplot")

    # 5. Категориальные — частоты
    for col in categorical:
        if len(plot_files) >= graph_count:
            break

        def cat_plot(c=col):
            vc = df[c].astype(str).value_counts().head(15)
            if vc.empty:
                return None
            fig, ax = plt.subplots(figsize=(10, max(4, len(vc) * 0.35)))
            colors = sns.color_palette("tab10", len(vc))
            vc.plot(kind="barh", ax=ax, color=colors)
            ax.set_title(f"Топ категорий: {c}")
            ax.invert_yaxis()
            return _save_fig(output_dir, _safe_filename(c, "count"))

        add(cat_plot, f"{col} count")

    # 6. Числовой vs категориальный
    if numeric and categorical:
        num_col, cat_col = numeric[0], categorical[0]

        def group_box():
            sub = df[[cat_col, num_col]].copy()
            sub[num_col] = pd.to_numeric(sub[num_col], errors="coerce")
            sub = sub.dropna()
            if sub.empty:
                return None
            top_cats = sub[cat_col].astype(str).value_counts().head(10).index
            sub = sub[sub[cat_col].astype(str).isin(top_cats)]
            fig, ax = plt.subplots(figsize=(12, 6))
            sns.boxplot(data=sub, x=cat_col, y=num_col, ax=ax, palette="tab10")
            ax.set_title(f"{num_col} по {cat_col}")
            ax.tick_params(axis="x", rotation=45)
            return _save_fig(output_dir, _safe_filename(num_col, cat_col, "box"))

        add(group_box, f"{num_col} by {cat_col} boxplot")

    # 7. Scatter двух числовых
    if len(numeric) >= 2:
        x_col, y_col = numeric[0], numeric[1]

        def scatter_plot():
            sub = df[[x_col, y_col]].apply(pd.to_numeric, errors="coerce").dropna()
            if len(sub) < 2:
                return None
            fig, ax = plt.subplots()
            ax.scatter(sub[x_col], sub[y_col], alpha=0.5, c=range(len(sub)), cmap="viridis")
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title(f"Scatter: {x_col} vs {y_col}")
            return _save_fig(output_dir, _safe_filename(x_col, y_col, "scatter"))

        add(scatter_plot, f"scatter {x_col} {y_col}")

    # 8. Временные ряды
    for col in datetime_cols:
        if len(plot_files) >= graph_count:
            break

        def ts_plot(c=col):
            ts = pd.to_datetime(df[c], errors="coerce").dropna()
            if len(ts) < 3:
                return None
            counts = ts.dt.to_period("M").value_counts().sort_index()
            fig, ax = plt.subplots()
            counts.plot(kind="bar", ax=ax, color="teal")
            ax.set_title(f"Записи по месяцам: {c}")
            ax.tick_params(axis="x", rotation=45)
            return _save_fig(output_dir, _safe_filename(c, "timeseries"))

        add(ts_plot, f"{col} timeseries")

    # 9. Violin для оставшихся слотов
    if numeric and categorical and len(plot_files) < graph_count:
        num_col, cat_col = numeric[0], categorical[0]

        def violin_plot():
            sub = df[[cat_col, num_col]].copy()
            sub[num_col] = pd.to_numeric(sub[num_col], errors="coerce")
            sub = sub.dropna()
            top_cats = sub[cat_col].astype(str).value_counts().head(8).index
            sub = sub[sub[cat_col].astype(str).isin(top_cats)]
            if sub.empty:
                return None
            fig, ax = plt.subplots(figsize=(12, 6))
            sns.violinplot(data=sub, x=cat_col, y=num_col, ax=ax, palette="tab10")
            ax.set_title(f"Violin: {num_col} по {cat_col}")
            ax.tick_params(axis="x", rotation=45)
            return _save_fig(output_dir, _safe_filename(num_col, cat_col, "violin"))

        add(violin_plot, f"violin {num_col} {cat_col}")

    plot_files = sorted(set(plot_files))[:graph_count]
    code_ref = format_viz_code_reference(plot_files, graph_count)
    log = f"Построено графиков: {len(plot_files)} из {graph_count}\n" + "\n".join(f"- {a}" for a in actions)
    return plot_files, code_ref, log


def format_viz_code_reference(plot_files: list[str], graph_count: int) -> str:
    lines = [
        "# Автоматическая визуализация (app/core/visualization.py, без LLM)",
        f"# Запрошено графиков: {graph_count}, построено: {len(plot_files)}",
        "",
        "from app.core.visualization import generate_visualizations",
        "",
        "plot_files, viz_code, log = generate_visualizations(df, output_dir, graph_count)",
        "print(log)",
        "",
        "# Созданные файлы:",
    ]
    lines.extend(f"#   {name}" for name in plot_files)
    return "\n".join(lines)

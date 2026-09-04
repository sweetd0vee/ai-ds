"""Этапы пайплайна анализа. Логика каждого шага совпадает с прежним монолитом."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from .data_analysis import format_calculation_code_reference
from .loaders import load_dataframe, load_tables, tables_meta
from .pipeline_helpers import (
    job_file_entries,
    join_named_blocks,
    refresh_table_summaries,
    run_all_visualizations,
    run_llm_analysis,
    save_analysis_frame,
    save_analysis_reports,
    save_final_report,
    save_text,
    split_graph_count,
    structure_and_analyze,
    truncate,
)
from .plots_export import ensure_plots_report_docx
from .quality_export import build_quality_xlsx
from .relations import detect_relations, format_relations_report, relations_hypotheses
from .reports import build_final_report
from .structure_export import build_structure_xlsx
from ..config import PREVIEW_ROWS
from ..jobs import JobStore


@dataclass
class PipelineContext:
    job_id: str
    store: JobStore
    job: object
    output_dir: Path
    graph_count: int
    analyst: object
    state: dict = field(default_factory=dict)
    tables: list = field(default_factory=list)
    table_summaries: list = field(default_factory=list)
    packaged: list = field(default_factory=list)
    relations: dict = field(default_factory=dict)
    relations_raw: str = ""
    quality_report_raw: str = ""
    correlations_raw: str = ""
    insights_report_raw: str = ""
    discovery_brief: str = ""
    discovery_raw: str = ""
    python_hypotheses: list = field(default_factory=list)
    metrics_results_raw: str = ""
    analysis_summary: str = ""
    hypotheses: list = field(default_factory=list)
    hypotheses_raw: str = ""
    plot_files: list = field(default_factory=list)
    plot_details: list = field(default_factory=list)
    viz_code: str = ""
    viz_log: str = ""

    @property
    def filename(self) -> str:
        return self.job.filename

    @property
    def n_tables(self) -> int:
        return len(self.tables)

    @property
    def first(self):
        return self.tables[0]

    @property
    def first_analysis(self):
        return self.packaged[0][1]


async def step_prepare(ctx: PipelineContext):
    entries = job_file_entries(ctx.job)
    n_files = len(entries)
    await ctx.store.update(
        ctx.job_id, "preparing", 5,
        "Загрузка файлов" if n_files > 1 else "Загрузка файла",
    )
    if entries:
        ctx.tables = await asyncio.to_thread(load_tables, entries)
    else:
        df_single = await asyncio.to_thread(load_dataframe, ctx.job.file_path)
        ctx.tables = [{
            "id": "data",
            "name": ctx.job.filename or Path(ctx.job.file_path).name,
            "filename": ctx.job.filename or Path(ctx.job.file_path).name,
            "sheet": None,
            "path": ctx.job.file_path,
            "rows": int(df_single.shape[0]),
            "cols": int(df_single.shape[1]),
            "columns": [str(c) for c in df_single.columns],
            "df": df_single,
        }]

    ctx.table_summaries = tables_meta(ctx.tables, PREVIEW_ROWS)
    ctx.relations = await asyncio.to_thread(detect_relations, ctx.tables)
    if ctx.n_tables > 1:
        await ctx.store.update(
            ctx.job_id, "preparing", 8,
            f"Поиск связей между {ctx.n_tables} таблицами",
            partial={
                "tables": ctx.table_summaries,
                "table_count": ctx.n_tables,
                "relations": ctx.relations,
            },
        )

    if not ctx.tables or all(t["df"] is None or t["df"].empty for t in ctx.tables):
        raise ValueError("Не удалось загрузить данные или файл пуст")

    ctx.relations_raw = format_relations_report(ctx.relations)
    first = ctx.first
    ctx.state["preview"] = first["df"].head(PREVIEW_ROWS).fillna("").astype(str).to_dict(orient="records")
    ctx.state["columns"] = [str(c) for c in first["df"].columns]
    ctx.state["shape"] = [first["rows"], first["cols"]]
    ctx.state["graph_count"] = ctx.graph_count
    ctx.state["tables"] = ctx.table_summaries
    ctx.state["table_count"] = ctx.n_tables
    ctx.state["relations"] = ctx.relations
    ctx.state["relations_raw"] = ctx.relations_raw
    await asyncio.to_thread(save_text, ctx.output_dir / "relations.txt", ctx.relations_raw)
    await ctx.store.update(
        ctx.job_id, "preparing", 10,
        f"Загружено таблиц: {ctx.n_tables}" if ctx.n_tables > 1 else "Данные загружены",
        partial=ctx.state,
    )


async def step_structure(ctx: PipelineContext):
    await ctx.store.update(ctx.job_id, "structure_analysis", 18, "Анализ структуры данных (Python)")
    ctx.packaged = list(await asyncio.gather(*[
        asyncio.to_thread(structure_and_analyze, table) for table in ctx.tables
    ]))

    ctx.table_summaries = refresh_table_summaries(ctx.table_summaries, ctx.packaged)
    frames = {table["id"]: analysis["df_processed"] for table, analysis in ctx.packaged}
    analysis_path = ctx.output_dir.parent / "analysis_df.pkl"
    await asyncio.to_thread(save_analysis_frame, analysis_path, frames)
    ctx.job.analysis_path = str(analysis_path)
    ctx.store.persist(ctx.job)

    first_analysis = ctx.first_analysis
    ctx.state.update({
        "tables": ctx.table_summaries,
        "data_structure": first_analysis["parsed_structure"] if ctx.n_tables == 1 else None,
        "data_structure_raw": first_analysis["structure_raw"] if ctx.n_tables == 1 else None,
    })
    await asyncio.to_thread(
        build_structure_xlsx,
        first_analysis["parsed_structure"],
        ctx.output_dir / "data_structure.xlsx",
    )
    await ctx.store.update(ctx.job_id, "structure_analysis", 25, "Структура определена", partial=ctx.state)


async def step_insights(ctx: PipelineContext):
    await ctx.store.update(ctx.job_id, "data_insights", 28, "Качество данных (Python, по таблицам)")
    ctx.quality_report_raw = join_named_blocks(ctx.packaged, "quality_report_raw")
    ctx.correlations_raw = join_named_blocks(ctx.packaged, "correlations_raw")
    ctx.insights_report_raw = join_named_blocks(ctx.packaged, "insights_report_raw")
    first_analysis = ctx.first_analysis
    if ctx.n_tables == 1:
        ctx.state.update({
            "quality_report": first_analysis["quality_report"],
            "correlations": first_analysis["correlations"],
        })
    ctx.state.update({
        "tables": ctx.table_summaries,
        "quality_report_raw": ctx.quality_report_raw,
        "correlations_raw": ctx.correlations_raw,
        "insights_report_raw": ctx.insights_report_raw,
    })
    await asyncio.gather(
        asyncio.to_thread(save_text, ctx.output_dir / "quality_report.txt", ctx.quality_report_raw),
        asyncio.to_thread(save_text, ctx.output_dir / "correlations.txt", ctx.correlations_raw),
        asyncio.to_thread(
            build_quality_xlsx,
            first_analysis["quality_report"],
            first_analysis["correlations"],
            ctx.output_dir / "quality_insights.xlsx",
            source_file=ctx.filename,
        ),
    )
    await ctx.store.update(ctx.job_id, "data_insights", 30, "Качество готово", partial=ctx.state)


async def step_discovery(ctx: PipelineContext):
    await ctx.store.update(ctx.job_id, "scientific_discovery", 31, "Поиск аномалий и инсайтов (Python)")
    discovery_parts = []
    discovery_raw_parts = []
    python_hypotheses = relations_hypotheses(ctx.relations) if ctx.n_tables > 1 else []
    for table, analysis in ctx.packaged:
        discovery_parts.append(
            f"Таблица «{table['name']}» ({table['rows']}×{table['cols']}):\n{analysis['discovery_brief']}"
        )
        discovery_raw_parts.append(f"=== {table['name']} ===\n{analysis['discovery_raw']}")
        for hyp in analysis["discovery"].get("hypotheses") or []:
            item = dict(hyp)
            if ctx.n_tables > 1:
                item["title"] = f"{table['name']}: {item.get('title') or ''}".strip()
            python_hypotheses.append(item)
    for index, item in enumerate(python_hypotheses, 1):
        item["id"] = index
    ctx.python_hypotheses = python_hypotheses
    ctx.discovery_brief = "\n\n".join(discovery_parts)
    ctx.discovery_raw = "\n\n".join(discovery_raw_parts)
    ctx.state.update({
        "tables": ctx.table_summaries,
        "discovery": ctx.first_analysis["discovery"] if ctx.n_tables == 1 else None,
        "discovery_brief": ctx.discovery_brief,
        "discovery_raw": ctx.discovery_raw,
        "hypotheses": python_hypotheses,
    })
    await asyncio.to_thread(save_text, ctx.output_dir / "discovery_insights.txt", ctx.discovery_raw)
    ctx.state["insights_report_raw"] = ctx.insights_report_raw + "\n\n" + ctx.discovery_raw
    await ctx.store.update(
        ctx.job_id,
        "scientific_discovery",
        34,
        f"Гипотез: {len(python_hypotheses)}",
        partial=ctx.state,
    )


async def step_metrics(ctx: PipelineContext):
    await ctx.store.update(ctx.job_id, "metrics_plan", 36, "План метрик (Python)")
    if not any(analysis["metrics_plan_dict"] for _, analysis in ctx.packaged):
        raise ValueError("Не удалось построить план метрик")
    metrics_plan_raw = join_named_blocks(ctx.packaged, "metrics_plan_raw")
    calculation_code = "\n\n".join(
        format_calculation_code_reference(
            analysis["metrics_plan_dict"] or {},
            table_names=[table["id"]],
        )
        for table, analysis in ctx.packaged
    )
    ctx.metrics_results_raw = join_named_blocks(ctx.packaged, "metrics_results_raw")
    ctx.state.update({
        "tables": ctx.table_summaries,
        "metrics_plan_raw": metrics_plan_raw,
        "metrics_plan_dict": ctx.first_analysis["metrics_plan_dict"] if ctx.n_tables == 1 else {},
        "calculation_code": calculation_code,
        "metrics_results_raw": ctx.metrics_results_raw,
    })
    await asyncio.to_thread(
        save_text,
        ctx.output_dir / "generated_calculation_code.py",
        f"# Встроенный расчёт метрик\n\n{calculation_code}",
    )
    await ctx.store.update(ctx.job_id, "metrics_plan", 38, "План метрик готов", partial=ctx.state)
    await ctx.store.update(ctx.job_id, "metrics_calculation", 55, "Метрики рассчитаны", partial=ctx.state)


async def step_analysis_and_visualizations(ctx: PipelineContext):
    llm_discovery = "\n\n".join(
        f"Таблица «{table['name']}» ({table['rows']}×{table['cols']}):\n"
        f"{truncate(analysis['discovery_brief'], 1600)}"
        for table, analysis in ctx.packaged
    )
    relations_brief = truncate(
        (ctx.relations.get("summary") or "") if ctx.n_tables > 1 else "Одна таблица.",
        600,
    )
    graph_counts = split_graph_count(ctx.graph_count, len(ctx.packaged))

    await ctx.store.update(
        ctx.job_id, "metrics_analysis", 60,
        "Интерпретация инсайтов (LLM) и графики",
    )
    (plot_files, viz_code, viz_log, plot_details), analysis_summary = await asyncio.gather(
        asyncio.to_thread(run_all_visualizations, ctx.packaged, graph_counts, ctx.output_dir),
        run_llm_analysis(ctx.analyst, llm_discovery, relations_brief, ctx.job_id),
    )
    ctx.plot_files = plot_files
    ctx.viz_code = viz_code
    ctx.viz_log = viz_log
    ctx.plot_details = plot_details
    ctx.analysis_summary = analysis_summary
    ctx.hypotheses_raw = ""
    ctx.hypotheses = ctx.python_hypotheses
    ctx.state["analysis_summary"] = analysis_summary
    ctx.state["hypotheses_raw"] = ctx.hypotheses_raw
    ctx.state["hypotheses"] = ctx.hypotheses
    ctx.state["hypotheses_python"] = ctx.python_hypotheses
    await ctx.store.update(ctx.job_id, "metrics_analysis", 65, "Анализ готов", partial=ctx.state)
    await ctx.store.update(
        ctx.job_id,
        "hypotheses_generation",
        72,
        f"Сформулировано гипотез: {len(ctx.hypotheses)}",
        partial=ctx.state,
    )
    await ctx.store.update(ctx.job_id, "viz_generation", 74, f"Построение {ctx.graph_count} графиков (Python)")

    await save_analysis_reports(
        ctx.output_dir,
        analysis_summary,
        source_file=ctx.filename,
        hypotheses=ctx.hypotheses,
        hypotheses_raw=ctx.hypotheses_raw,
    )

    ctx.table_summaries = refresh_table_summaries(ctx.table_summaries, ctx.packaged)
    ctx.state["tables"] = ctx.table_summaries
    ctx.state["viz_code"] = viz_code
    ctx.state["viz_output"] = viz_log
    ctx.state["plot_files"] = plot_files
    ctx.state["plot_details"] = plot_details
    await asyncio.gather(
        asyncio.to_thread(
            save_text,
            ctx.output_dir / "generated_visualization_code.py",
            f"# Автоматическая визуализация\n\n{viz_code}",
        ),
        asyncio.to_thread(
            ensure_plots_report_docx,
            ctx.output_dir,
            plot_files,
            plot_details=plot_details,
            source_file=ctx.filename,
            correlations=ctx.first_analysis["correlations"],
            viz_output=viz_log,
        ),
    )
    await ctx.store.update(
        ctx.job_id, "viz_generation", 82,
        f"Готово {len(plot_files)} графиков",
        partial=ctx.state,
    )


async def step_final_report(ctx: PipelineContext):
    await ctx.store.update(ctx.job_id, "final_report", 86, "Формирование итогового отчёта (Python)")
    first = ctx.first
    final_report = await asyncio.to_thread(
        build_final_report,
        ctx.filename,
        [first["rows"], first["cols"]],
        ctx.metrics_results_raw,
        ctx.analysis_summary,
        ctx.plot_files,
        ctx.graph_count,
        ctx.quality_report_raw,
        ctx.correlations_raw,
        ctx.hypotheses,
        ctx.discovery_raw,
        relations_raw=ctx.relations_raw if ctx.n_tables > 1 else "",
        table_count=ctx.n_tables,
    )
    ctx.state["final_report"] = final_report
    await ctx.store.update(ctx.job_id, "final_report", 92, "Сохранение отчёта", partial=ctx.state)
    await save_final_report(ctx.output_dir, final_report, source_file=ctx.filename)

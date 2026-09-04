"""Вспомогательные функции пайплайна: I/O, анализ одной таблицы, графики."""

from __future__ import annotations

import asyncio
import logging
import pickle
import shutil
from pathlib import Path

from .analysis_export import build_analysis_docx
from .data_analysis import (
    analyze_data_structure,
    build_metrics_plan,
    compute_metrics,
    format_metrics_results,
)
from .data_insights import (
    build_quality_report,
    compute_correlations,
    format_correlations,
    format_quality_report,
)
from .hypotheses_export import build_hypotheses_docx
from .llm import chain_invoke
from .preprocess import preprocess_dates_based_on_llm
from .prompts import DATA_ANALYZE
from .quality_export import format_insights_report
from .report_export import build_report_docx
from .scientific_discovery import (
    discover_insights,
    format_discovery_brief,
    format_discovery_report,
)
from .visualization import generate_visualizations

logger = logging.getLogger(__name__)

ANALYSIS_META_KEYS = (
    ("parsed_structure", "structure"),
    ("structure_raw", "structure_raw"),
    ("quality_report", "quality_report"),
    ("quality_report_raw", "quality_report_raw"),
    ("correlations", "correlations"),
    ("correlations_raw", "correlations_raw"),
    ("discovery", "discovery"),
    ("discovery_brief", "discovery_brief"),
    ("discovery_raw", "discovery_raw"),
    ("metrics_plan_dict", "metrics_plan_dict"),
    ("metrics_plan_raw", "metrics_plan_raw"),
    ("metrics_results_raw", "metrics_results_raw"),
    ("plot_files", "plot_files"),
    ("plot_details", "plot_details"),
    ("viz_code", "viz_code"),
    ("viz_output", "viz_output"),
)


def truncate(text: str, limit: int = 5000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n… (сокращено для LLM)"


def save_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save_analysis_frame(path: Path, frames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump(frames, fh, protocol=4)


def job_file_entries(job) -> list[tuple[str, str]]:
    paths = list(job.file_paths or [])
    if not paths and job.file_path:
        paths = [job.file_path]
    names = list(job.filenames or [])
    entries = []
    for i, path in enumerate(paths):
        name = names[i] if i < len(names) else Path(path).name
        entries.append((path, name))
    return entries


def split_graph_count(total: int, n: int) -> list[int]:
    if n <= 0:
        return []
    base, rem = divmod(max(int(total), 0), n)
    counts = [base] * n
    for i in range(rem):
        counts[i] += 1
    return counts


def join_named_blocks(packaged, key: str) -> str:
    return "\n\n".join(
        f"=== {table['name']} ===\n{analysis[key]}"
        for table, analysis in packaged
    )


async def save_analysis_reports(
    output_dir: Path,
    analysis_summary: str,
    *,
    source_file: str = "",
    hypotheses: list[dict] | None = None,
    hypotheses_raw: str = "",
):
    tasks = [
        asyncio.to_thread(save_text, output_dir / "analysis_summary_report.txt", analysis_summary),
        asyncio.to_thread(
            build_analysis_docx,
            analysis_summary,
            output_dir / "analysis_summary_report.docx",
            source_file=source_file,
        ),
    ]
    if hypotheses is not None:
        tasks.append(
            asyncio.to_thread(
                build_hypotheses_docx,
                hypotheses,
                output_dir / "hypotheses_report.docx",
                source_file=source_file,
                raw_fallback=hypotheses_raw,
            ),
        )
    await asyncio.gather(*tasks)


async def save_final_report(
    output_dir: Path,
    final_report: str,
    *,
    source_file: str = "",
):
    await asyncio.gather(
        asyncio.to_thread(save_text, output_dir / "final_report.txt", final_report),
        asyncio.to_thread(
            build_report_docx,
            final_report,
            output_dir / "final_report.docx",
            source_file=source_file,
        ),
    )


def analyze_one_table(df, parsed_structure: dict) -> dict:
    datetime_candidates = parsed_structure.get("datetime_candidates", [])
    df_processed = preprocess_dates_based_on_llm(df.copy(), datetime_candidates)
    quality_report = build_quality_report(df_processed, parsed_structure)
    correlations = compute_correlations(df_processed, parsed_structure)
    discovery = discover_insights(df_processed, parsed_structure, correlations)
    metrics_plan_dict, metrics_plan_raw = build_metrics_plan(df_processed, parsed_structure)
    if metrics_plan_dict:
        metrics_results = compute_metrics(df_processed, metrics_plan_dict)
        metrics_results_raw = format_metrics_results(metrics_results)
    else:
        metrics_results_raw = ""
    return {
        "df_processed": df_processed,
        "datetime_candidates": datetime_candidates,
        "quality_report": quality_report,
        "quality_report_raw": format_quality_report(quality_report),
        "correlations": correlations,
        "correlations_raw": format_correlations(correlations),
        "insights_report_raw": format_insights_report(quality_report, correlations),
        "discovery": discovery,
        "discovery_brief": format_discovery_brief(discovery),
        "discovery_raw": format_discovery_report(discovery),
        "metrics_plan_dict": metrics_plan_dict,
        "metrics_plan_raw": metrics_plan_raw,
        "metrics_results_raw": metrics_results_raw,
    }


def structure_and_analyze(table: dict) -> tuple[dict, dict]:
    parsed_structure, structure_raw = analyze_data_structure(table["df"])
    if not parsed_structure.get("columns"):
        raise ValueError(f"Не удалось определить структуру: {table['name']}")
    analysis = analyze_one_table(table["df"], parsed_structure)
    analysis["parsed_structure"] = parsed_structure
    analysis["structure_raw"] = structure_raw
    return table, analysis


def attach_analysis_to_meta(meta: dict, analysis: dict) -> dict:
    item = dict(meta)
    for src, dest in ANALYSIS_META_KEYS:
        value = analysis.get(src)
        if dest in ("plot_files", "plot_details"):
            item[dest] = value or []
        elif dest in ("viz_code", "viz_output"):
            item[dest] = value or ""
        elif dest == "structure":
            item[dest] = value or item.get("structure")
        elif dest == "structure_raw":
            item[dest] = value or item.get("structure_raw")
        else:
            item[dest] = value
    return item


def refresh_table_summaries(table_summaries: list[dict], packaged: list) -> list[dict]:
    return [
        attach_analysis_to_meta(meta, analysis)
        for meta, (_, analysis) in zip(table_summaries, packaged)
    ]


def prefix_plot_files(
    tmp_dir: Path,
    dest_dir: Path,
    names: list[str],
    details: list[dict],
    prefix: str,
) -> tuple[list[str], list[dict]]:
    renamed: list[str] = []
    details_by_name = {item.get("filename"): item for item in details}
    new_details: list[dict] = []
    for name in names:
        src = tmp_dir / name
        dest_name = f"{prefix}__{name}" if prefix else name
        dest = dest_dir / dest_name
        if src.exists():
            dest.write_bytes(src.read_bytes())
        renamed.append(dest_name)
        detail = dict(details_by_name.get(name) or {"filename": name})
        detail["filename"] = dest_name
        new_details.append(detail)
    return renamed, new_details


def run_all_visualizations(packaged, graph_counts: list[int], output_dir: Path):
    all_files: list[str] = []
    all_details: list[dict] = []
    logs: list[str] = []
    codes: list[str] = []
    for (table, analysis), n_plots in zip(packaged, graph_counts):
        if n_plots <= 0:
            analysis["plot_files"] = []
            analysis["plot_details"] = []
            continue
        tmp_dir = output_dir / f".plots_{table['id']}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        files, code, log, details = generate_visualizations(
            analysis["df_processed"],
            tmp_dir,
            n_plots,
            correlations=analysis["correlations"],
            parsed_structure=analysis["parsed_structure"],
            discovery=analysis["discovery"],
        )
        prefix = table["id"] if len(packaged) > 1 else ""
        files, details = prefix_plot_files(tmp_dir, output_dir, files, details, prefix)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        analysis["plot_files"] = files
        analysis["plot_details"] = details
        analysis["viz_code"] = code
        analysis["viz_output"] = log
        all_files.extend(files)
        all_details.extend(details)
        logs.append(f"{table['name']}: {log}")
        codes.append(f"# {table['name']}\n{code}")
    return all_files, "\n\n".join(codes), "\n\n".join(logs), all_details


async def run_llm_analysis(analyst, llm_discovery: str, relations_brief: str, job_id: str) -> str:
    try:
        return await chain_invoke(
            DATA_ANALYZE,
            "analysis_summary",
            analyst,
            partial={
                "discovery_brief": truncate(llm_discovery, 3600),
                "relations_brief": relations_brief,
            },
        )
    except Exception:
        logger.exception("LLM analysis failed for job %s, using Python brief", job_id)
        return llm_discovery

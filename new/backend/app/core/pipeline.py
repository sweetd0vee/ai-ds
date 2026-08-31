import asyncio
import logging
import pickle
import shutil
from pathlib import Path

from .analysis_export import build_analysis_docx
from .hypotheses_export import build_hypotheses_docx
from .scientific_discovery import (
    discover_insights,
    format_discovery_brief,
    format_discovery_report,
)
from .report_export import build_report_docx
from .data_analysis import (
    analyze_data_structure,
    build_metrics_plan,
    compute_metrics,
    format_calculation_code_reference,
    format_metrics_results,
)
from .data_insights import (
    build_quality_report,
    compute_correlations,
    format_correlations,
    format_quality_report,
)
from .plots_export import ensure_plots_report_docx
from .quality_export import build_quality_xlsx, format_insights_report
from .loaders import load_dataframe, load_tables, tables_meta
from .llm import chain_invoke, get_llm_analyst
from .preprocess import preprocess_dates_based_on_llm
from .prompts import DATA_ANALYZE
from .relations import (
    detect_relations,
    format_relations_report,
    relations_hypotheses,
)
from .reports import build_final_report
from .structure_export import build_structure_xlsx
from .visualization import generate_visualizations
from ..config import PREVIEW_ROWS
from ..jobs import JobStore

logger = logging.getLogger(__name__)


def _truncate(text: str, limit: int = 5000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n… (сокращено для LLM)"


def _save_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def _save_analysis_reports(
    output_dir: Path,
    analysis_summary: str,
    *,
    source_file: str = "",
    hypotheses: list[dict] | None = None,
    hypotheses_raw: str = "",
):
    tasks = [
        asyncio.to_thread(_save_text, output_dir / "analysis_summary_report.txt", analysis_summary),
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


async def _save_final_report(
    output_dir: Path,
    final_report: str,
    *,
    source_file: str = "",
):
    await asyncio.gather(
        asyncio.to_thread(_save_text, output_dir / "final_report.txt", final_report),
        asyncio.to_thread(
            build_report_docx,
            final_report,
            output_dir / "final_report.docx",
            source_file=source_file,
        ),
    )


def _job_file_entries(job) -> list[tuple[str, str]]:
    paths = list(job.file_paths or [])
    if not paths and job.file_path:
        paths = [job.file_path]
    names = list(job.filenames or [])
    entries = []
    for i, path in enumerate(paths):
        name = names[i] if i < len(names) else Path(path).name
        entries.append((path, name))
    return entries


def _save_analysis_frame(path: Path, frames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump(frames, fh, protocol=4)


def _split_graph_count(total: int, n: int) -> list[int]:
    if n <= 0:
        return []
    base, rem = divmod(max(int(total), 0), n)
    counts = [base] * n
    for i in range(rem):
        counts[i] += 1
    return counts


def _analyze_one_table(df, parsed_structure: dict) -> dict:
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


def _structure_and_analyze(table: dict) -> tuple[dict, dict]:
    parsed_structure, structure_raw = analyze_data_structure(table["df"])
    if not parsed_structure.get("columns"):
        raise ValueError(f"Не удалось определить структуру: {table['name']}")
    analysis = _analyze_one_table(table["df"], parsed_structure)
    analysis["parsed_structure"] = parsed_structure
    analysis["structure_raw"] = structure_raw
    return table, analysis


def _attach_analysis_to_meta(meta: dict, analysis: dict) -> dict:
    item = dict(meta)
    item.update({
        "structure": analysis.get("parsed_structure") or item.get("structure"),
        "structure_raw": analysis.get("structure_raw") or item.get("structure_raw"),
        "quality_report": analysis.get("quality_report"),
        "quality_report_raw": analysis.get("quality_report_raw"),
        "correlations": analysis.get("correlations"),
        "correlations_raw": analysis.get("correlations_raw"),
        "discovery": analysis.get("discovery"),
        "discovery_brief": analysis.get("discovery_brief"),
        "discovery_raw": analysis.get("discovery_raw"),
        "metrics_plan_dict": analysis.get("metrics_plan_dict"),
        "metrics_plan_raw": analysis.get("metrics_plan_raw"),
        "metrics_results_raw": analysis.get("metrics_results_raw"),
        "plot_files": analysis.get("plot_files") or [],
        "plot_details": analysis.get("plot_details") or [],
        "viz_code": analysis.get("viz_code") or "",
        "viz_output": analysis.get("viz_output") or "",
    })
    return item


def _prefix_plot_files(tmp_dir: Path, dest_dir: Path, names: list[str], details: list[dict], prefix: str) -> tuple[list[str], list[dict]]:
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


async def run_analysis_pipeline(job_id: str, store: JobStore):
    job = store.get(job_id)
    file_path = job.file_path
    output_dir = Path(job.output_dir)
    graph_count = job.graph_count
    output_dir.mkdir(parents=True, exist_ok=True)

    state: dict = {}
    analyst = get_llm_analyst(job.analyst_model)

    try:
        entries = _job_file_entries(job)
        n_files = len(entries)
        await store.update(
            job_id, "preparing", 5,
            "Загрузка файлов" if n_files > 1 else "Загрузка файла",
        )
        if entries:
            tables = await asyncio.to_thread(load_tables, entries)
        else:
            df_single = await asyncio.to_thread(load_dataframe, file_path)
            tables = [{
                "id": "data",
                "name": job.filename or Path(file_path).name,
                "filename": job.filename or Path(file_path).name,
                "sheet": None,
                "path": file_path,
                "rows": int(df_single.shape[0]),
                "cols": int(df_single.shape[1]),
                "columns": [str(c) for c in df_single.columns],
                "df": df_single,
            }]

        table_summaries = tables_meta(tables, PREVIEW_ROWS)
        relations = await asyncio.to_thread(detect_relations, tables)
        if len(tables) > 1:
            await store.update(
                job_id, "preparing", 8,
                f"Поиск связей между {len(tables)} таблицами",
                partial={
                    "tables": table_summaries,
                    "table_count": len(tables),
                    "relations": relations,
                },
            )

        if not tables or all(t["df"] is None or t["df"].empty for t in tables):
            raise ValueError("Не удалось загрузить данные или файл пуст")

        relations_raw = format_relations_report(relations)
        first = tables[0]
        state["preview"] = first["df"].head(PREVIEW_ROWS).fillna("").astype(str).to_dict(orient="records")
        state["columns"] = [str(c) for c in first["df"].columns]
        state["shape"] = [first["rows"], first["cols"]]
        state["graph_count"] = graph_count
        state["tables"] = table_summaries
        state["table_count"] = len(tables)
        state["relations"] = relations
        state["relations_raw"] = relations_raw
        await asyncio.to_thread(_save_text, output_dir / "relations.txt", relations_raw)
        await store.update(
            job_id, "preparing", 10,
            f"Загружено таблиц: {len(tables)}" if len(tables) > 1 else "Данные загружены",
            partial=state,
        )

        await store.update(job_id, "structure_analysis", 18, "Анализ структуры данных (Python)")
        packaged = list(await asyncio.gather(*[
            asyncio.to_thread(_structure_and_analyze, table) for table in tables
        ]))

        table_summaries = [
            _attach_analysis_to_meta(meta, analysis)
            for meta, (_, analysis) in zip(table_summaries, packaged)
        ]
        frames = {table["id"]: analysis["df_processed"] for table, analysis in packaged}
        analysis_path = output_dir.parent / "analysis_df.pkl"
        await asyncio.to_thread(_save_analysis_frame, analysis_path, frames)
        job.analysis_path = str(analysis_path)
        store.persist(job)

        first_analysis = packaged[0][1]
        state.update({
            "tables": table_summaries,
            "data_structure": first_analysis["parsed_structure"] if len(tables) == 1 else None,
            "data_structure_raw": first_analysis["structure_raw"] if len(tables) == 1 else None,
        })
        await asyncio.to_thread(
            build_structure_xlsx,
            first_analysis["parsed_structure"],
            output_dir / "data_structure.xlsx",
        )
        await store.update(job_id, "structure_analysis", 25, "Структура определена", partial=state)

        await store.update(job_id, "data_insights", 28, "Качество данных (Python, по таблицам)")
        quality_chunks = []
        corr_chunks = []
        for table, analysis in packaged:
            quality_chunks.append(f"=== {table['name']} ===\n{analysis['quality_report_raw']}")
            corr_chunks.append(f"=== {table['name']} ===\n{analysis['correlations_raw']}")
        quality_report_raw = "\n\n".join(quality_chunks)
        correlations_raw = "\n\n".join(corr_chunks)
        insights_report_raw = "\n\n".join(
            f"=== {table['name']} ===\n{analysis['insights_report_raw']}"
            for table, analysis in packaged
        )
        if len(tables) == 1:
            state.update({
                "quality_report": first_analysis["quality_report"],
                "correlations": first_analysis["correlations"],
            })
        state.update({
            "tables": table_summaries,
            "quality_report_raw": quality_report_raw,
            "correlations_raw": correlations_raw,
            "insights_report_raw": insights_report_raw,
        })
        await asyncio.gather(
            asyncio.to_thread(_save_text, output_dir / "quality_report.txt", quality_report_raw),
            asyncio.to_thread(_save_text, output_dir / "correlations.txt", correlations_raw),
            asyncio.to_thread(
                build_quality_xlsx,
                first_analysis["quality_report"],
                first_analysis["correlations"],
                output_dir / "quality_insights.xlsx",
                source_file=job.filename,
            ),
        )
        await store.update(
            job_id, "data_insights", 30, "Качество готово", partial=state
        )

        await store.update(job_id, "scientific_discovery", 31, "Поиск аномалий и инсайтов (Python)")
        discovery_parts = []
        discovery_raw_parts = []
        python_hypotheses = relations_hypotheses(relations) if len(tables) > 1 else []
        for table, analysis in packaged:
            discovery_parts.append(
                f"Таблица «{table['name']}» ({table['rows']}×{table['cols']}):\n{analysis['discovery_brief']}"
            )
            discovery_raw_parts.append(f"=== {table['name']} ===\n{analysis['discovery_raw']}")
            for hyp in analysis["discovery"].get("hypotheses") or []:
                item = dict(hyp)
                if len(tables) > 1:
                    item["title"] = f"{table['name']}: {item.get('title') or ''}".strip()
                python_hypotheses.append(item)
        for index, item in enumerate(python_hypotheses, 1):
            item["id"] = index
        discovery_brief = "\n\n".join(discovery_parts)
        discovery_raw = "\n\n".join(discovery_raw_parts)
        state.update({
            "tables": table_summaries,
            "discovery": first_analysis["discovery"] if len(tables) == 1 else None,
            "discovery_brief": discovery_brief,
            "discovery_raw": discovery_raw,
            "hypotheses": python_hypotheses,
        })
        await asyncio.to_thread(_save_text, output_dir / "discovery_insights.txt", discovery_raw)
        state["insights_report_raw"] = insights_report_raw + "\n\n" + discovery_raw
        await store.update(
            job_id,
            "scientific_discovery",
            34,
            f"Гипотез: {len(python_hypotheses)}",
            partial=state,
        )

        await store.update(job_id, "metrics_plan", 36, "План метрик (Python)")
        if not any(analysis["metrics_plan_dict"] for _, analysis in packaged):
            raise ValueError("Не удалось построить план метрик")
        metrics_plan_raw = "\n\n".join(
            f"=== {table['name']} ===\n{analysis['metrics_plan_raw']}"
            for table, analysis in packaged
        )
        calculation_code = "\n\n".join(
            format_calculation_code_reference(
                analysis["metrics_plan_dict"] or {},
                table_names=[table["id"]],
            )
            for table, analysis in packaged
        )
        metrics_results_raw = "\n\n".join(
            f"=== {table['name']} ===\n{analysis['metrics_results_raw']}"
            for table, analysis in packaged
        )
        state.update({
            "tables": table_summaries,
            "metrics_plan_raw": metrics_plan_raw,
            "metrics_plan_dict": first_analysis["metrics_plan_dict"] if len(tables) == 1 else {},
            "calculation_code": calculation_code,
            "metrics_results_raw": metrics_results_raw,
        })
        await asyncio.to_thread(
            _save_text,
            output_dir / "generated_calculation_code.py",
            f"# Встроенный расчёт метрик\n\n{calculation_code}",
        )
        await store.update(job_id, "metrics_plan", 38, "План метрик готов", partial=state)
        await store.update(job_id, "metrics_calculation", 55, "Метрики рассчитаны", partial=state)

        llm_discovery = "\n\n".join(
            f"Таблица «{table['name']}» ({table['rows']}×{table['cols']}):\n"
            f"{_truncate(analysis['discovery_brief'], 1600)}"
            for table, analysis in packaged
        )
        relations_brief = _truncate(
            (relations.get("summary") or "") if len(tables) > 1 else "Одна таблица.",
            600,
        )

        graph_counts = _split_graph_count(graph_count, len(packaged))

        def _run_all_visualizations():
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
                files, details = _prefix_plot_files(tmp_dir, output_dir, files, details, prefix)
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

        async def run_llm_analysis():
            try:
                return await chain_invoke(
                    DATA_ANALYZE,
                    "analysis_summary",
                    analyst,
                    partial={
                        "discovery_brief": _truncate(llm_discovery, 3600),
                        "relations_brief": relations_brief,
                    },
                )
            except Exception:
                logger.exception("LLM analysis failed for job %s, using Python brief", job_id)
                return llm_discovery

        await store.update(
            job_id, "metrics_analysis", 60,
            "Интерпретация инсайтов (LLM) и графики",
        )
        (plot_files, viz_code, viz_log, plot_details), analysis_summary = await asyncio.gather(
            asyncio.to_thread(_run_all_visualizations),
            run_llm_analysis(),
        )
        state["analysis_summary"] = analysis_summary
        hypotheses_raw = ""
        hypotheses = python_hypotheses
        state["hypotheses_raw"] = hypotheses_raw
        state["hypotheses"] = hypotheses
        state["hypotheses_python"] = python_hypotheses
        await store.update(job_id, "metrics_analysis", 65, "Анализ готов", partial=state)
        await store.update(
            job_id,
            "hypotheses_generation",
            72,
            f"Сформулировано гипотез: {len(hypotheses)}",
            partial=state,
        )
        await store.update(job_id, "viz_generation", 74, f"Построение {graph_count} графиков (Python)")

        await _save_analysis_reports(
            output_dir,
            analysis_summary,
            source_file=job.filename,
            hypotheses=hypotheses,
            hypotheses_raw=hypotheses_raw,
        )

        table_summaries = [
            _attach_analysis_to_meta(meta, analysis)
            for meta, (_, analysis) in zip(table_summaries, packaged)
        ]
        state["tables"] = table_summaries
        state["viz_code"] = viz_code
        state["viz_output"] = viz_log
        state["plot_files"] = plot_files
        state["plot_details"] = plot_details
        await asyncio.gather(
            asyncio.to_thread(
                _save_text,
                output_dir / "generated_visualization_code.py",
                f"# Автоматическая визуализация\n\n{viz_code}",
            ),
            asyncio.to_thread(
                ensure_plots_report_docx,
                output_dir,
                plot_files,
                plot_details=plot_details,
                source_file=job.filename,
                correlations=first_analysis["correlations"],
                viz_output=viz_log,
            ),
        )
        await store.update(
            job_id, "viz_generation", 82,
            f"Готово {len(plot_files)} графиков",
            partial=state,
        )

        await store.update(job_id, "final_report", 86, "Формирование итогового отчёта (Python)")

        final_report = await asyncio.to_thread(
            build_final_report,
            job.filename,
            [first["rows"], first["cols"]],
            metrics_results_raw,
            analysis_summary,
            plot_files,
            graph_count,
            quality_report_raw,
            correlations_raw,
            hypotheses,
            discovery_raw,
            relations_raw=relations_raw if len(tables) > 1 else "",
            table_count=len(tables),
        )
        state["final_report"] = final_report
        await store.update(job_id, "final_report", 92, "Сохранение отчёта", partial=state)

        await _save_final_report(output_dir, final_report, source_file=job.filename)

        await store.complete(job_id, state)

    except Exception as e:
        logger.exception("Pipeline failed for job %s", job_id)
        await store.fail(job_id, str(e), state)

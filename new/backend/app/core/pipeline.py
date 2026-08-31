import asyncio
import json
import logging
import pickle
from pathlib import Path

from .analysis_export import build_analysis_docx
from .hypotheses import merge_hypotheses, parse_hypotheses
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
from .prompts import DATA_ANALYZE, DATA_HYPOTHESES
from .relations import (
    build_analysis_frame,
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


def _attach_table_structures(table_summaries: list[dict], tables: list[dict]) -> list[dict]:
    by_id = {t["id"]: t for t in tables}
    result = []
    for meta in table_summaries:
        item = dict(meta)
        table = by_id.get(meta["id"])
        if table is not None:
            parsed, raw = analyze_data_structure(table["df"])
            item["structure"] = parsed
            item["structure_raw"] = raw
        result.append(item)
    return result


def _save_analysis_frame(path: Path, df):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump(df, fh, protocol=4)


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

        df, join_plan = await asyncio.to_thread(build_analysis_frame, tables, relations)
        if df is None or df.empty:
            raise ValueError("Не удалось загрузить данные или файл пуст")

        analysis_path = output_dir.parent / "analysis_df.pkl"
        await asyncio.to_thread(_save_analysis_frame, analysis_path, df)
        job.analysis_path = str(analysis_path)
        store.persist(job)

        relations_raw = format_relations_report(relations, join_plan)
        state["preview"] = df.head(PREVIEW_ROWS).fillna("").astype(str).to_dict(orient="records")
        state["columns"] = [str(c) for c in df.columns]
        state["shape"] = list(df.shape)
        state["graph_count"] = graph_count
        state["tables"] = table_summaries
        state["table_count"] = len(tables)
        state["relations"] = relations
        state["join_plan"] = join_plan
        state["relations_raw"] = relations_raw
        state["analysis_source"] = join_plan.get("mode")
        await asyncio.to_thread(_save_text, output_dir / "relations.txt", relations_raw)
        await store.update(
            job_id, "preparing", 10,
            f"Загружено таблиц: {len(tables)}" if len(tables) > 1 else "Данные загружены",
            partial=state,
        )

        await store.update(job_id, "structure_analysis", 18, "Анализ структуры данных (Python)")
        parsed_structure, structure_raw = await asyncio.to_thread(analyze_data_structure, df)
        if not parsed_structure.get("columns"):
            raise ValueError("Не удалось определить структуру данных")

        table_summaries = await asyncio.to_thread(_attach_table_structures, table_summaries, tables)
        state.update({
            "data_structure_raw": structure_raw,
            "data_structure": parsed_structure,
            "tables": table_summaries,
        })
        await asyncio.to_thread(
            build_structure_xlsx,
            parsed_structure,
            output_dir / "data_structure.xlsx",
        )
        await store.update(job_id, "structure_analysis", 25, "Структура определена", partial=state)

        datetime_candidates = parsed_structure.get("datetime_candidates", [])
        df_processed = preprocess_dates_based_on_llm(df.copy(), datetime_candidates)

        await store.update(job_id, "data_insights", 28, "Качество данных и связи (Python)")
        quality_report = await asyncio.to_thread(
            build_quality_report, df_processed, parsed_structure
        )
        correlations = await asyncio.to_thread(
            compute_correlations, df_processed, parsed_structure
        )
        quality_report_raw = format_quality_report(quality_report)
        correlations_raw = format_correlations(correlations)
        insights_report_raw = format_insights_report(quality_report, correlations)
        if relations_raw and len(tables) > 1:
            insights_report_raw = relations_raw + "\n\n" + insights_report_raw
        state.update({
            "quality_report": quality_report,
            "quality_report_raw": quality_report_raw,
            "correlations": correlations,
            "correlations_raw": correlations_raw,
            "insights_report_raw": insights_report_raw,
        })
        await asyncio.gather(
            asyncio.to_thread(_save_text, output_dir / "quality_report.txt", quality_report_raw),
            asyncio.to_thread(_save_text, output_dir / "correlations.txt", correlations_raw),
            asyncio.to_thread(
                build_quality_xlsx,
                quality_report,
                correlations,
                output_dir / "quality_insights.xlsx",
                source_file=job.filename,
            ),
        )
        await store.update(
            job_id, "data_insights", 30, "Качество и связи готовы", partial=state
        )

        await store.update(job_id, "scientific_discovery", 31, "Поиск аномалий и инсайтов (Python)")
        discovery = await asyncio.to_thread(
            discover_insights, df_processed, parsed_structure, correlations
        )
        if len(tables) > 1 and relations.get("summary"):
            highlights = list(discovery.get("highlights") or [])
            highlights.insert(0, {
                "kind": "table_relation",
                "severity": "high" if relations.get("join_links") else "medium",
                "title": "Связи между таблицами",
                "detail": relations["summary"],
            })
            discovery["highlights"] = highlights[:16]
            kind_labels = dict(discovery.get("kind_labels") or {})
            kind_labels["table_relation"] = "Связь таблиц"
            discovery["kind_labels"] = kind_labels
        discovery_brief = format_discovery_brief(discovery)
        if relations_raw and len(tables) > 1:
            discovery_brief = relations_raw + "\n\n" + discovery_brief
        discovery_raw = format_discovery_report(discovery)
        rel_hyps = relations_hypotheses(relations, join_plan) if len(tables) > 1 else []
        python_hypotheses = rel_hyps + (discovery.get("hypotheses") or [])
        for index, item in enumerate(python_hypotheses, 1):
            item["id"] = index
        state.update({
            "discovery": discovery,
            "discovery_brief": discovery_brief,
            "discovery_raw": discovery_raw,
            "hypotheses": python_hypotheses,
        })
        await asyncio.to_thread(
            _save_text, output_dir / "discovery_insights.txt", discovery_raw
        )
        insights_report_raw = (
            format_insights_report(quality_report, correlations)
            + "\n\n"
            + discovery_raw
        )
        state["insights_report_raw"] = insights_report_raw
        await store.update(
            job_id,
            "scientific_discovery",
            34,
            f"Найдено инсайтов: {len(discovery.get('highlights') or [])}, гипотез: {len(python_hypotheses)}",
            partial=state,
        )

        await store.update(job_id, "metrics_plan", 36, "План метрик (Python)")
        metrics_plan_dict, metrics_plan_raw = await asyncio.to_thread(
            build_metrics_plan, df_processed, parsed_structure
        )
        if not metrics_plan_dict:
            raise ValueError("Не удалось построить план метрик")

        state["metrics_plan_raw"] = metrics_plan_raw
        state["metrics_plan_dict"] = metrics_plan_dict
        await store.update(job_id, "metrics_plan", 38, "План метрик готов", partial=state)

        calculation_code = format_calculation_code_reference(
            metrics_plan_dict,
            table_names=[t["id"] for t in tables],
        )
        state["calculation_code"] = calculation_code
        await asyncio.to_thread(
            _save_text,
            output_dir / "generated_calculation_code.py",
            f"# Встроенный расчёт метрик\n\n{calculation_code}",
        )

        await store.update(job_id, "metrics_calculation", 45, "Расчёт метрик (Python)")
        metrics_results = await asyncio.to_thread(
            compute_metrics, df_processed, metrics_plan_dict
        )
        metrics_results_raw = format_metrics_results(metrics_results)
        state["metrics_results_raw"] = metrics_results_raw
        await store.update(job_id, "metrics_calculation", 55, "Метрики рассчитаны", partial=state)

        await store.update(job_id, "metrics_analysis", 60, "Интерпретация инсайтов (LLM)")
        try:
            analysis_summary = await chain_invoke(
                DATA_ANALYZE,
                "analysis_summary",
                analyst,
                partial={
                    "discovery_brief": _truncate(discovery_brief, 7000),
                    "quality_report_raw": _truncate(quality_report_raw, 2500),
                    "correlations_raw": _truncate(correlations_raw, 2500),
                    "relations_brief": _truncate(relations_raw if len(tables) > 1 else "Одна таблица.", 2500),
                },
            )
        except Exception:
            logger.exception("LLM analysis failed for job %s, using Python brief", job_id)
            analysis_summary = discovery_brief
        state["analysis_summary"] = analysis_summary
        await store.update(job_id, "metrics_analysis", 65, "Анализ готов", partial=state)

        await store.update(job_id, "hypotheses_generation", 68, "Уточнение гипотез (LLM)")
        hypotheses_raw = ""
        try:
            hypotheses_llm = get_llm_analyst(job.analyst_model, num_predict=2800)
            hypotheses_raw = await chain_invoke(
                DATA_HYPOTHESES,
                "hypotheses",
                hypotheses_llm,
                partial={
                    "discovery_brief": _truncate(discovery_brief, 5000),
                    "python_hypotheses_json": _truncate(
                        json.dumps(python_hypotheses, ensure_ascii=False, indent=2),
                        7000,
                    ),
                },
            )
            llm_hypotheses = parse_hypotheses(hypotheses_raw)
            hypotheses = merge_hypotheses(python_hypotheses, llm_hypotheses)
        except Exception:
            logger.exception("LLM hypotheses failed for job %s, keeping Python hypotheses", job_id)
            hypotheses = python_hypotheses
        if not hypotheses:
            hypotheses = python_hypotheses
        state["hypotheses_raw"] = hypotheses_raw
        state["hypotheses"] = hypotheses
        state["hypotheses_python"] = python_hypotheses
        await store.update(
            job_id,
            "hypotheses_generation",
            72,
            f"Сформулировано гипотез: {len(hypotheses)}",
            partial=state,
        )

        await store.update(job_id, "viz_generation", 74, f"Построение {graph_count} графиков (Python)")

        async def run_visualization():
            return await asyncio.to_thread(
                generate_visualizations,
                df_processed,
                output_dir,
                graph_count,
                correlations=correlations,
                parsed_structure=parsed_structure,
                discovery=discovery,
            )

        (plot_files, viz_code, viz_log, plot_details), _ = await asyncio.gather(
            run_visualization(),
            _save_analysis_reports(
                output_dir,
                analysis_summary,
                source_file=job.filename,
                hypotheses=hypotheses,
                hypotheses_raw=hypotheses_raw,
            ),
        )

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
                correlations=correlations,
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
            state["shape"],
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

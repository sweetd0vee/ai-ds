"""On-demand сборка и отдача файлов задачи."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from ..jobs import JobStore

logger = logging.getLogger(__name__)

ALLOWED_DOWNLOADS = {
    "final_report.txt", "final_report.docx",
    "analysis_summary_report.txt", "analysis_summary_report.docx",
    "hypotheses_report.docx",
    "hypotheses_report.xlsx",
    "plots_report.docx",
    "generated_calculation_code.py", "generated_visualization_code.py",
    "quality_report.txt", "correlations.txt",
    "quality_insights.xlsx",
    "data_structure.xlsx",
    "relations.txt",
}

MEDIA_TYPES = {
    "data_structure.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "quality_insights.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "final_report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "analysis_summary_report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "hypotheses_report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "hypotheses_report.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "plots_report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def require_job(store: JobStore, job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "Задача не найдена")
    return job


def _job_results(job) -> dict:
    return job.results or {}


def _build_or_500(action: str, job_id: str, builder, kind: str):
    try:
        builder()
    except Exception as exc:
        logger.exception("Failed to build %s for job %s", action, job_id)
        raise HTTPException(500, f"Не удалось сформировать {kind}: {exc}") from exc


async def ensure_download_file(job, filename: str) -> Path:
    file_path = Path(job.output_dir) / filename
    results = _job_results(job)
    job_id = job.id

    if filename == "data_structure.xlsx" and not file_path.exists():
        structure = results.get("data_structure")
        if not structure:
            raise HTTPException(404, "Структура данных не найдена")
        from ..core.structure_export import build_structure_xlsx

        _build_or_500(
            "data_structure.xlsx",
            job_id,
            lambda: build_structure_xlsx(structure, file_path),
            "XLSX",
        )
    elif filename == "quality_insights.xlsx" and not file_path.exists():
        quality = results.get("quality_report")
        correlations = results.get("correlations")
        if not quality or not correlations:
            raise HTTPException(404, "Отчёт о качестве не найден")
        from ..core.quality_export import build_quality_xlsx

        _build_or_500(
            "quality_insights.xlsx",
            job_id,
            lambda: build_quality_xlsx(
                quality,
                correlations,
                file_path,
                source_file=job.filename,
            ),
            "XLSX",
        )
    elif filename == "analysis_summary_report.docx":
        analysis = results.get("analysis_summary")
        if not analysis:
            raise HTTPException(404, "Текст анализа не найден")
        from ..core.analysis_export import build_analysis_docx

        _build_or_500(
            "analysis_summary_report.docx",
            job_id,
            lambda: build_analysis_docx(analysis, file_path, source_file=job.filename),
            "DOCX",
        )
    elif filename in ("hypotheses_report.docx", "hypotheses_report.xlsx"):
        hypotheses = results.get("hypotheses") or []
        raw = results.get("hypotheses_raw") or ""
        if not hypotheses and not raw:
            raise HTTPException(404, "Гипотезы не найдены")
        from ..core.hypotheses_export import build_hypotheses_docx, build_hypotheses_xlsx

        kind = "XLSX" if filename.endswith(".xlsx") else "DOCX"

        def _build_hypotheses():
            if filename.endswith(".xlsx"):
                build_hypotheses_xlsx(
                    hypotheses,
                    file_path,
                    source_file=job.filename,
                    raw_fallback=raw,
                )
            else:
                build_hypotheses_docx(
                    hypotheses,
                    file_path,
                    source_file=job.filename,
                    raw_fallback=raw,
                )

        _build_or_500(filename, job_id, _build_hypotheses, kind)
    elif filename == "plots_report.docx":
        plot_files = results.get("plot_files") or []
        if not plot_files:
            raise HTTPException(404, "Графики не найдены")

        from ..core.plots_export import ensure_plots_report_docx

        parsed = results.get("data_structure") or {}
        try:
            await asyncio.to_thread(
                ensure_plots_report_docx,
                Path(job.output_dir),
                plot_files,
                plot_details=results.get("plot_details"),
                source_file=job.filename,
                correlations=results.get("correlations"),
                viz_output=results.get("viz_output", ""),
                dataset_path=job.file_path,
                datetime_candidates=parsed.get("datetime_candidates") or [],
            )
        except Exception as exc:
            logger.exception("Failed to build plots_report.docx for job %s", job_id)
            raise HTTPException(500, f"Не удалось сформировать DOCX: {exc}") from exc
    elif filename == "final_report.docx":
        report = results.get("final_report")
        if not report:
            raise HTTPException(404, "Итоговый отчёт не найден")
        from ..core.report_export import build_report_docx

        _build_or_500(
            "final_report.docx",
            job_id,
            lambda: build_report_docx(report, file_path, source_file=job.filename),
            "DOCX",
        )
    elif not file_path.exists():
        raise HTTPException(404, "Файл не найден")

    return file_path


def file_response(file_path: Path, filename: str) -> FileResponse:
    return FileResponse(
        file_path,
        filename=filename,
        media_type=MEDIA_TYPES.get(filename),
    )

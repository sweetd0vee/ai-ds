import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse

from ..config import JOBS_DIR, settings
from ..core.pipeline import run_analysis_pipeline
from ..jobs import JobStore
from ..core.sandbox import run_sandbox_code
from ..models import AppConfigResponse, JobCreateResponse, JobStatusResponse, RunCodeRequest, RunCodeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")
job_store = JobStore()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/config", response_model=AppConfigResponse)
async def get_app_config():
    return AppConfigResponse(
        analyst_models=settings.analyst_models,
        default_analyst_model=settings.analyst_model,
    )


@router.post("/analyze", response_model=JobCreateResponse)
async def start_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    graph_count: int = Form(20),
    analyst_model: str | None = Form(None),
):
    if not file.filename:
        raise HTTPException(400, "Файл не указан")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".csv", ".xlsx"):
        raise HTTPException(400, "Поддерживаются только .csv и .xlsx")

    if graph_count not in (10, 15, 20, 30):
        raise HTTPException(400, "graph_count: 10, 15, 20 или 30")

    model = (analyst_model or settings.analyst_model).strip()
    if model not in settings.analyst_models:
        raise HTTPException(400, f"Недопустимая модель. Доступны: {', '.join(settings.analyst_models)}")

    try:
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        job = job_store.create("", "", file.filename, graph_count=graph_count, analyst_model=model)
        job_dir = JOBS_DIR / job.id
        job_dir.mkdir(parents=True, exist_ok=True)

        input_path = job_dir / f"input{ext}"
        content = await file.read()
        input_path.write_bytes(content)

        output_dir = job_dir / "output"
        output_dir.mkdir(exist_ok=True)

        job.file_path = str(input_path)
        job.output_dir = str(output_dir)
        job_store.persist(job)

        background_tasks.add_task(run_analysis_pipeline, job.id, job_store)

        return JobCreateResponse(
            job_id=job.id,
            filename=file.filename,
            message="Анализ запущен",
            graph_count=graph_count,
        )
    except Exception as exc:
        logger.exception("Failed to start analysis")
        raise HTTPException(500, f"Не удалось запустить анализ: {exc}") from exc


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Задача не найдена")

    return JobStatusResponse(**job_store.to_dict(job))


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Задача не найдена")

    queue = job_store.subscribe(job_id)

    async def event_generator():
        try:
            yield f"data: {json.dumps(job_store.to_dict(job), ensure_ascii=False)}\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    if payload["status"] in ("completed", "failed"):
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            job_store.unsubscribe(job_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/jobs/{job_id}/plots/{filename}")
async def get_plot(job_id: str, filename: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Задача не найдена")

    if not filename.startswith("plot_") or not filename.endswith(".png"):
        raise HTTPException(400, "Недопустимое имя файла")

    plot_path = Path(job.output_dir) / filename
    if not plot_path.exists():
        raise HTTPException(404, "График не найден")

    return FileResponse(plot_path, media_type="image/png", filename=filename)


@router.post("/jobs/{job_id}/run-code", response_model=RunCodeResponse)
async def run_job_code(job_id: str, body: RunCodeRequest):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Задача не найдена")

    if not job.file_path:
        raise HTTPException(400, "Файл задачи не найден")

    results = job.results or {}
    datetime_candidates = (
        results.get("data_structure", {}).get("datetime_candidates") or []
    )
    metrics_plan = results.get("metrics_plan_dict") or {}

    payload = await asyncio.to_thread(
        run_sandbox_code,
        body.code,
        job.file_path,
        datetime_candidates,
        metrics_plan,
    )
    return RunCodeResponse(**payload)


@router.get("/jobs/{job_id}/download/{filename}")
async def download_file(job_id: str, filename: str):
    allowed = {
        "final_report.txt", "final_report.docx",
        "analysis_summary_report.txt", "analysis_summary_report.docx",
        "hypotheses_report.docx",
        "plots_report.docx",
        "generated_calculation_code.py", "generated_visualization_code.py",
        "quality_report.txt", "correlations.txt",
        "quality_insights.xlsx",
        "data_structure.xlsx",
    }
    if filename not in allowed:
        raise HTTPException(400, "Файл недоступен для скачивания")

    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Задача не найдена")

    file_path = Path(job.output_dir) / filename
    if filename == "data_structure.xlsx" and not file_path.exists():
        structure = job.results.get("data_structure")
        if not structure:
            raise HTTPException(404, "Структура данных не найдена")
        from ..core.structure_export import build_structure_xlsx

        try:
            build_structure_xlsx(structure, file_path)
        except Exception as exc:
            logger.exception("Failed to build data_structure.xlsx for job %s", job_id)
            raise HTTPException(500, f"Не удалось сформировать XLSX: {exc}") from exc
    elif filename == "quality_insights.xlsx" and not file_path.exists():
        quality = job.results.get("quality_report")
        correlations = job.results.get("correlations")
        if not quality or not correlations:
            raise HTTPException(404, "Отчёт о качестве не найден")
        from ..core.quality_export import build_quality_xlsx

        try:
            build_quality_xlsx(
                quality,
                correlations,
                file_path,
                source_file=job.filename,
            )
        except Exception as exc:
            logger.exception("Failed to build quality_insights.xlsx for job %s", job_id)
            raise HTTPException(500, f"Не удалось сформировать XLSX: {exc}") from exc
    elif filename == "analysis_summary_report.docx":
        analysis = job.results.get("analysis_summary")
        if not analysis:
            raise HTTPException(404, "Текст анализа не найден")
        from ..core.analysis_export import build_analysis_docx

        try:
            build_analysis_docx(analysis, file_path, source_file=job.filename)
        except Exception as exc:
            logger.exception("Failed to build analysis_summary_report.docx for job %s", job_id)
            raise HTTPException(500, f"Не удалось сформировать DOCX: {exc}") from exc
    elif filename == "hypotheses_report.docx":
        hypotheses = job.results.get("hypotheses") or []
        raw = job.results.get("hypotheses_raw") or ""
        if not hypotheses and not raw:
            raise HTTPException(404, "Гипотезы не найдены")
        from ..core.hypotheses_export import build_hypotheses_docx

        try:
            build_hypotheses_docx(
                hypotheses,
                file_path,
                source_file=job.filename,
                raw_fallback=raw,
            )
        except Exception as exc:
            logger.exception("Failed to build hypotheses_report.docx for job %s", job_id)
            raise HTTPException(500, f"Не удалось сформировать DOCX: {exc}") from exc
    elif filename == "plots_report.docx":
        plot_files = job.results.get("plot_files") or []
        if not plot_files:
            raise HTTPException(404, "Графики не найдены")

        from ..core.plots_export import ensure_plots_report_docx

        parsed = job.results.get("data_structure") or {}
        try:
            await asyncio.to_thread(
                ensure_plots_report_docx,
                Path(job.output_dir),
                plot_files,
                plot_details=job.results.get("plot_details"),
                source_file=job.filename,
                correlations=job.results.get("correlations"),
                viz_output=job.results.get("viz_output", ""),
                dataset_path=job.file_path,
                datetime_candidates=parsed.get("datetime_candidates") or [],
            )
        except Exception as exc:
            logger.exception("Failed to build plots_report.docx for job %s", job_id)
            raise HTTPException(500, f"Не удалось сформировать DOCX: {exc}") from exc
    elif filename == "final_report.docx":
        report = job.results.get("final_report")
        if not report:
            raise HTTPException(404, "Итоговый отчёт не найден")
        from ..core.report_export import build_report_docx

        try:
            build_report_docx(report, file_path, source_file=job.filename)
        except Exception as exc:
            logger.exception("Failed to build final_report.docx for job %s", job_id)
            raise HTTPException(500, f"Не удалось сформировать DOCX: {exc}") from exc
    elif not file_path.exists():
        raise HTTPException(404, "Файл не найден")

    media_types = {
        "data_structure.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "quality_insights.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "final_report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "analysis_summary_report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "hypotheses_report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "plots_report.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return FileResponse(
        file_path,
        filename=filename,
        media_type=media_types.get(filename),
    )

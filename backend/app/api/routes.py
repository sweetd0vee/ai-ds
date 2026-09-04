import asyncio
import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse

from .artifacts import (
    ALLOWED_DOWNLOADS,
    ensure_download_file,
    file_response,
    require_job,
)
from ..config import JOBS_DIR, settings
from ..core.hypotheses import append_auditor_hypothesis
from ..core.hypotheses_export import (
    build_hypotheses_docx,
    build_hypotheses_xlsx,
    filter_hypotheses_by_ids,
)
from ..core.loaders import ALLOWED_EXTS, MAX_UPLOAD_FILES
from ..core.pipeline import run_analysis_pipeline
from ..core.sandbox import run_sandbox_code
from ..jobs import JobStore
from ..models import (
    AppConfigResponse,
    HypothesisCreateRequest,
    HypothesesExportRequest,
    JobCreateResponse,
    JobListItem,
    JobListResponse,
    JobStatusResponse,
    RunCodeRequest,
    RunCodeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")
job_store = JobStore()


def _display_filename(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{names[0]} +{len(names) - 1}"


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", Path(name).name, flags=re.UNICODE)
    return (cleaned[:160] or "file").strip("._") or "file"


def _collect_uploads(
    files: list[UploadFile] | None,
    file: UploadFile | None,
) -> list[UploadFile]:
    uploads: list[UploadFile] = []
    seen: set[int] = set()
    for item in list(files or []) + ([file] if file is not None else []):
        if item is None or id(item) in seen:
            continue
        seen.add(id(item))
        if item.filename:
            uploads.append(item)
    return uploads


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
    files: list[UploadFile] | None = File(None),
    file: UploadFile | None = File(None),
    graph_count: int = Form(20),
    analyst_model: str | None = Form(None),
):
    uploads = _collect_uploads(files, file)
    if not uploads:
        raise HTTPException(400, "Файлы не указаны")
    if len(uploads) > MAX_UPLOAD_FILES:
        raise HTTPException(400, f"Не больше {MAX_UPLOAD_FILES} файлов за раз")

    for item in uploads:
        ext = Path(item.filename).suffix.lower()
        if ext not in ALLOWED_EXTS:
            raise HTTPException(400, "Поддерживаются только .csv и .xlsx")

    if graph_count not in (10, 15, 20, 30):
        raise HTTPException(400, "graph_count: 10, 15, 20 или 30")

    model = (analyst_model or settings.analyst_model).strip()
    if model not in settings.analyst_models:
        raise HTTPException(400, f"Недопустимая модель. Доступны: {', '.join(settings.analyst_models)}")

    original_names = [item.filename for item in uploads]
    display_name = _display_filename(original_names)

    try:
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        job = job_store.create("", "", display_name, graph_count=graph_count, analyst_model=model)
        job_dir = JOBS_DIR / job.id
        job_dir.mkdir(parents=True, exist_ok=True)
        inputs_dir = job_dir / "inputs"
        inputs_dir.mkdir(exist_ok=True)

        saved_paths: list[str] = []
        for index, item in enumerate(uploads):
            ext = Path(item.filename).suffix.lower()
            dest = inputs_dir / f"{index:02d}_{_safe_filename(item.filename)}"
            if dest.suffix.lower() != ext:
                dest = dest.with_suffix(ext)
            dest.write_bytes(await item.read())
            saved_paths.append(str(dest))

        output_dir = job_dir / "output"
        output_dir.mkdir(exist_ok=True)

        job.file_path = saved_paths[0]
        job.file_paths = saved_paths
        job.filenames = original_names
        job.output_dir = str(output_dir)
        job_store.persist(job)

        background_tasks.add_task(run_analysis_pipeline, job.id, job_store)

        return JobCreateResponse(
            job_id=job.id,
            filename=display_name,
            filenames=original_names,
            message="Анализ запущен",
            graph_count=graph_count,
        )
    except Exception as exc:
        logger.exception("Failed to start analysis")
        raise HTTPException(500, f"Не удалось запустить анализ: {exc}") from exc


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs():
    items: list[JobListItem] = []
    for job in job_store.list_all():
        shape = (job.results or {}).get("shape")
        rows = cols = None
        if isinstance(shape, (list, tuple)) and len(shape) >= 2:
            rows, cols = int(shape[0]), int(shape[1])
        items.append(
            JobListItem(
                job_id=job.id,
                filename=job.filename,
                filenames=job.filenames or ([job.filename] if job.filename else []),
                status=job.status,
                progress=job.progress,
                graph_count=job.graph_count,
                analyst_model=job.analyst_model,
                created_at=job.created_at,
                updated_at=job.updated_at,
                rows=rows,
                cols=cols,
            )
        )
    return JobListResponse(jobs=items)


@router.delete("/jobs")
async def clear_jobs():
    deleted = job_store.delete_all()
    return {"deleted": deleted}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    if not job_store.delete(job_id):
        raise HTTPException(404, "Задача не найдена")
    return {"job_id": job_id}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = require_job(job_store, job_id)
    return JobStatusResponse(**job_store.to_dict(job))


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(job_id: str):
    job = require_job(job_store, job_id)
    queue = job_store.subscribe(job_id)

    async def event_generator():
        try:
            yield f"data: {json.dumps(job_store.to_dict(job), ensure_ascii=False, default=str)}\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
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
    job = require_job(job_store, job_id)

    if not filename.startswith("plot_") or not filename.endswith(".png"):
        raise HTTPException(400, "Недопустимое имя файла")

    plot_path = Path(job.output_dir) / filename
    if not plot_path.exists():
        raise HTTPException(404, "График не найден")

    return FileResponse(plot_path, media_type="image/png", filename=filename)


@router.post("/jobs/{job_id}/run-code", response_model=RunCodeResponse)
async def run_job_code(job_id: str, body: RunCodeRequest):
    job = require_job(job_store, job_id)

    if not job.file_path and not job.file_paths:
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
        file_paths=job.file_paths or None,
        filenames=job.filenames or None,
        analysis_path=job.analysis_path or None,
    )
    return RunCodeResponse(**payload)


@router.post("/jobs/{job_id}/hypotheses", response_model=JobStatusResponse)
async def add_hypothesis(job_id: str, body: HypothesisCreateRequest):
    job = require_job(job_store, job_id)
    if job.status in ("running", "pending"):
        raise HTTPException(409, "Дождитесь окончания анализа, затем добавьте гипотезу")

    existing = (job.results or {}).get("hypotheses") or []
    try:
        hypotheses, _created = append_auditor_hypothesis(existing, body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    updated = await job_store.patch_results(job_id, {"hypotheses": hypotheses})
    if not updated:
        raise HTTPException(404, "Задача не найдена")
    return JobStatusResponse(**job_store.to_dict(updated))


@router.post("/jobs/{job_id}/hypotheses/export")
async def export_hypotheses(job_id: str, body: HypothesesExportRequest):
    job = require_job(job_store, job_id)

    hypotheses = job.results.get("hypotheses") or [] if job.results else []
    raw = job.results.get("hypotheses_raw") or "" if job.results else ""
    if not hypotheses and not raw:
        raise HTTPException(404, "Гипотезы не найдены")

    if hypotheses:
        if not body.ids:
            raise HTTPException(400, "Выберите хотя бы одну гипотезу")
        selected = filter_hypotheses_by_ids(hypotheses, body.ids)
        if not selected:
            raise HTTPException(400, "Среди выбранных нет доступных гипотез")
    else:
        selected = []

    filename = "hypotheses_report.xlsx" if body.format == "xlsx" else "hypotheses_report.docx"
    file_path = Path(job.output_dir) / filename
    try:
        if body.format == "xlsx":
            build_hypotheses_xlsx(
                selected,
                file_path,
                source_file=job.filename,
                raw_fallback=raw,
            )
        else:
            build_hypotheses_docx(
                selected,
                file_path,
                source_file=job.filename,
                raw_fallback=raw,
            )
    except Exception as exc:
        logger.exception("Failed to export hypotheses %s for job %s", body.format, job_id)
        raise HTTPException(500, f"Не удалось сформировать файл: {exc}") from exc

    media_types = {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return FileResponse(file_path, filename=filename, media_type=media_types[body.format])


@router.get("/jobs/{job_id}/download/{filename}")
async def download_file(job_id: str, filename: str):
    if filename not in ALLOWED_DOWNLOADS:
        raise HTTPException(400, "Файл недоступен для скачивания")

    job = require_job(job_store, job_id)
    file_path = await ensure_download_file(job, filename)
    return file_response(file_path, filename)

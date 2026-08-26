import asyncio
import json
import logging
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import JOBS_DIR
from .core.utils import convert_numpy_types

logger = logging.getLogger(__name__)


@dataclass
class Job:
    id: str
    file_path: str
    output_dir: str
    filename: str
    graph_count: int = 20
    analyst_model: str = "qwen3.8:27b"
    status: str = "pending"
    step: str = "pending"
    progress: int = 0
    message: str = "Ожидание запуска"
    error: str | None = None
    results: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class JobStore:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._listeners: dict[str, list[asyncio.Queue]] = {}
        self._load_all_from_disk()

    @staticmethod
    def _state_path(job_id: str) -> Path:
        return JOBS_DIR / job_id / "job_state.json"

    def _save_to_disk(self, job: Job):
        try:
            path = self._state_path(job.id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(convert_numpy_types(asdict(job)), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save job %s", job.id)

    def _load_from_disk(self, job_id: str) -> Job | None:
        path = self._state_path(job_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                data.setdefault("analyst_model", "qwen3.8:27b")
                if "results" in data:
                    data["results"] = JobStore._normalize_results(data.get("results")) or {}
                return Job(**data)
            except Exception:
                logger.exception("Failed to load job state %s", job_id)

        job_dir = JOBS_DIR / job_id
        if not job_dir.is_dir():
            return None

        input_files = sorted(job_dir.glob("input.*"))
        if not input_files:
            return None

        output_dir = job_dir / "output"
        output_dir.mkdir(exist_ok=True)
        return Job(
            id=job_id,
            file_path=str(input_files[0]),
            output_dir=str(output_dir),
            filename=input_files[0].name,
            status="unknown",
            message="Восстановлено с диска",
        )

    def _load_all_from_disk(self):
        if not JOBS_DIR.exists():
            return
        for job_dir in JOBS_DIR.iterdir():
            if not job_dir.is_dir():
                continue
            job = self._load_from_disk(job_dir.name)
            if job:
                self._jobs[job.id] = job

    def create(
        self,
        file_path: str,
        output_dir: str,
        filename: str,
        graph_count: int = 20,
        analyst_model: str = "qwen3.8:27b",
    ) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            file_path=file_path,
            output_dir=output_dir,
            filename=filename,
            graph_count=graph_count,
            analyst_model=analyst_model,
        )
        self._jobs[job_id] = job
        self._save_to_disk(job)
        return job

    def list_all(self) -> list[Job]:
        self._load_all_from_disk()
        jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs

    def delete(self, job_id: str) -> bool:
        job_dir = JOBS_DIR / job_id
        existed = job_id in self._jobs or job_dir.is_dir()
        self._jobs.pop(job_id, None)
        self._listeners.pop(job_id, None)
        if job_dir.is_dir():
            shutil.rmtree(job_dir)
        return existed

    def delete_all(self) -> int:
        self._load_all_from_disk()
        count = len(self._jobs)
        self._jobs.clear()
        self._listeners.clear()
        if JOBS_DIR.exists():
            for job_dir in JOBS_DIR.iterdir():
                if job_dir.is_dir():
                    shutil.rmtree(job_dir, ignore_errors=True)
        return count

    def get(self, job_id: str) -> Job | None:
        job = self._jobs.get(job_id)
        if job:
            return job
        job = self._load_from_disk(job_id)
        if job:
            self._jobs[job_id] = job
        return job

    def subscribe(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._listeners.setdefault(job_id, []).append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        listeners = self._listeners.get(job_id, [])
        if queue in listeners:
            listeners.remove(queue)

    async def _notify(self, job_id: str):
        job = self._jobs.get(job_id)
        if not job:
            return
        payload = self.to_dict(job)
        for queue in self._listeners.get(job_id, []):
            await queue.put(payload)

    @staticmethod
    def _normalize_results(results: dict | None) -> dict | None:
        if not results:
            return results
        if results.get("data_structure") or not results.get("parsed_data_structure"):
            return results
        return {**results, "data_structure": results["parsed_data_structure"]}

    @staticmethod
    def _enrich_results(results: dict | None) -> dict | None:
        results = JobStore._normalize_results(results)
        if not results:
            return results
        raw = results.get("hypotheses_raw")
        if raw and not results.get("hypotheses"):
            from .core.hypotheses import parse_hypotheses

            reparsed = parse_hypotheses(raw)
            if reparsed:
                return {**results, "hypotheses": reparsed}
        return results

    @staticmethod
    def to_dict(job: Job) -> dict:
        return {
            "job_id": job.id,
            "status": job.status,
            "step": job.step,
            "progress": job.progress,
            "message": job.message,
            "error": job.error,
            "filename": job.filename,
            "graph_count": job.graph_count,
            "analyst_model": job.analyst_model,
            "results": JobStore._enrich_results(job.results or None),
        }

    async def update(
        self,
        job_id: str,
        step: str,
        progress: int,
        message: str,
        partial: dict | None = None,
    ):
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "running"
            job.step = step
            job.progress = progress
            job.message = message
            if partial:
                job.results = {**job.results, **partial}
            job.updated_at = datetime.utcnow().isoformat()
            self._save_to_disk(job)
        await self._notify(job_id)

    async def complete(self, job_id: str, results: dict):
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "completed"
            job.step = "completed"
            job.progress = 100
            job.message = "Анализ завершён"
            job.results = results
            job.updated_at = datetime.utcnow().isoformat()
            self._save_to_disk(job)
        await self._notify(job_id)

    async def fail(self, job_id: str, error: str, partial_results: dict | None = None):
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.error = error
            job.message = f"Ошибка: {error}"
            if partial_results:
                job.results = {**job.results, **partial_results}
            job.updated_at = datetime.utcnow().isoformat()
            self._save_to_disk(job)
        await self._notify(job_id)

    def persist(self, job: Job):
        self._jobs[job.id] = job
        self._save_to_disk(job)

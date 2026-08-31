from typing import Any, Literal

from pydantic import BaseModel, Field


class JobCreateResponse(BaseModel):
    job_id: str
    filename: str
    message: str
    graph_count: int = 20


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    step: str
    progress: int
    message: str
    error: str | None = None
    filename: str
    graph_count: int = 20
    analyst_model: str = "qwen3.8:27b"
    results: dict[str, Any] | None = None


class RunCodeRequest(BaseModel):
    code: str


class RunCodeResponse(BaseModel):
    success: bool
    output: str
    error: str | None = None
    warnings: list[str] = []


class JobListItem(BaseModel):
    job_id: str
    filename: str
    status: str
    progress: int = 0
    graph_count: int = 20
    analyst_model: str = "qwen3.8:27b"
    created_at: str
    updated_at: str
    rows: int | None = None
    cols: int | None = None


class JobListResponse(BaseModel):
    jobs: list[JobListItem]


class AppConfigResponse(BaseModel):
    analyst_models: list[str]
    default_analyst_model: str


class HypothesesExportRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
    format: Literal["xlsx", "docx"] = "xlsx"

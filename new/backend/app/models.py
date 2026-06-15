from typing import Any

from pydantic import BaseModel


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
    analyst_model: str = "qwen3:8b"
    results: dict[str, Any] | None = None


class RunCodeRequest(BaseModel):
    code: str


class RunCodeResponse(BaseModel):
    success: bool
    output: str
    error: str | None = None
    warnings: list[str] = []


class AppConfigResponse(BaseModel):
    analyst_models: list[str]
    default_analyst_model: str

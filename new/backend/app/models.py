import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class JobCreateResponse(BaseModel):
    job_id: str
    filename: str
    filenames: list[str] = Field(default_factory=list)
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
    filenames: list[str] = Field(default_factory=list)
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
    filenames: list[str] = Field(default_factory=list)
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


class HypothesisCreateRequest(BaseModel):
    title: str = ""
    statement: str
    rationale: str = ""
    verification: str = ""
    columns: list[str] = Field(default_factory=list)
    priority: str = "medium"

    @field_validator("title", "rationale", "verification")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return (value or "").strip()

    @field_validator("statement")
    @classmethod
    def statement_required(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("Укажите формулировку гипотезы")
        return text

    @field_validator("columns", mode="before")
    @classmethod
    def normalize_columns(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

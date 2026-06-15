from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JOBS_DIR = DATA_DIR / "jobs"
PREVIEW_ROWS = 20


class Settings:
    analyst_model: str = "qwen3:8b"
    coder_model: str = "qwen3-coder:latest"
    analyst_models: list[str] = [
        "qwen3:8b",
        "qwen3:4b",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "llama3.2:latest",
        "mistral:latest",
        "gemma3:4b",
    ]
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()

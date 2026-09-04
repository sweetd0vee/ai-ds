from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JOBS_DIR = DATA_DIR / "jobs"
PREVIEW_ROWS = 20


class Settings:
    ollama_base_url: str = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    analyst_model: str = os.environ.get("ANALYST_MODEL", "qwen3.8:27b")
    analyst_models: list[str] = [
        "qwen3.8:27b",
        "qwen3:4b",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "llama3.2:latest",
        "mistral:latest",
        "gemma3:4b",
    ]
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5190,http://127.0.0.1:5190,"
            "http://localhost:5180,http://127.0.0.1:5180,"
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:5174,http://127.0.0.1:5174,"
            "http://localhost:8080,http://127.0.0.1:8080",
        ).split(",")
        if origin.strip()
    ]


settings = Settings()

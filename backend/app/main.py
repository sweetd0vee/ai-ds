import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings, JOBS_DIR

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Электронный Data Scientist API",
    description="Асинхронный анализ CSV/Excel с LLM",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS_DIR.mkdir(parents=True, exist_ok=True)
app.include_router(router)

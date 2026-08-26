from fastapi import FastAPI

from module1.api.routes import router
from module1.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Module 1 — Image Processing + OCR + Structured Product Information Extraction",
)

app.include_router(router)

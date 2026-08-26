from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from module1.core.config import settings
from module1.core.errors import ErrorCode, PipelineError
from module1.models.schemas import (
    ErrorDetail,
    ErrorResponse,
    ExtractionResponse,
    HealthResponse,
)
from module1.services.pipeline import pipeline

router = APIRouter()

_ERROR_RESPONSES: dict[int, dict] = {
    status: {"model": ErrorResponse, "description": code.value}
    for code, status in {
        ErrorCode.EMPTY_FILE: 400,
        ErrorCode.FILE_TOO_LARGE: 413,
        ErrorCode.UNSUPPORTED_FORMAT: 415,
        ErrorCode.INVALID_IMAGE: 422,
        ErrorCode.OCR_UNAVAILABLE: 503,
    }.items()
}


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=settings.version,
        ocr_engine=settings.ocr_engine,
    )


@router.post(
    "/api/v1/extract",
    response_model=ExtractionResponse,
    responses=_ERROR_RESPONSES,
    summary="Extract structured product information from a packaged commodity image",
)
async def extract_product_information(file: UploadFile = File(...)) -> ExtractionResponse | JSONResponse:
    data = await file.read()
    filename = file.filename or ""
    try:
        return await run_in_threadpool(pipeline.run, data, filename)
    except PipelineError as exc:
        payload = ErrorResponse(error=ErrorDetail(code=exc.code.value, message=exc.message))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

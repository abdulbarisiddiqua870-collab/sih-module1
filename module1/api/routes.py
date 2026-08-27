from fastapi import APIRouter, File, Request, UploadFile
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
        ErrorCode.PROCESSING_ERROR: 500,
    }.items()
}

UPLOAD_READ_CHUNK = 64 * 1024
MULTIPART_OVERHEAD_LIMIT = 1024 * 1024


async def _read_upload(file: UploadFile, request: Request) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > settings.max_upload_bytes + MULTIPART_OVERHEAD_LIMIT:
                raise PipelineError(ErrorCode.FILE_TOO_LARGE, "File exceeds the upload limit")
        except ValueError:
            pass
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise PipelineError(ErrorCode.FILE_TOO_LARGE, "File exceeds the upload limit")

    data = bytearray()
    while True:
        chunk = await file.read(UPLOAD_READ_CHUNK)
        if not chunk:
            break
        if len(data) + len(chunk) > settings.max_upload_bytes:
            raise PipelineError(ErrorCode.FILE_TOO_LARGE, "File exceeds the upload limit")
        data.extend(chunk)
    return bytes(data)


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
async def extract_product_information(
    request: Request,
    file: UploadFile = File(...),
) -> ExtractionResponse | JSONResponse:
    try:
        data = await _read_upload(file, request)
        filename = file.filename or ""
        return await run_in_threadpool(pipeline.run, data, filename)
    except PipelineError as exc:
        payload = ErrorResponse(error=ErrorDetail(code=exc.code.value, message=exc.message))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

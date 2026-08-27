from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    EMPTY_FILE = "EMPTY_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    INVALID_IMAGE = "INVALID_IMAGE"
    OCR_UNAVAILABLE = "OCR_UNAVAILABLE"
    PROCESSING_ERROR = "PROCESSING_ERROR"


ERROR_STATUS_CODES: dict[ErrorCode, int] = {
    ErrorCode.EMPTY_FILE: 400,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.UNSUPPORTED_FORMAT: 415,
    ErrorCode.INVALID_IMAGE: 422,
    ErrorCode.OCR_UNAVAILABLE: 503,
    ErrorCode.PROCESSING_ERROR: 500,
}


class PipelineError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = ERROR_STATUS_CODES[code]

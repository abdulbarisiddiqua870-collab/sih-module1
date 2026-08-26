from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DetectionStatus(str, Enum):
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    NOT_APPLICABLE = "not_applicable"
    UNCERTAIN = "uncertain"


PRODUCT_NAME = "product_name"
COMMON_OR_GENERIC_NAME = "common_or_generic_name"
MANUFACTURER_NAME = "manufacturer_name"
MANUFACTURER_ADDRESS = "manufacturer_address"
PACKER_NAME = "packer_name"
PACKER_ADDRESS = "packer_address"
IMPORTER_NAME = "importer_name"
IMPORTER_ADDRESS = "importer_address"
COUNTRY_OF_ORIGIN = "country_of_origin"
NET_QUANTITY = "net_quantity"
MRP = "mrp"
MANUFACTURE_PACK_IMPORT_DATE = "manufacture_pack_import_date"
BEST_BEFORE_USE_BY = "best_before_use_by"
CONSUMER_CARE = "consumer_care"
UNIT_SALE_PRICE = "unit_sale_price"
DIMENSIONS = "dimensions"

KNOWN_FIELDS: frozenset[str] = frozenset(
    {
        PRODUCT_NAME,
        COMMON_OR_GENERIC_NAME,
        MANUFACTURER_NAME,
        MANUFACTURER_ADDRESS,
        PACKER_NAME,
        PACKER_ADDRESS,
        IMPORTER_NAME,
        IMPORTER_ADDRESS,
        COUNTRY_OF_ORIGIN,
        NET_QUANTITY,
        MRP,
        MANUFACTURE_PACK_IMPORT_DATE,
        BEST_BEFORE_USE_BY,
        CONSUMER_CARE,
        UNIT_SALE_PRICE,
        DIMENSIONS,
    }
)


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    ocr_engine: str


class ImageInfo(BaseModel):
    filename: str
    width: int
    height: int
    format: str
    dpi: float | None = None


class QualityInfo(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    blur_score: float = Field(ge=0.0, le=1.0)
    brightness_score: float = Field(ge=0.0, le=1.0)
    contrast_score: float = Field(ge=0.0, le=1.0)
    resolution_ok: bool
    warnings: list[str] = []


class RegionGeometry(BaseModel):
    bounding_box: list[int] | None = Field(default=None, min_length=4, max_length=4)
    region_width_px: int | None = None
    region_height_px: int | None = None
    char_height_px: int | None = None


class FieldResult(RegionGeometry):
    value: str | None = None
    detection_status: DetectionStatus = DetectionStatus.NOT_DETECTED
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence: str | None = None


class UnmappedDetection(RegionGeometry):
    text: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class MetadataInfo(BaseModel):
    ocr_engine: str
    preprocessing_applied: list[str] = []
    processing_time_ms: float = 0.0


class ExtractionResponse(BaseModel):
    success: bool = True
    image: ImageInfo | None = None
    quality: QualityInfo | None = None
    fields: dict[str, FieldResult] = Field(default_factory=dict)
    unmapped_detections: list[UnmappedDetection] = []
    raw_ocr_text: str = ""
    cleaned_ocr_text: str = ""
    metadata: MetadataInfo | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail

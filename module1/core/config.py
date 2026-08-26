from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SIH Module 1"
    version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Upload limits
    max_upload_bytes: int = 20 * 1024 * 1024  # 20 MB
    allowed_extensions: set[str] = {".jpg", ".jpeg", ".png"}

    # Image processing
    max_image_dimension: int = 4096
    min_image_dimension: int = 100

    # OCR
    ocr_engine: str = "tesseract"
    tesseract_lang: str = "eng"
    tesseract_psm: int = 3
    tesseract_cmd: str | None = None
    ocr_orientation_aware: bool = True
    osd_min_confidence: float = 0.5
    orientation_probe_max_side: int = 600

    # Preprocessing
    apply_denoise: bool = True
    apply_clahe: bool = True
    apply_sharpen: bool = True
    apply_deskew: bool = True

    # Paths
    temp_dir: Path = Path("/tmp/sih_module1")

    # Logging
    log_level: str = "INFO"

    model_config = {
        "env_prefix": "SIH_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()

import tempfile
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Patient Medical Timeline API"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/timeline"
    db_echo: bool = False

    # Temporary upload storage (swap for S3/GCS in production)
    upload_dir: Path = Path(tempfile.gettempdir()) / "timeline_uploads"
    max_upload_mb: int = 25
    max_files_per_upload: int = 20

    cors_origins: list[str] = ["http://localhost:3000"]

    # --- OCR ---
    ocr_language: str = "eng"          # tesseract language(s), e.g. "eng+spa"
    ocr_dpi: int = 300                 # rasterization DPI for scanned PDF pages
    ocr_min_text_chars: int = 40       # below this, a PDF page is treated as scanned
    ocr_page_segmentation_mode: int = 6
    tesseract_cmd: str | None = None    # optional explicit path to tesseract.exe
    max_pages_per_file: int = 200

    # --- LLM extraction ---
    llm_provider: Literal["anthropic", "openai", "gemini"] = "anthropic"
    llm_model: str = "claude-sonnet-5-5"   # e.g. "gpt-4o" when llm_provider="openai" or "gemini-2.5-flash" for Gemini
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None
    auth_secret_key: str | None = None
    auth_token_expire_minutes: int = 60
    llm_max_tokens: int = 4096
    llm_timeout_seconds: int = 120
    llm_max_retries: int = 3
    extraction_chunk_chars: int = 12000    # ~3k tokens of source text per LLM call
    extraction_concurrency: int = 3        # parallel LLM calls per record
    max_concurrent_records: int = 2        # records processed at once per worker

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()

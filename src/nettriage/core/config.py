"""Application settings for NetTriage AI — loaded from environment variables."""

import functools
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised typed settings with env-var overrides.

    All configurable values are listed here so the application can start
    with sensible defaults and still be customised via environment variables.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ---- Application ----
    app_name: str = "NetTriage AI"
    environment: str = "dev"

    # ---- DeepSeek LLM ----
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout_seconds: int = 30
    deepseek_max_retries: int = 2

    # ---- Database ----
    database_url: str = "sqlite:///./data/nettriage.db"

    # ---- File storage ----
    upload_dir: Path = Path("./data/uploads")
    export_dir: Path = Path("./data/exports")
    max_upload_mb: int = 20
    max_csv_rows: int = 50000
    csv_chunksize: int = 500

    # ---- Review / confidence thresholds ----
    review_confidence_threshold: float = 0.80
    conflict_score_delta: float = 0.08

    # ---- Logging ----
    log_level: str = "INFO"


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application Settings singleton."""
    return Settings()

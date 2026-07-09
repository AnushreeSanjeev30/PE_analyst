"""Environment-based application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pe_analyst.core.enums import Environment

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Validated application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    app_name: str = "PE-Analyst"

    app_env: Environment = Environment.DEVELOPMENT

    debug: bool = True

    host: str = "127.0.0.1"

    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
    )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    log_level: str = "INFO"

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------

    openai_api_key: str | None = None

    openai_model: str = "gpt-5-mini"

    openai_embedding_model: str = "text-embedding-3-small"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/pe_analyst"
    )

    # ------------------------------------------------------------------
    # Vector Store
    # ------------------------------------------------------------------

    vector_store_provider: str = "pgvector"

    vector_collection_name: str = "pe_analyst_documents"

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    upload_dir: Path = Path("data/uploads")

    processed_data_dir: Path = Path("data/processed")

    max_upload_size_mb: int = Field(
        default=50,
        gt=0,
    )

    # ------------------------------------------------------------------
    # Document Processing
    # ------------------------------------------------------------------

    document_chunk_size: int = Field(
        default=1200,
        gt=0,
    )

    document_chunk_overlap: int = Field(
        default=200,
        ge=0,
    )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    retrieval_top_k: int = Field(
        default=10,
        gt=0,
    )

    rerank_top_k: int = Field(
        default=5,
        gt=0,
    )

    # ------------------------------------------------------------------
    # Agent Workflow
    # ------------------------------------------------------------------

    max_agent_iterations: int = Field(
        default=10,
        gt=0,
    )

    enable_agent_tracing: bool = True

    # ------------------------------------------------------------------
    # External Research
    # ------------------------------------------------------------------

    sec_user_agent: str | None = None

    # ------------------------------------------------------------------
    # LBO Defaults
    # ------------------------------------------------------------------

    default_holding_period_years: int = Field(
        default=5,
        gt=0,
    )

    default_tax_rate: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
    )

    default_interest_rate: float = Field(
        default=0.08,
        ge=0.0,
        le=1.0,
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalize and validate the configured logging level."""

        normalized_value = value.upper()

        allowed_levels = {
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        }

        if normalized_value not in allowed_levels:
            message = (
                f"Invalid LOG_LEVEL '{value}'. "
                f"Expected one of: {sorted(allowed_levels)}."
            )
            raise ValueError(message)

        return normalized_value

    @field_validator("document_chunk_overlap")
    @classmethod
    def validate_chunk_overlap(
        cls,
        value: int,
        info: ValidationInfo,
    ) -> int:
        """Ensure overlap remains smaller than the configured chunk size."""

        chunk_size = info.data.get("document_chunk_size")

        if chunk_size is not None and value >= chunk_size:
            message = (
                "DOCUMENT_CHUNK_OVERLAP must be smaller than "
                "DOCUMENT_CHUNK_SIZE."
            )
            raise ValueError(message)

        return value

    @field_validator("rerank_top_k")
    @classmethod
    def validate_rerank_top_k(
        cls,
        value: int,
        info: ValidationInfo,
    ) -> int:
        """Ensure reranking does not request more items than retrieval."""

        retrieval_top_k = info.data.get("retrieval_top_k")

        if retrieval_top_k is not None and value > retrieval_top_k:
            message = "RERANK_TOP_K cannot exceed RETRIEVAL_TOP_K."
            raise ValueError(message)

        return value

    # ------------------------------------------------------------------
    # Environment Helpers
    # ------------------------------------------------------------------

    @property
    def is_development(self) -> bool:
        """Return whether the application is running in development."""

        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """Return whether the application is running in testing."""

        return self.app_env == Environment.TESTING

    @property
    def is_production(self) -> bool:
        """Return whether the application is running in production."""

        return self.app_env == Environment.PRODUCTION

    # ------------------------------------------------------------------
    # Storage Helpers
    # ------------------------------------------------------------------

    def ensure_directories(self) -> None:
        """Create application-managed storage directories when missing."""

        self.upload_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.processed_data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""

    return Settings()
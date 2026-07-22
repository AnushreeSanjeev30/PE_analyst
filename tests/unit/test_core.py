"""Tests for PE-Analyst core infrastructure."""

import logging

import pytest
from pydantic import ValidationError

from pe_analyst import __version__
from pe_analyst.core.config import Settings
from pe_analyst.core.enums import (
    Environment,
    InvestmentDecision,
    RiskSeverity,
)
from pe_analyst.core.logging import configure_logging, get_logger


def test_package_version() -> None:
    """The package should expose its current version."""

    assert __version__ == "0.1.0"


def test_default_settings() -> None:
    """Settings should provide valid application defaults."""

    settings = Settings(_env_file=None)

    assert settings.app_name == "PE-Analyst"
    assert settings.app_env == Environment.DEVELOPMENT
    assert settings.port == 8000
    assert settings.default_holding_period_years == 5


def test_environment_helpers() -> None:
    """Environment helper properties should reflect the configured environment."""

    settings = Settings(
        _env_file=None,
        app_env=Environment.TESTING,
    )

    assert settings.is_testing is True
    assert settings.is_development is False
    assert settings.is_production is False


def test_invalid_log_level() -> None:
    """Invalid logging levels should fail configuration validation."""

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            log_level="NOT_A_LEVEL",
        )


def test_invalid_chunk_overlap() -> None:
    """Chunk overlap must remain smaller than chunk size."""

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            document_chunk_size=100,
            document_chunk_overlap=100,
        )


def test_invalid_rerank_top_k() -> None:
    """Reranking count cannot exceed retrieval count."""

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            retrieval_top_k=5,
            rerank_top_k=10,
        )


def test_enum_values() -> None:
    """Important domain enums should expose stable serialized values."""

    assert RiskSeverity.CRITICAL.value == "critical"
    assert InvestmentDecision.APPROVE.value == "approve"


def test_ensure_directories(test_settings: Settings) -> None:
    """Managed directories should be created when requested."""

    assert not test_settings.upload_dir.exists()
    assert not test_settings.processed_data_dir.exists()

    test_settings.ensure_directories()

    assert test_settings.upload_dir.exists()
    assert test_settings.processed_data_dir.exists()


def test_logging_configuration(test_settings: Settings) -> None:
    """Logging infrastructure should return standard Python loggers."""

    configure_logging(test_settings)

    logger = get_logger("pe_analyst.tests")

    assert isinstance(logger, logging.Logger)

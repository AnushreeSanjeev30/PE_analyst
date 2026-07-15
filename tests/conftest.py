"""Shared pytest fixtures for PE-Analyst."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from pe_analyst.core.config import Settings
from pe_analyst.core.enums import Environment


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Return isolated application settings for tests."""

    return Settings(
        app_env=Environment.TESTING,
        debug=True,
        upload_dir=tmp_path / "uploads",
        processed_data_dir=tmp_path / "processed",
        openai_api_key=None,
    )


@pytest.fixture
def company_id() -> UUID:
    """Return a random company identifier."""
    return uuid4()


@pytest.fixture
def document_id() -> UUID:
    """Return a random document identifier."""
    return uuid4()
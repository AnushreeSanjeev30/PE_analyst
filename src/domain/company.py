"""
Company domain model.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .common import Entity


class Exchange(StrEnum):
    """
    Supported stock exchanges.
    """

    NASDAQ = "NASDAQ"
    NYSE = "NYSE"
    NSE = "NSE"
    BSE = "BSE"
    LSE = "LSE"
    PRIVATE = "PRIVATE"


class Company(Entity):
    """
    Represents one company under analysis.
    """

    name: str

    ticker: str | None = None

    exchange: Exchange = Exchange.PRIVATE

    industry: str

    headquarters: str

    website: str | None = None

    description: str | None = None

    founded_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
    )

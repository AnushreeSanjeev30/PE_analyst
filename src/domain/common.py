"""
Common domain models and reusable types.

All business entities inherit from Entity.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    """
    Base class for all domain models.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class Entity(DomainModel):
    """
    Base entity shared by all business objects.
    """

    id: UUID = Field(default_factory=uuid4)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


Percentage = Annotated[float, Field(ge=0, le=100)]
ConfidenceScore = Annotated[float, Field(ge=0, le=1)]

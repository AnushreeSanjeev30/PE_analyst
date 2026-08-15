"""Audit-ready models for an end-to-end deal-analysis run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from .types import AgentResponse


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class AgentRunRecord:
    stage: str
    agent_name: str
    status: RunStatus = RunStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    response: AgentResponse | None = None
    error: str | None = None


@dataclass(slots=True)
class DealAnalysisResult:
    run_id: UUID = field(default_factory=uuid4)
    status: RunStatus = RunStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    stages: list[AgentRunRecord] = field(default_factory=list)
    final_recommendation: str | None = None
    error: str | None = None

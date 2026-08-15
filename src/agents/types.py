from dataclasses import dataclass
from typing import Any


@dataclass
class AgentResponse:

    agent_name: str

    summary: str

    confidence: float

    findings: list[str]

    metadata: dict[str, Any]
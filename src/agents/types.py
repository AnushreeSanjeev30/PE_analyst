from dataclasses import dataclass


@dataclass
class AgentResponse:

    agent_name: str

    summary: str

    confidence: float

    findings: list[str]

    metadata: dict
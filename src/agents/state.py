from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:

    company_name: str

    financial_data: dict[str, Any] = field(default_factory=dict)

    ratios: dict[str, float] = field(default_factory=dict)

    valuation: dict[str, Any] = field(default_factory=dict)

    quality: dict[str, Any] = field(default_factory=dict)

    risk: dict[str, Any] = field(default_factory=dict)

    industry: dict[str, Any] = field(default_factory=dict)

    due_diligence: dict[str, Any] = field(default_factory=dict)

    recommendation: dict[str, Any] = field(default_factory=dict)

    conversation_history: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)
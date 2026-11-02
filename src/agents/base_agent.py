from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from .prompts import AGENT_INSTRUCTIONS
from .state import AgentState
from .types import AgentResponse

if TYPE_CHECKING:
    from .narration import Narrative, Narrator


class BaseAgent(ABC):

    narration_max_tokens: int = 900

    def __init__(self, name: str):

        self.name = name

        # Optional LLM narrator. When unset, the agent is fully deterministic.
        self.narrator: Narrator | None = None

    def run(
        self,
        state: AgentState,
    ) -> AgentResponse:

        self.validate(state)

        response = self.execute(state)

        self.narrate(state, response)

        self.update_state(
            state,
            response,
        )

        return response

    def validate(
        self,
        state: AgentState,
    ) -> None:

        if state is None:

            raise ValueError(
                "State cannot be None."
            )

    @abstractmethod
    def execute(
        self,
        state: AgentState,
    ) -> AgentResponse:
        ...

    # ------------------------------------------------------------------
    # LLM narration (optional; never changes the deterministic result)
    # ------------------------------------------------------------------

    @property
    def narration_instructions(self) -> str | None:

        return AGENT_INSTRUCTIONS.get(self.name)

    def narrative_facts(
        self,
        state: AgentState,
        response: AgentResponse,
    ) -> dict[str, Any]:

        return {
            "company": state.company_name,
            "summary": response.summary,
            "findings": response.findings,
            "output": {
                key: value for key, value in response.metadata.items() if key != "narrative"
            },
        }

    def narrate(
        self,
        state: AgentState,
        response: AgentResponse,
    ) -> None:

        instructions = self.narration_instructions
        if self.narrator is None or not instructions:
            return

        narrative = self.narrator.narrate(
            self.name,
            instructions,
            self.narrative_facts(state, response),
            max_output_tokens=self.narration_max_tokens,
        )
        response.metadata["narrative"] = narrative
        state.metadata.setdefault("narratives", {})[self.name] = narrative
        self.on_narrative(state, response, narrative)

    def on_narrative(
        self,
        state: AgentState,
        response: AgentResponse,
        narrative: Narrative,
    ) -> None:
        """Hook for agents that fold the narrative into their own report."""

        return None

    def update_state(
        self,
        state: AgentState,
        response: AgentResponse,
    ) -> None:

        state.conversation_history.append(
            f"{self.name}: {response.summary}"
        )

from abc import ABC, abstractmethod

from .state import AgentState
from .types import AgentResponse


class BaseAgent(ABC):

    def __init__(self, name: str):

        self.name = name

    def run(
        self,
        state: AgentState,
    ) -> AgentResponse:

        self.validate(state)

        response = self.execute(state)

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

    def update_state(
        self,
        state: AgentState,
        response: AgentResponse,
    ) -> None:

        state.conversation_history.append(
            f"{self.name}: {response.summary}"
        )
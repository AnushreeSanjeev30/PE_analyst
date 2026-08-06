class AgentError(Exception):
    pass


class ValidationError(AgentError):
    pass


class ToolExecutionError(AgentError):
    pass


class PromptError(AgentError):
    pass
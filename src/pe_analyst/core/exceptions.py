"""Custom exception hierarchy for PE-Analyst."""


class PEAnalystError(Exception):
    """Base exception for all application-specific errors."""


class ConfigurationError(PEAnalystError):
    """Raised when application configuration is invalid."""


class DocumentProcessingError(PEAnalystError):
    """Raised when document ingestion or processing fails."""


class UnsupportedDocumentError(DocumentProcessingError):
    """Raised when an unsupported document format is provided."""


class FinancialDataError(PEAnalystError):
    """Raised when financial data is missing, malformed, or inconsistent."""


class FinancialCalculationError(PEAnalystError):
    """Raised when a deterministic financial calculation fails."""


class LBOCalculationError(FinancialCalculationError):
    """Raised when an LBO calculation cannot be completed."""


class ScenarioAnalysisError(FinancialCalculationError):
    """Raised when scenario or sensitivity analysis fails."""


class RetrievalError(PEAnalystError):
    """Raised when evidence retrieval fails."""


class EvidenceValidationError(PEAnalystError):
    """Raised when evidence cannot support an analytical claim."""


class ExternalResearchError(PEAnalystError):
    """Raised when external market research fails."""


class AgentExecutionError(PEAnalystError):
    """Raised when a specialist agent cannot complete its task."""


class WorkflowExecutionError(PEAnalystError):
    """Raised when the investment workflow fails."""


class RepositoryError(PEAnalystError):
    """Raised when persistence or repository operations fail."""


class EntityNotFoundError(RepositoryError):
    """Raised when a requested persistent entity does not exist."""
class ValuationError(Exception):
    """Base valuation exception."""


class InvalidAssumptionError(ValuationError):
    """Raised when assumptions are invalid."""


class ComparableAnalysisError(ValuationError):
    """
    Raised when comparable company analysis fails.
    """

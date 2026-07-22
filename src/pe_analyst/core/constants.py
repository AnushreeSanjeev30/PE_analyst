"""Application-wide constants for PE-Analyst."""

from typing import Final

APP_NAME: Final[str] = "PE-Analyst"

APP_VERSION: Final[str] = "0.1.0"

DEFAULT_CURRENCY: Final[str] = "USD"

DEFAULT_FINANCIAL_SCALE: Final[str] = "millions"


SUPPORTED_DOCUMENT_EXTENSIONS: Final[tuple[str, ...]] = (
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
)


FINANCIAL_STATEMENT_TYPES: Final[tuple[str, ...]] = (
    "income_statement",
    "balance_sheet",
    "cash_flow_statement",
)


DEFAULT_SCENARIO_NAMES: Final[tuple[str, ...]] = (
    "downside",
    "base",
    "upside",
)


DEFAULT_INVESTMENT_COMMITTEE_ROLES: Final[tuple[str, ...]] = (
    "deal_partner",
    "risk_officer",
    "operating_partner",
    "chairperson",
)


PERCENTAGE_MULTIPLIER: Final[int] = 100

BASIS_POINTS_PER_PERCENT: Final[int] = 100

MONTHS_PER_YEAR: Final[int] = 12


MINIMUM_FINANCIAL_YEARS: Final[int] = 2

DEFAULT_FORECAST_YEARS: Final[int] = 5


DEFAULT_CONFIDENCE_THRESHOLD: Final[float] = 0.70

HIGH_CONFIDENCE_THRESHOLD: Final[float] = 0.85


DEFAULT_MATERIALITY_THRESHOLD: Final[float] = 0.05


DEFAULT_DECIMAL_PRECISION: Final[int] = 4

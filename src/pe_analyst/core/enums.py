"""Shared enumerations used throughout PE-Analyst."""

from enum import StrEnum


class Environment(StrEnum):
    """Supported application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class DocumentType(StrEnum):
    """Supported company document categories."""

    ANNUAL_REPORT = "annual_report"
    FINANCIAL_STATEMENT = "financial_statement"
    INVESTOR_PRESENTATION = "investor_presentation"
    EARNINGS_RELEASE = "earnings_release"
    DEAL_DOCUMENT = "deal_document"
    INDUSTRY_REPORT = "industry_report"
    OTHER = "other"


class FinancialStatementType(StrEnum):
    """Core financial statement categories."""

    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW_STATEMENT = "cash_flow_statement"


class AnalysisType(StrEnum):
    """Major analysis categories produced by the platform."""

    DOCUMENT = "document"
    FINANCIAL = "financial"
    INDUSTRY = "industry"
    DUE_DILIGENCE = "due_diligence"
    LBO = "lbo"
    SCENARIO = "scenario"
    INVESTMENT_MEMO = "investment_memo"
    INVESTMENT_COMMITTEE = "investment_committee"


class ScenarioType(StrEnum):
    """Supported investment scenarios."""

    DOWNSIDE = "downside"
    BASE = "base"
    UPSIDE = "upside"


class RiskSeverity(StrEnum):
    """Severity assigned to identified investment risks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(StrEnum):
    """Major private-equity risk categories."""

    FINANCIAL = "financial"
    COMMERCIAL = "commercial"
    OPERATIONAL = "operational"
    LEGAL = "legal"
    REGULATORY = "regulatory"
    MANAGEMENT = "management"
    TECHNOLOGY = "technology"
    ESG = "esg"
    TRANSACTION = "transaction"
    EXIT = "exit"
    OTHER = "other"


class ConfidenceLevel(StrEnum):
    """Qualitative confidence assigned to analytical findings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceSourceType(StrEnum):
    """Source categories used by the evidence system."""

    COMPANY_DOCUMENT = "company_document"
    REGULATORY_FILING = "regulatory_filing"
    COMPANY_WEBSITE = "company_website"
    GOVERNMENT_SOURCE = "government_source"
    INDUSTRY_REPORT = "industry_report"
    NEWS_SOURCE = "news_source"
    DATABASE = "database"
    ANALYST_INPUT = "analyst_input"
    OTHER = "other"


class CommitteeRole(StrEnum):
    """Roles participating in the Investment Committee simulation."""

    DEAL_PARTNER = "deal_partner"
    RISK_OFFICER = "risk_officer"
    OPERATING_PARTNER = "operating_partner"
    CHAIRPERSON = "chairperson"


class InvestmentDecision(StrEnum):
    """Possible Investment Committee decisions."""

    APPROVE = "approve"
    REJECT = "reject"
    INVESTIGATE_FURTHER = "investigate_further"
    MODIFY_TERMS = "modify_terms"


class WorkflowStatus(StrEnum):
    """Lifecycle states for an investment-analysis workflow."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

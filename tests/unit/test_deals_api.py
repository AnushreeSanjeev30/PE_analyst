from fastapi.testclient import TestClient

from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings, get_settings
from pe_analyst.document_intelligence.schemas import (
    DocumentIntelligenceReport,
    ExtractedRiskFactorSchema,
    IndustryEvidenceSchema,
    SourceReferenceSchema,
)
from pe_analyst.document_intelligence.storage import DocumentReportStore
from pe_analyst.main import app


def _financials() -> dict:
    return {
        "revenue": 1_000.0,
        "cost_of_goods_sold": 600.0,
        "ebitda": 220.0,
        "ebit": 150.0,
        "net_income": 100.0,
        "operating_cash_flow": 140.0,
        "capital_expenditure": 40.0,
        "total_assets": 1_000.0,
        "shareholders_equity": 400.0,
        "total_debt": 200.0,
        "interest_expense": 20.0,
        "current_assets": 200.0,
        "inventory": 50.0,
        "current_liabilities": 180.0,
    }


def _valuation_inputs() -> dict:
    return {
        "current_price_per_share": 85.0,
        "dcf": {
            "revenue": 1_000.0,
            "assumptions": {
                "revenue_growth": 0.08,
                "ebit_margin": 0.20,
                "cash": 100.0,
                "debt": 200.0,
                "shares_outstanding": 10.0,
            },
        },
        "comparables": {
            "target": {
                "revenue": 1_000.0,
                "ebitda": 220.0,
                "cash": 100.0,
                "debt": 200.0,
                "shares_outstanding": 10.0,
            },
            "peers": [
                {
                    "name": "Peer A",
                    "enterprise_value": 1_800.0,
                    "market_cap": 1_600.0,
                    "revenue": 200.0,
                    "ebitda": 40.0,
                    "net_income": 20.0,
                    "book_value": 200.0,
                },
                {
                    "name": "Peer B",
                    "enterprise_value": 2_000.0,
                    "market_cap": 1_750.0,
                    "revenue": 250.0,
                    "ebitda": 50.0,
                    "net_income": 25.0,
                    "book_value": 225.0,
                },
                {
                    "name": "Peer C",
                    "enterprise_value": 1_650.0,
                    "market_cap": 1_400.0,
                    "revenue": 220.0,
                    "ebitda": 44.0,
                    "net_income": 22.0,
                    "book_value": 180.0,
                },
            ],
        },
        "lbo": {
            "assumptions": {"purchase_price": 1_600.0, "holding_period": 5, "exit_multiple": 8.0},
            "operating_projection": [
                {
                    "year": year,
                    "revenue": 1_000.0 + year * 60,
                    "ebitda": 220.0 + year * 15,
                    "taxes": 30.0 + year,
                    "capex": 30.0 + year,
                    "change_in_nwc": 10.0 + year,
                }
                for year in range(1, 6)
            ],
        },
    }


def _industry_inputs() -> dict:
    return {
        "industry_name": "Vertical Software",
        "evidence": [
            {
                "topic": "market",
                "source": "2025 Annual Report",
                "page_number": 12,
                "excerpt": "Market demand remains strong.",
                "claim": "Management expects durable demand.",
                "confidence": 0.9,
            },
            {
                "topic": "competition",
                "source": "2025 Annual Report",
                "page_number": 18,
                "excerpt": "The market is fragmented.",
                "claim": "Fragmentation supports consolidation.",
                "confidence": 0.85,
            },
            {
                "topic": "management",
                "source": "2025 Annual Report",
                "page_number": 26,
                "excerpt": "We are investing in sales capacity.",
                "claim": "Management is funding growth capacity.",
                "confidence": 0.8,
            },
        ],
    }


def _request_body(**overrides: object) -> dict:
    body = {
        "company_name": "ExampleCo",
        "current_financials": _financials(),
        "previous_financials": _financials(),
        "valuation_inputs": _valuation_inputs(),
        "risk_inputs": {"altman_z": 3.2, "piotroski_score": 7, "industry_risk_score": 30},
        "industry_inputs": _industry_inputs(),
        "due_diligence_inputs": [],
    }
    body.update(overrides)
    return body


def _client(test_settings: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_current_user] = lambda: UserPublic(
        id="test-user", email="analyst@example.com", role="analyst"
    )
    return TestClient(app)


def test_analyze_deal_with_explicit_inputs_returns_a_completed_report(
    test_settings: Settings,
) -> None:
    client = _client(test_settings)
    try:
        response = client.post("/api/v1/deals/analyze", json=_request_body())

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert body["final_recommendation"] in {"BUY", "HOLD", "REJECT"}
        assert body["due_diligence_report"]["summary"]["assessment"] == "Clear"
        assert [stage["stage"] for stage in body["stages"]] == [
            "financial",
            "valuation",
            "scenario",
            "risk",
            "due_diligence",
            "industry",
            "investment_committee",
            "deal_partner",
            "risk_officer",
            "operating_partner",
            "chairperson",
            "memo",
        ]
        assert body["ic_decision"]["final_recommendation"] == body["final_recommendation"]
    finally:
        app.dependency_overrides.clear()


def test_analyze_deal_derives_evidence_from_a_stored_document(test_settings: Settings) -> None:
    client = _client(test_settings)
    try:
        report = DocumentIntelligenceReport(
            document_id="doc-123",
            file_name="ExampleCo.pdf",
            page_count=1,
            sections=[],
            statement_line_items=[],
            risk_factors=[
                ExtractedRiskFactorSchema(
                    title="Litigation exposure",
                    text="The company faces ongoing litigation.",
                    source=SourceReferenceSchema(
                        page_number=9, excerpt="Ongoing litigation.", confidence=0.8
                    ),
                )
            ],
            notes=[],
            management_discussion=[],
            industry_evidence=[
                IndustryEvidenceSchema(
                    topic="market",
                    source="ExampleCo.pdf",
                    page_number=3,
                    excerpt="Market demand is growing.",
                    claim="Market demand is growing.",
                    confidence=0.85,
                ),
                IndustryEvidenceSchema(
                    topic="competition",
                    source="ExampleCo.pdf",
                    page_number=3,
                    excerpt="Competition remains intense.",
                    claim="Competition remains intense.",
                    confidence=0.85,
                ),
                IndustryEvidenceSchema(
                    topic="management",
                    source="ExampleCo.pdf",
                    page_number=4,
                    excerpt="Management is executing well.",
                    claim="Management is executing well.",
                    confidence=0.8,
                ),
            ],
            warnings=[],
        )
        DocumentReportStore.save(report, test_settings)

        body = _request_body(
            document_id="doc-123",
            industry_name="Vertical Software",
        )
        del body["industry_inputs"]
        del body["due_diligence_inputs"]

        response = client.post("/api/v1/deals/analyze", json=body)

        assert response.status_code == 200
        payload = response.json()
        assert payload["industry_report"]["summary"]["industry_name"] == "Vertical Software"
        assert payload["due_diligence_report"]["red_flags"]
        assert payload["due_diligence_report"]["red_flags"][0]["title"] == "Litigation exposure"
    finally:
        app.dependency_overrides.clear()


def test_analyze_deal_404s_for_an_unknown_document_id(test_settings: Settings) -> None:
    client = _client(test_settings)
    try:
        body = _request_body(document_id="missing", industry_name="Vertical Software")
        del body["industry_inputs"]
        del body["due_diligence_inputs"]

        response = client.post("/api/v1/deals/analyze", json=body)

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_analyze_deal_requires_industry_name_when_deriving_from_a_document(
    test_settings: Settings,
) -> None:
    client = _client(test_settings)
    try:
        report = DocumentIntelligenceReport(
            document_id="doc-456",
            file_name="ExampleCo.pdf",
            page_count=1,
            sections=[],
            statement_line_items=[],
            risk_factors=[],
            notes=[],
            management_discussion=[],
            industry_evidence=[],
            warnings=[],
        )
        DocumentReportStore.save(report, test_settings)

        body = _request_body(document_id="doc-456")
        del body["industry_inputs"]
        del body["due_diligence_inputs"]

        response = client.post("/api/v1/deals/analyze", json=body)

        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()

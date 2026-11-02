"""End to end: an annual-report PDF -> extraction -> every agent -> IC decision and memo.

Nothing is mocked except authentication: the PDF is a real file parsed by pypdf/pdfplumber, the
financial statements fed to the agents are the ones extracted from its tables, and industry and
diligence evidence come from its text with page citations.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from tests.e2e.pdf_builder import Page, build_pdf

from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings, get_settings
from pe_analyst.deals.api import get_narrator
from pe_analyst.main import app


def annual_report_pdf() -> bytes:
    overview = Page().text("Northwind Software Inc. - 2025 Annual Report", size=14).paragraph([
        "Market overview: industry demand for vertical software grew 12% in 2025.",
        "Competition remains fragmented; we hold a strong competitive position.",
        "Management strategy focuses on cross-sell expansion and pricing discipline.",
    ])
    risks = Page().text("Item 1A. Risk Factors", size=12).paragraph([
        "Customer concentration could adversely affect our revenue if a top client churns.",
        "Rising interest rates may increase the cost of refinancing our credit facility.",
    ])
    income = Page().text("Consolidated Statements of Operations (in millions)", size=12).table([
        ["", "2025", "2024"],
        ["Total revenues", "1,000", "900"],
        ["Cost of revenue", "600", "560"],
        ["Operating income", "150", "130"],
        ["Interest expense", "(20)", "(22)"],
        ["Net income", "100", "85"],
    ])
    balance = Page().text("Consolidated Balance Sheets (in millions)", size=12).table([
        ["", "2025", "2024"],
        ["Inventories", "50", "45"],
        ["Total current assets", "200", "180"],
        ["Total assets", "1,000", "900"],
        ["Total current liabilities", "180", "170"],
        ["Long-term debt", "200", "210"],
        ["Total stockholders' equity", "400", "350"],
    ])
    cash = Page().text("Consolidated Statements of Cash Flows (in millions)", size=12).table([
        ["", "2025", "2024"],
        ["Depreciation and amortization", "70", "60"],
        ["Net cash provided by operating activities", "140", "120"],
        ["Purchases of property and equipment", "(40)", "(35)"],
    ])
    notes = Page().text("Notes to Consolidated Financial Statements", size=12).paragraph([
        "Note 1. Revenue is recognized ratably over subscription terms.",
        "Note 2. The credit facility matures in 2029 and carries covenants.",
    ])
    return build_pdf([overview, risks, income, balance, cash, notes])


def _lbo_inputs() -> dict[str, object]:
    return {
        "current_price_per_share": 85.0,
        "dcf": {
            "revenue": 1_000.0,
            "assumptions": {"revenue_growth": 0.08, "ebit_margin": 0.20, "cash": 100.0,
                            "debt": 200.0, "shares_outstanding": 10.0},
        },
        "comparables": {
            "target": {"revenue": 1_000.0, "ebitda": 220.0, "cash": 100.0, "debt": 200.0,
                       "shares_outstanding": 10.0},
            "peers": [
                {"name": f"Peer {name}", "enterprise_value": ev, "market_cap": ev * 0.9,
                 "revenue": ev / 9, "ebitda": ev / 45, "net_income": ev / 90,
                 "book_value": ev / 9}
                for name, ev in (("A", 1_800.0), ("B", 2_000.0), ("C", 1_650.0))
            ],
        },
        "lbo": {
            "assumptions": {"purchase_price": 1_600.0, "holding_period": 5, "exit_multiple": 8.0},
            "operating_projection": [
                {"year": year, "revenue": 1_000.0 + year * 60, "ebitda": 220.0 + year * 15,
                 "taxes": 30.0 + year, "capex": 30.0 + year, "change_in_nwc": 10.0 + year}
                for year in range(1, 6)
            ],
        },
    }


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_narrator] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: UserPublic(
        id="e2e-user", email="analyst@example.com", role="analyst"
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_uploaded_annual_report_drives_the_whole_workflow(client: TestClient) -> None:
    upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("Northwind_2025.pdf", annual_report_pdf(), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert document["page_count"] == 6
    assert document["statement_line_items"], document["warnings"]
    assert document["risk_factors"]

    response = client.post(
        "/api/v1/deals/analyze",
        json={
            "company_name": "Northwind Software",
            "document_id": document["document_id"],
            "industry_name": "Vertical Software",
            "valuation_inputs": _lbo_inputs(),
            "risk_inputs": {"altman_z": 3.2, "piotroski_score": 7, "industry_risk_score": 30},
        },
    )

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["status"] == "completed", report["error"]
    assert report["final_recommendation"] in {"BUY", "HOLD", "REJECT"}
    assert [stage["status"] for stage in report["stages"]] == ["completed"] * 12

    # Financials came from the PDF's tables: ROE = 100 / 400.
    roe_metric = report["financial_report"]["metrics"][0]
    assert roe_metric["name"] == "ROE" and roe_metric["value"] == pytest.approx(25.0)
    # Industry claims and red flags cite pages of the uploaded document.
    citations = [
        citation
        for finding in report["industry_report"]["findings"]
        for citation in finding["citations"]
    ]
    assert citations and all(item["source"].endswith("Northwind_2025.pdf") for item in citations)
    assert report["due_diligence_report"]["items_reviewed"] > 0

    memo = report["investment_memo"]
    assert memo["recommendation"] == report["final_recommendation"]
    assert "## Returns and Scenarios" in memo["markdown"]
    assert report["scenario_report"]["cases"]


def test_document_missing_a_statement_field_is_rejected_with_the_field_named(
    client: TestClient,
) -> None:
    page = Page().text("Consolidated Statements of Operations", size=12).table([
        ["", "2025", "2024"],
        ["Total revenues", "1,000", "900"],
    ])
    upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("Thin.pdf", build_pdf([page]), "application/pdf")},
    )

    response = client.post(
        "/api/v1/deals/analyze",
        json={
            "company_name": "Thin Co",
            "document_id": upload.json()["document_id"],
            "industry_name": "Software",
            "valuation_inputs": _lbo_inputs(),
        },
    )

    assert response.status_code == 422
    assert "total_assets" in response.json()["detail"]

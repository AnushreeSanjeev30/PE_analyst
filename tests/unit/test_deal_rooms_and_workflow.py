"""Deal rooms (team sharing), multi-document analyses, suggested inputs, opening the source
PDF, and comparing two runs."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings, get_settings
from pe_analyst.db.models import UserModel
from pe_analyst.deals.api import get_narrator
from pe_analyst.deals.assumptions import (
    PeerInput,
    ValuationAssumptionInputs,
    build_valuation_inputs,
    suggest_inputs,
)
from pe_analyst.deals.comparison import diff_inputs
from pe_analyst.document_intelligence.agent_inputs import map_financials_across
from pe_analyst.document_intelligence.financial_mapping import STATEMENT_FIELDS
from pe_analyst.document_intelligence.schemas import (
    DocumentIntelligenceReport,
    DocumentSectionSchema,
    IndustryEvidenceSchema,
    SourceReferenceSchema,
    StatementLineItemSchema,
)
from pe_analyst.document_intelligence.service import DocumentIntelligenceService
from pe_analyst.engines.financial.models import FinancialStatement
from pe_analyst.main import app

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"

ALICE = UserPublic(id="alice", email="alice@example.com", role="analyst")
BOB = UserPublic(id="bob", email="bob@example.com", role="analyst")
CARA = UserPublic(id="cara", email="cara@example.com", role="analyst")

PEERS = [
    {
        "name": "Peer A",
        "enterprise_value": 1800.0,
        "market_cap": 1600.0,
        "revenue": 200.0,
        "ebitda": 40.0,
        "net_income": 20.0,
        "book_value": 200.0,
    },
    {
        "name": "Peer B",
        "enterprise_value": 2000.0,
        "market_cap": 1750.0,
        "revenue": 250.0,
        "ebitda": 50.0,
        "net_income": 25.0,
        "book_value": 225.0,
    },
]


def _assumptions(**overrides: Any) -> dict[str, Any]:
    return {
        "revenue_growth": 0.08,
        "ebit_margin": 0.15,
        "ebitda_margin": 0.22,
        "capex_pct_revenue": 0.04,
        "cash": 100.0,
        "debt": 200.0,
        "shares_outstanding": 10.0,
        "current_price_per_share": 85.0,
        "entry_multiple": 7.0,
        "exit_multiple": 8.0,
        "holding_period": 5,
        "peers": PEERS,
        **overrides,
    }


def _act_as(user: UserPublic) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
def client(test_settings: Settings, app_db: Callable[[], Session]) -> Iterator[TestClient]:
    with app_db() as session:
        for user in (ALICE, BOB, CARA):
            session.add(UserModel(id=user.id, email=user.email, hashed_password="x"))
        session.commit()
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_narrator] = lambda: None
    _act_as(ALICE)
    try:
        yield TestClient(app)
    finally:
        for dependency in (get_settings, get_narrator, get_current_user):
            app.dependency_overrides.pop(dependency, None)


def _upload(client: TestClient, name: str, deal_room_id: str | None = None) -> str:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": (name, (SAMPLES / name).read_bytes(), "application/pdf")},
        data={"deal_room_id": deal_room_id} if deal_room_id else None,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["document_id"])


def _room(client: TestClient, name: str = "Project Meridian") -> str:
    response = client.post("/api/v1/deal-rooms", json={"name": name})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _analyse(client: TestClient, **body: Any) -> dict[str, Any]:
    payload = {
        "company_name": "Meridian Software",
        "industry_name": "Vertical Software",
        "valuation_assumptions": _assumptions(),
        **body,
    }
    started = client.post("/api/v1/deals/analyses", json=payload)
    assert started.status_code == 202, started.text
    record = client.get(f"/api/v1/deals/analyses/{started.json()['id']}").json()
    assert record["status"] == "completed", record["error"]
    return dict(record)


# ---------------------------------------------------------------------------
# 1. Team sharing
# ---------------------------------------------------------------------------


def test_a_deal_team_shares_documents_and_analyses(client: TestClient) -> None:
    room_id = _room(client)
    document_id = _upload(client, "Meridian_Software_2025.pdf", room_id)
    analysis = _analyse(client, document_ids=[document_id], deal_room_id=room_id)

    # Before being added, Bob sees none of it.
    _act_as(BOB)
    assert client.get("/api/v1/deal-rooms").json() == []
    assert client.get(f"/api/v1/deal-rooms/{room_id}").status_code == 404
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 404
    assert client.get(f"/api/v1/deals/analyses/{analysis['id']}").status_code == 404

    _act_as(ALICE)
    added = client.post(f"/api/v1/deal-rooms/{room_id}/members", json={"email": "BOB@example.com"})
    assert added.status_code == 201, added.text

    _act_as(BOB)
    room = client.get(f"/api/v1/deal-rooms/{room_id}").json()
    assert {member["email"]: member["role"] for member in room["members"]} == {
        "alice@example.com": "owner",
        "bob@example.com": "member",
    }
    assert room["can_manage"] is False
    assert (room["document_count"], room["analysis_count"], room["member_count"]) == (1, 1, 2)
    documents = client.get("/api/v1/documents", params={"deal_room_id": room_id}).json()
    assert [item["document_id"] for item in documents] == [document_id]
    assert documents[0]["display_name"] == "Meridian_Software_2025.pdf"
    assert client.get(f"/api/v1/deals/analyses/{analysis['id']}").status_code == 200
    listed = client.get("/api/v1/deals/analyses", params={"deal_room_id": room_id}).json()
    assert [item["id"] for item in listed] == [analysis["id"]]
    # A member can search the shared document too.
    question = {"question": "What is the growth?", "document_id": document_id}
    assert client.post("/api/v1/rag/query", json=question).status_code == 200


def test_only_the_owner_manages_the_team_and_members_cannot_delete_others_work(
    client: TestClient,
) -> None:
    room_id = _room(client)
    document_id = _upload(client, "Meridian_Software_2025.pdf", room_id)
    analysis = _analyse(client, document_ids=[document_id], deal_room_id=room_id)
    client.post(f"/api/v1/deal-rooms/{room_id}/members", json={"email": BOB.email})

    _act_as(BOB)
    invite = client.post(f"/api/v1/deal-rooms/{room_id}/members", json={"email": CARA.email})
    assert invite.status_code == 403
    assert client.patch(f"/api/v1/deal-rooms/{room_id}", json={"name": "X"}).status_code == 403
    assert client.delete(f"/api/v1/deal-rooms/{room_id}").status_code == 403
    assert client.delete(f"/api/v1/deals/analyses/{analysis['id']}").status_code == 404
    moved = client.put(f"/api/v1/documents/{document_id}/deal-room", json={"deal_room_id": None})
    assert moved.status_code == 403

    # A member may leave on their own, and then loses access.
    assert client.delete(f"/api/v1/deal-rooms/{room_id}/members/{BOB.id}").status_code == 204
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 404


def test_adding_an_unknown_or_duplicate_member_is_a_clear_error(client: TestClient) -> None:
    room_id = _room(client)
    url = f"/api/v1/deal-rooms/{room_id}/members"

    unknown = client.post(url, json={"email": "nobody@example.com"})
    assert unknown.status_code == 400
    assert "register" in unknown.json()["detail"]

    assert client.post(url, json={"email": BOB.email}).status_code == 201
    assert client.post(url, json={"email": BOB.email}).status_code == 400
    assert client.post(url, json={"email": ALICE.email}).status_code == 400


def test_deleting_a_deal_keeps_its_documents_but_makes_them_private_again(
    client: TestClient,
) -> None:
    room_id = _room(client)
    document_id = _upload(client, "Meridian_Software_2025.pdf", room_id)
    client.post(f"/api/v1/deal-rooms/{room_id}/members", json={"email": BOB.email})

    assert client.delete(f"/api/v1/deal-rooms/{room_id}").status_code == 204

    assert client.get(f"/api/v1/documents/{document_id}").status_code == 200
    _act_as(BOB)
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 404


def test_an_existing_private_document_can_be_filed_in_a_deal(client: TestClient) -> None:
    document_id = _upload(client, "Meridian_Software_2025.pdf")
    room_id = _room(client)
    client.post(f"/api/v1/deal-rooms/{room_id}/members", json={"email": BOB.email})

    moved = client.put(f"/api/v1/documents/{document_id}/deal-room", json={"deal_room_id": room_id})

    assert moved.status_code == 200
    assert moved.json()["deal_room_id"] == room_id
    _act_as(BOB)
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 200


def test_filing_into_a_deal_you_cannot_access_is_rejected(client: TestClient) -> None:
    room_id = _room(client)

    _act_as(BOB)
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("a.pdf", (SAMPLES / "Meridian_Software_2025.pdf").read_bytes())},
        data={"deal_room_id": room_id},
    )
    assert response.status_code == 404
    body = {
        "company_name": "X",
        "deal_room_id": room_id,
        "valuation_assumptions": _assumptions(),
        "industry_inputs": {},
    }
    assert client.post("/api/v1/deals/analyses", json=body).status_code == 404


# ---------------------------------------------------------------------------
# 3. Several documents per deal  /  4. Opening the cited page
# ---------------------------------------------------------------------------


def test_an_analysis_combines_documents_and_cites_the_right_file(client: TestClient) -> None:
    meridian = _upload(client, "Meridian_Software_2025.pdf")
    harbor = _upload(client, "Harbor_Logistics_2025.pdf")

    record = _analyse(client, document_ids=[meridian, harbor])

    explanation = record["report"]["ic_decision"]["explanation"]
    drivers = {driver["area"]: driver for driver in explanation["drivers"]}
    # Financials come from the first document listed...
    assert {c["document_id"] for c in drivers["Financial health"]["evidence"]} == {meridian}
    # ...while red flags are found in the second, and say so.
    flags = record["report"]["due_diligence_report"]["red_flags"]
    assert flags and {flag["citation"]["document_id"] for flag in flags} == {harbor}
    assert {flag["citation"]["source"] for flag in flags} == {"Harbor_Logistics_2025.pdf"}
    # Industry evidence is drawn from both.
    assert {c["document_id"] for c in drivers["Industry"]["evidence"]} == {meridian, harbor}
    assert record["document_id"] == meridian


def test_the_original_pdf_can_be_opened_by_people_who_may_read_it(client: TestClient) -> None:
    document_id = _upload(client, "Meridian_Software_2025.pdf")

    response = client.get(f"/api/v1/documents/{document_id}/file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "inline" in response.headers["content-disposition"]
    assert "Meridian_Software_2025.pdf" in response.headers["content-disposition"]
    assert response.content == (SAMPLES / "Meridian_Software_2025.pdf").read_bytes()

    _act_as(BOB)
    assert client.get(f"/api/v1/documents/{document_id}/file").status_code == 404


def _line(label: str, values: list[float], page: int = 1) -> StatementLineItemSchema:
    return StatementLineItemSchema(
        statement="income_statement",
        label=label,
        raw_values=[str(value) for value in values],
        parsed_values=values,
        source=SourceReferenceSchema(page_number=page, excerpt=label, confidence=0.85),
    )


def _report(
    document_id: str, lines: list[StatementLineItemSchema], units: str | None = None
) -> DocumentIntelligenceReport:
    sections = []
    if units:
        sections.append(
            DocumentSectionSchema(
                kind="income_statement",
                title="Statements of Operations",
                pages=[1],
                references=[
                    SourceReferenceSchema(
                        page_number=1,
                        excerpt=f"Statements of Operations (in {units})",
                        confidence=0.85,
                    )
                ],
            )
        )
    return DocumentIntelligenceReport(
        document_id=document_id,
        file_name=f"{document_id}.pdf",
        page_count=1,
        sections=sections,
        statement_line_items=lines,
        risk_factors=[],
        notes=[],
        management_discussion=[],
        industry_evidence=[],
        warnings=[],
    )


def test_financials_are_merged_field_by_field_across_documents() -> None:
    accounts = _report("accounts", [_line("Total revenues", [1000.0, 900.0])], "millions")
    cim = _report(
        "cim",
        [
            _line("Total revenues", [5.0, 4.0]),  # ignored: the accounts already report it
            _line("Net income", [100_000.0, 85_000.0]),
            _line("Inventories", [50_000.0, 45_000.0]),
        ],
        "thousands",
    )

    mapped, sources = map_financials_across([accounts, cim])

    assert mapped.current["revenue"] == 1000.0
    assert sources["revenue"].document_id == "accounts"
    # Thousands are converted into the first document's millions.
    assert mapped.current["net_income"] == pytest.approx(100.0)
    assert sources["net_income"].document_id == "cim"
    # A real inventory line beats the first document's "assumed zero" default.
    assert mapped.current["inventory"] == pytest.approx(50.0)
    assert any("different units" in warning for warning in mapped.warnings)
    assert "total_assets" in mapped.missing


# ---------------------------------------------------------------------------
# 2. Suggested inputs and structured assumptions
# ---------------------------------------------------------------------------


def _sample_report(name: str) -> DocumentIntelligenceReport:
    return DocumentIntelligenceReport.from_result(
        DocumentIntelligenceService().process(SAMPLES / name)
    )


def test_inputs_are_proposed_from_the_document_with_their_source() -> None:
    suggested = suggest_inputs([_sample_report("Meridian_Software_2025.pdf")])

    by_field = {item.field: item for item in suggested.assumptions}
    assert suggested.missing_financials == []
    assert suggested.current_financials["revenue"] == 1000.0
    assert set(suggested.current_financials) == set(STATEMENT_FIELDS)
    assert by_field["revenue_growth"].value == pytest.approx(100 / 900)
    assert by_field["revenue_growth"].basis == "Calculated"
    assert by_field["revenue_growth"].citation.page_number == 3
    assert by_field["ebitda_margin"].value == pytest.approx(0.22)
    assert by_field["debt"].value == 200.0
    assert by_field["debt"].basis == "Document"
    # Nothing in the document supports these, and the suggestion says so.
    assert by_field["entry_multiple"].basis == "Default"
    assert by_field["shares_outstanding"].basis == "Needs input"
    assert by_field["shares_outstanding"].value is None
    assert suggested.market_growth_pct.value == pytest.approx(0.12)
    assert "grew 12%" in suggested.market_growth_pct.citation.excerpt


@pytest.mark.parametrize(
    ("sample", "position", "growth"),
    [
        ("Harbor_Logistics_2025.pdf", "Weak", 0.06),
        ("Castell_Retail_2025.pdf", "Weak", -0.09),
        ("Meridian_Software_2025.pdf", "Neutral", 0.12),
    ],
)
def test_competitive_position_and_market_growth_are_read_from_the_wording(
    sample: str, position: str, growth: float
) -> None:
    suggested = suggest_inputs([_sample_report(sample)])

    assert suggested.competitive_position.value == position
    assert suggested.market_growth_pct.value == pytest.approx(growth)
    if position != "Neutral":
        assert suggested.competitive_position.citation is not None


def test_conflicting_claims_about_position_are_flagged_not_resolved() -> None:
    report = _report("doc", [])
    report = report.model_copy(
        update={
            "industry_evidence": [
                IndustryEvidenceSchema(
                    topic="competition",
                    source="doc.pdf",
                    page_number=2,
                    excerpt="We are the market leader in our segment. "
                    "Pricing pressure from new entrants reduced our margins.",
                    claim="",
                    confidence=0.85,
                )
            ]
        }
    )

    suggestion = suggest_inputs([report]).competitive_position

    assert suggestion.value == "Neutral"
    assert "point both ways" in suggestion.note


def _statement(**overrides: float) -> FinancialStatement:
    values = {
        "revenue": 1000.0,
        "cost_of_goods_sold": 600.0,
        "ebitda": 220.0,
        "ebit": 150.0,
        "net_income": 100.0,
        "operating_cash_flow": 140.0,
        "capital_expenditure": 40.0,
        "total_assets": 1000.0,
        "shareholders_equity": 400.0,
        "total_debt": 200.0,
        "interest_expense": 20.0,
        "current_assets": 200.0,
        "inventory": 50.0,
        "current_liabilities": 180.0,
        **overrides,
    }
    return FinancialStatement(**values)


def test_assumptions_expand_into_full_valuation_inputs() -> None:
    assumptions = ValuationAssumptionInputs(**_assumptions(holding_period=3))

    inputs = build_valuation_inputs(assumptions, _statement())

    assert inputs["lbo"]["assumptions"]["purchase_price"] == pytest.approx(7.0 * 220.0)
    projection = inputs["lbo"]["operating_projection"]
    assert [year["year"] for year in projection] == [1, 2, 3]
    assert projection[0]["revenue"] == pytest.approx(1080.0)
    assert projection[0]["ebitda"] == pytest.approx(1080.0 * 0.22)
    assert projection[0]["taxes"] == pytest.approx(1080.0 * 0.15 * 0.25)
    assert projection[0]["change_in_nwc"] == pytest.approx(80.0 * 0.02)
    assert projection[2]["revenue"] == pytest.approx(1000.0 * 1.08**3)
    assert inputs["dcf"]["assumptions"]["shares_outstanding"] == 10.0
    assert inputs["comparables"]["target"]["ebitda"] == 220.0
    assert inputs["current_price_per_share"] == 85.0


def test_assumptions_that_cannot_be_valued_are_rejected_with_the_reason() -> None:
    with pytest.raises(ValueError, match="EBITDA must be positive"):
        build_valuation_inputs(
            ValuationAssumptionInputs(**_assumptions()), _statement(ebitda=-10.0)
        )
    with pytest.raises(ValueError, match="two comparable companies"):
        build_valuation_inputs(
            ValuationAssumptionInputs(**_assumptions(peers=[PeerInput(**PEERS[0])])),
            _statement(),
        )


def test_suggest_endpoint_reads_the_callers_documents_only(client: TestClient) -> None:
    document_id = _upload(client, "Meridian_Software_2025.pdf")

    response = client.post("/api/v1/deals/suggest-inputs", json={"document_ids": [document_id]})

    assert response.status_code == 200
    assert response.json()["current_financials"]["revenue"] == 1000.0
    _act_as(BOB)
    denied = client.post("/api/v1/deals/suggest-inputs", json={"document_ids": [document_id]})
    assert denied.status_code == 404


def test_confirmed_position_and_growth_reach_the_industry_view(client: TestClient) -> None:
    document_id = _upload(client, "Meridian_Software_2025.pdf")

    record = _analyse(
        client, document_ids=[document_id], competitive_position="Strong", market_growth_pct=0.12
    )

    summary = record["report"]["industry_report"]["summary"]
    assert summary["competitive_position"] == "Strong"
    assert summary["market_growth_pct"] == pytest.approx(0.12)


def test_a_request_needs_exactly_one_valuation_source(client: TestClient) -> None:
    base = {"company_name": "X", "industry_inputs": {}}

    neither = client.post("/api/v1/deals/analyses", json=base)
    both = client.post(
        "/api/v1/deals/analyses",
        json={**base, "valuation_assumptions": _assumptions(), "valuation_inputs": {}},
    )

    assert neither.status_code == 422
    assert both.status_code == 422


# ---------------------------------------------------------------------------
# 5. Comparing two runs
# ---------------------------------------------------------------------------


def test_two_runs_are_compared_input_by_input_and_result_by_result(client: TestClient) -> None:
    document_id = _upload(client, "Meridian_Software_2025.pdf")
    cheap = _analyse(client, document_ids=[document_id])
    dear = _analyse(
        client,
        document_ids=[document_id],
        valuation_assumptions=_assumptions(entry_multiple=12.0),
    )

    response = client.get(
        "/api/v1/deals/analyses/compare", params={"base": cheap["id"], "other": dear["id"]}
    )

    assert response.status_code == 200, response.text
    comparison = response.json()
    assert [change["path"] for change in comparison["input_changes"]] == [
        "valuation_assumptions.entry_multiple"
    ]
    assert comparison["input_changes"][0]["base"] == 7.0
    assert comparison["input_changes"][0]["other"] == 12.0
    metrics = {metric["key"]: metric for metric in comparison["metrics"]}
    # Paying more for the same business lowers the return.
    assert metrics["irr"]["changed"] and metrics["irr"]["delta"] < 0
    assert metrics["entry_ev"]["other"] == pytest.approx(12.0 * 220.0)
    assert not metrics["financial_health"]["changed"]
    assert comparison["base"]["recommendation"] == cheap["recommendation"]
    assert comparison["recommendation_changed"] == (
        cheap["recommendation"] != dear["recommendation"]
    )
    assert "1 input differs." in comparison["summary"]
    assert {driver["area"] for driver in comparison["drivers"]} >= {"Valuation", "Risk"}


def test_comparison_needs_access_to_both_runs(client: TestClient) -> None:
    document_id = _upload(client, "Meridian_Software_2025.pdf")
    mine = _analyse(client, document_ids=[document_id])

    _act_as(BOB)
    theirs = client.get(
        "/api/v1/deals/analyses/compare", params={"base": mine["id"], "other": mine["id"]}
    )

    assert theirs.status_code == 404


def test_input_diff_reports_nested_and_list_changes() -> None:
    base = {"a": {"b": 1, "c": [1, 2]}, "same": "x", "gone": True}
    other = {"a": {"b": 2, "c": [1, 3, 4]}, "same": "x", "new": None, "added": 5}

    changes = {change.path: (change.base, change.other) for change in diff_inputs(base, other)}

    assert changes == {
        "a.b": (1, 2),
        "a.c[1]": (2, 3),
        "a.c[2]": (None, 4),
        "gone": (True, None),
        "added": (None, 5),
    }


# ---------------------------------------------------------------------------
# Exporting to Word and PDF
# ---------------------------------------------------------------------------


def _docx_text(content: bytes) -> str:
    import io

    from docx import Document

    document = Document(io.BytesIO(content))
    text = [paragraph.text for paragraph in document.paragraphs]
    text += [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    return "\n".join(text)


def _pdf_text(content: bytes) -> str:
    import io

    from pypdf import PdfReader

    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(content)).pages)


def test_an_analysis_downloads_as_a_word_memo_with_its_reasons_and_sources(
    client: TestClient,
) -> None:
    document_id = _upload(client, "Harbor_Logistics_2025.pdf")
    record = _analyse(client, company_name="Harbor Logistics", document_ids=[document_id])

    response = client.get(
        f"/api/v1/deals/analyses/{record['id']}/export", params={"format": "docx"}
    )

    assert response.status_code == 200, response.text
    assert "wordprocessingml" in response.headers["content-type"]
    assert (
        'filename="Harbor_Logistics_investment_memo.docx"'
        in (response.headers["content-disposition"])
    )
    text = _docx_text(response.content)
    assert "Investment Committee Memo: Harbor Logistics" in text
    assert f"Recommendation: {record['recommendation']}" in text
    assert "Why this decision" in text
    # The quoted evidence and where it came from survive into the document.
    assert "Customer concentration is significant" in text
    assert "Harbor_Logistics_2025.pdf, page 2" in text
    assert "Entry multiple (EV / EBITDA)" in text
    assert "not investment advice" in text


def test_an_analysis_downloads_as_a_pdf(client: TestClient) -> None:
    document_id = _upload(client, "Harbor_Logistics_2025.pdf")
    record = _analyse(client, company_name="Harbor Logistics", document_ids=[document_id])

    response = client.get(f"/api/v1/deals/analyses/{record['id']}/export")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    text = _pdf_text(response.content)
    assert "Investment Committee Memo: Harbor Logistics" in text
    assert "Why this decision" in text
    assert "Key figures" in text


@pytest.mark.parametrize("file_format", ["pdf", "docx"])
def test_a_comparison_downloads_in_both_formats(client: TestClient, file_format: str) -> None:
    document_id = _upload(client, "Meridian_Software_2025.pdf")
    cheap = _analyse(client, document_ids=[document_id])
    dear = _analyse(
        client,
        document_ids=[document_id],
        valuation_assumptions=_assumptions(entry_multiple=12.0),
    )

    response = client.get(
        "/api/v1/deals/analyses/compare/export",
        params={"base": cheap["id"], "other": dear["id"], "format": file_format},
    )

    assert response.status_code == 200, response.text
    text = (_docx_text if file_format == "docx" else _pdf_text)(response.content)
    assert "Run Comparison: Meridian Software" in text
    # Inputs are named in plain words, not as request paths.
    assert "Entry multiple (EV / EBITDA)" in text
    assert "valuation_assumptions" not in text
    assert "7.00x" in text and "12.00x" in text
    assert "Base-case IRR" in text


def test_export_respects_access_and_rejects_unknown_formats(client: TestClient) -> None:
    document_id = _upload(client, "Meridian_Software_2025.pdf")
    record = _analyse(client, document_ids=[document_id])
    url = f"/api/v1/deals/analyses/{record['id']}/export"

    assert client.get(url, params={"format": "xlsx"}).status_code == 422
    _act_as(BOB)
    assert client.get(url).status_code == 404


def test_pdf_export_survives_symbols_outside_the_built_in_font() -> None:
    from pe_analyst.deals.export import ExportDocument, Paragraph, render_pdf

    document = ExportDocument("T", "S", [Paragraph("IRR 22% → 11% (− 10.5 pts) ≥ target")])

    assert "IRR 22% -> 11% (- 10.5 pts) >= target" in _pdf_text(render_pdf(document))


# ---------------------------------------------------------------------------
# Filling in what the documents leave out
# ---------------------------------------------------------------------------


def test_figures_are_worked_out_from_related_lines_and_flagged() -> None:
    report = _report(
        "doc",
        [
            _line("Total revenues", [1000.0, 900.0]),
            _line("Gross profit", [400.0, 340.0]),
            _line("Adjusted EBITDA", [220.0, 190.0]),
            _line("Depreciation and amortization", [70.0, 60.0]),
            _line("Total assets", [1000.0, 900.0]),
            _line("Total liabilities", [600.0, 550.0]),
        ],
    )

    mapped, _ = map_financials_across([report])

    assert (mapped.current["cost_of_goods_sold"], mapped.previous["cost_of_goods_sold"]) == (
        600.0,
        560.0,
    )
    assert (mapped.current["ebit"], mapped.previous["ebit"]) == (150.0, 130.0)
    assert (mapped.current["shareholders_equity"], mapped.previous["shareholders_equity"]) == (
        400.0,
        350.0,
    )
    for name in ("cost_of_goods_sold", "ebit", "shareholders_equity"):
        assert name not in mapped.missing
        assert any(warning.startswith(f"{name} derived") for warning in mapped.warnings)


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        ("Harbor_Logistics_2025.pdf", "Harbor Logistics Group"),
        ("Meridian_Software_2025.pdf", "Meridian Software Inc"),
    ],
)
def test_the_company_name_is_read_from_the_document_title(sample: str, expected: str) -> None:
    suggestion = suggest_inputs([_sample_report(sample)]).company_name

    assert suggestion.value == expected
    assert suggestion.basis == "Document"


def test_the_company_name_falls_back_to_a_cleaned_file_name() -> None:
    report = _report("Acme_Widgets_FY2024_Annual_Report_final", [])

    suggestion = suggest_inputs([report]).company_name

    assert suggestion.value == "Acme Widgets"
    assert suggestion.basis == "Default"


def test_a_comparable_company_added_or_dropped_is_one_readable_row() -> None:
    from pe_analyst.deals.export import input_label

    base = {
        "valuation_assumptions": {"peers": [PEERS[0], PEERS[1]]},
        "risk_inputs": {"altman_z": 3.2},
    }
    other = {"valuation_assumptions": {"peers": [PEERS[0]]}}

    changes = {change.path: (change.base, change.other) for change in diff_inputs(base, other)}

    assert changes == {
        "valuation_assumptions.peers[1]": ("Peer B (included)", "not included"),
        "risk_inputs.altman_z": (3.2, None),
    }
    assert input_label("valuation_assumptions.peers[1]") == "Comparable company 2"
    assert input_label("valuation_assumptions.entry_multiple") == "Entry multiple (EV / EBITDA)"
    assert input_label("risk_inputs.altman_z") == "Risk inputs: altman z"


def test_long_passages_get_a_title_cut_at_a_word() -> None:
    title = DocumentIntelligenceService._title(
        "Our supply chain depends on two component makers, and disruption at either may "
        "increase our costs."
    )

    assert title.endswith("...")
    assert len(title) <= 80
    assert not title.rstrip(".").endswith(" may i")
    assert DocumentIntelligenceService._title("Short sentence.") == "Short sentence."

from agents.due_diligence_tools import DueDiligenceTools
from agents.industry_tools import IndustryTools
from pe_analyst.document_intelligence.agent_inputs import (
    build_due_diligence_inputs,
    build_industry_inputs,
)
from pe_analyst.document_intelligence.schemas import (
    DocumentIntelligenceReport,
    ExtractedNoteSchema,
    ExtractedRiskFactorSchema,
    IndustryEvidenceSchema,
    SourceReferenceSchema,
)


def _report_with_evidence() -> DocumentIntelligenceReport:
    return DocumentIntelligenceReport(
        document_id="doc-1",
        file_name="ExampleCo.pdf",
        page_count=1,
        sections=[],
        statement_line_items=[],
        risk_factors=[
            ExtractedRiskFactorSchema(
                title="Litigation exposure",
                text="The company is party to ongoing litigation.",
                source=SourceReferenceSchema(
                    page_number=9,
                    excerpt="We are party to ongoing litigation.",
                    confidence=0.8,
                ),
            )
        ],
        notes=[
            ExtractedNoteSchema(
                title="Supply chain",
                text="Management noted ongoing supply chain pressure.",
                source=SourceReferenceSchema(
                    page_number=11,
                    excerpt="Supply chain pressure continues.",
                    confidence=0.75,
                ),
            )
        ],
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
        ],
        warnings=[],
    )


def test_build_industry_inputs_matches_the_shape_industry_tools_expects() -> None:
    report = _report_with_evidence()

    inputs = build_industry_inputs(report, industry_name="Widgets")

    assert inputs["industry_name"] == "Widgets"
    assert len(inputs["evidence"]) == 2
    normalized = IndustryTools().validate_and_normalize(inputs)
    assert normalized["industry_name"] == "Widgets"
    assert {item["topic"] for item in normalized["evidence"]} == {"market", "competition"}


def test_build_industry_inputs_carries_optional_fields_through() -> None:
    report = _report_with_evidence()

    inputs = build_industry_inputs(
        report,
        industry_name="Widgets",
        competitors=[{"name": "Acme", "market_share_pct": 20.0}],
        market_growth_pct=5.0,
        competitive_position="Strong",
        porter_forces={"threat_of_new_entrants": "Low"},
        management_themes=["Expansion"],
    )

    assert inputs["market_growth_pct"] == 5.0
    assert inputs["competitive_position"] == "Strong"
    assert inputs["competitors"] == [{"name": "Acme", "market_share_pct": 20.0}]
    assert inputs["porter_forces"] == {"threat_of_new_entrants": "Low"}
    assert inputs["management_themes"] == ["Expansion"]


def test_build_due_diligence_inputs_matches_the_shape_due_diligence_tools_expects() -> None:
    report = _report_with_evidence()

    items = build_due_diligence_inputs(report)

    assert len(items) == 2
    assert {item["category"] for item in items} == {"risk_factor", "note"}
    normalized = DueDiligenceTools().validate_and_normalize(items)
    flags = DueDiligenceTools().evaluate(normalized)
    assert any(flag.title == "Litigation exposure" for flag in flags)


def test_build_due_diligence_inputs_is_empty_when_nothing_was_extracted() -> None:
    report = _report_with_evidence().model_copy(update={"risk_factors": [], "notes": []})

    assert build_due_diligence_inputs(report) == []

import pytest

from agents import AgentState, IndustryAgent


def _industry_inputs() -> dict:
    return {
        "industry_name": "Vertical Software",
        "market_growth_pct": 0.12,
        "competitive_position": "Strong",
        "competitors": [
            {"name": "Peer A", "market_share_pct": 18.0, "positioning": "Enterprise leader"},
        ],
        "porter_forces": {"rivalry": 4, "buyer_power": 3},
        "management_themes": ["Cross-sell expansion"],
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


def test_industry_agent_keeps_source_citations() -> None:
    state = AgentState(company_name="ExampleCo", metadata={"industry_inputs": _industry_inputs()})

    report = IndustryAgent().run(state).metadata["report"]

    assert report.summary.industry_name == "Vertical Software"
    assert report.evidence_count == 3
    assert report.findings[0].citations[0].page_number == 12
    assert state.metadata["industry_report"] is report


def test_industry_agent_rejects_ungrounded_inputs() -> None:
    state = AgentState(
        company_name="ExampleCo", metadata={"industry_inputs": {"industry_name": "Software"}}
    )

    with pytest.raises(ValueError, match="evidence"):
        IndustryAgent().run(state)

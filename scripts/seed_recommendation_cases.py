"""Write synthetic deal archetypes to datasets/recommendation_consistency/.

These cases are labelled from conventional PE judgment, NOT from what the system currently
outputs. A disagreement is a finding about the rules worth investigating, not a broken case.
They are synthetic and marked low-to-medium label confidence: replace or extend them with deals
labelled by someone with PE experience (ideally real past IC decisions) before trusting scores.

    python scripts/seed_recommendation_cases.py
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from pe_analyst.evaluation import DATASETS_DIR

BASE_CURRENT = {
    "revenue": 1_000.0, "cost_of_goods_sold": 600.0, "ebitda": 220.0, "ebit": 150.0,
    "net_income": 100.0, "operating_cash_flow": 140.0, "capital_expenditure": 40.0,
    "total_assets": 1_000.0, "shareholders_equity": 400.0, "total_debt": 200.0,
    "interest_expense": 20.0, "current_assets": 200.0, "inventory": 50.0,
    "current_liabilities": 180.0,
}
BASE_PREVIOUS = {
    "revenue": 900.0, "cost_of_goods_sold": 560.0, "ebitda": 190.0, "ebit": 130.0,
    "net_income": 85.0, "operating_cash_flow": 120.0, "capital_expenditure": 35.0,
    "total_assets": 900.0, "shareholders_equity": 350.0, "total_debt": 210.0,
    "interest_expense": 22.0, "current_assets": 180.0, "inventory": 45.0,
    "current_liabilities": 170.0,
}
PEERS = [
    {"name": "Peer A", "enterprise_value": 1_800.0, "market_cap": 1_600.0, "revenue": 200.0,
     "ebitda": 40.0, "net_income": 20.0, "book_value": 200.0},
    {"name": "Peer B", "enterprise_value": 2_000.0, "market_cap": 1_750.0, "revenue": 250.0,
     "ebitda": 50.0, "net_income": 25.0, "book_value": 225.0},
    {"name": "Peer C", "enterprise_value": 1_650.0, "market_cap": 1_400.0, "revenue": 220.0,
     "ebitda": 44.0, "net_income": 22.0, "book_value": 180.0},
]


def evidence(position: str, growth: float) -> dict[str, Any]:
    return {
        "industry_name": "Vertical Software",
        "market_growth_pct": growth,
        "competitive_position": position,
        "competitors": [{"name": "Peer A", "market_share_pct": 18.0, "positioning": "Leader"}],
        "porter_forces": {"rivalry": 3, "buyer_power": 3},
        "management_themes": ["Cross-sell expansion"],
        "evidence": [
            {"topic": topic, "source": "Annual Report", "page_number": page,
             "excerpt": excerpt, "claim": excerpt, "confidence": 0.85}
            for topic, page, excerpt in (
                ("market", 12, "Market demand remains steady."),
                ("competition", 18, "The market is fragmented."),
                ("management", 26, "Management expects continued execution."),
            )
        ],
    }


def deal(
    *,
    purchase_price: float = 1_600.0,
    ebitda_step: float = 15.0,
    exit_multiple: float = 8.0,
    price: float = 85.0,
    growth: float = 0.08,
    margin: float = 0.20,
    position: str = "Strong",
    market_growth: float = 0.10,
    current: dict[str, float] | None = None,
    previous: dict[str, float] | None = None,
    risk: dict[str, float] | None = None,
    diligence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cur = current or BASE_CURRENT
    return {
        "company_name": "SyntheticCo",
        "current_financials": cur,
        "previous_financials": previous or BASE_PREVIOUS,
        "valuation_inputs": {
            "current_price_per_share": price,
            "dcf": {
                "revenue": cur["revenue"],
                "assumptions": {
                    "revenue_growth": growth, "ebit_margin": margin, "cash": 100.0,
                    "debt": cur["total_debt"], "shares_outstanding": 10.0,
                },
            },
            "comparables": {
                "target": {
                    "revenue": cur["revenue"], "ebitda": cur["ebitda"], "cash": 100.0,
                    "debt": cur["total_debt"], "shares_outstanding": 10.0,
                },
                "peers": PEERS,
            },
            "lbo": {
                "assumptions": {
                    "purchase_price": purchase_price, "holding_period": 5,
                    "exit_multiple": exit_multiple,
                },
                "operating_projection": [
                    {
                        "year": year,
                        "revenue": cur["revenue"] * (1 + growth) ** year,
                        "ebitda": cur["ebitda"] + year * ebitda_step,
                        "taxes": 30.0 + year, "capex": 30.0 + year, "change_in_nwc": 10.0 + year,
                    }
                    for year in range(1, 6)
                ],
            },
        },
        "industry_inputs": evidence(position, market_growth),
        "risk_inputs": risk or {"altman_z": 3.2, "piotroski_score": 7, "industry_risk_score": 30},
        "due_diligence_inputs": diligence or [],
    }


def distressed() -> tuple[dict[str, float], dict[str, float]]:
    current = deepcopy(BASE_CURRENT)
    current.update(
        revenue=850.0, ebitda=90.0, ebit=30.0, net_income=-40.0, operating_cash_flow=20.0,
        shareholders_equity=80.0, total_debt=700.0, interest_expense=60.0,
        current_assets=150.0, current_liabilities=260.0,
    )
    return current, BASE_PREVIOUS


def cheap_quality() -> tuple[dict[str, float], dict[str, float]]:
    current = deepcopy(BASE_CURRENT)
    current.update(net_income=130.0, ebitda=260.0, ebit=190.0, operating_cash_flow=190.0,
                   total_debt=100.0, interest_expense=8.0)
    return current, BASE_PREVIOUS


def middling() -> tuple[dict[str, float], dict[str, float]]:
    current = deepcopy(BASE_CURRENT)
    current.update(net_income=50.0, ebitda=150.0, ebit=90.0, operating_cash_flow=90.0,
                   total_debt=350.0, interest_expense=30.0)
    return current, BASE_PREVIOUS


CASES: list[tuple[str, str, str, str, dict[str, Any]]] = [
    # (id, expected, label confidence, rationale, input)
    (
        "quality-compounder-fair-price", "BUY", "medium",
        "High ROE, low leverage, clean diligence, >20% base IRR at a sensible entry.",
        deal(purchase_price=1_200.0, ebitda_step=25.0, exit_multiple=9.0, position="Leader",
             current=cheap_quality()[0], price=60.0),
    ),
    (
        "good-business-overpriced", "HOLD", "low",
        "Healthy company, but the entry price leaves base IRR well under a 20% hurdle.",
        deal(purchase_price=2_600.0, exit_multiple=8.0, price=140.0),
    ),
    (
        "distressed-overlevered", "REJECT", "high",
        "Loss-making, debt ~7.8x EBITDA, interest coverage <1x, Altman Z in distress zone.",
        deal(purchase_price=1_000.0, ebitda_step=2.0, exit_multiple=6.0, growth=-0.03,
             margin=0.04, position="Weak", market_growth=0.0,
             current=distressed()[0],
             risk={"altman_z": 1.1, "piotroski_score": 2, "industry_risk_score": 70}),
    ),
    (
        "fraud-red-flag", "REJECT", "high",
        "Numbers look fine, but diligence surfaces a restatement and an SEC investigation.",
        deal(
            purchase_price=1_200.0, ebitda_step=25.0, exit_multiple=9.0,
            diligence=[{
                "title": "Restatement of prior-year revenue",
                "text": "The company disclosed a restatement of revenue and an ongoing SEC "
                        "investigation into its revenue recognition practices.",
                "source": "Annual Report", "page_number": 44,
                "excerpt": "restatement ... SEC investigation", "confidence": 0.9,
            }],
        ),
    ),
    (
        "average-business-average-price", "HOLD", "low",
        "~12% ROE, 2.3x leverage, neutral position; returns near but not clearly above hurdle.",
        deal(purchase_price=1_300.0, ebitda_step=10.0, exit_multiple=8.0, position="Neutral",
             market_growth=0.04, margin=0.12, current=middling()[0]),
    ),
    (
        "baseline-fixture", "BUY", "low",
        "The unit-test fixture deal: solid growth and strong position at a moderate price.",
        deal(),
    ),
]


def main() -> None:
    out = DATASETS_DIR / "recommendation_consistency"
    out.mkdir(parents=True, exist_ok=True)
    for index, (case_id, expected, confidence, rationale, case_input) in enumerate(CASES):
        body = {
            "id": case_id,
            # Every third case is held out, so tuning can't overfit the whole set.
            "split": "holdout" if index % 3 == 2 else "dev",
            "input": case_input,
            "expected": expected,
            "metadata": {
                "synthetic": True,
                "label_source": "conventional PE heuristic -- replace with analyst labels",
                "label_confidence": confidence,
                "rationale": rationale,
            },
        }
        (out / f"{case_id}.json").write_text(json.dumps(body, indent=2), encoding="utf-8")
    print(f"Wrote {len(CASES)} cases to {out}")


if __name__ == "__main__":
    main()

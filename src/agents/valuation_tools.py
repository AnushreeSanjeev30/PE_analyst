"""Deterministic valuation tools used by :class:`ValuationAgent`.

The tool layer owns all financial calculations.  The agent only interprets
validated results, preserving a reviewable audit trail for investment teams.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from lbo.assumptions import LBOAssumptions
from lbo.lbo_engine import LBOEngine
from lbo.scenario import ScenarioEngine
from lbo.schemas import OperatingProjection
from lbo.sensitivity import SensitivityEngine
from pe_analyst.valuation import DCFEngine, PeerCompany, ValuationAssumptions
from pe_analyst.valuation.statistics import StatisticsEngine

_DEFAULT_TARGET_IRR = 0.20


class ValuationTools:
    """Bridge between agent input contracts and deterministic valuation engines."""

    @staticmethod
    def _coerce_dcf_assumptions(raw: Any) -> ValuationAssumptions:
        if isinstance(raw, ValuationAssumptions):
            return raw
        if isinstance(raw, dict):
            return ValuationAssumptions(**raw)
        raise TypeError("dcf.assumptions must be a ValuationAssumptions instance or dictionary")

    @staticmethod
    def _coerce_peer(raw: Any) -> PeerCompany:
        if isinstance(raw, PeerCompany):
            return raw
        if isinstance(raw, dict):
            return PeerCompany(**raw)
        raise TypeError("Each peer must be a PeerCompany instance or dictionary")

    @staticmethod
    def _coerce_lbo_assumptions(raw: Any) -> LBOAssumptions:
        if isinstance(raw, LBOAssumptions):
            raw.validate()
            return raw
        if isinstance(raw, dict):
            assumptions = LBOAssumptions(**raw)
            assumptions.validate()
            return assumptions
        raise TypeError("lbo.assumptions must be an LBOAssumptions instance or dictionary")

    @staticmethod
    def _coerce_projection(raw: Any) -> OperatingProjection:
        if isinstance(raw, OperatingProjection):
            return raw
        if isinstance(raw, dict):
            return OperatingProjection(**raw)
        raise TypeError("Each LBO operating projection must be a dictionary or OperatingProjection")

    def run_dcf(self, dcf_input: dict[str, Any]) -> dict[str, Any]:
        if "revenue" not in dcf_input or "assumptions" not in dcf_input:
            raise ValueError("dcf input requires revenue and assumptions")
        revenue = float(dcf_input["revenue"])
        if revenue <= 0:
            raise ValueError("dcf.revenue must be positive")
        assumptions = self._coerce_dcf_assumptions(dcf_input["assumptions"])
        if assumptions.shares_outstanding <= 0:
            raise ValueError("DCF shares_outstanding must be positive")
        result = DCFEngine(assumptions).calculate(revenue)
        return {"result": asdict(result), "assumptions": asdict(assumptions)}

    def run_comparables(self, comparable_input: dict[str, Any]) -> dict[str, Any]:
        peers_raw = comparable_input.get("peers", [])
        if len(peers_raw) < 2:
            raise ValueError("Comparable analysis requires at least two peer companies")
        peers = [self._coerce_peer(peer) for peer in peers_raw]
        target = comparable_input.get("target", {})
        required = {"revenue", "ebitda", "cash", "debt", "shares_outstanding"}
        missing = required - target.keys()
        if missing:
            raise ValueError(f"comparables.target is missing: {', '.join(sorted(missing))}")
        if target["revenue"] <= 0 or target["shares_outstanding"] <= 0:
            raise ValueError("Target revenue and shares_outstanding must be positive")

        ev_revenue = [peer.ev_revenue for peer in peers if peer.ev_revenue > 0]
        ev_ebitda = [peer.ev_ebitda for peer in peers if peer.ev_ebitda > 0]
        if not ev_revenue and not ev_ebitda:
            raise ValueError(
                "Peers must contain at least one positive EV/revenue or EV/EBITDA multiple"
            )
        implied_values: dict[str, float] = {}
        if ev_revenue:
            implied_values["ev_revenue"] = StatisticsEngine.median(ev_revenue) * float(
                target["revenue"]
            )
        if ev_ebitda and float(target["ebitda"]) > 0:
            implied_values["ev_ebitda"] = StatisticsEngine.median(ev_ebitda) * float(
                target["ebitda"]
            )
        enterprise_value = StatisticsEngine.mean(list(implied_values.values()))
        equity_value = enterprise_value - float(target["debt"]) + float(target["cash"])
        return {
            "peer_count": len(peers),
            "median_ev_revenue": StatisticsEngine.median(ev_revenue),
            "median_ev_ebitda": StatisticsEngine.median(ev_ebitda),
            "implied_enterprise_value": enterprise_value,
            "implied_equity_value": equity_value,
            "implied_value_per_share": equity_value / float(target["shares_outstanding"]),
            "methods": implied_values,
        }

    def run_lbo(self, lbo_input: dict[str, Any]) -> dict[str, Any]:
        if "assumptions" not in lbo_input or "operating_projection" not in lbo_input:
            raise ValueError("lbo input requires assumptions and operating_projection")
        assumptions = self._coerce_lbo_assumptions(lbo_input["assumptions"])
        projections = [self._coerce_projection(item) for item in lbo_input["operating_projection"]]
        if len(projections) != assumptions.holding_period:
            raise ValueError("LBO operating_projection length must equal holding_period")
        return {
            "result": asdict(LBOEngine(assumptions).run(projections)),
            "assumptions": asdict(assumptions),
        }

    def run_scenarios(
        self, lbo_input: dict[str, Any], *, target_irr: float = _DEFAULT_TARGET_IRR
    ) -> dict[str, Any]:
        if "assumptions" not in lbo_input or "operating_projection" not in lbo_input:
            raise ValueError("lbo input requires assumptions and operating_projection")
        assumptions = self._coerce_lbo_assumptions(lbo_input["assumptions"])
        projections = [self._coerce_projection(item) for item in lbo_input["operating_projection"]]
        if len(projections) != assumptions.holding_period:
            raise ValueError("LBO operating_projection length must equal holding_period")

        outcomes = ScenarioEngine(assumptions, projections).run()
        try:
            breakeven = SensitivityEngine(assumptions, projections).breakeven_exit_multiple(
                target_irr
            )
        except ValueError:
            breakeven = None
        return {
            "target_irr": target_irr,
            "outcomes": outcomes,
            "breakeven_exit_multiple": breakeven,
        }

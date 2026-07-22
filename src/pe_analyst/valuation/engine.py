from .assumptions import ValuationAssumptions
from .dcf import DCFEngine
from .multiples import MultiplesEngine


class ValuationEngine:
    def __init__(self, assumptions: ValuationAssumptions | None = None):
        self.assumptions = assumptions or ValuationAssumptions()
        self.dcf = DCFEngine(self.assumptions)
        self.multiples = MultiplesEngine()

    def value_company(self, revenue: float) -> dict[str, float | ValuationAssumptions]:
        ev = self.dcf.enterprise_value(revenue)

        return {
            "enterprise_value": ev,
            "assumptions": self.assumptions,
        }

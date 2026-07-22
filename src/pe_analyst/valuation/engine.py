from .assumptions import ValuationAssumptions
from .dcf import DCFEngine
from .results import DCFResult


class ValuationEngine:
    def __init__(self, assumptions: ValuationAssumptions):
        self.dcf = DCFEngine(assumptions)

    def value_company(self, revenue: float) -> DCFResult:
        return self.dcf.calculate(revenue)

from dataclasses import dataclass

from .assumptions import LBOAssumptions
from .schemas import Acquisition


@dataclass(slots=True)
class SourcesUsesAnalysis:
    acquisition: Acquisition

    @property
    def sources(self) -> float:
        return self.acquisition.total_sources

    @property
    def uses(self) -> float:
        return self.acquisition.total_uses

    @property
    def funding_gap(self) -> float:
        return self.sources - self.uses

    @property
    def balanced(self) -> bool:
        return abs(self.funding_gap) < 1e-6


class SourcesUsesBuilder:

    @staticmethod
    def build(
        assumptions: LBOAssumptions,
    ) -> SourcesUsesAnalysis:

        assumptions.validate()

        acquisition = Acquisition(
            purchase_price=assumptions.purchase_price,

            equity_contribution=assumptions.equity_amount,

            debt_contribution=assumptions.debt_amount,

            transaction_fees=assumptions.transaction_fees,

            financing_fees=assumptions.financing_fees,

            cash_to_balance_sheet=assumptions.cash_on_balance_sheet,
        )

        return SourcesUsesAnalysis(acquisition)
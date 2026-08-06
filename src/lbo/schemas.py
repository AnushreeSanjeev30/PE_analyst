from dataclasses import dataclass


@dataclass(slots=True)
class Acquisition:
    purchase_price: float
    equity_contribution: float
    debt_contribution: float

    transaction_fees: float
    financing_fees: float

    cash_to_balance_sheet: float = 0.0

    @property
    def enterprise_value(self) -> float:
        return self.purchase_price

    @property
    def total_uses(self) -> float:
        return (
            self.purchase_price
            + self.transaction_fees
            + self.financing_fees
            + self.cash_to_balance_sheet
        )

    @property
    def total_sources(self) -> float:
        return (
            self.equity_contribution
            + self.debt_contribution
        )
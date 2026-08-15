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
        return self.equity_contribution + self.debt_contribution


@dataclass(slots=True)
class OperatingProjection:
    year: int
    revenue: float
    ebitda: float
    taxes: float
    capex: float
    change_in_nwc: float


@dataclass(slots=True)
class DebtTranche:
    name: str
    opening_balance: float
    interest_rate: float
    mandatory_amortization: float
    optional_amortization: float = 0.0
    interest_expense: float = 0.0
    closing_balance: float = 0.0


@dataclass(slots=True)
class CashFlowWaterfall:
    year: int
    operating_cash_flow: float
    interest_paid: float
    debt_repayment: float
    ending_cash: float


@dataclass(slots=True)
class ExitAnalysis:
    exit_year: int
    exit_multiple: float
    exit_ebitda: float
    enterprise_value: float
    equity_value: float


@dataclass(slots=True)
class LBOResult:
    irr: float
    moic: float
    exit_equity: float
    exit_enterprise_value: float
    debt_remaining: float
    annual_cashflows: list[float]

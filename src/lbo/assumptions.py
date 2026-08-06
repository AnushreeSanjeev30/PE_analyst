from dataclasses import dataclass


@dataclass(slots=True)
class LBOAssumptions:
    """
    Central configuration object for the LBO model.
    All percentages are expressed as decimals.
    """

    # Acquisition
    purchase_price: float

    equity_percentage: float = 0.40
    debt_percentage: float = 0.60

    transaction_fee_pct: float = 0.02
    financing_fee_pct: float = 0.01

    # Projection
    holding_period: int = 5

    revenue_growth: float = 0.06
    ebitda_growth: float = 0.07

    tax_rate: float = 0.25

    capex_pct_sales: float = 0.03

    depreciation_pct_sales: float = 0.02

    nwc_pct_sales: float = 0.01

    # Debt
    interest_rate: float = 0.08

    mandatory_amortization_pct: float = 0.10

    # Exit
    exit_multiple: float = 8.0

    # Misc
    cash_on_balance_sheet: float = 0.0

    management_rollover: float = 0.0

    @property
    def equity_amount(self) -> float:
        return self.purchase_price * self.equity_percentage

    @property
    def debt_amount(self) -> float:
        return self.purchase_price * self.debt_percentage

    @property
    def transaction_fees(self) -> float:
        return self.purchase_price * self.transaction_fee_pct

    @property
    def financing_fees(self) -> float:
        return self.purchase_price * self.financing_fee_pct

    def validate(self) -> None:
        if abs(self.equity_percentage + self.debt_percentage - 1.0) > 1e-6:
            raise ValueError(
                "Debt % + Equity % must equal 100%"
            )

        if self.purchase_price <= 0:
            raise ValueError(
                "Purchase price must be positive."
            )

        if self.holding_period <= 0:
            raise ValueError(
                "Holding period must be positive."
            )

        if self.exit_multiple <= 0:
            raise ValueError(
                "Exit multiple must be positive."
            )
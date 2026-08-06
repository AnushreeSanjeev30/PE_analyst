from .assumptions import LBOAssumptions
from .schemas import (
    CashFlowWaterfall,
    DebtTranche,
    OperatingProjection,
)


class CashFlowEngine:

    def __init__(
        self,
        assumptions: LBOAssumptions,
    ):

        self.assumptions = assumptions

    def build(
        self,
        operating_projection: list[OperatingProjection],
        debt_schedule: list[DebtTranche],
    ) -> list[CashFlowWaterfall]:

        waterfall = []

        cash = self.assumptions.cash_on_balance_sheet

        for projection, debt in zip(
            operating_projection,
            debt_schedule,
        ):

            operating_cf = (

                projection.ebitda

                - projection.taxes

                - projection.capex

                - projection.change_in_nwc

            )

            debt_payment = (

                debt.opening_balance

                - debt.closing_balance

            )

            cash += (

                operating_cf

                - debt.interest_expense

                - debt_payment

            )

            waterfall.append(

                CashFlowWaterfall(

                    year=projection.year,

                    operating_cash_flow=operating_cf,

                    interest_paid=debt.interest_expense,

                    debt_repayment=debt_payment,

                    ending_cash=cash,

                )

            )

        return waterfall
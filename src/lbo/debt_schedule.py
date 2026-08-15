from copy import deepcopy

from .assumptions import LBOAssumptions
from .schemas import DebtTranche


class DebtSchedule:

    def __init__(
        self,
        assumptions: LBOAssumptions,
    ):

        self.assumptions = assumptions

        self.tranche = DebtTranche(
            name="Senior Debt",
            opening_balance=assumptions.debt_amount,
            interest_rate=assumptions.interest_rate,
            mandatory_amortization=assumptions.mandatory_amortization_pct,
        )

    def project(self) -> list[DebtTranche]:

        debt = deepcopy(self.tranche)

        schedule: list[DebtTranche] = []

        for _year in range(1, self.assumptions.holding_period + 1):

            opening = debt.opening_balance

            mandatory_payment = (
                opening
                * debt.mandatory_amortization
            )

            optional_payment = debt.optional_amortization

            closing = max(
                0.0,
                opening
                - mandatory_payment
                - optional_payment,
            )

            debt.interest_expense = (
                opening
                * debt.interest_rate
            )

            debt.closing_balance = closing

            schedule.append(deepcopy(debt))

            debt.opening_balance = closing

        return schedule
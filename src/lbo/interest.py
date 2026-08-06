from .schemas import DebtTranche


class InterestEngine:

    @staticmethod
    def calculate(
        debt_schedule: list[DebtTranche],
    ) -> list[float]:

        interest = []

        for debt in debt_schedule:

            avg_balance = (
                debt.opening_balance
                + debt.closing_balance
            ) / 2

            interest.append(
                avg_balance
                * debt.interest_rate
            )

        return interest
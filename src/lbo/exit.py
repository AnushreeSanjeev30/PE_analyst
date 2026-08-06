from .schemas import (
    DebtTranche,
    ExitAnalysis,
    OperatingProjection,
)


class ExitEngine:

    @staticmethod
    def calculate(
        operating_projection: list[OperatingProjection],
        debt_schedule: list[DebtTranche],
        exit_multiple: float,
    ) -> ExitAnalysis:

        final_projection = operating_projection[-1]

        remaining_debt = debt_schedule[-1].closing_balance

        enterprise_value = (
            final_projection.ebitda
            * exit_multiple
        )

        equity_value = (
            enterprise_value
            - remaining_debt
        )

        return ExitAnalysis(
            exit_year=final_projection.year,
            exit_multiple=exit_multiple,
            exit_ebitda=final_projection.ebitda,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
        )
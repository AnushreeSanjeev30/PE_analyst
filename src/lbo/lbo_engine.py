from .assumptions import LBOAssumptions
from .cash_flow import CashFlowEngine
from .debt_schedule import DebtSchedule
from .exit import ExitEngine
from .irr import IRREngine
from .schemas import (
    LBOResult,
    OperatingProjection,
)


class LBOEngine:

    def __init__(
        self,
        assumptions: LBOAssumptions,
    ):

        self.assumptions = assumptions

    def run(
        self,
        operating_projection: list[OperatingProjection],
    ) -> LBOResult:

        debt_schedule = (
            DebtSchedule(
                self.assumptions
            ).project()
        )

        CashFlowEngine(
            self.assumptions
        ).build(
            operating_projection,
            debt_schedule,
        )

        exit_analysis = (
            ExitEngine.calculate(
                operating_projection,
                debt_schedule,
                self.assumptions.exit_multiple,
            )
        )

        irr = IRREngine.irr(
            self.assumptions.equity_amount,
            exit_analysis.equity_value,
            self.assumptions.holding_period,
        )

        moic = IRREngine.moic(
            self.assumptions.equity_amount,
            exit_analysis.equity_value,
        )

        return LBOResult(
            irr=irr,
            moic=moic,
            exit_equity=exit_analysis.equity_value,
            exit_enterprise_value=exit_analysis.enterprise_value,
            debt_remaining=debt_schedule[-1].closing_balance,
            annual_cashflows=[
                -self.assumptions.equity_amount,
                exit_analysis.equity_value,
            ],
        )
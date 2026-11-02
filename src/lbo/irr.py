import math


class IRREngine:

    @staticmethod
    def moic(
        invested_equity: float,
        exit_equity: float,
    ) -> float:

        return (
            exit_equity
            / invested_equity
        )

    @staticmethod
    def irr(
        invested_equity: float,
        exit_equity: float,
        years: int,
    ) -> float:

        # Equity holders cannot lose more than they invested: a wiped-out or negative
        # exit equity value is a total loss, i.e. -100% IRR, not an undefined fractional
        # power of a negative number.
        if exit_equity <= 0:

            return -1.0

        return (
            math.pow(
                exit_equity / invested_equity,
                1 / years,
            )
            - 1
        )
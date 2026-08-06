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

        return (
            math.pow(
                exit_equity / invested_equity,
                1 / years,
            )
            - 1
        )
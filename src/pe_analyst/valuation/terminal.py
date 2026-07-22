class TerminalValueEngine:
    @staticmethod
    def gordon_growth(
        fcff: float,
        wacc: float,
        growth: float,
    ) -> float:
        if growth >= wacc:
            raise ValueError("Terminal growth must be less than WACC.")

        return fcff * (1 + growth) / (wacc - growth)

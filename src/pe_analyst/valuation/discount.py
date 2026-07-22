class DiscountEngine:
    @staticmethod
    def present_value(
        cash_flow: float,
        rate: float,
        year: int,
    ) -> float:
        return cash_flow / ((1 + rate) ** year)

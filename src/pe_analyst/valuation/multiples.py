class MultiplesEngine:
    @staticmethod
    def ev_ebitda(ev: float, ebitda: float) -> float:
        if ebitda == 0:
            return 0.0

        return ev / ebitda

    @staticmethod
    def ev_revenue(ev: float, revenue: float) -> float:
        if revenue == 0:
            return 0.0

        return ev / revenue

    @staticmethod
    def pe(price: float, earnings: float) -> float:
        if earnings == 0:
            return 0.0

        return price / earnings

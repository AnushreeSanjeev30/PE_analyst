from dataclasses import dataclass


@dataclass(slots=True)
class DCFResult:
    enterprise_value: float
    equity_value: float
    terminal_value: float
    pv_fcff: float
    price_per_share: float

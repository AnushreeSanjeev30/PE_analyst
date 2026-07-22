import pytest

from pe_analyst.valuation import DiscountEngine


def test_present_value():
    assert DiscountEngine.present_value(
        100,
        0.10,
        1,
    ) == pytest.approx(90.90909)

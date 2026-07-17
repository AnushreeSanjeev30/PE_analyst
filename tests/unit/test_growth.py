import pytest

from pe_analyst.engines.financial.growth import (
    average_growth,
    cagr,
    growth_rate,
    project_value,
)


def test_growth_rate():
    assert growth_rate(100, 120) == pytest.approx(0.20)


def test_growth_rate_negative():
    assert growth_rate(100, 80) == pytest.approx(-0.20)


def test_growth_zero():
    with pytest.raises(ZeroDivisionError):
        growth_rate(0, 100)


def test_cagr():
    assert cagr(100, 133.1, 3) == pytest.approx(
        0.10,
        abs=1e-3,
    )


def test_average_growth():
    assert average_growth(
        [0.10, 0.20, 0.30]
    ) == pytest.approx(0.20)


def test_projection():
    assert project_value(
        100,
        0.10,
        2,
    ) == pytest.approx(121)
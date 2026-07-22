from pe_analyst.valuation import StatisticsEngine


def test_mean():
    assert StatisticsEngine.mean([1, 2, 3]) == 2


def test_median():
    assert StatisticsEngine.median([1, 2, 3]) == 2


def test_minimum():
    assert StatisticsEngine.minimum([5, 1, 9]) == 1


def test_maximum():
    assert StatisticsEngine.maximum([5, 1, 9]) == 9


def test_percentile_25():
    result = StatisticsEngine.percentile(
        [1, 2, 3, 4],
        0.25,
    )

    assert result == 1.75


def test_percentile_75():
    result = StatisticsEngine.percentile(
        [1, 2, 3, 4],
        0.75,
    )

    assert result == 3.25

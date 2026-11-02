import pytest

from pe_analyst.core.config import Settings
from pe_analyst.market_data import (
    MarketDataProviderError,
    UnconfiguredMarketDataProvider,
    build_market_data_provider,
)


def test_unconfigured_provider_raises_a_clear_error_instead_of_fabricating_data() -> None:
    provider = UnconfiguredMarketDataProvider()

    with pytest.raises(MarketDataProviderError, match="No market-data vendor is configured"):
        provider.get_comparable_companies("Industrials")


def test_build_market_data_provider_returns_unconfigured_by_default(
    test_settings: Settings,
) -> None:
    provider = build_market_data_provider(test_settings)

    assert isinstance(provider, UnconfiguredMarketDataProvider)


def test_build_market_data_provider_rejects_an_unimplemented_vendor(
    test_settings: Settings,
) -> None:
    settings = test_settings.model_copy(update={"market_data_provider": "bloomberg"})

    with pytest.raises(MarketDataProviderError, match="Unknown MARKET_DATA_PROVIDER"):
        build_market_data_provider(settings)

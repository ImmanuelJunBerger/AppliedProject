import pytest

pd = pytest.importorskip("pandas")

from crypto_mlsystem.derivatives_data import fetch_funding_history


class FakeFundingExchange:
    def load_markets(self):
        return {
            "BTC/USDT:USDT": {
                "base": "BTC", "quote": "USDT", "settle": "USDT",
                "swap": True, "linear": True, "active": True,
            },
            "ETH/USD:USD": {
                "base": "ETH", "quote": "USD", "settle": "USD",
                "swap": True, "linear": False, "active": True,
            },
        }

    def parse8601(self, value):
        return int(pd.Timestamp(value).timestamp() * 1000)

    def fetch_funding_rate_history(self, symbol, since=None, limit=1000):
        first = self.parse8601("2020-01-01T00:00:00Z")
        second = self.parse8601("2020-01-01T08:00:00Z")
        if since <= first:
            return [
                {"timestamp": first, "fundingRate": 0.0001},
                {"timestamp": second, "fundingRate": -0.00005},
            ]
        return []


def test_funding_history_maps_contracts_and_aggregates_daily():
    frame, missing = fetch_funding_history(
        ["BTC", "ETH"], since="2020-01-01", until="2020-01-02",
        limit=2, sleep_seconds=0, exchange=FakeFundingExchange(),
    )
    assert missing == ["ETH"]
    assert len(frame) == 1
    assert frame.iloc[0].symbol == "BTC"
    assert frame.iloc[0].funding_rate == pytest.approx(0.00005)


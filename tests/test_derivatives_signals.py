import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from crypto_mlsystem.data import DataIngestion
from crypto_mlsystem.derivatives_data import download_public_derivatives
from crypto_mlsystem.derivatives_features import build_derivatives_features
from crypto_mlsystem.derivatives_research import strategy_weights


class FakeDownloader:
    def funding_history(self, symbol, start, end):
        dates = pd.date_range(start, end, freq="8h")
        return [
            {"fundingTime": int(date.timestamp() * 1000), "fundingRate": str(0.0001)}
            for date in dates
        ]

    def premium_index_history(self, symbol, start, end):
        dates = pd.date_range(start, end, freq="D")
        return [[int(date.timestamp() * 1000), "0.001", "0.002", "-0.001", "0.001", "0", int(date.timestamp() * 1000) + 1, "0", 1, "0", "0", "0"] for date in dates]

    def recent_metric(self, endpoint, symbol, period="1d", limit=500):
        dates = pd.date_range("2026-05-01", periods=30, freq="D")
        if "openInterest" in endpoint:
            return [{"timestamp": int(date.timestamp() * 1000), "sumOpenInterestValue": "1000000"} for date in dates]
        if "globalLongShort" in endpoint:
            return [{"timestamp": int(date.timestamp() * 1000), "longShortRatio": "1.1"} for date in dates]
        return [{"timestamp": int(date.timestamp() * 1000), "buyVol": "110", "sellVol": "100"} for date in dates]


def _spot_and_derivatives(days=600):
    panel = DataIngestion().synthetic_panel(days=days, assets=4, seed=51)
    panel.loc[panel.symbol == "COIN01", "symbol"] = "BTC"
    panel.loc[panel.symbol == "COIN02", "symbol"] = "ETH"
    panel = panel[panel.symbol.isin(["BTC", "ETH"])]
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    derivatives = pd.DataFrame([
        {"date": date, "symbol": symbol, "funding_rate": 0.0001 * np.sin(number / 20), "basis_close": 0.001}
        for symbol in ("BTC", "ETH") for number, date in enumerate(dates)
    ])
    return panel, derivatives


def test_downloader_persists_raw_and_processed_coverage(tmp_path):
    processed, coverage = download_public_derivatives(
        tmp_path / "raw", tmp_path / "processed", symbols=("BTCUSDT",),
        start="2020-01-01", end="2021-12-31", downloader=FakeDownloader(),
    )
    assert (tmp_path / "raw" / "BTCUSDT_funding.json").exists()
    assert (tmp_path / "processed" / "binance_derivatives_daily.csv").exists()
    assert {"funding_rate", "basis_close", "open_interest", "taker_imbalance"}.issubset(processed.columns)
    assert coverage.loc[coverage.dataset == "funding", "usable_for_locked_study"].iloc[0]
    assert not coverage.loc[coverage.dataset == "open_interest", "usable_for_locked_study"].iloc[0]


def test_derivatives_features_are_lagged_one_full_day():
    panel, derivatives = _spot_and_derivatives()
    original = build_derivatives_features(panel, derivatives)
    decision = pd.Timestamp(original.frame.date.unique()[300])
    changed = derivatives.copy()
    changed.loc[changed.date == decision, "funding_rate"] = 0.25
    revised = build_derivatives_features(panel, changed)
    original_row = original.frame[(original.frame.date == decision) & (original.frame.symbol == "BTC")].iloc[0]
    revised_row = revised.frame[(revised.frame.date == decision) & (revised.frame.symbol == "BTC")].iloc[0]
    assert original_row.funding_rate == revised_row.funding_rate
    next_date = decision + pd.Timedelta(days=1)
    next_original = original.frame[(original.frame.date == next_date) & (original.frame.symbol == "BTC")].iloc[0]
    next_revised = revised.frame[(revised.frame.date == next_date) & (revised.frame.symbol == "BTC")].iloc[0]
    assert next_original.funding_rate != next_revised.funding_rate


def test_recent_open_interest_is_excluded_and_oi_strategies_are_unavailable():
    panel, derivatives = _spot_and_derivatives()
    last_dates = sorted(derivatives.date.unique())[-20:]
    derivatives.loc[derivatives.date.isin(last_dates), "open_interest"] = 1_000_000
    dataset = build_derivatives_features(panel, derivatives, holdout_start="2021-01-01")
    assert "open_interest_change_7" not in dataset.feature_sets["derivatives_only"]
    weights, reason = strategy_weights(dataset, "oi_confirmed_trend")
    assert weights is None
    assert "insufficient" in reason.lower()


def test_future_prices_change_targets_not_time_t_features():
    panel, derivatives = _spot_and_derivatives()
    original = build_derivatives_features(panel, derivatives)
    decision = pd.Timestamp(original.frame.date.unique()[300])
    changed = panel.copy()
    mask = (
        (changed.symbol == "BTC") & (changed.date > decision)
        & (changed.date <= decision + pd.Timedelta(days=7))
    )
    changed.loc[mask, ["open", "high", "low", "close"]] *= 1.5
    revised = build_derivatives_features(changed, derivatives)
    first = original.frame[(original.frame.date == decision) & (original.frame.symbol == "BTC")].iloc[0]
    second = revised.frame[(revised.frame.date == decision) & (revised.frame.symbol == "BTC")].iloc[0]
    pd.testing.assert_series_equal(
        first[original.feature_sets["price_derivatives"]],
        second[original.feature_sets["price_derivatives"]],
        check_names=False,
    )
    assert first.forward_return_7 != second.forward_return_7


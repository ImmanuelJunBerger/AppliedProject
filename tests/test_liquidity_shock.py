import numpy as np
import pandas as pd

from crypto_mlsystem.liquidity_shock import (
    _development_thresholds,
    _shock_transform,
    build_liquidity_shock_dataset,
    liquidity_shock_candidates,
)
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def test_shock_transform_uses_only_prior_observations():
    dates = pd.date_range("2020-01-01", periods=260, freq="D")
    series = pd.Series(np.linspace(0, 1, len(dates)), index=dates)
    baseline = _shock_transform(series)

    changed_future = series.copy()
    changed_future.iloc[220:] = 999.0
    changed = _shock_transform(changed_future)

    pd.testing.assert_series_equal(
        baseline.loc[: dates[219], "z"],
        changed.loc[: dates[219], "z"],
        check_names=False,
    )


def test_liquidity_shock_candidates_cover_required_dimensions():
    candidates = liquidity_shock_candidates()
    assert {candidate.universe_size for candidate in candidates} == {10, 20}
    assert {candidate.rebalance_days for candidate in candidates} == {7, 14}
    assert {"positive_liquidity_continuation", "negative_liquidity_risk_off", "combined_shock_index"}.issubset(
        {candidate.family for candidate in candidates}
    )
    assert {"btc_eth", "top_momentum", "top_losers"}.issubset({candidate.allocation for candidate in candidates})


def _synthetic_public_data(dates: pd.DatetimeIndex, holdout_multiplier: float = 1.0) -> PublicDataBundle:
    stable_supply = 100_000_000 + np.arange(len(dates)) * 10_000.0
    tvl = 1_000_000_000 + np.arange(len(dates)) * 50_000.0
    holdout = dates >= pd.Timestamp("2025-01-01")
    stable_supply = stable_supply.copy()
    tvl = tvl.copy()
    stable_supply[holdout] *= holdout_multiplier
    tvl[holdout] *= holdout_multiplier
    stable = pd.DataFrame({
        "date": dates,
        "stablecoin_supply": stable_supply,
        "stablecoin_supply_usd": stable_supply,
    })
    stable["stablecoin_supply_change_7d"] = stable.stablecoin_supply_usd.pct_change(7, fill_method=None)
    chain_tvl = pd.DataFrame({"date": dates, "chain": "all", "tvl": tvl})
    rows = []
    for symbol in ("BTC", "ETH"):
        rows.append(pd.DataFrame({
            "date": dates,
            "symbol": symbol,
            "volatility_4h_7d": 0.02 + 0.001 * np.sin(np.arange(len(dates)) / 20.0),
        }))
    intraday = pd.concat(rows, ignore_index=True)
    return PublicDataBundle(
        coverage=pd.DataFrame(),
        stablecoins=stable,
        chain_tvl=chain_tvl,
        protocol_tvl=pd.DataFrame(),
        coingecko_markets=pd.DataFrame(),
        coingecko_categories=pd.DataFrame(),
        coingecko_coin_daily=pd.DataFrame(),
        binance_4h=pd.DataFrame(),
        binance_4h_daily_features=intraday,
        token_unlocks=pd.DataFrame(),
        metadata={},
    )


def _synthetic_panel(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT", "LTC", "TRX"]
    for i, symbol in enumerate(symbols):
        base_return = 0.0002 + i * 0.00001
        noise = 0.01 * np.sin(np.arange(len(dates)) / (11 + i))
        close = 100 * np.cumprod(1 + base_return + noise)
        volume = 1_000_000 + i * 100_000 + 10_000 * np.cos(np.arange(len(dates)) / 13.0)
        rows.append(pd.DataFrame({
            "date": dates,
            "symbol": symbol,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": volume,
            "market_cap": close * volume,
        }))
    return pd.concat(rows, ignore_index=True)


def test_development_thresholds_ignore_holdout_public_data_changes():
    dates = pd.date_range("2019-01-01", "2026-06-22", freq="D")
    panel = _synthetic_panel(dates)
    dataset = build_liquidity_shock_dataset(panel, _synthetic_public_data(dates))
    changed = build_liquidity_shock_dataset(panel, _synthetic_public_data(dates, holdout_multiplier=100.0))
    assert dataset.thresholds == changed.thresholds
    direct = _development_thresholds(dataset.shock_features)
    assert direct == dataset.thresholds

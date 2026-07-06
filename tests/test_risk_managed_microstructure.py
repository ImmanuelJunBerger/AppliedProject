import numpy as np
import pandas as pd

from crypto_mlsystem.risk_managed_microstructure import (
    RiskManagedMomentumCandidate,
    aggregate_agg_trades_to_microstructure_features,
    build_risk_managed_momentum_dataset,
    build_risk_managed_weights,
    microstructure_feature_inventory,
    risk_managed_momentum_candidates,
)


def _synthetic_panel() -> pd.DataFrame:
    dates = pd.date_range("2019-01-01", "2026-06-22", freq="D")
    rows = []
    symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT", "LTC", "TRX"]
    for i, symbol in enumerate(symbols):
        returns = 0.0002 + i * 0.00001 + 0.006 * np.sin(np.arange(len(dates)) / (17 + i))
        close = 100 * np.cumprod(1 + returns)
        volume = 1_000_000 + i * 100_000 + 10_000 * np.cos(np.arange(len(dates)) / 11.0)
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


def test_risk_managed_weights_are_long_only_and_unlevered():
    dataset = build_risk_managed_momentum_dataset(_synthetic_panel())
    candidate = RiskManagedMomentumCandidate(
        name="test",
        universe_size=10,
        rebalance_days=7,
        momentum_days=21,
        top_k=3,
        volatility_lookback=30,
        target_volatility=0.25,
    )
    weights = build_risk_managed_weights(dataset, candidate)
    assert (weights.fillna(0) >= -1e-12).all().all()
    assert weights.sum(axis=1).max() <= 1.0 + 1e-12


def test_candidate_grid_covers_required_baseline_dimensions():
    candidates = risk_managed_momentum_candidates()
    assert {candidate.universe_size for candidate in candidates} == {10, 20, 30}
    assert {candidate.rebalance_days for candidate in candidates} == {7, 14}
    assert {candidate.momentum_days for candidate in candidates} == {21, 63, 126}


def test_agg_trade_microstructure_aggregation():
    trades = pd.DataFrame({
        "T": [1_700_000_000_000, 1_700_000_100_000, 1_700_000_200_000, 1_700_000_300_000],
        "p": ["100.0", "101.0", "99.0", "102.0"],
        "q": ["1.0", "2.0", "1.5", "0.5"],
        "m": [False, True, False, True],
    })
    features = aggregate_agg_trades_to_microstructure_features(trades, "1h")
    assert not features.empty
    assert "taker_buy_sell_imbalance" in features
    assert "volume_concentration" in features
    assert np.isfinite(features.taker_buy_sell_imbalance.iloc[0])


def test_microstructure_inventory_contains_required_features():
    inventory = microstructure_feature_inventory()
    required = {
        "spread_over_mid",
        "l1_imbalance",
        "depth_imbalance",
        "taker_buy_sell_imbalance",
        "trade_count_imbalance",
        "net_order_flow",
        "short_horizon_volatility",
    }
    assert required.issubset(set(inventory.feature))

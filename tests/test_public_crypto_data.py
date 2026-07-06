import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

from crypto_mlsystem.data import DataIngestion
from crypto_mlsystem.feature_research import build_feature_research_frame, information_coefficient_report
from crypto_mlsystem.public_crypto_data import (
    PublicDataBundle,
    build_4h_daily_features,
    build_liquidity_conditioned_weights,
    parse_stablecoin_chart,
)


def test_parse_stablecoin_chart_builds_growth_features():
    payload = [
        {"date": str(int(pd.Timestamp("2020-01-01", tz="UTC").timestamp())), "totalCirculating": {"peggedUSD": 100}},
        {"date": str(int(pd.Timestamp("2020-01-31", tz="UTC").timestamp())), "totalCirculating": {"peggedUSD": 120}},
        {"date": str(int(pd.Timestamp("2020-04-01", tz="UTC").timestamp())), "totalCirculating": {"peggedUSD": 150}},
    ]
    frame = parse_stablecoin_chart(payload)
    assert "stablecoin_supply_change_30d" in frame.columns
    assert frame.stablecoin_supply.iloc[-1] == 150


def test_4h_features_are_lagged_to_daily_decisions():
    timestamps = pd.date_range("2020-01-01", periods=100, freq="4h")
    raw = pd.DataFrame({
        "timestamp": timestamps,
        "date": timestamps.normalize(),
        "symbol": "BTC",
        "open": np.linspace(100, 130, len(timestamps)),
        "high": np.linspace(101, 131, len(timestamps)),
        "low": np.linspace(99, 129, len(timestamps)),
        "close": np.linspace(100, 140, len(timestamps)),
        "volume": 10,
        "quote_volume": np.linspace(1000, 2000, len(timestamps)),
    })
    features = build_4h_daily_features(raw)
    assert {"trend_4h_7d", "volatility_4h_7d", "volume_shock_4h"}.issubset(features.columns)
    first_available = features.trend_4h_7d.first_valid_index()
    if first_available is not None:
        assert features.loc[first_available, "date"] > raw.date.min()


def test_feature_research_frame_contains_required_new_public_features():
    panel = DataIngestion().synthetic_panel(days=520, assets=8, seed=81)
    panel.loc[panel.symbol == "COIN01", "symbol"] = "BTC"
    panel.loc[panel.symbol == "COIN02", "symbol"] = "ETH"
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    stable = pd.DataFrame({
        "date": dates,
        "stablecoin_supply": np.linspace(100, 200, len(dates)),
        "stablecoin_supply_usd": np.linspace(100, 200, len(dates)),
    })
    stable["stablecoin_supply_change_7d"] = stable.stablecoin_supply_usd.pct_change(7)
    stable["stablecoin_supply_change_30d"] = stable.stablecoin_supply_usd.pct_change(30)
    stable["stablecoin_supply_change_90d"] = stable.stablecoin_supply_usd.pct_change(90)
    stable["stablecoin_supply_z_90"] = 0.0
    chain_tvl = pd.DataFrame({"date": dates, "chain": "all", "tvl": np.linspace(1000, 1300, len(dates))})
    public = PublicDataBundle(
        coverage=pd.DataFrame(),
        stablecoins=stable,
        chain_tvl=chain_tvl,
        protocol_tvl=pd.DataFrame(),
        coingecko_markets=pd.DataFrame(),
        coingecko_categories=pd.DataFrame(),
        coingecko_coin_daily=pd.DataFrame(),
        binance_4h=pd.DataFrame(),
        binance_4h_daily_features=pd.DataFrame(),
        token_unlocks=pd.DataFrame(),
        metadata={},
    )
    frame, metadata = build_feature_research_frame(panel, public_data=public, top_n=5, min_history_days=90)
    assert "momentum_21d" in metadata.feature.values
    assert "stablecoin_supply_change_30d" in metadata.feature.values
    assert "tvl_growth_30d" in metadata.feature.values
    ic = information_coefficient_report(frame, metadata.head(5))
    assert {"feature", "horizon", "full_sample_ic", "newey_west_t"}.issubset(ic.columns)


def test_liquidity_weights_hold_cash_when_stablecoins_contract():
    panel = DataIngestion().synthetic_panel(days=520, assets=4, seed=82)
    panel.loc[panel.symbol == "COIN01", "symbol"] = "BTC"
    panel.loc[panel.symbol == "COIN02", "symbol"] = "ETH"
    panel = panel[panel.symbol.isin(["BTC", "ETH"])]
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    stable = pd.DataFrame({
        "date": dates,
        "stablecoin_supply": np.linspace(200, 100, len(dates)),
        "stablecoin_supply_usd": np.linspace(200, 100, len(dates)),
    })
    stable["stablecoin_supply_change_30d"] = stable.stablecoin_supply_usd.pct_change(30)
    stable["stablecoin_supply_change_90d"] = stable.stablecoin_supply_usd.pct_change(90)
    candidate = pytest.importorskip("crypto_mlsystem.public_crypto_data").LiquidityCandidate(
        "test", 7, 30, 0.80, -0.99, 0.35, False
    )
    weights = build_liquidity_conditioned_weights(panel, stable, pd.DataFrame(), None, candidate)
    assert weights.sum(axis=1).max() == pytest.approx(0.0)

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

from crypto_mlsystem.data import DataIngestion
from crypto_mlsystem.public_crypto_data import PublicDataBundle
from crypto_mlsystem.tier1_regime_momentum import (
    TIER1_FEATURES,
    RegimeMomentumCandidate,
    build_regime_momentum_dataset,
    build_strategy_weights,
    classify_regimes,
)


def _fixture(days=2400):
    panel = DataIngestion().synthetic_panel(days=days, assets=12, seed=101)
    panel.loc[panel.symbol == "COIN01", "symbol"] = "BTC"
    panel.loc[panel.symbol == "COIN02", "symbol"] = "ETH"
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    stable = pd.DataFrame({
        "date": dates,
        "stablecoin_supply": np.linspace(100, 300, len(dates)),
        "stablecoin_supply_usd": np.linspace(100, 300, len(dates)),
    })
    stable["stablecoin_supply_change_7d"] = stable.stablecoin_supply_usd.pct_change(7)
    stable["stablecoin_supply_change_30d"] = stable.stablecoin_supply_usd.pct_change(30)
    stable["stablecoin_supply_change_90d"] = stable.stablecoin_supply_usd.pct_change(90)
    stable["stablecoin_supply_z_90"] = 0.0
    chain_tvl = pd.DataFrame({"date": dates, "chain": "all", "tvl": np.linspace(1000, 2000, len(dates))})
    chain_tvl["tvl_change_30d"] = chain_tvl.tvl.pct_change(30)
    intraday = pd.concat([
        pd.DataFrame({"date": dates, "symbol": symbol, "volatility_4h_7d": 0.5 + 0.1 * np.sin(np.arange(len(dates)) / 17)})
        for symbol in ("BTC", "ETH")
    ], ignore_index=True)
    public = PublicDataBundle(
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
    return panel, public


def test_dataset_regime_features_are_tier1_only():
    panel, public = _fixture()
    dataset = build_regime_momentum_dataset(panel, public, universe_size=10)
    assert tuple(dataset.tier1_features.columns) == TIER1_FEATURES
    assert "market_drawdown" not in dataset.tier1_features.columns
    assert "distance_to_200dma" not in dataset.tier1_features.columns
    assert "trend_4h_7d" not in dataset.tier1_features.columns


def test_thresholds_are_development_only():
    panel, public = _fixture()
    first = build_regime_momentum_dataset(panel, public, universe_size=10)
    changed = public
    changed_stable = changed.stablecoins.copy()
    changed_stable.loc[changed_stable.date >= pd.Timestamp("2025-01-01"), "stablecoin_supply_change_7d"] = 99.0
    changed = PublicDataBundle(
        coverage=changed.coverage,
        stablecoins=changed_stable,
        chain_tvl=changed.chain_tvl,
        protocol_tvl=changed.protocol_tvl,
        coingecko_markets=changed.coingecko_markets,
        coingecko_categories=changed.coingecko_categories,
        coingecko_coin_daily=changed.coingecko_coin_daily,
        binance_4h=changed.binance_4h,
        binance_4h_daily_features=changed.binance_4h_daily_features,
        token_unlocks=changed.token_unlocks,
        metadata=changed.metadata,
    )
    second = build_regime_momentum_dataset(panel, changed, universe_size=10)
    assert first.threshold_sets == second.threshold_sets


def test_risk_off_regime_holds_cash():
    panel, public = _fixture()
    dataset = build_regime_momentum_dataset(panel, public, universe_size=10)
    candidate = RegimeMomentumCandidate(
        name="test",
        universe_size=10,
        rebalance_days=7,
        momentum_signal="momentum_63d",
        top_k=3,
        threshold_set="very_strict",
        risk_on_votes=5,
        neutral_policy="cash",
    )
    regimes = classify_regimes(dataset, candidate)
    weights, _ = build_strategy_weights(dataset, candidate)
    risk_off_dates = weights.index.intersection(regimes[regimes == "risk_off"].index)
    if len(risk_off_dates):
        assert weights.loc[risk_off_dates].sum(axis=1).max() == pytest.approx(0.0)

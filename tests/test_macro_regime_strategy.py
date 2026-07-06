import numpy as np
import pandas as pd

from crypto_mlsystem.macro_regime_strategy import (
    ALLOWED_REGIME_FEATURES,
    MACRO_TIER1_FEATURES,
    build_macro_regime_dataset,
    predeclared_macro_regime_candidates,
    run_macro_regime_strategy_study,
    write_macro_regime_strategy_reports,
)
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2700) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE", "LINK", "AVAX", "LTC", "UNI", "ATOM"]
    market = rng.normal(0.0005, 0.025, len(dates))
    rows = []
    for i, symbol in enumerate(symbols):
        beta = 1.0 + i * 0.03
        ret = beta * market + rng.normal(0.0001, 0.02 + i * 0.001, len(dates))
        close = (100 + 10 * i) * np.exp(np.cumsum(ret))
        volume = rng.lognormal(16 - i * 0.04, 0.3, len(dates))
        market_cap = close * rng.lognormal(18 - i * 0.03, 0.2, len(dates))
        high = close * 1.02
        low = close * 0.98
        for date, price, h, l, vol, cap in zip(dates, close, high, low, volume, market_cap):
            rows.append({
                "date": date,
                "symbol": symbol,
                "open": price,
                "high": h,
                "low": l,
                "close": price,
                "volume": vol,
                "market_cap": cap,
            })
    return pd.DataFrame(rows)


def _macro(dates: pd.DatetimeIndex) -> pd.DataFrame:
    t = np.arange(len(dates))
    return pd.DataFrame({
        "date": dates,
        "equity_realized_vol_21d": 0.15 + 0.03 * np.sin(t / 33),
        "equity_momentum_21d": 0.02 * np.sin(t / 45),
        "dow_vol_level": 18 + 4 * np.sin(t / 40),
        "vix_level": 20 + 5 * np.sin(t / 37),
        "vix_change_5d": np.gradient(20 + 5 * np.sin(t / 37)),
        "vix_change_21d": pd.Series(20 + 5 * np.sin(t / 37)).diff(21).to_numpy(),
    })


def _public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    stable_supply = 100e9 * np.cumprod(1 + np.full(len(dates), 0.0002))
    stablecoins = pd.DataFrame({
        "date": dates,
        "stablecoin_supply_usd": stable_supply,
        "stablecoin_supply_change_7d": pd.Series(stable_supply).pct_change(7).to_numpy(),
    })
    tvl = 50e9 * np.cumprod(1 + np.full(len(dates), 0.00015))
    chain_tvl = pd.DataFrame({"date": dates, "chain": "all", "tvl": tvl})
    return PublicDataBundle(
        coverage=pd.DataFrame(),
        stablecoins=stablecoins,
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


def test_predeclared_candidates_are_small_and_fixed():
    candidates = predeclared_macro_regime_candidates()
    assert len(candidates) == 8
    assert {candidate.allocation for candidate in candidates} == {"btc_eth", "top10_momentum"}
    assert {candidate.gate_profile for candidate in candidates} == {"balanced", "strict"}


def test_dataset_uses_only_allowed_regime_features():
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    dataset = build_macro_regime_dataset(panel, _macro(dates), _public_data(dates))
    assert set(dataset.regime_features.columns) == set(ALLOWED_REGIME_FEATURES)
    assert set(MACRO_TIER1_FEATURES).issubset(dataset.regime_features.columns)
    assert "credit_spread_level" not in dataset.regime_features
    assert "macro_risk_on_composite" not in dataset.regime_features


def test_macro_regime_strategy_reports(tmp_path):
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = run_macro_regime_strategy_study(panel, _macro(dates), _public_data(dates))
    write_macro_regime_strategy_reports(tmp_path, result)

    for filename in (
        "results_summary.md",
        "holdout_results.md",
        "regime_diagnostics.md",
        "final_recommendation.md",
        "results.json",
    ):
        assert (tmp_path / filename).exists()
    text = (tmp_path / "results_summary.md").read_text(encoding="utf-8")
    assert "Tested configurations: 8" in text
    assert "Tier 2 and Tier 3 features are not used" in text

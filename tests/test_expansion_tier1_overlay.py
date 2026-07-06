import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from crypto_mlsystem import expansion_tier1_overlay as eto
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 22) -> pd.DataFrame:
    rng = np.random.default_rng(441)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = 0.0003 + 0.001 * np.sin(np.arange(days) / 65) + rng.normal(0, 0.018, days)
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.85 + i * 0.01) * market + rng.normal(0.0001, 0.014 + i * 0.0003, days)
        close = (100 + i * 3) * np.exp(np.cumsum(ret))
        volume = rng.lognormal(16.8 - i * 0.01, 0.20, days)
        market_cap = close * rng.lognormal(18.2 - i * 0.01, 0.10, days)
        for date, price, vol, cap in zip(dates, close, volume, market_cap):
            rows.append({
                "date": date,
                "symbol": symbol,
                "open": price,
                "high": price * 1.02,
                "low": price * 0.98,
                "close": price,
                "volume": vol,
                "market_cap": cap,
            })
    return pd.DataFrame(rows)


def _macro(dates: pd.DatetimeIndex) -> pd.DataFrame:
    t = np.arange(len(dates))
    vix = 19 + 4 * np.sin(t / 43)
    return pd.DataFrame({
        "date": dates,
        "equity_realized_vol_21d": 0.15 + 0.02 * np.sin(t / 37),
        "equity_momentum_21d": 0.02 * np.sin(t / 53),
        "dow_vol_level": 18 + 3 * np.sin(t / 47),
        "vix_level": vix,
        "vix_change_5d": pd.Series(vix).diff(5).to_numpy(),
        "vix_change_21d": pd.Series(vix).diff(21).to_numpy(),
    })


def _public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    stable_supply = 100e9 * np.cumprod(1 + 0.0001 + 0.00004 * np.sin(np.arange(len(dates)) / 45))
    tvl = 50e9 * np.cumprod(1 + 0.00008 + 0.00003 * np.sin(np.arange(len(dates)) / 52))
    intraday = []
    for symbol in ("BTC", "ETH"):
        intraday.append(pd.DataFrame({
            "date": dates,
            "symbol": symbol,
            "volatility_4h_7d": 0.42 + 0.05 * np.sin(np.arange(len(dates)) / 30),
        }))
    return PublicDataBundle(
        coverage=pd.DataFrame(),
        stablecoins=pd.DataFrame({
            "date": dates,
            "stablecoin_supply_usd": stable_supply,
            "stablecoin_supply_change_7d": pd.Series(stable_supply).pct_change(7).to_numpy(),
        }),
        chain_tvl=pd.DataFrame({"date": dates, "chain": "all", "tvl": tvl}),
        protocol_tvl=pd.DataFrame(),
        coingecko_markets=pd.DataFrame(),
        coingecko_categories=pd.DataFrame(),
        coingecko_coin_daily=pd.DataFrame(),
        binance_4h=pd.DataFrame(),
        binance_4h_daily_features=pd.concat(intraday, ignore_index=True),
        token_unlocks=pd.DataFrame(),
        metadata={},
    )


def _logistic_spec() -> eto.ModelSpec:
    return eto.ModelSpec(
        "logistic_regression",
        "Logistic regression",
        lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced", random_state=13)),
    )


def test_expansion_tier1_overlay_uses_tier1_features_and_writes_reports(monkeypatch, tmp_path):
    tier1_subset = [
        "recovery_from_drawdown",
        "tvl_percentile",
        "stablecoin_supply_percentile",
        "eth_btc_relative_strength_30d",
        "top20_above_30dma_pct",
    ]
    monkeypatch.setattr(eto, "load_tier1_feature_names", lambda path=None: tier1_subset)

    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = eto.run_expansion_tier1_overlay(panel, _macro(dates), _public_data(dates), specs=[_logistic_spec()])

    assert set(result["tier1_features"]).issubset(set(tier1_subset))
    assert "holdout_sharpe" not in set(result["selection"].columns)
    assert result["tested_configurations"]["prediction_configs"] == len(eto.TARGETS)
    assert result["protocol"]["baseline"] == eto.BASELINE_NAME

    eto.write_expansion_tier1_overlay_reports(tmp_path, result)
    expected = {
        "results_summary.md",
        "development_metrics.md",
        "holdout_metrics.md",
        "exposure_turnover_drawdown.md",
        "expansion_layer_contribution.md",
        "feature_importance.md",
        "calibration.md",
        "cpcv_diagnostics.md",
        "statistical_validation.md",
        "benchmark_comparison.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "was not modified" in (tmp_path / "results_summary.md").read_text(encoding="utf-8")
    assert "genuine upside capture" in (tmp_path / "final_recommendation.md").read_text(encoding="utf-8")

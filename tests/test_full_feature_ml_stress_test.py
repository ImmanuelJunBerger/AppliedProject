import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from crypto_mlsystem import full_feature_ml_stress_test as ffm
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(907)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    regime = 0.0004 + 0.0015 * np.sin(np.arange(days) / 63)
    market = regime + rng.normal(0.0, 0.019, days)
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.90 + 0.02 * i) * market + rng.normal(0.0001, 0.014 + i * 0.0005, days)
        close = (100 + i) * np.exp(np.cumsum(ret))
        volume = rng.lognormal(16.5 - i * 0.01, 0.20, days)
        market_cap = close * rng.lognormal(18.1 - i * 0.01, 0.10, days)
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
    vix = 20 + 4 * np.sin(t / 41)
    return pd.DataFrame({
        "date": dates,
        "equity_realized_vol_21d": 0.15 + 0.03 * np.sin(t / 37),
        "equity_momentum_21d": 0.02 * np.sin(t / 53),
        "dow_vol_level": 18 + 3 * np.sin(t / 47),
        "vix_level": vix,
        "vix_change_5d": pd.Series(vix).diff(5).to_numpy(),
        "vix_change_21d": pd.Series(vix).diff(21).to_numpy(),
    })


def _public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    stable_supply = 100e9 * np.cumprod(1 + 0.0001 + 0.00005 * np.sin(np.arange(len(dates)) / 50))
    tvl = 45e9 * np.cumprod(1 + 0.00008 + 0.00004 * np.sin(np.arange(len(dates)) / 45))
    intraday = []
    for symbol in ("BTC", "ETH"):
        intraday.append(pd.DataFrame({
            "date": dates,
            "symbol": symbol,
            "trend_4h_7d": 0.01 * np.sin(np.arange(len(dates)) / 21),
            "trend_4h_14d": 0.02 * np.sin(np.arange(len(dates)) / 34),
            "volatility_4h_7d": 0.45 + 0.08 * np.sin(np.arange(len(dates)) / 35),
            "volatility_4h_30d": 0.50 + 0.06 * np.sin(np.arange(len(dates)) / 51),
            "drawdown_4h_30d": -0.12 + 0.04 * np.sin(np.arange(len(dates)) / 42),
            "volume_shock_4h": 1.0 + 0.2 * np.sin(np.arange(len(dates)) / 29),
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


def _logistic_spec() -> ffm.ModelSpec:
    return ffm.ModelSpec(
        "elastic_net_logistic",
        "Elastic Net logistic regression",
        1,
        lambda auto, n: make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=500, class_weight="balanced", random_state=9),
        ),
    )


def test_targets_match_stress_test_prompt():
    assert [name for name, _ in ffm.TARGET_SPECS] == [
        "btc_eth_50_50_forward_positive_30d",
        "btc_forward_30d_gt_10",
        "eth_forward_30d_gt_15",
        "frozen_macro_positive_next_period",
        "avoid_large_negative_btc_eth_30d",
    ]


def test_full_feature_ml_stress_test_reports_without_reselecting_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(ffm, "_dev_supports_stacking", lambda prediction_selection: False)
    monkeypatch.setattr(
        ffm,
        "predeclared_strategy_specs",
        lambda: [
            ffm.StrategySpec(
                name="test_confirmation",
                strategy_type="ml_confirmation_overlay",
                rebalance_days=7,
                mode="confirmation",
                description="Test confirmation overlay.",
            ),
            ffm.StrategySpec(
                name="test_allocator",
                strategy_type="ml_btc_vs_eth_allocator",
                rebalance_days=7,
                mode="allocator",
                description="Test allocator.",
            ),
        ],
    )
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = ffm.run_full_feature_ml_stress_test(
        panel,
        _macro(dates),
        _public_data(dates),
        model_specs=[_logistic_spec()],
    )
    assert result["strategy_selection"]["candidate"].isin(["test_confirmation", "test_allocator"]).all()
    assert "holdout_sharpe" not in set(result["strategy_selection"].columns)
    assert result["statistics"]["tested_strategy_configurations"] == 2
    assert result["final_decision"] in {
        "reject_full_feature_ml_keep_frozen",
        "full_feature_ml_complements_frozen_for_paper_monitoring",
    }

    ffm.write_full_feature_ml_stress_test_reports(tmp_path, result)
    expected = {
        "executive_summary.md",
        "feature_sets.md",
        "model_comparison.md",
        "train_validation_holdout_results.md",
        "overfitting_diagnostics.md",
        "feature_importance_stability.md",
        "benchmark_comparison.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "was not modified" in (tmp_path / "executive_summary.md").read_text(encoding="utf-8")

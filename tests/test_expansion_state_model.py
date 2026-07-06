import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from crypto_mlsystem import expansion_state_model as esm
from crypto_mlsystem.macro_regime_strategy import build_macro_regime_dataset
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 14) -> pd.DataFrame:
    rng = np.random.default_rng(101)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    regime = 0.0006 + 0.0015 * np.sin(np.arange(days) / 65)
    market = regime + rng.normal(0.0, 0.020, days)
    rows = []
    for i, symbol in enumerate(symbols):
        beta = 0.85 + 0.02 * i
        ret = beta * market + rng.normal(0.0001, 0.015 + i * 0.0004, days)
        close = (80 + 2 * i) * np.exp(np.cumsum(ret))
        volume = rng.lognormal(16.6 - i * 0.015, 0.25, days)
        market_cap = close * rng.lognormal(18.0 - i * 0.01, 0.12, days)
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
    vix = 20 + 5 * np.sin(t / 39)
    return pd.DataFrame({
        "date": dates,
        "equity_realized_vol_21d": 0.16 + 0.03 * np.sin(t / 31),
        "equity_momentum_21d": 0.02 * np.sin(t / 49),
        "dow_vol_level": 18 + 4 * np.sin(t / 43),
        "vix_level": vix,
        "vix_change_5d": pd.Series(vix).diff(5).to_numpy(),
        "vix_change_21d": pd.Series(vix).diff(21).to_numpy(),
    })


def _public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    stable_supply = 100e9 * np.cumprod(1 + 0.0001 + 0.00005 * np.sin(np.arange(len(dates)) / 50))
    tvl = 45e9 * np.cumprod(1 + 0.00008 + 0.00004 * np.sin(np.arange(len(dates)) / 45))
    intraday_rows = []
    for symbol in ("BTC", "ETH"):
        intraday_rows.append(pd.DataFrame({
            "date": dates,
            "symbol": symbol,
            "volatility_4h_7d": 0.45 + 0.08 * np.sin(np.arange(len(dates)) / 35),
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
        binance_4h_daily_features=pd.concat(intraday_rows, ignore_index=True),
        token_unlocks=pd.DataFrame(),
        metadata={},
    )


def _logistic_spec() -> esm.ModelSpec:
    return esm.ModelSpec(
        "logistic_regression",
        "Logistic regression",
        lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced", random_state=7)),
    )


def test_expansion_targets_cover_requested_definitions():
    assert [name for name, _ in esm.TARGET_SPECS] == [
        "btc_30d_gt_15",
        "eth_30d_gt_20",
        "btc_eth_50_50_30d_gt_15",
        "top10_30d_gt_20",
        "eth_leads_btc_30d_gt_5",
    ]


def test_feature_frame_includes_4h_volatility_without_holdout_ranking():
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    public_data = _public_data(dates)
    dataset = build_macro_regime_dataset(panel, _macro(dates), public_data)
    features = esm._feature_frame(dataset, public_data)
    assert "volatility_4h_7d" in features.columns
    assert set(esm.FEATURES).issubset(features.columns)


def test_expansion_state_reports_and_development_only_selection(monkeypatch, tmp_path):
    monkeypatch.setattr(
        esm,
        "predeclared_overlay_specs",
        lambda expansion_threshold, leadership_threshold: [
            esm.OverlaySpec(
                name="test_expansion_sizing",
                overlay_type="expansion_probability_sizing",
                expansion_threshold=expansion_threshold,
                leadership_threshold=leadership_threshold,
                rebalance_days=7,
                description="Test expansion sizing.",
            ),
            esm.OverlaySpec(
                name="test_eth_tilt",
                overlay_type="eth_leadership_tilt",
                expansion_threshold=expansion_threshold,
                leadership_threshold=leadership_threshold,
                rebalance_days=7,
                description="Test ETH leadership tilt.",
            ),
        ],
    )
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = esm.run_expansion_state_model(panel, _macro(dates), _public_data(dates), model_specs=[_logistic_spec()])

    assert "holdout_sharpe" not in set(result["overlay_selection"].columns)
    assert result["prediction_selection"]["split"].eq("development_cpcv").all()
    assert result["tested_configurations"]["prediction_configs"] == len(esm.TARGET_SPECS)

    esm.write_expansion_state_reports(tmp_path, result)
    expected = {
        "results_summary.md",
        "target_diagnostics.md",
        "predictive_performance.md",
        "calibration_and_feature_importance.md",
        "strategy_overlay_results.md",
        "benchmark_comparison.md",
        "statistical_validation.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "did not modify or" in (tmp_path / "results_summary.md").read_text(encoding="utf-8")

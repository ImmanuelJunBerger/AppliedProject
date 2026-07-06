import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from crypto_mlsystem import trend_scanning_ml as tsm
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 14) -> pd.DataFrame:
    rng = np.random.default_rng(704)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = 0.0004 + 0.0014 * np.sin(np.arange(days) / 79) + rng.normal(0, 0.018, days)
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.85 + i * 0.015) * market + rng.normal(0.0001, 0.014 + i * 0.0004, days)
        close = (100 + i * 2) * np.exp(np.cumsum(ret))
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
    idx = np.arange(len(dates))
    vix = 20 + 4 * np.sin(idx / 41)
    return pd.DataFrame({
        "date": dates,
        "equity_realized_vol_21d": 0.15 + 0.02 * np.sin(idx / 37),
        "equity_momentum_21d": 0.02 * np.sin(idx / 53),
        "dow_vol_level": 18 + 3 * np.sin(idx / 47),
        "vix_level": vix,
        "vix_change_5d": pd.Series(vix).diff(5).to_numpy(),
        "vix_change_21d": pd.Series(vix).diff(21).to_numpy(),
    })


def _public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    idx = np.arange(len(dates))
    stable = 100e9 * np.cumprod(1 + 0.0001 + 0.00005 * np.sin(idx / 50))
    tvl = 45e9 * np.cumprod(1 + 0.00008 + 0.00004 * np.sin(idx / 45))
    intraday = []
    for symbol in ("BTC", "ETH"):
        intraday.append(pd.DataFrame({
            "date": dates,
            "symbol": symbol,
            "volatility_4h_7d": 0.45 + 0.08 * np.sin(idx / 35),
        }))
    return PublicDataBundle(
        coverage=pd.DataFrame(),
        stablecoins=pd.DataFrame({
            "date": dates,
            "stablecoin_supply_usd": stable,
            "stablecoin_supply_change_7d": pd.Series(stable).pct_change(7).to_numpy(),
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


def _logistic_spec() -> tsm.ModelSpec:
    return tsm.ModelSpec(
        "logistic_regression",
        "Logistic regression",
        lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced", random_state=11)),
    )


def test_trend_scanning_labels_have_requested_fields():
    panel = _panel(days=500)
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    dataset = tsm.build_macro_regime_dataset(panel, _macro(dates), _public_data(dates), universe_size=10)
    rebalance = tsm._rebalance_dates(dataset.close.index, 7)
    scan = tsm.build_trend_scan_table(dataset, rebalance)
    labels = tsm.apply_trend_thresholds(scan, thresholds=(1.0,))
    assert {"selected_horizon", "t_stat", "sign_label", "trend_strength", "forward_realized_return", "label_confidence"}.issubset(labels.columns)
    assert set(labels.target).issuperset({"btc_upward_trend", "eth_upward_trend", "btc_eth_upward_trend"})


def test_trend_scanning_reports_and_no_holdout_selection(monkeypatch, tmp_path):
    monkeypatch.setattr(tsm, "LABEL_TSTAT_THRESHOLDS", (1.0,))
    monkeypatch.setattr(
        tsm,
        "predeclared_strategy_specs",
        lambda: [
            tsm.StrategySpec("pure_test_weekly", "pure_trend_scanning", 7, 1, "test pure"),
            tsm.StrategySpec("macro_confirm_test_weekly", "macro_gate_trend_confirmation", 7, 2, "test macro confirm"),
        ],
    )
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = tsm.run_trend_scanning_ml(panel, _macro(dates), _public_data(dates), model_specs=[_logistic_spec()])

    assert result["protocol"]["baseline"] == tsm.BASELINE_NAME
    assert result["tested_configurations"]["label_thresholds"] == 1
    assert "holdout_sharpe" not in set(result["strategy_selection"].columns)
    assert result["winner"] in {"pure_test_weekly", "macro_confirm_test_weekly"}

    tsm.write_trend_scanning_reports(tmp_path, result)
    expected = {
        "executive_summary.md",
        "trend_label_construction.md",
        "label_diagnostics.md",
        "predictive_performance.md",
        "meta_model_results.md",
        "strategy_results.md",
        "benchmark_comparison.md",
        "feature_importance.md",
        "statistical_validation.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "was not modified" in (tmp_path / "executive_summary.md").read_text(encoding="utf-8")

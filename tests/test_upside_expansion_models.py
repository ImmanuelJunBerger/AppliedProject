import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from crypto_mlsystem import upside_expansion_models as uem
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 22) -> pd.DataFrame:
    rng = np.random.default_rng(121)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = 0.0004 + 0.001 * np.sin(np.arange(days) / 70) + rng.normal(0, 0.018, days)
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.85 + i * 0.01) * market + rng.normal(0.0001, 0.014 + i * 0.0003, days)
        close = (90 + i * 2) * np.exp(np.cumsum(ret))
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
    vix = 19 + 4 * np.sin(t / 41)
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


def _logistic_spec() -> uem.ModelSpec:
    return uem.ModelSpec(
        "logistic_regression",
        "Logistic regression",
        lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced", random_state=13)),
    )


def test_upside_target_families_are_predeclared():
    families = [family for family, _, _ in uem.AGGREGATE_TARGETS]
    targets = [target for _, target, _ in uem.AGGREGATE_TARGETS]
    assert families.count("convex") == 3
    assert families.count("relative") == 2
    assert "risk_off_to_risk_on_2_4w" in targets
    assert uem.CROSS_SECTIONAL_TARGET == "top20_top_quintile_30d"


def test_upside_models_write_requested_reports_with_development_only_selection(monkeypatch, tmp_path):
    def small_specs(convex_threshold, eth_threshold, btc_threshold, transition_threshold, cross_threshold, component_passes=None):
        return [
            uem.UpsideOverlaySpec("convex_test", "convex", "convex_upside", 7, convex_threshold, None, description="Convex test."),
            uem.UpsideOverlaySpec("relative_test", "relative", "relative_winner", 7, eth_threshold, btc_threshold, description="Relative test."),
            uem.UpsideOverlaySpec("transition_test", "transition", "regime_transition", 7, transition_threshold, None, description="Transition test."),
            uem.UpsideOverlaySpec("cross_test", "cross_sectional", "cross_sectional_leadership", 7, cross_threshold, None, top_k=3, description="Cross test."),
            uem.UpsideOverlaySpec("combined_test", "combined", "combined", 7, convex_threshold, eth_threshold, top_k=3, description="Combined test."),
        ]

    monkeypatch.setattr(uem, "predeclared_overlay_specs", small_specs)
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = uem.run_upside_expansion_models(panel, _macro(dates), _public_data(dates), model_specs=[_logistic_spec()])

    assert result["tested_configurations"]["prediction_configs"] == len(uem.AGGREGATE_TARGETS) + 1
    assert "holdout_sharpe" not in set(result["overlay_selection"].columns)
    assert set(["convex", "relative", "transition", "cross_sectional", "combined"]).issubset(result["selected_by_family"])

    uem.write_upside_expansion_reports(tmp_path, result)
    expected = {
        "results_summary.md",
        "target_diagnostics.md",
        "predictive_performance.md",
        "convex_upside_results.md",
        "relative_winner_results.md",
        "regime_transition_results.md",
        "cross_sectional_leadership_results.md",
        "combined_overlay_results.md",
        "benchmark_comparison.md",
        "statistical_validation.md",
        "final_recommendation.md",
        "expansion_feature_inventory.md",
        "expansion_feature_research.md",
        "expansion_feature_tiers.md",
        "expansion_feature_correlation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "was not modified" in (tmp_path / "results_summary.md").read_text(encoding="utf-8")
    assert "Expansion feature tiers" in (tmp_path / "expansion_feature_tiers.md").read_text(encoding="utf-8")

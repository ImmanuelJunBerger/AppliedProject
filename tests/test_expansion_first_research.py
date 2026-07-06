import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from crypto_mlsystem import expansion_first_research as efr
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 22) -> pd.DataFrame:
    rng = np.random.default_rng(719)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = 0.0004 + 0.001 * np.sin(np.arange(days) / 73) + rng.normal(0, 0.018, days)
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.85 + i * 0.01) * market + rng.normal(0.0001, 0.014 + i * 0.0003, days)
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
        "credit_spread_level": 3 + 0.2 * np.sin(t / 51),
        "rates_10y_level": 4 + 0.1 * np.sin(t / 55),
        "usd_trend_21d": 0.01 * np.sin(t / 45),
    })


def _public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    stable_supply = 100e9 * np.cumprod(1 + 0.0001 + 0.00004 * np.sin(np.arange(len(dates)) / 45))
    tvl = 50e9 * np.cumprod(1 + 0.00008 + 0.00003 * np.sin(np.arange(len(dates)) / 52))
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
        binance_4h_daily_features=pd.DataFrame(),
        token_unlocks=pd.DataFrame(),
        metadata={},
    )


def _logistic_spec() -> efr.ModelSpec:
    return efr.ModelSpec(
        "logistic_regression",
        "Linear",
        lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced", random_state=13)),
    )


def test_expansion_first_research_writes_reports_without_reselecting_frozen(monkeypatch, tmp_path):
    small_candidates = [
        efr.AlphaCandidate("expansion_first_small", "expansion_first", "btc_eth_cash", "probability_weight", "none", "test expansion-first"),
        efr.AlphaCandidate("hybrid_small", "hybrid", "btc_eth_cash", "probability_weight", "macro_gate", "test hybrid"),
    ]
    monkeypatch.setattr(efr, "predeclared_alpha_candidates", lambda: small_candidates)
    monkeypatch.setattr(efr, "_derivatives_feature_frame", lambda index, path="": (pd.DataFrame(index=index), pd.DataFrame()))

    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = efr.run_expansion_first_research(panel, _macro(dates), _public_data(dates), specs=[_logistic_spec()])

    assert result["protocol"]["baseline"] == efr.BASELINE_NAME
    assert set(result["winners"]) == {"expansion_first", "hybrid", "overall"}
    assert result["tested_configurations"]["strategy_configs"] == 2
    assert "holdout_sharpe" not in set(result["selection"].columns)

    efr.write_expansion_first_reports(tmp_path, result)
    expected = {
        "executive_summary.md",
        "architecture_comparison.md",
        "feature_usage.md",
        "model_comparison.md",
        "portfolio_construction.md",
        "risk_management_comparison.md",
        "benchmark_comparison.md",
        "holdout_results.md",
        "statistical_validation.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "was not modified" in (tmp_path / "executive_summary.md").read_text(encoding="utf-8")

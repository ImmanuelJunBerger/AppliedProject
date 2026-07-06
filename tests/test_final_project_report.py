import numpy as np
import pandas as pd

from crypto_mlsystem.final_project_report import (
    SIMPLE_GATE_DEFINITIONS,
    run_final_project_analysis,
    write_final_project_reports,
)
from crypto_mlsystem.macro_regime_benchmark_analysis import FIXED_SELECTED
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2700, assets: int = 36) -> pd.DataFrame:
    rng = np.random.default_rng(29)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = rng.normal(0.0003, 0.024, len(dates))
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.7 + i * 0.006) * market + rng.normal(0.0001, 0.016 + i * 0.0003, len(dates))
        close = (40 + i) * np.exp(np.cumsum(ret))
        volume = rng.lognormal(17 - i * 0.02, 0.25, len(dates))
        market_cap = close * rng.lognormal(18 - i * 0.015, 0.12, len(dates))
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
    vix = 21 + 5 * np.sin(t / 40)
    return pd.DataFrame({
        "date": dates,
        "equity_realized_vol_21d": 0.13 + 0.02 * np.sin(t / 23),
        "equity_momentum_21d": 0.02 * np.sin(t / 47),
        "dow_vol_level": 17 + 3 * np.sin(t / 31),
        "vix_level": vix,
        "vix_change_5d": pd.Series(vix).diff(5).to_numpy(),
        "vix_change_21d": pd.Series(vix).diff(21).to_numpy(),
    })


def _public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    stable_supply = 90e9 * np.cumprod(1 + np.full(len(dates), 0.00015))
    tvl = 35e9 * np.cumprod(1 + np.full(len(dates), 0.00008))
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


def test_final_project_analysis_keeps_strategy_fixed():
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = run_final_project_analysis(panel, _macro(dates), _public_data(dates))

    assert FIXED_SELECTED.name == "btc_eth_macro_gate_balanced"
    assert set(result["simple_gates"]["gate"]) == set(SIMPLE_GATE_DEFINITIONS)
    assert {"summary", "folds"}.issubset(result["development_holdout"])
    assert "sharpe_retention_label" in result["development_holdout"]["summary"]
    assert not result["explainability"]["allocation_explanations"].empty
    assert not result["stress"].empty


def test_final_project_reports_are_written(tmp_path):
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = run_final_project_analysis(panel, _macro(dates), _public_data(dates))
    write_final_project_reports(tmp_path, result)

    expected = {
        "executive_summary.md",
        "client_specification.md",
        "methodology.md",
        "data_and_features.md",
        "results_and_benchmarks.md",
        "development_vs_holdout.md",
        "robustness_and_limitations.md",
        "final_recommendation.md",
        "development_cpcv_folds.csv",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "Sharpe retention" in (tmp_path / "development_vs_holdout.md").read_text(encoding="utf-8")
    assert "CPCV fold distribution" in (tmp_path / "development_vs_holdout.md").read_text(encoding="utf-8")
    assert "paper-monitoring candidate" in (tmp_path / "final_recommendation.md").read_text(encoding="utf-8")

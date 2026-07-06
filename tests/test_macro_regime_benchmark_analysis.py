import numpy as np
import pandas as pd

from crypto_mlsystem.macro_regime_benchmark_analysis import (
    FIXED_SELECTED,
    run_macro_regime_benchmark_analysis,
    write_macro_regime_benchmark_reports,
)
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2700, assets: int = 36) -> pd.DataFrame:
    rng = np.random.default_rng(17)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    base_symbols = ["BTC", "ETH"]
    other_symbols = [f"COIN{i:02d}" for i in range(assets - 2)]
    symbols = base_symbols + other_symbols
    market = rng.normal(0.0004, 0.025, len(dates))
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.8 + i * 0.01) * market + rng.normal(0.0001, 0.018 + i * 0.0004, len(dates))
        close = (50 + i) * np.exp(np.cumsum(ret))
        volume = rng.lognormal(17 - i * 0.025, 0.25, len(dates))
        market_cap = close * rng.lognormal(18 - i * 0.02, 0.15, len(dates))
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
    vix = 20 + 4 * np.sin(t / 30)
    return pd.DataFrame({
        "date": dates,
        "equity_realized_vol_21d": 0.14 + 0.02 * np.sin(t / 25),
        "equity_momentum_21d": 0.03 * np.sin(t / 50),
        "dow_vol_level": 17 + 3 * np.sin(t / 35),
        "vix_level": vix,
        "vix_change_5d": pd.Series(vix).diff(5).to_numpy(),
        "vix_change_21d": pd.Series(vix).diff(21).to_numpy(),
    })


def _public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    stable_supply = 100e9 * np.cumprod(1 + np.full(len(dates), 0.0002))
    tvl = 40e9 * np.cumprod(1 + np.full(len(dates), 0.0001))
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


def test_benchmark_analysis_keeps_selected_strategy_fixed():
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = run_macro_regime_benchmark_analysis(panel, _macro(dates), _public_data(dates))
    metrics = result["metrics"]

    assert result["selected_candidate"]["name"] == FIXED_SELECTED.name
    assert set(metrics.loc[metrics.name == FIXED_SELECTED.name, "cost_bps"]) == {10, 25, 50, 100}
    assert {"equal_weight_top10", "equal_weight_top20", "equal_weight_top30"}.issubset(set(metrics.name))
    assert {"pure_top10_momentum", "pure_top20_momentum", "pure_top30_momentum"}.issubset(set(metrics.name))


def test_benchmark_reports_are_written(tmp_path):
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = run_macro_regime_benchmark_analysis(panel, _macro(dates), _public_data(dates))
    write_macro_regime_benchmark_reports(tmp_path, result)

    benchmark = tmp_path / "benchmark_comparison.md"
    universe = tmp_path / "universe_benchmark_comparison.md"
    assert benchmark.exists()
    assert universe.exists()
    assert "does not modify the selected strategy" in benchmark.read_text(encoding="utf-8")
    assert "not today's-top-coins retroactively applied" in universe.read_text(encoding="utf-8")

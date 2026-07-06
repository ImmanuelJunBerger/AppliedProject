import numpy as np
import pandas as pd

from crypto_mlsystem import new_data_extension as nde
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(740)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = 0.0003 + 0.0012 * np.sin(np.arange(days) / 71) + rng.normal(0, 0.018, days)
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.85 + 0.01 * i) * market + rng.normal(0.0001, 0.014 + i * 0.0003, days)
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


def _public_data() -> PublicDataBundle:
    return PublicDataBundle(
        coverage=pd.DataFrame(),
        stablecoins=pd.DataFrame(),
        chain_tvl=pd.DataFrame(),
        protocol_tvl=pd.DataFrame(),
        coingecko_markets=pd.DataFrame(),
        coingecko_categories=pd.DataFrame(),
        coingecko_coin_daily=pd.DataFrame(),
        binance_4h=pd.DataFrame(),
        binance_4h_daily_features=pd.DataFrame(),
        token_unlocks=pd.DataFrame(),
        metadata={},
    )


def test_data_inventory_has_required_schema_and_rejects_unavailable_sources():
    inventory = nde.build_data_inventory()
    required = {
        "source",
        "available",
        "access_method",
        "start_date",
        "end_date",
        "frequency",
        "assets",
        "point_in_time_safe",
        "known_reporting_lag",
        "cost_or_api_key_required",
        "usable_for_backtest",
        "reason_if_unusable",
    }
    assert required.issubset(inventory.columns)
    assert inventory.source.str.contains("ETF", case=False).any()
    assert not inventory[inventory.source.str.contains("ETF", case=False)].usable_for_backtest.any()
    assert inventory.usable_for_backtest.any()


def test_new_data_extension_writes_reports_and_respects_strategy_gate(tmp_path):
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = nde.run_new_data_extension(panel, _macro(dates), _public_data())

    assert result["protocol"]["baseline"] == nde.BASELINE_NAME
    assert isinstance(result["tier1_features"], list)
    if len(result["tier1_features"]) < 3:
        assert result["strategy_ran"] is False
        assert "at least 3 required" in result["skip_reason"]
    assert not result["features"].empty
    assert {"feature", "new_data_tier", "reason"}.issubset(result["feature_tiers"].columns)

    nde.write_new_data_extension_reports(tmp_path, result)
    expected = {
        "executive_summary.md",
        "data_inventory.md",
        "accepted_datasets.md",
        "rejected_datasets.md",
        "feature_engineering.md",
        "feature_research.md",
        "strategy_results.md",
        "benchmark_comparison.md",
        "statistical_validation.md",
        "limitations.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "was not modified" in (tmp_path / "executive_summary.md").read_text(encoding="utf-8")

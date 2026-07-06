import numpy as np
import pandas as pd

from crypto_mlsystem import new_data_expansion_strategy as ndes
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 22) -> pd.DataFrame:
    rng = np.random.default_rng(517)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = 0.0003 + 0.001 * np.sin(np.arange(days) / 67) + rng.normal(0, 0.018, days)
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


def test_new_data_feature_gate_skips_strategy_and_writes_reports(monkeypatch, tmp_path):
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")

    onchain = pd.DataFrame({
        "date": dates,
        "btc_transaction_count": 400_000 + 20_000 * np.sin(np.arange(len(dates)) / 37),
        "btc_active_addresses": 800_000 + 25_000 * np.sin(np.arange(len(dates)) / 41),
    })
    inventory = pd.DataFrame([{
        "source_family": "on-chain",
        "source": "synthetic test source",
        "status": "downloaded",
        "start_date": str(dates.min().date()),
        "end_date": str(dates.max().date()),
        "observations": len(dates),
        "frequency": "daily",
        "timestamp_convention": "UTC",
        "reporting_lag": "lagged",
        "point_in_time_usable": True,
        "notes": "test",
        "url_or_wrds_table": "test",
    }])

    monkeypatch.setattr(ndes, "discover_new_data_sources", lambda processed_dir=None: (inventory, {"blockchain_btc_onchain": onchain}))

    def no_tier1(research, metadata):
        return pd.DataFrame({
            "feature": metadata.feature,
            "new_data_tier": "New Data Tier 3",
            "reason": "test forced skip",
            "best_target": "",
            "development_directed_auc": np.nan,
            "development_ic": np.nan,
            "newey_west_t_stat": np.nan,
            "p_value": np.nan,
            "positive_cpcv_fold_fraction": np.nan,
            "holdout_directed_auc_diagnostic": np.nan,
            "holdout_sign_consistent_diagnostic": False,
        })

    monkeypatch.setattr(ndes, "classify_new_data_features", no_tier1)
    result = ndes.run_new_data_expansion_strategy(panel, _macro(dates), _public_data(), processed_dir=tmp_path / "cache")

    assert result["strategy_ran"] is False
    assert "at least 3 required" in result["skip_reason"]
    assert result["tier1_features"] == []
    assert set(result["feature_metadata"].query("availability == 'implemented'").feature).issubset(set(result["features"].columns))

    ndes.write_new_data_expansion_reports(tmp_path / "reports", result)
    expected = {
        "data_inventory.md",
        "feature_engineering.md",
        "feature_research.md",
        "feature_tiers.md",
        "strategy_results.md",
        "benchmark_comparison.md",
        "statistical_validation.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in (tmp_path / "reports").iterdir()})
    assert "Strategy test was not run" in (tmp_path / "reports" / "strategy_results.md").read_text(encoding="utf-8")

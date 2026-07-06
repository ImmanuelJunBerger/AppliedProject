import json

import numpy as np
import pandas as pd

from crypto_mlsystem import agentic_strategy_discovery as asd
from crypto_mlsystem.macro_regime_benchmark_analysis import FIXED_SELECTED
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(1207)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = 0.0004 + 0.0012 * np.sin(np.arange(days) / 67) + rng.normal(0.0, 0.018, days)
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.90 + 0.02 * i) * market + rng.normal(0.0001, 0.014 + i * 0.0004, days)
        close = (100 + i) * np.exp(np.cumsum(ret))
        volume = rng.lognormal(16.4 - i * 0.01, 0.20, days)
        market_cap = close * rng.lognormal(18.0 - i * 0.01, 0.10, days)
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


def test_candidate_registry_is_deterministic_and_not_full_feature_ml():
    registry = asd._candidate_registry()
    assert len(registry) == 7
    assert all(candidate.deterministic_rule for candidate in registry)
    assert not any(candidate.llm_calls_inside_backtest for candidate in registry)
    text = json.dumps([candidate.candidate_name for candidate in registry]).lower()
    assert "full_feature" not in text
    assert "ml_full_feature_alpha_7d_s+10" not in text


def test_agentic_discovery_reports_and_guardrails(tmp_path):
    frozen_before = FIXED_SELECTED
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = asd.run_agentic_strategy_discovery(panel, _macro(dates), _public_data(dates))

    assert FIXED_SELECTED == frozen_before
    assert "holdout_sharpe" not in set(result["selection"].columns)
    assert result["selection"]["candidate"].notna().all()
    assert result["excluded_features"].feature.astype(str).str.contains("ETF|options|COT|exchange", case=False).any()
    assert not result["feature_metadata"].feature.astype(str).str.contains("forward", case=False).any()
    assert not result["metrics"].empty
    assert result["final_decision"] in {"replace_frozen_strategy", "reject_agentic_replacement_keep_frozen"}

    asd.write_agentic_strategy_discovery_reports(tmp_path, result)
    expected = {
        "executive_summary.md",
        "agentic_architecture.md",
        "candidate_registry.md",
        "candidate_registry.json",
        "feature_mapping.md",
        "strategy_family_results.md",
        "validation_results.md",
        "benchmark_comparison.md",
        "statistical_validation.md",
        "economic_interpretation.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    registry = json.loads((tmp_path / "candidate_registry.json").read_text(encoding="utf-8"))
    assert all(item["deterministic_rule"] for item in registry)
    assert "btc_eth_macro_gate_balanced" in (tmp_path / "executive_summary.md").read_text(encoding="utf-8")

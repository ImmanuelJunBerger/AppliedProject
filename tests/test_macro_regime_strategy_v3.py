import numpy as np
import pandas as pd

from crypto_mlsystem.macro_regime_strategy_v3 import (
    predeclared_simplified_macro_candidates,
    run_macro_regime_strategy_v3,
    write_macro_regime_strategy_v3_reports,
)
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2700, assets: int = 18) -> pd.DataFrame:
    rng = np.random.default_rng(43)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = rng.normal(0.0003, 0.022, len(dates))
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.75 + i * 0.01) * market + rng.normal(0.0001, 0.017 + i * 0.0003, len(dates))
        close = (50 + i) * np.exp(np.cumsum(ret))
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
    vix = 20 + 4 * np.sin(t / 35)
    return pd.DataFrame({
        "date": dates,
        "equity_realized_vol_21d": 0.14 + 0.02 * np.sin(t / 23),
        "equity_momentum_21d": 0.025 * np.sin(t / 47),
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


def test_v3_candidate_set_is_constrained_to_requested_gates():
    candidates = predeclared_simplified_macro_candidates()
    assert len(candidates) == 5
    assert {candidate.label[0] for candidate in candidates} == {"A", "B", "C", "D", "E"}
    assert sum(candidate.is_current_strategy for candidate in candidates) == 1
    assert all(candidate.feature_count <= 6 for candidate in candidates)


def test_v3_selection_uses_development_columns_only_and_writes_reports(tmp_path):
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = run_macro_regime_strategy_v3(panel, _macro(dates), _public_data(dates))
    selection_columns = set(result["selection"].columns)
    assert "holdout_sharpe" not in selection_columns
    assert "selection_score" in selection_columns
    assert result["winner"].name == result["selection"].iloc[0].candidate

    write_macro_regime_strategy_v3_reports(tmp_path, result)
    expected = {
        "simplification_results.md",
        "development_vs_holdout.md",
        "regime_stability.md",
        "pbo_and_statistics.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "Holdout was not used" in (tmp_path / "simplification_results.md").read_text(encoding="utf-8")

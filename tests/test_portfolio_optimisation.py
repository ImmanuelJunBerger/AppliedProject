import numpy as np
import pandas as pd

from crypto_mlsystem import portfolio_optimisation as po
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2750, assets: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(831)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = 0.0004 + 0.001 * np.sin(np.arange(days) / 71) + rng.normal(0, 0.018, days)
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


def test_portfolio_optimisation_writes_reports_without_changing_signal(monkeypatch, tmp_path):
    small = [
        po.PortfolioCandidate("equal_small", "equal_weight", "btc_eth", False, "test equal"),
        po.PortfolioCandidate("inv_vol_small", "inverse_volatility", "btc_eth_cash", True, "test inv vol"),
    ]
    monkeypatch.setattr(po, "predeclared_portfolio_candidates", lambda: small)
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = po.run_portfolio_optimisation(panel, _macro(dates), _public_data())

    assert result["protocol"]["baseline"] == po.BASELINE_NAME
    assert result["tested_configurations"] == 2
    assert "holdout_sharpe" not in set(result["selection"].columns)
    assert result["winner"] in {"equal_small", "inv_vol_small"}

    po.write_portfolio_optimisation_reports(tmp_path, result)
    expected = {
        "executive_summary.md",
        "portfolio_methods.md",
        "dynamic_risk_budgeting.md",
        "performance_comparison.md",
        "cost_sensitivity.md",
        "statistical_validation.md",
        "economic_interpretation.md",
        "benchmark_comparison.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "was not modified" in (tmp_path / "executive_summary.md").read_text(encoding="utf-8")

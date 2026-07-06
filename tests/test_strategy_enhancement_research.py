import numpy as np
import pandas as pd

from crypto_mlsystem import strategy_enhancement_research as ser
from crypto_mlsystem.public_crypto_data import PublicDataBundle


def _panel(days: int = 2700, assets: int = 14) -> pd.DataFrame:
    rng = np.random.default_rng(71)
    dates = pd.date_range("2019-01-01", periods=days, freq="D")
    symbols = ["BTC", "ETH"] + [f"COIN{i:02d}" for i in range(assets - 2)]
    market = rng.normal(0.0004, 0.021, len(dates))
    rows = []
    for i, symbol in enumerate(symbols):
        ret = (0.80 + i * 0.015) * market + rng.normal(0.0001, 0.016 + i * 0.0004, len(dates))
        close = (75 + i * 3) * np.exp(np.cumsum(ret))
        volume = rng.lognormal(16.5 - i * 0.02, 0.2, len(dates))
        market_cap = close * rng.lognormal(18.0 - i * 0.01, 0.1, len(dates))
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
        "equity_realized_vol_21d": 0.15 + 0.03 * np.sin(t / 29),
        "equity_momentum_21d": 0.02 * np.sin(t / 53),
        "dow_vol_level": 18 + 3 * np.sin(t / 37),
        "vix_level": vix,
        "vix_change_5d": pd.Series(vix).diff(5).to_numpy(),
        "vix_change_21d": pd.Series(vix).diff(21).to_numpy(),
    })


def _public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    stable_supply = 95e9 * np.cumprod(1 + np.full(len(dates), 0.00012))
    tvl = 42e9 * np.cumprod(1 + np.full(len(dates), 0.00009))
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


def test_enhancement_candidate_sets_cover_all_requested_studies():
    candidates = ser.all_study_candidates()
    assert set(candidates) == set(ser.STUDY_TITLES)
    assert all(candidates[study] for study in ser.STUDY_TITLES)
    assert any(candidate.name.startswith("meta_") for candidate in candidates["study_2_meta_labeling"])


def test_development_percentile_does_not_rank_against_holdout_values():
    dates = pd.date_range("2024-12-01", "2025-01-10", freq="D")
    series = pd.Series(np.arange(len(dates), dtype=float), index=dates)
    percentiles = ser._development_percentile(series)
    assert percentiles.loc["2025-01-10"] == 1.0
    assert percentiles.loc["2024-12-01"] > 0.0


def test_strategy_enhancement_reports_with_development_only_selection(monkeypatch, tmp_path):
    def quick_candidates():
        studies = {}
        for study in ser.STUDY_TITLES:
            def build(dataset, features, base_weights, base_result):
                return base_weights * 0.5

            studies[study] = [
                ser.EnhancementCandidate(
                    study=study,
                    name=f"{study}_quick",
                    family="quick test candidate",
                    description="Half-sized frozen strategy for fast report smoke testing.",
                    feature_drivers="frozen macro features",
                    builder=build,
                )
            ]
        return studies

    monkeypatch.setattr(ser, "all_study_candidates", quick_candidates)
    panel = _panel()
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    result = ser.run_strategy_enhancement_research(panel, _macro(dates), _public_data(dates))
    assert "holdout_sharpe" not in set(result["selection"].columns)
    assert set(result["studies"]) == set(ser.STUDY_TITLES)

    ser.write_strategy_enhancement_reports(tmp_path, result)
    expected = {
        "executive_summary.md",
        "study_1_exposure_sizing.md",
        "study_2_meta_labeling.md",
        "study_3_asset_selection.md",
        "study_4_dynamic_horizon.md",
        "study_5_signal_ensemble.md",
        "comparison_to_frozen_strategy.md",
        "statistical_validation.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in tmp_path.iterdir()})
    assert "frozen selected strategy remains" in (tmp_path / "executive_summary.md").read_text(encoding="utf-8")

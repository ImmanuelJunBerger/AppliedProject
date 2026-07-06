from pathlib import Path

import numpy as np
import pandas as pd

from crypto_mlsystem.data import DataIngestion
from crypto_mlsystem.wrds_macro_features import (
    build_lagged_macro_features,
    build_weekly_macro_crypto_panel,
    run_macro_feature_research,
)


def _sample_macro(dates: pd.DatetimeIndex) -> pd.DataFrame:
    n = len(dates)
    return pd.DataFrame({
        "date": dates,
        "sp500_index": 4000 * np.cumprod(1 + np.full(n, 0.0004)),
        "sp500_return": np.full(n, 0.0004),
        "vix": 18 + np.sin(np.arange(n) / 20),
        "treasury_10y": 3.5 + np.linspace(0, 0.5, n),
        "treasury_2y": 3.0 + np.linspace(0, 0.4, n),
        "yield_curve_10y2y": 0.5 + np.linspace(0, 0.1, n),
        "trade_weighted_usd_broad": 120 * np.cumprod(1 + np.full(n, 0.0001)),
        "high_yield_spread": 3.0 + np.cos(np.arange(n) / 30),
    })


def test_lagged_macro_features_are_shifted_one_day():
    panel = DataIngestion().synthetic_panel(days=320, assets=8)
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    macro = _sample_macro(dates)

    features, metadata = build_lagged_macro_features(macro, panel)

    assert "equity_momentum_21d" in features.columns
    assert "macro_risk_on_composite" in features.columns
    assert "commodity_momentum" not in features.columns
    assert metadata.loc[metadata.feature == "vix_level", "lag"].iloc[0].startswith("1 calendar day")
    current_date = dates[40]
    expected = macro.set_index("date").loc[current_date - pd.Timedelta(days=1), "vix"]
    actual = features.set_index("date").loc[current_date, "vix_level"]
    assert actual == expected


def test_weekly_macro_crypto_panel_contains_macro_features_and_targets():
    panel = DataIngestion().synthetic_panel(days=420, assets=12)
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    macro = _sample_macro(dates)
    features, _ = build_lagged_macro_features(macro, panel)

    weekly = build_weekly_macro_crypto_panel(panel, features, top_n=5)

    assert not weekly.empty
    assert {"date", "symbol", "future_return_1w", "vix_level", "macro_risk_on_composite"}.issubset(weekly.columns)
    assert weekly.groupby("date").symbol.nunique().max() <= 5


def test_macro_feature_research_writes_requested_reports(tmp_path):
    panel = DataIngestion().synthetic_panel(days=460, assets=12)
    dates = pd.date_range(panel.date.min(), panel.date.max(), freq="D")
    macro = _sample_macro(dates)
    coverage = pd.DataFrame([
        {
            "source_name": "test_macro",
            "library": "test",
            "table": "daily",
            "status": "downloaded",
            "start_date": str(dates.min().date()),
            "end_date": str(dates.max().date()),
            "rows": len(dates),
            "columns": "sp500_index, vix",
            "frequency": "daily",
            "note": "test source",
        }
    ])

    result = run_macro_feature_research(
        crypto_panel=panel,
        macro_daily=macro,
        coverage=coverage,
        output_dir=tmp_path / "reports",
        processed_dir=tmp_path / "processed",
        top_n=5,
    )

    for filename in (
        "data_coverage.md",
        "feature_inventory.md",
        "feature_research.md",
        "final_recommendation.md",
    ):
        assert (tmp_path / "reports" / filename).exists()
    text = (tmp_path / "reports" / "final_recommendation.md").read_text(encoding="utf-8")
    assert "No trading strategy was run" in text
    assert not result.ic_report.empty

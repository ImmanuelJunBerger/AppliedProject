import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

from crypto_mlsystem.data import DataIngestion
from crypto_mlsystem.forecast_portfolio import (
    OverlayRule,
    build_overlay_weights,
    overlay_candidates,
    run_forecast_portfolio_study,
)
from crypto_mlsystem.signals import build_signal_bundle
from crypto_mlsystem.volatility_expansion import point_in_time_liquid_universe


def test_overlay_candidate_grids_are_predeclared_and_small():
    assert len(overlay_candidates("risk_off_sizing")) == 3
    assert len(overlay_candidates("breakout_activation")) == 3
    assert len(overlay_candidates("volatility_targeted_sizing")) == 6
    assert len(overlay_candidates("strategy_switching")) == 6


def test_risk_off_sizing_reduces_exposure_when_probability_is_high():
    panel = DataIngestion().synthetic_panel(days=420, assets=8, seed=31)
    _, universes = point_in_time_liquid_universe(panel, top_n=5)
    bundle = build_signal_bundle(panel, universes, "W-FRI", 0.20)
    forecast = pd.Series(0.0, index=bundle.asset_returns.index)
    first, second = bundle.rebalance_dates[-2:]
    forecast.loc[first] = 0.1
    forecast.loc[second] = 0.9
    weights = build_overlay_weights(
        bundle, forecast, OverlayRule("risk_off_sizing", floor=0.25), "trend_following"
    )
    low_multiplier = 0.25 + 0.75 * 0.9
    high_multiplier = 0.25 + 0.75 * 0.1
    assert weights.loc[first].sum() == pytest.approx(
        bundle.weights["trend_following"].loc[first].sum() * low_multiplier
    )
    assert weights.loc[second].sum() == pytest.approx(
        bundle.weights["trend_following"].loc[second].sum() * high_multiplier
    )


def test_holdout_probabilities_do_not_change_development_selected_rules():
    panel = DataIngestion().synthetic_panel(days=760, assets=9, seed=37)
    _, universes = point_in_time_liquid_universe(panel, top_n=5)
    dates = pd.date_range("2020-07-30", periods=560, freq="D")
    holdout_start = pd.Timestamp("2021-08-01")
    predictions = pd.DataFrame({
        "date": dates,
        "model": "elastic_net",
        "feature_set": "price_only",
        "probability": 0.5 + 0.3 * np.sin(np.arange(len(dates)) / 17),
    })
    first = run_forecast_portfolio_study(
        panel, predictions, universes,
        holdout_start=holdout_start, holdout_end=dates.max(), cost_levels=(25,),
    )
    changed = predictions.copy()
    changed.loc[changed.date >= holdout_start, "probability"] = 1 - changed.loc[
        changed.date >= holdout_start, "probability"
    ]
    second = run_forecast_portfolio_study(
        panel, changed, universes,
        holdout_start=holdout_start, holdout_end=dates.max(), cost_levels=(25,),
    )
    assert first.selected_rules == second.selected_rules
    assert first.protocol["prediction_model_fitted"] is False
    assert first.protocol["holdout_threshold_searches"] == 0


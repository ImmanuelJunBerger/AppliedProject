import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from crypto_mlsystem.data import DataIngestion
from crypto_mlsystem.volatility_expansion import (
    HAR_FEATURES,
    build_volatility_expansion_dataset,
    point_in_time_liquid_universe,
    run_volatility_expansion_study,
)


def _simple_panel(days=260):
    dates = pd.date_range("2020-01-01", periods=days, freq="D")
    rows = []
    for number, symbol in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]):
        close = 10 + number + np.linspace(0, 2, days) + 0.2 * np.sin(np.arange(days) / (4 + number))
        volume = np.full(days, 1000.0 / (number + 1))
        for date_, price, amount in zip(dates, close, volume):
            rows.append((date_, symbol, price, price * 1.01, price * 0.99, price, amount, price * amount))
    return pd.DataFrame(
        rows,
        columns=["date", "symbol", "open", "high", "low", "close", "volume", "market_cap"],
    )


def test_liquid_universe_uses_only_prior_volume():
    panel = _simple_panel()
    shock_date = pd.Timestamp("2020-08-15")
    before, _ = point_in_time_liquid_universe(panel, top_n=5)
    shocked = panel.copy()
    shocked.loc[(shocked.date >= shock_date) & (shocked.symbol == "FFF"), "volume"] = 1e12
    after, _ = point_in_time_liquid_universe(shocked, top_n=5)
    comparison_end = shock_date - pd.Timedelta(days=1)
    pd.testing.assert_frame_equal(before.loc[:comparison_end], after.loc[:comparison_end])


def test_forward_label_is_separate_from_time_t_features():
    panel = DataIngestion().synthetic_panel(days=500, assets=10, seed=11)
    original = build_volatility_expansion_dataset(panel, top_n=5)
    decision_date = original.frame.index[100]
    changed = panel.copy()
    future = changed.date > decision_date
    changed.loc[future, "close"] *= np.where(
        (changed.loc[future, "date"] - decision_date).dt.days <= 7, 1.5, 1.0
    )
    changed.loc[future, "high"] = np.maximum(changed.loc[future, "high"], changed.loc[future, "close"])
    changed_dataset = build_volatility_expansion_dataset(changed, top_n=5)
    pd.testing.assert_series_equal(
        original.frame.loc[decision_date, HAR_FEATURES],
        changed_dataset.frame.loc[decision_date, HAR_FEATURES],
    )
    assert original.frame.loc[decision_date, "future_rv_7"] != changed_dataset.frame.loc[decision_date, "future_rv_7"]


def test_locked_holdout_never_enters_training_or_cpcv_tuning():
    panel = DataIngestion().synthetic_panel(days=760, assets=9, seed=17)
    holdout_start = pd.Timestamp("2021-08-01")
    holdout_end = pd.Timestamp("2022-01-15")
    result = run_volatility_expansion_study(
        panel,
        top_n=5,
        holdout_start=holdout_start,
        holdout_end=holdout_end,
        min_training_days=180,
        outer_test_months=4,
        model_names=("har", "elastic_net"),
    )
    holdout_predictions = result.predictions[result.predictions.split == "holdout"]
    assert not holdout_predictions.empty
    assert holdout_predictions.date.min() >= holdout_start
    holdout_selection = result.selection_history[result.selection_history.split == "holdout"]
    assert (pd.to_datetime(holdout_selection.max_train_label_end) < holdout_start).all()
    assert (pd.to_datetime(holdout_selection.train_end) < holdout_start).all()
    assert set(result.metrics.model) == {"har", "elastic_net"}
    assert "price_derivatives" in set(result.availability.loc[result.availability.available, "feature_set"])


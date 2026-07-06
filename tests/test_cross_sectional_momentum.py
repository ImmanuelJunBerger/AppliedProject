import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from crypto_mlsystem.cross_sectional_momentum import (
    Candidate,
    benchmark_portfolio,
    build_momentum_dataset,
    momentum_baseline_scores,
    scores_to_portfolio,
    walk_forward_candidate_scores,
)
from crypto_mlsystem.data import DataIngestion


def _dataset(days=850, assets=12, seed=23):
    panel = DataIngestion().synthetic_panel(days=days, assets=assets, seed=seed)
    return panel, build_momentum_dataset(panel, top_n=8, min_history_days=120)


def test_residual_and_raw_forward_ranks_are_equivalent_within_week():
    _, dataset = _dataset(days=500)
    assert dataset.metadata["residual_rank_equals_forward_rank"] is True
    np.testing.assert_allclose(
        dataset.events.target_forward_rank,
        dataset.events.target_residual_rank,
        equal_nan=True,
    )


def test_future_prices_change_labels_but_not_signal_time_features():
    panel, dataset = _dataset(days=520)
    decision_date = pd.Timestamp(dataset.events.date.unique()[20])
    symbol = dataset.events.loc[dataset.events.date == decision_date, "symbol"].iloc[0]
    original = dataset.events[(dataset.events.date == decision_date) & (dataset.events.symbol == symbol)].iloc[0]

    changed = panel.copy()
    future_week = (
        (changed.symbol == symbol)
        & (changed.date > decision_date)
        & (changed.date <= decision_date + pd.Timedelta(days=7))
    )
    changed.loc[future_week, ["open", "high", "low", "close"]] *= 1.50
    changed_dataset = build_momentum_dataset(changed, top_n=8, min_history_days=120)
    revised = changed_dataset.events[
        (changed_dataset.events.date == decision_date) & (changed_dataset.events.symbol == symbol)
    ].iloc[0]

    feature_columns = dataset.feature_sets["all_features"]
    pd.testing.assert_series_equal(
        original[feature_columns], revised[feature_columns], check_names=False
    )
    assert original.forward_return != revised.forward_return


def test_locked_holdout_is_excluded_from_training_and_cpcv():
    _, dataset = _dataset(days=900)
    holdout_start = pd.Timestamp(dataset.events.date.unique()[-18])
    holdout_end = pd.Timestamp(dataset.events.label_end.max())
    candidate = Candidate("elastic_net__forward_rank", "elastic_net", "forward_rank", "price_only")
    scores, selections, _, _ = walk_forward_candidate_scores(
        dataset,
        [candidate],
        holdout_start=holdout_start,
        holdout_end=holdout_end,
        minimum_training_weeks=20,
    )

    holdout_scores = scores[scores.split == "holdout"]
    holdout_selections = selections[selections.split == "holdout"]
    assert not holdout_scores.empty
    assert not holdout_selections.empty
    assert holdout_scores.date.min() >= holdout_start
    assert (pd.to_datetime(holdout_selections.max_train_label_end) < holdout_start).all()


def test_portfolio_is_long_only_capped_and_turnover_constrained():
    _, dataset = _dataset(days=520)
    scores = momentum_baseline_scores(dataset)
    result = scores_to_portfolio(
        dataset,
        scores,
        top_k=5,
        max_asset_weight=0.20,
        turnover_cap=0.75,
        cost_bps=25,
    )
    assert result.weights.min().min() >= -1e-12
    assert result.weights.max().max() <= 0.20 + 1e-12
    assert result.weights.sum(axis=1).max() <= 1.0 + 1e-12
    assert result.turnover.max() <= 0.75 + 1e-12


def test_buy_and_hold_benchmarks_are_fully_invested():
    panel = DataIngestion().synthetic_panel(days=520, assets=8, seed=31)
    panel.loc[panel.symbol == "COIN01", "symbol"] = "BTC"
    panel.loc[panel.symbol == "COIN02", "symbol"] = "ETH"
    dataset = build_momentum_dataset(panel, top_n=6, min_history_days=120)
    btc = benchmark_portfolio(dataset, "btc_buy_hold", dataset.events.date.min(), dataset.events.date.max(), 25)
    pair = benchmark_portfolio(dataset, "btc_eth_50_50", dataset.events.date.min(), dataset.events.date.max(), 25)
    assert btc.weights.BTC.max() == pytest.approx(1.0)
    assert pair.weights[["BTC", "ETH"]].max().max() == pytest.approx(0.5)
    assert pair.weights[["BTC", "ETH"]].sum(axis=1).max() == pytest.approx(1.0)

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from crypto_mlsystem.cross_sectional_momentum import PortfolioResult, build_momentum_dataset
from crypto_mlsystem.data import DataIngestion
from crypto_mlsystem.paper_trading_candidate import (
    backtest_weights,
    candidate_weights,
    cpcv_candidate_selection,
    paper_trading_acceptance,
    predeclared_candidates,
)


def _crypto_datasets(days=720):
    panel = DataIngestion().synthetic_panel(days=days, assets=15, seed=41)
    panel.loc[panel.symbol == "COIN01", "symbol"] = "BTC"
    panel.loc[panel.symbol == "COIN02", "symbol"] = "ETH"
    probability = pd.Series(0.50, index=pd.date_range(panel.date.min(), panel.date.max(), freq="D"))
    return (
        build_momentum_dataset(panel, top_n=12, volatility_probability=probability, min_history_days=120),
        build_momentum_dataset(panel, top_n=10, volatility_probability=probability, min_history_days=120),
    )


def test_candidate_grid_is_predeclared_and_covers_all_families():
    candidates = predeclared_candidates()
    assert len(candidates) == 28
    assert len({candidate.name for candidate in candidates}) == len(candidates)
    assert {candidate.family[0] for candidate in candidates} == {"A", "B", "C", "D"}


def test_candidate_weights_are_long_only_and_never_levered():
    primary, top10 = _crypto_datasets()
    for candidate in [predeclared_candidates()[0], predeclared_candidates()[-1]]:
        weights = candidate_weights(primary, top10, candidate)
        assert weights.min().min() >= 0
        assert weights.sum(axis=1).max() <= 1.0 + 1e-12
        result = backtest_weights(
            primary, weights, cost_bps=25, drawdown_brake=candidate.drawdown_brake
        )
        assert result.turnover.max() <= 0.75 + 1e-12


def _fake_result(seed, holdout_shift=0.0):
    dates = pd.date_range("2020-01-01", "2025-06-30", freq="D")
    rng = np.random.default_rng(seed)
    returns = pd.Series(rng.normal(0.0003, 0.01, len(dates)), index=dates)
    returns.loc["2025-01-01":] += holdout_shift
    zero = pd.Series(0.0, index=dates)
    weights = pd.DataFrame({"BTC": 0.5}, index=dates)
    return PortfolioResult(returns, returns, weights, zero, zero, {}, {})


def test_cpcv_selection_is_invariant_to_holdout_returns():
    candidates = predeclared_candidates()[:4]
    original = {candidate.name: _fake_result(number) for number, candidate in enumerate(candidates)}
    altered = {candidate.name: _fake_result(number, holdout_shift=(number + 1) * 0.01) for number, candidate in enumerate(candidates)}
    first = cpcv_candidate_selection(candidates, original, pd.Timestamp("2020-01-01"))
    second = cpcv_candidate_selection(candidates, altered, pd.Timestamp("2020-01-01"))
    assert first[2] == second[2]
    assert first[3] == second[3]
    pd.testing.assert_frame_equal(first[0], second[0])


def test_paper_trading_acceptance_requires_every_condition():
    btc = {"Maximum Drawdown": -0.50}
    passing = {
        "Sharpe": 0.80, "CAGR": 0.10, "Maximum Drawdown": -0.30,
        "Annual Turnover": 4.0,
    }
    cost_50 = {"Sharpe": 0.60, "CAGR": 0.07}
    accepted, failures = paper_trading_acceptance(passing, cost_50, btc)
    assert accepted and not failures
    failing = dict(passing, Sharpe=0.40)
    accepted, failures = paper_trading_acceptance(failing, cost_50, btc)
    assert not accepted
    assert any("0.5" in failure for failure in failures)


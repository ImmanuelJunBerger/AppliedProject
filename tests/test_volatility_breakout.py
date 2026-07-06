import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

from crypto_mlsystem.volatility_breakout import _accept_with_cap, block_bootstrap_sharpe_ci


def test_acceptance_cap_prevents_over_filtering():
    probabilities = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95])
    accepted = _accept_with_cap(probabilities, threshold=0.99, max_rejection=0.70)
    assert accepted.sum() >= 3
    assert accepted[-1]


def test_block_bootstrap_sharpe_is_deterministic():
    returns = pd.Series(np.tile([0.01, -0.005, 0.002], 100))
    first = block_bootstrap_sharpe_ci(returns, samples=100, seed=7)
    second = block_bootstrap_sharpe_ci(returns, samples=100, seed=7)
    assert first == second
    assert first["lower"] <= first["median"] <= first["upper"]

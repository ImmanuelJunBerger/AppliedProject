import numpy as np
import pandas as pd

from crypto_mlsystem.public_crypto_data import PublicDataBundle
from crypto_mlsystem.rl_crypto_allocation import (
    RLCandidate,
    action_weights,
    build_rl_allocation_dataset,
    fit_state_bins,
    rl_candidates,
    transition_reward,
)


def _synthetic_panel() -> pd.DataFrame:
    dates = pd.date_range("2019-01-01", "2026-06-22", freq="D")
    rows = []
    symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT", "LTC", "TRX"]
    for i, symbol in enumerate(symbols):
        returns = 0.00015 + i * 0.00001 + 0.005 * np.sin(np.arange(len(dates)) / (19 + i))
        close = 100 * np.cumprod(1 + returns)
        volume = 1_000_000 + i * 100_000 + 5_000 * np.cos(np.arange(len(dates)) / 17.0)
        rows.append(pd.DataFrame({
            "date": dates,
            "symbol": symbol,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": volume,
            "market_cap": close * volume,
        }))
    return pd.concat(rows, ignore_index=True)


def _synthetic_public_data(dates: pd.DatetimeIndex) -> PublicDataBundle:
    stable_supply = 100_000_000 + np.arange(len(dates)) * 10_000.0
    tvl = 1_000_000_000 + np.arange(len(dates)) * 50_000.0
    stable = pd.DataFrame({
        "date": dates,
        "stablecoin_supply": stable_supply,
        "stablecoin_supply_usd": stable_supply,
    })
    stable["stablecoin_supply_change_7d"] = stable.stablecoin_supply_usd.pct_change(7, fill_method=None)
    chain_tvl = pd.DataFrame({"date": dates, "chain": "all", "tvl": tvl})
    return PublicDataBundle(
        coverage=pd.DataFrame(),
        stablecoins=stable,
        chain_tvl=chain_tvl,
        protocol_tvl=pd.DataFrame(),
        coingecko_markets=pd.DataFrame(),
        coingecko_categories=pd.DataFrame(),
        coingecko_coin_daily=pd.DataFrame(),
        binance_4h=pd.DataFrame(),
        binance_4h_daily_features=pd.DataFrame(),
        token_unlocks=pd.DataFrame(),
        metadata={},
    )


def test_rl_action_weights_are_long_only_unlevered():
    dates = pd.date_range("2019-01-01", "2026-06-22", freq="D")
    dataset = build_rl_allocation_dataset(_synthetic_panel(), _synthetic_public_data(dates))
    date = pd.Timestamp("2021-01-08")
    for action in ("cash", "btc", "eth", "btc_eth_50_50", "top3_momentum", "top5_momentum"):
        weights = action_weights(dataset, date, action, "top10")
        assert (weights >= -1e-12).all()
        assert weights.sum() <= 1.0 + 1e-12


def test_rl_candidate_grid_covers_required_models_rewards_and_universes():
    candidates = rl_candidates()
    assert {candidate.universe for candidate in candidates} == {"btc_eth", "top10"}
    assert {candidate.rebalance_days for candidate in candidates} == {7, 14}
    assert {"tabular_q", "fitted_q_linear"} == {candidate.model for candidate in candidates}
    assert {
        "raw_return",
        "return_minus_volatility",
        "return_minus_drawdown",
        "return_minus_turnover",
        "adaptive_risk_control",
    } == {candidate.reward for candidate in candidates}


def test_risk_aware_rewards_penalize_risk_and_turnover():
    daily = pd.Series([0.01, -0.02, 0.015, -0.01, 0.005])
    raw = transition_reward(daily, turnover=1.0, reward_name="raw_return", cost_bps=25)
    vol_penalty = transition_reward(daily, turnover=1.0, reward_name="return_minus_volatility", cost_bps=25)
    dd_penalty = transition_reward(daily, turnover=1.0, reward_name="return_minus_drawdown", cost_bps=25)
    turn_penalty = transition_reward(daily, turnover=1.0, reward_name="return_minus_turnover", cost_bps=25)
    adaptive = transition_reward(daily, turnover=1.0, reward_name="adaptive_risk_control", cost_bps=25)
    assert vol_penalty < raw
    assert dd_penalty < raw
    assert turn_penalty < raw
    assert adaptive < raw


def test_state_bins_depend_only_on_passed_training_data():
    train = pd.DataFrame({
        "btc_momentum_30": np.linspace(-1, 1, 100),
        "prev_cash_weight": np.linspace(0, 1, 100),
    })
    holdout_changed = pd.concat([
        train,
        pd.DataFrame({"btc_momentum_30": [1000, 2000], "prev_cash_weight": [1, 1]}),
    ], ignore_index=True)
    train_bins = fit_state_bins(train)
    changed_bins = fit_state_bins(holdout_changed.iloc[:100])
    assert train_bins == changed_bins

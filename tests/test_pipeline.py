import pytest
pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from crypto_mlsystem.data import DataIngestion, UniverseBuilder
from crypto_mlsystem.strategies import strategy_return_frame
from crypto_mlsystem.features import build_features, make_strategy_targets
from crypto_mlsystem.ml import walk_forward_allocations
from crypto_mlsystem.backtest import apply_allocations


def test_full_walk_forward_pipeline_runs():
    panel = DataIngestion().synthetic_panel(days=520, assets=12)
    universe = UniverseBuilder(min_history_days=250).monthly_universe(panel, 10)
    selected = sorted(set().union(*universe.values()))
    panel = panel[panel.symbol.isin(selected)]
    sret = strategy_return_frame(panel)
    feats = build_features(panel, sret)
    targets = make_strategy_targets(sret)
    alloc = walk_forward_allocations(feats, targets, list(sret.columns), train_min_days=260, model_name="equal_weight")
    result = apply_allocations(sret, alloc, cost_bps=25)
    assert not alloc.empty
    assert set(alloc.columns) == set(sret.columns)
    assert "Sharpe" in result["metrics"]
    assert result["returns"].index.is_monotonic_increasing


def test_monthly_universe_is_point_in_time_and_membership_can_change():
    dates = pd.date_range("2024-01-01", "2024-03-05", freq="D")
    rows = []
    for date in dates:
        for symbol in ["AAA", "BBB"]:
            volume = 100 if symbol == "AAA" else 10
            if date >= pd.Timestamp("2024-02-01") and symbol == "BBB":
                volume = 1000
            rows.append((date, symbol, 1, 1, 1, 1, volume, volume))
    panel = pd.DataFrame(rows, columns=["date", "symbol", "open", "high", "low", "close", "volume", "market_cap"])
    builder = UniverseBuilder(min_history_days=1)
    universes = builder.monthly_universe(panel, 1)

    assert universes[pd.Timestamp("2024-02-01")] == ["AAA"]
    assert universes[pd.Timestamp("2024-03-01")] == ["BBB"]
    mask = builder.membership_mask(panel, universes)
    assert bool(mask.loc["2024-02-15", "AAA"])
    assert not bool(mask.loc["2024-03-01", "AAA"])

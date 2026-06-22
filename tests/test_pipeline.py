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

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

from crypto_mlsystem.data import DataIngestion, UniverseBuilder
from crypto_mlsystem.signals import build_signal_bundle


def test_asset_signals_are_long_only_capped_and_rebalanced():
    panel = DataIngestion().synthetic_panel(days=240, assets=15)
    universes = UniverseBuilder(min_history_days=30).monthly_universe(panel, 10)
    bundle = build_signal_bundle(panel, universes, "W-FRI", max_asset_weight=0.20)
    for weights in bundle.weights.values():
        assert (weights >= 0).all().all()
        assert float(weights.max().max()) <= 0.2000001
        assert (weights.sum(axis=1) <= 1.0000001).all()
        changes = weights.diff().abs().sum(axis=1) > 1e-12
        assert set(weights.index[changes]).issubset(set(bundle.rebalance_dates))

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

from crypto_mlsystem.signals import SignalBundle
from crypto_mlsystem.triple_barrier import triple_barrier_events


def test_triple_barrier_profit_and_stop_labels_use_future_path_only_for_labels():
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    close = np.linspace(100, 103, len(dates))
    rows = []
    for i, (date, price) in enumerate(zip(dates, close)):
        high = price * (1.10 if i == 22 else 1.001)
        low = price * (0.90 if i == 26 else 0.999)
        rows.append((date, "AAA", price, high, low, price, 1000, 100000))
    panel = pd.DataFrame(rows, columns=["date", "symbol", "open", "high", "low", "close", "volume", "market_cap"])
    weights = pd.DataFrame(0.0, index=dates, columns=["AAA"])
    weights.loc[dates[20]] = 1.0
    strengths = weights.copy()
    eligible = pd.DataFrame(True, index=dates, columns=["AAA"])
    returns = pd.DataFrame({"AAA": pd.Series(close, index=dates).pct_change().fillna(0)})
    bundle = SignalBundle({"trend_following": weights}, {"trend_following": strengths}, eligible, returns, pd.DatetimeIndex([dates[20]]))
    events = triple_barrier_events(panel, bundle, profit_taking=1000.0, stop_loss=1000.0, vertical_days=5)
    assert len(events) == 1
    assert events.iloc[0].label == 1
    assert events.iloc[0].label_end == dates[22]

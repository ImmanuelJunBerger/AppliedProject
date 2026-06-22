from __future__ import annotations
import numpy as np
import pandas as pd

STABLE_OR_WRAPPED = {"USDT","USDC","DAI","BUSD","TUSD","FDUSD","WBTC","WETH","STETH"}

class DataIngestion:
    """Loads cleaned crypto panels or generates deterministic research fixtures.

    Expected input columns: date, symbol, open, high, low, close, volume, market_cap.
    Optional columns are preserved: funding_rate, open_interest, basis.
    """
    required = {"date", "symbol", "open", "high", "low", "close", "volume", "market_cap"}

    def load_csv(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path, parse_dates=["date"])
        missing = self.required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")
        return self.clean(df)

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy().sort_values(["date", "symbol"])
        numeric = [c for c in df.columns if c not in {"date", "symbol"}]
        df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce")
        df = df.drop_duplicates(["date", "symbol"]).query("close > 0 and volume >= 0")
        return df

    def synthetic_panel(self, days: int = 1200, assets: int = 35, seed: int = 7) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        dates = pd.date_range("2020-01-01", periods=days, freq="D")
        rows = []
        market = rng.normal(0.0008, 0.035, days)
        for i in range(assets):
            beta = rng.uniform(0.6, 1.4)
            alpha = rng.normal(0, 0.0004)
            vol = rng.uniform(0.025, 0.08)
            ret = alpha + beta * market + rng.normal(0, vol, days)
            close = 20 * np.exp(np.cumsum(ret))
            volume = rng.lognormal(16 - i * 0.045, 0.5, days)
            cap = close * rng.lognormal(19 - i * 0.04, 0.25, days)
            high = close * (1 + np.abs(rng.normal(0.015, 0.01, days)))
            low = close * (1 - np.abs(rng.normal(0.015, 0.01, days)))
            sym = f"COIN{i+1:02d}"
            for d, c, h, l, v, m in zip(dates, close, high, low, volume, cap):
                rows.append((d, sym, c, h, l, c, v, m, rng.normal(0.0001, 0.0005), v / 10, rng.normal(0, 0.01)))
        return pd.DataFrame(rows, columns=["date","symbol","open","high","low","close","volume","market_cap","funding_rate","open_interest","basis"])

class UniverseBuilder:
    def __init__(self, exclusions: set[str] | None = None, min_history_days: int = 365):
        self.exclusions = (exclusions or set()) | STABLE_OR_WRAPPED
        self.min_history_days = min_history_days

    def monthly_universe(self, panel: pd.DataFrame, top_n: int) -> dict[pd.Timestamp, list[str]]:
        panel = panel.copy()
        panel["turnover"] = panel["close"] * panel["volume"]
        history = panel.groupby("symbol")["date"].nunique()
        eligible = history[history >= self.min_history_days].index.difference(self.exclusions)
        month_ends = panel["date"].dt.to_period("M").drop_duplicates().dt.to_timestamp("M")
        universes = {}
        for month_end in month_ends:
            lookback = panel[(panel.date <= month_end) & (panel.date > month_end - pd.Timedelta(days=30)) & panel.symbol.isin(eligible)]
            ranking = lookback.groupby("symbol")[["turnover", "market_cap"]].median().mean(axis=1).sort_values(ascending=False)
            universes[month_end] = ranking.head(top_n).index.tolist()
        return universes

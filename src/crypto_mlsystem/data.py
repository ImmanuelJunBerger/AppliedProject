from __future__ import annotations
import numpy as np
import pandas as pd

STABLE_OR_WRAPPED = {
    "USDT", "USDC", "DAI", "BUSD", "TUSD", "FDUSD", "USDP", "PYUSD",
    "USDE", "USDS", "USD1", "XUSD", "USDD", "USDJ", "UST", "USTC",
    "GUSD", "LUSD", "SUSD", "CUSD", "FRAX", "RLUSD", "BFUSD", "AEUR",
    "EURS", "EURC", "BIDR", "IDRT", "EUR", "GBP", "AUD", "BRL", "TRY",
    "RUB", "UAH", "NGN", "PLN", "RON", "ZAR", "ARS", "MXN", "JPY",
    "WBTC", "WETH", "STETH", "WSTETH", "WBETH", "BETH", "BTCB", "CBBTC",
    "PAXG", "XAUT",
}

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
        """Build a point-in-time liquid universe at each month start.

        Membership effective on a date uses only observations strictly before that
        date.  This avoids both full-sample eligibility look-ahead and using the
        current month's liquidity to trade earlier in that month.
        """
        panel = panel.copy()
        panel["turnover"] = panel["close"] * panel["volume"]
        panel = panel[~panel["symbol"].isin(self.exclusions)]
        dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
        effective_dates = pd.Series(dates, index=dates).groupby(dates.to_period("M")).first().tolist()
        universes = {}
        for effective_date in effective_dates:
            prior = panel[panel.date < effective_date]
            history = prior.groupby("symbol")["date"].nunique()
            eligible = history[history >= self.min_history_days].index
            lookback = prior[
                (prior.date >= effective_date - pd.Timedelta(days=30))
                & prior.symbol.isin(eligible)
            ]
            ranking = lookback.groupby("symbol")["turnover"].median().sort_values(ascending=False)
            universes[pd.Timestamp(effective_date)] = ranking.head(top_n).index.tolist()
        return universes

    @staticmethod
    def membership_mask(panel: pd.DataFrame, universes: dict[pd.Timestamp, list[str]]) -> pd.DataFrame:
        """Return a daily boolean asset-membership matrix for a dated universe."""
        dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
        symbols = sorted(panel["symbol"].unique())
        snapshots = pd.DataFrame(np.nan, index=dates, columns=symbols, dtype=float)
        for date, members in universes.items():
            if date in snapshots.index:
                snapshots.loc[date] = 0.0
                snapshots.loc[date, snapshots.columns.intersection(members)] = 1.0
        return snapshots.ffill().fillna(False).astype(bool)

import numpy as np
import pandas as pd
from .strategies import price_matrix

def build_features(panel: pd.DataFrame, strategy_returns: pd.DataFrame) -> pd.DataFrame:
    px = price_matrix(panel); ret = px.pct_change()
    features = pd.DataFrame(index=px.index)
    mkt = ret.mean(axis=1)
    features["realized_vol_30"] = mkt.rolling(30).std() * (365 ** 0.5)
    features["breadth_30"] = (ret > 0).rolling(30).mean().mean(axis=1)
    features["dispersion_30"] = ret.rolling(30).std().mean(axis=1)
    features["avg_corr_60"] = ret.rolling(60).corr().groupby(level=0).mean().mean(axis=1)
    for horizon in [7, 14, 30, 90]:
        features[f"momentum_{horizon}"] = px.pct_change(horizon).mean(axis=1)
    wealth = (1 + mkt.fillna(0)).cumprod()
    features["market_drawdown"] = wealth / wealth.cummax() - 1
    features["tail_proxy_30"] = mkt.rolling(30).quantile(0.05)
    vol = panel.pivot(index="date", columns="symbol", values="volume")
    cap = panel.pivot(index="date", columns="symbol", values="market_cap")
    features["volume_growth_30"] = vol.sum(axis=1).pct_change(30)
    features["turnover"] = (vol * px).sum(axis=1) / cap.sum(axis=1)
    for name in strategy_returns.columns:
        sr = strategy_returns[name]
        features[f"{name}_return_28"] = sr.rolling(28).mean()
        features[f"{name}_vol_28"] = sr.rolling(28).std()
        curve = (1 + sr.fillna(0)).cumprod()
        features[f"{name}_drawdown"] = curve / curve.cummax() - 1
        features[f"{name}_win_rate_28"] = (sr > 0).rolling(28).mean()
    return features.shift(1).replace([np.inf, -np.inf], np.nan).dropna()

def make_strategy_targets(strategy_returns: pd.DataFrame, horizon: int = 7) -> pd.Series:
    future = strategy_returns.rolling(horizon).sum().shift(-horizon)
    return future.idxmax(axis=1).rename("best_strategy")

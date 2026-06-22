import numpy as np
import pandas as pd

def performance_metrics(returns: pd.Series, turnover: pd.Series | None = None, costs: pd.Series | None = None) -> dict:
    r = returns.dropna(); wealth = (1 + r).cumprod(); dd = wealth / wealth.cummax() - 1
    ann = 365; downside = r[r < 0].std() * np.sqrt(ann)
    cagr = wealth.iloc[-1] ** (ann / max(len(r), 1)) - 1 if len(r) else 0
    vol = r.std() * np.sqrt(ann)
    return {
        "CAGR": cagr, "Sharpe": (r.mean() * ann) / vol if vol else 0,
        "Sortino": (r.mean() * ann) / downside if downside else 0,
        "Calmar": cagr / abs(dd.min()) if dd.min() else 0,
        "Annualized Volatility": vol, "Maximum Drawdown": dd.min(),
        "Hit Rate": (r > 0).mean(), "Turnover": 0 if turnover is None else turnover.reindex(r.index).mean(),
        "Exposure": (r != 0).mean(), "Transaction Costs": 0 if costs is None else costs.reindex(r.index).sum(),
    }

def rolling_sharpe(returns, window=90):
    return returns.rolling(window).mean() / returns.rolling(window).std() * np.sqrt(365)

def rolling_drawdown(returns):
    wealth = (1 + returns.fillna(0)).cumprod(); return wealth / wealth.cummax() - 1

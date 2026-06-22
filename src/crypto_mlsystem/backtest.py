import pandas as pd
from .costs import transaction_cost
from .metrics import performance_metrics

def apply_allocations(strategy_returns: pd.DataFrame, allocations: pd.DataFrame, cost_bps: int = 25):
    weights = allocations.reindex(strategy_returns.index).ffill().fillna(0)
    gross = (weights * strategy_returns).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(weights.abs().sum(axis=1))
    costs = transaction_cost(turnover, cost_bps)
    net = gross - costs
    return {"returns": net, "gross_returns": gross, "weights": weights, "turnover": turnover, "costs": costs, "metrics": performance_metrics(net, turnover, costs)}

def benchmark_returns(panel: pd.DataFrame, strategy_returns: pd.DataFrame):
    px = panel.pivot(index="date", columns="symbol", values="close").sort_index(); ret = px.pct_change().fillna(0)
    out = {"equal_weight_strategy": strategy_returns.mean(axis=1), "equal_weight_universe": ret.mean(axis=1)}
    if px.shape[1] >= 1: out["BTC_proxy_buy_hold"] = ret.iloc[:, 0]
    if px.shape[1] >= 2:
        out["ETH_proxy_buy_hold"] = ret.iloc[:, 1]; out["50_50_BTC_ETH_proxy"] = ret.iloc[:, :2].mean(axis=1)
    return pd.DataFrame(out)

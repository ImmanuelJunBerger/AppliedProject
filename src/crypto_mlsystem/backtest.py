import pandas as pd
from .costs import transaction_cost
from .metrics import performance_metrics

def apply_allocations(strategy_returns: pd.DataFrame, allocations: pd.DataFrame, cost_bps: int = 25):
    if not allocations.empty:
        strategy_returns = strategy_returns.loc[allocations.index.min():]
    weights = allocations.reindex(strategy_returns.index).ffill().fillna(0)
    gross = (weights * strategy_returns).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(weights.abs().sum(axis=1))
    costs = transaction_cost(turnover, cost_bps)
    net = gross - costs
    return {"returns": net, "gross_returns": gross, "weights": weights, "turnover": turnover, "costs": costs, "metrics": performance_metrics(net, turnover, costs)}

def benchmark_returns(panel: pd.DataFrame, strategy_returns: pd.DataFrame, universes=None):
    px = panel.pivot(index="date", columns="symbol", values="close").sort_index(); ret = px.pct_change().fillna(0)
    if universes is not None:
        from .data import UniverseBuilder
        eligible = UniverseBuilder.membership_mask(panel, universes).reindex(index=px.index, columns=px.columns, fill_value=False)
        universe_return = ret.where(eligible).mean(axis=1).fillna(0)
    else:
        universe_return = ret.mean(axis=1)
    out = {"equal_weight_strategy": strategy_returns.mean(axis=1), "equal_weight_universe": universe_return}
    if "BTC" in ret: out["BTC_proxy_buy_hold"] = ret["BTC"]
    if "ETH" in ret:
        out["ETH_proxy_buy_hold"] = ret["ETH"]
    if {"BTC", "ETH"}.issubset(ret.columns):
        out["50_50_BTC_ETH_proxy"] = ret[["BTC", "ETH"]].mean(axis=1)
    return pd.DataFrame(out)

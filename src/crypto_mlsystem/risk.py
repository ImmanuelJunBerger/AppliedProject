import pandas as pd

def reasoning_layer(weights: pd.DataFrame, features: pd.DataFrame, max_strategy: float, turnover_limit: float) -> pd.DataFrame:
    aligned = features.reindex(weights.index).ffill()
    out = weights.copy().clip(0, max_strategy)
    if "realized_vol_30" in aligned:
        scale = (0.80 - aligned["realized_vol_30"]).clip(0.25, 1.0)
        out = out.mul(scale, axis=0)
    out = out.div(out.sum(axis=1).replace(0, 1), axis=0).fillna(0)
    prev = out.shift().fillna(0)
    turnover = (out - prev).abs().sum(axis=1)
    too_high = turnover > turnover_limit
    out.loc[too_high] = prev.loc[too_high] + (out.loc[too_high] - prev.loc[too_high]).mul(turnover_limit / turnover.loc[too_high], axis=0)
    return out

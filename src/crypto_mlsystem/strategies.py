import numpy as np
import pandas as pd

def price_matrix(panel):
    return panel.pivot(index="date", columns="symbol", values="close").sort_index()

def _normalize_long_only(scores):
    scores = scores.clip(lower=0).replace([np.inf, -np.inf], np.nan).fillna(0)
    denom = scores.sum(axis=1).replace(0, np.nan)
    return scores.div(denom, axis=0).fillna(0)

def trend_following(panel):
    px = price_matrix(panel); ret = px.pct_change()
    score = (px.pct_change(30) > 0).astype(float) + (px.rolling(20).mean() > px.rolling(100).mean()).astype(float)
    return _normalize_long_only(score.shift(1)).mul(ret).sum(axis=1).rename("trend_following")

def cross_sectional_momentum(panel):
    px = price_matrix(panel); ret = px.pct_change(); mom = px.pct_change(90).shift(1)
    ranks = mom.rank(axis=1, pct=True)
    return _normalize_long_only((ranks - 0.5).clip(lower=0)).mul(ret).sum(axis=1).rename("cross_sectional_momentum")

def mean_reversion(panel):
    px = price_matrix(panel); ret = px.pct_change(); rev = -px.pct_change(7).shift(1)
    vol_filter = ret.rolling(30).std().shift(1) < ret.rolling(90).std().shift(1) * 1.5
    return _normalize_long_only(rev.where(vol_filter)).mul(ret).sum(axis=1).rename("mean_reversion")

def volatility_breakout(panel):
    px = price_matrix(panel); ret = px.pct_change(); high = panel.pivot(index="date", columns="symbol", values="high")
    breakout = (px.shift(1) > high.rolling(20).max().shift(2)).astype(float)
    vol_expansion = ret.rolling(7).std().shift(1) > ret.rolling(30).std().shift(1)
    return _normalize_long_only(breakout.where(vol_expansion, 0)).mul(ret).sum(axis=1).rename("volatility_breakout")

def defensive_cash(panel):
    px = price_matrix(panel); ret = px.pct_change(); btc = px.iloc[:, 0]
    hostile = (btc.pct_change(30).shift(1) < 0) | (ret.mean(axis=1).rolling(30).std().shift(1) > ret.mean(axis=1).rolling(90).std().shift(1))
    exposure = (~hostile).astype(float) * 0.7
    return (ret.mean(axis=1).fillna(0) * exposure).rename("defensive_cash")

def strategy_return_frame(panel):
    return pd.concat([trend_following(panel), cross_sectional_momentum(panel), mean_reversion(panel), volatility_breakout(panel), defensive_cash(panel)], axis=1).fillna(0)

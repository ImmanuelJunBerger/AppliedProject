import numpy as np
import pandas as pd

def price_matrix(panel):
    return panel.pivot(index="date", columns="symbol", values="close").sort_index()

def _normalize_long_only(scores):
    scores = scores.clip(lower=0).replace([np.inf, -np.inf], np.nan).fillna(0)
    denom = scores.sum(axis=1).replace(0, np.nan)
    return scores.div(denom, axis=0).fillna(0)

def _mask(panel, universes, px):
    if universes is None:
        return pd.DataFrame(True, index=px.index, columns=px.columns)
    from .data import UniverseBuilder
    return UniverseBuilder.membership_mask(panel, universes).reindex(index=px.index, columns=px.columns, fill_value=False)

def trend_following(panel, eligible=None):
    px = price_matrix(panel); ret = px.pct_change()
    score = (px.pct_change(30) > 0).astype(float) + (px.rolling(20).mean() > px.rolling(100).mean()).astype(float)
    return _normalize_long_only(score.shift(1).where(eligible)).mul(ret).sum(axis=1).rename("trend_following")

def cross_sectional_momentum(panel, eligible=None):
    px = price_matrix(panel); ret = px.pct_change(); mom = px.pct_change(90).shift(1)
    ranks = mom.where(eligible).rank(axis=1, pct=True)
    return _normalize_long_only((ranks - 0.5).clip(lower=0)).mul(ret).sum(axis=1).rename("cross_sectional_momentum")

def mean_reversion(panel, eligible=None):
    px = price_matrix(panel); ret = px.pct_change(); rev = -px.pct_change(7).shift(1)
    vol_filter = ret.rolling(30).std().shift(1) < ret.rolling(90).std().shift(1) * 1.5
    return _normalize_long_only(rev.where(vol_filter & eligible)).mul(ret).sum(axis=1).rename("mean_reversion")

def volatility_breakout(panel, eligible=None):
    px = price_matrix(panel); ret = px.pct_change(); high = panel.pivot(index="date", columns="symbol", values="high")
    breakout = (px.shift(1) > high.rolling(20).max().shift(2)).astype(float)
    vol_expansion = ret.rolling(7).std().shift(1) > ret.rolling(30).std().shift(1)
    return _normalize_long_only(breakout.where(vol_expansion & eligible, 0)).mul(ret).sum(axis=1).rename("volatility_breakout")

def defensive_cash(panel, eligible=None):
    px = price_matrix(panel); ret = px.pct_change(); btc = px.iloc[:, 0]
    if "BTC" in px.columns:
        btc = px["BTC"]
    market_return = ret.where(eligible).mean(axis=1)
    hostile = (btc.pct_change(30).shift(1) < 0) | (market_return.rolling(30).std().shift(1) > market_return.rolling(90).std().shift(1))
    exposure = (~hostile).astype(float) * 0.7
    return (market_return.fillna(0) * exposure).rename("defensive_cash")

def strategy_return_frame(panel, universes=None):
    px = price_matrix(panel); eligible = _mask(panel, universes, px)
    return pd.concat([trend_following(panel, eligible), cross_sectional_momentum(panel, eligible), mean_reversion(panel, eligible), volatility_breakout(panel, eligible), defensive_cash(panel, eligible)], axis=1).fillna(0)

"""Signal library for the Run 7 discovery program.

CONTRACT FOR EVERY FUNCTION HERE:
  * input  : Panel (time x asset frames)
  * output : weight DataFrame (time x asset); row t = target weights decided using
             information available AT bar t. `panel.evaluate` shifts by one bar.
  * every statistic is a TRAILING rolling window. Where a statistic is used as a
    normaliser or threshold it is additionally `.shift(1)`-ed so bar t never enters
    its own threshold.

Anything that cannot satisfy that contract does not belong in this file.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .panel import Panel, normalize_weights


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _xs_decile(score: pd.DataFrame, frac: float = 0.2, long_only: bool = False) -> pd.DataFrame:
    """Cross-sectional long-top / short-bottom weights from a score matrix."""
    s = score.copy()
    valid = s.notna().sum(axis=1)
    r = s.rank(axis=1, pct=True)
    k = max(frac, 1e-9)
    W = pd.DataFrame(0.0, index=s.index, columns=s.columns)
    W[r >= 1 - k] = 1.0
    if not long_only:
        W[r <= k] = -1.0
    W[valid < 5] = 0.0
    return normalize_weights(W)


def _ts_threshold(z: pd.DataFrame, hi: float, direction: int, hold: int) -> pd.DataFrame:
    """Time-series: take a position when |z| crosses a threshold, hold N bars.
    direction=+1 -> follow the sign of z; -1 -> fade it."""
    raw = pd.DataFrame(0.0, index=z.index, columns=z.columns)
    raw[z >= hi] = direction
    raw[z <= -hi] = -direction
    held = raw.replace(0.0, np.nan).ffill(limit=max(hold - 1, 0))
    held = held.where(raw.eq(0) | raw.notna(), raw)
    W = held.fillna(0.0)
    return normalize_weights(W)


def _zscore(x: pd.DataFrame, win: int) -> pd.DataFrame:
    mu = x.rolling(win, min_periods=win // 3).mean().shift(1)
    sd = x.rolling(win, min_periods=win // 3).std().shift(1)
    return (x - mu) / sd.replace(0, np.nan)


def _fwd_hold(entry: pd.DataFrame, hold: int) -> pd.DataFrame:
    """Convert sparse entry signals into a held position for `hold` bars.
    hold<=1 means no carry-forward at all (pandas rejects ffill(limit=0))."""
    if hold is None or hold <= 1:
        return normalize_weights(entry.fillna(0.0))
    out = entry.replace(0.0, np.nan).ffill(limit=hold - 1).fillna(0.0)
    return normalize_weights(out)


# ---------------------------------------------------------------------------
# FAMILY A — flow & positioning
# ---------------------------------------------------------------------------

def A01_funding_neg_extreme(p: Panel, z=2.0, win=24*30, hold=24) -> pd.DataFrame:
    z_ = _zscore(p.f["funding"], win)
    e = pd.DataFrame(0.0, index=z_.index, columns=z_.columns); e[z_ <= -z] = 1.0
    return _fwd_hold(e, hold)


def A02_funding_pos_extreme(p: Panel, z=2.0, win=24*30, hold=24) -> pd.DataFrame:
    z_ = _zscore(p.f["funding"], win)
    e = pd.DataFrame(0.0, index=z_.index, columns=z_.columns); e[z_ >= z] = -1.0
    return _fwd_hold(e, hold)


def A03_funding_carry(p: Panel, thresh=0.0001, win=24*7, hold=24) -> pd.DataFrame:
    persist = p.f["funding"].rolling(win, min_periods=win//3).mean().shift(1)
    e = pd.DataFrame(0.0, index=persist.index, columns=persist.columns)
    e[persist >= thresh] = -1.0
    e[persist <= -thresh] = 1.0
    return _fwd_hold(e, hold)


def A04_funding_signflip(p: Panel, win=24*7, hold=24) -> pd.DataFrame:
    m = p.f["funding"].rolling(win, min_periods=win//3).mean().shift(1)
    flip_up = (m > 0) & (m.shift(1) <= 0)
    flip_dn = (m < 0) & (m.shift(1) >= 0)
    e = pd.DataFrame(0.0, index=m.index, columns=m.columns)
    e[flip_dn] = 1.0; e[flip_up] = -1.0
    return _fwd_hold(e, hold)


def A05_xs_funding_rank(p: Panel, frac=0.2, hold=8) -> pd.DataFrame:
    # long the CHEAPEST funded (most negative), short the dearest -> score = -funding
    sc = -p.f["funding"].shift(1)
    return _fwd_hold(_xs_decile(sc, frac), hold)


def _oi_quadrant(p: Panel, oi_up: bool, px_up: bool, win=24, hold=12, direction=-1) -> pd.DataFrame:
    """OI/price quadrant signals.

    Open interest exists only for the metrics-allowlist subset (~25 symbols) while
    price covers the full panel (~135). Combining a 25-column boolean frame with a
    135-column one yields an OBJECT-dtype frame full of NaN, which pandas refuses as
    a boolean mask. So both sides are explicitly restricted to the OI columns first
    and cast back to bool -- this signal is only defined where OI is observed.
    """
    oi = p.f["oi"]
    cols = [c for c in oi.columns if c in p.close.columns and oi[c].notna().any()]
    if not cols:
        return pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    doi = oi[cols].pct_change(win)
    dpx = p.close[cols].pct_change(win)
    a = (doi > 0) if oi_up else (doi < 0)
    b = (dpx > 0) if px_up else (dpx < 0)
    cond = (a.fillna(False) & b.fillna(False)).astype(bool)
    e = pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    base = 1.0 if px_up else -1.0          # "follow" the price move
    sub = pd.DataFrame(0.0, index=cond.index, columns=cols)
    sub[cond] = direction * base
    e.loc[sub.index, cols] = sub.values
    return _fwd_hold(e, hold)


def A06_oi_up_px_up_fade(p, **k):   return _oi_quadrant(p, True,  True,  direction=-1, **k)
def A07_oi_dn_px_up_follow(p, **k): return _oi_quadrant(p, False, True,  direction=+1, **k)
def A08_oi_up_px_dn_fade(p, **k):   return _oi_quadrant(p, True,  False, direction=-1, **k)
def A09_oi_dn_px_dn_buy(p, **k):    return _oi_quadrant(p, False, False, direction=-1, **k)


def A10_oi_roc_extreme(p: Panel, z=2.0, win=24*14, hold=12) -> pd.DataFrame:
    roc = p.f["oi"].pct_change(24)
    z_ = _zscore(roc, win)
    e = pd.DataFrame(0.0, index=z_.index, columns=z_.columns)
    e[z_ >= z] = -1.0   # rapid leverage build-up -> fade
    return _fwd_hold(e, hold)


def A11_toptrader_follow(p: Panel, z=1.5, win=24*30, hold=24) -> pd.DataFrame:
    z_ = _zscore(p.f["tt_ratio"], win)
    e = pd.DataFrame(0.0, index=z_.index, columns=z_.columns)
    e[z_ >= z] = 1.0; e[z_ <= -z] = -1.0     # follow the informed cohort
    return _fwd_hold(e, hold)


def A12_retail_fade(p: Panel, z=1.5, win=24*30, hold=24) -> pd.DataFrame:
    z_ = _zscore(p.f["acct_ratio"], win)
    e = pd.DataFrame(0.0, index=z_.index, columns=z_.columns)
    e[z_ >= z] = -1.0; e[z_ <= -z] = 1.0     # fade the crowded retail side
    return _fwd_hold(e, hold)


def A13_taker_flow_fade(p: Panel, z=2.0, win=24*14, hold=6) -> pd.DataFrame:
    z_ = _zscore(p.f["taker_ratio"], win)
    e = pd.DataFrame(0.0, index=z_.index, columns=z_.columns)
    e[z_ >= z] = -1.0; e[z_ <= -z] = 1.0
    return _fwd_hold(e, hold)


def A15_cascade_long_only(p: Panel, k=6, z=4.0, vmult=2.0, win=24*14, hold=24) -> pd.DataFrame:
    """Run-6 structural fix: LONG side only (the gross-positive one), higher z, longer hold."""
    ret_k = p.close.pct_change(k)
    sd = ret_k.rolling(win, min_periods=win//4).std().shift(1)
    vol = p.f["qv"]
    medv = vol.rolling(win, min_periods=win//4).median().shift(1)
    cond = (ret_k <= -z * sd) & (vol >= vmult * medv)
    e = pd.DataFrame(0.0, index=cond.index, columns=cond.columns); e[cond] = 1.0
    return _fwd_hold(e, hold)


# ---------------------------------------------------------------------------
# FAMILY B — cross-sectional
# ---------------------------------------------------------------------------

def B_momentum(p: Panel, lookback_h: int, frac=0.2, hold=24, long_only=False) -> pd.DataFrame:
    sc = p.close.pct_change(lookback_h).shift(1)
    return _fwd_hold(_xs_decile(sc, frac, long_only), hold)


def B_reversal(p: Panel, lookback_h: int, frac=0.2, hold=3) -> pd.DataFrame:
    sc = -p.close.pct_change(lookback_h).shift(1)
    return _fwd_hold(_xs_decile(sc, frac), hold)


def B08_idio_vol(p: Panel, win=24*14, frac=0.2, hold=24) -> pd.DataFrame:
    mkt = p.ret.mean(axis=1)
    resid = p.ret.sub(mkt, axis=0)
    sc = -resid.rolling(win, min_periods=win//3).std().shift(1)   # long LOW idio vol
    return _fwd_hold(_xs_decile(sc, frac), hold)


def B09_low_beta(p: Panel, win=24*30, frac=0.2, hold=24) -> pd.DataFrame:
    mkt = p.ret.mean(axis=1)
    cov = p.ret.rolling(win, min_periods=win//3).cov(mkt)
    var = mkt.rolling(win, min_periods=win//3).var()
    beta = cov.div(var, axis=0).shift(1)
    return _fwd_hold(_xs_decile(-beta, frac), hold)               # long LOW beta


def B10_funding_adj_momentum(p: Panel, lookback_h=24*7, frac=0.2, hold=24) -> pd.DataFrame:
    mom = p.close.pct_change(lookback_h)
    carry = p.f["funding"].rolling(lookback_h, min_periods=8).mean() * (lookback_h / 8)
    return _fwd_hold(_xs_decile((mom - carry).shift(1), frac), hold)


def B11_liquidity_scaled_momentum(p: Panel, lookback_h=24*7, frac=0.2, hold=24) -> pd.DataFrame:
    mom = p.close.pct_change(lookback_h)
    adv = p.f["qv"].rolling(24*14, min_periods=24).mean()
    sc = (mom / np.log1p(adv)).shift(1)
    return _fwd_hold(_xs_decile(sc, frac), hold)


SECTORS = {
    "L1": ["ETHUSDT","SOLUSDT","ADAUSDT","AVAXUSDT","DOTUSDT","NEARUSDT","ATOMUSDT","ALGOUSDT",
           "TRXUSDT","EOSUSDT","APTUSDT","SUIUSDT","TONUSDT","SEIUSDT","TIAUSDT"],
    "DeFi": ["UNIUSDT","AAVEUSDT","SUSHIUSDT","COMPUSDT","MKRUSDT","CRVUSDT","SNXUSDT","1INCHUSDT",
             "YFIUSDT","LDOUSDT","PENDLEUSDT","ENAUSDT"],
    "Meme": ["DOGEUSDT","SHIBUSDT","PEPEUSDT","BONKUSDT","WIFUSDT","1000BONKUSDT","1000SHIBUSDT"],
    "Infra": ["LINKUSDT","FILUSDT","GRTUSDT","RENDERUSDT","ARUSDT","STXUSDT","INJUSDT","WLDUSDT"],
}


def B12_sector_rotation(p: Panel, lookback_h=24*7, hold=24*3) -> pd.DataFrame:
    cols = p.close.columns
    W = pd.DataFrame(0.0, index=p.index, columns=cols)
    sec_ret = {}
    for name, members in SECTORS.items():
        m = [c for c in members if c in cols]
        if len(m) >= 3:
            sec_ret[name] = p.close[m].pct_change(lookback_h).mean(axis=1)
    if len(sec_ret) < 2:
        return W
    S = pd.DataFrame(sec_ret).shift(1)
    r = S.rank(axis=1, pct=True)
    for name in S.columns:
        m = [c for c in SECTORS[name] if c in cols]
        if not m:
            continue
        lw = (r[name] >= 0.75).astype(float) - (r[name] <= 0.25).astype(float)
        for c in m:
            W[c] = lw / len(m)
    return _fwd_hold(normalize_weights(W), hold)


# ---------------------------------------------------------------------------
# FAMILY C — volatility
# ---------------------------------------------------------------------------

def C01_vol_compression_breakout(p: Panel, win=24*7, q=0.2, hold=12) -> pd.DataFrame:
    rv = p.ret.rolling(24, min_periods=12).std()
    rank = rv.rolling(win, min_periods=win//3).rank(pct=True).shift(1)
    brk = p.close.pct_change(4)
    e = pd.DataFrame(0.0, index=rv.index, columns=rv.columns)
    compressed = rank <= q
    e[compressed & (brk > 0)] = 1.0
    e[compressed & (brk < 0)] = -1.0
    return _fwd_hold(e, hold)


def C05_range_contraction(p: Panel, win=24, hold=12) -> pd.DataFrame:
    rng = (p.f["high"] - p.f["low"]) / p.close
    narrow = (rng <= rng.rolling(win, min_periods=8).min().shift(1))
    brk = p.close.pct_change(2)
    e = pd.DataFrame(0.0, index=rng.index, columns=rng.columns)
    e[narrow & (brk > 0)] = 1.0
    e[narrow & (brk < 0)] = -1.0
    return _fwd_hold(e, hold)


def C10_regime_conditional(p: Panel, win=24*14, hold=6) -> pd.DataFrame:
    """High-vol -> mean-revert; low-vol -> trend."""
    rv = p.ret.rolling(24, min_periods=12).std()
    hi = (rv > rv.rolling(win, min_periods=win//3).median().shift(1))
    sc = p.close.pct_change(6).shift(1)
    W = _xs_decile(sc.where(~hi), 0.2) + _xs_decile((-sc).where(hi), 0.2)
    return _fwd_hold(normalize_weights(W.fillna(0.0)), hold)


# ---------------------------------------------------------------------------
# FAMILY D — time & microstructure
# ---------------------------------------------------------------------------

def D_hour_bucket(p: Panel, hours: list[int], direction: int = 1, hold: int = 1) -> pd.DataFrame:
    e = pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    mask = p.index.hour.isin(hours)
    e.loc[mask] = float(direction)
    e = e.where(p.close.notna(), 0.0)
    return normalize_weights(e)


def D_dow_bucket(p: Panel, days: list[int], direction: int = 1) -> pd.DataFrame:
    e = pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    mask = p.index.dayofweek.isin(days)
    e.loc[mask] = float(direction)
    e = e.where(p.close.notna(), 0.0)
    return normalize_weights(e)


def D08_settlement_conditional(p: Panel, pre_hours=(23, 7, 15), direction=-1) -> pd.DataFrame:
    """Trade the settlement hour only when funding is materially non-zero,
    in the direction of dodging the payment."""
    e = pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    mask = p.index.hour.isin(list(pre_hours))
    f = p.f["funding"].shift(1)
    sign = np.sign(f).fillna(0.0)
    big = (f.abs() > 0.0001)
    vals = (direction * sign).where(big, 0.0)
    e[mask] = vals[mask]
    return normalize_weights(e.fillna(0.0))


def D09_weekend_revert(p: Panel, hold=24) -> pd.DataFrame:
    wknd = p.index.dayofweek.isin([5, 6])
    move = p.close.pct_change(24)
    e = pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    sel = pd.Series(wknd, index=p.index)
    e[sel.values] = -np.sign(move[sel.values]).fillna(0.0)
    return _fwd_hold(e, hold)


# ---------------------------------------------------------------------------
# FAMILY E — statistical arbitrage
# ---------------------------------------------------------------------------

def E06_residual_reversion(p: Panel, beta_win=24*30, z_win=24*7, z=2.0, hold=6) -> pd.DataFrame:
    """Beta-hedge each asset to the equal-weight market, then fade the residual."""
    mkt = p.ret.mean(axis=1)
    cov = p.ret.rolling(beta_win, min_periods=beta_win//3).cov(mkt)
    var = mkt.rolling(beta_win, min_periods=beta_win//3).var()
    beta = cov.div(var, axis=0)
    resid = p.ret.sub(beta.mul(mkt, axis=0))
    cum = resid.rolling(z_win, min_periods=z_win//3).sum()
    zz = _zscore(cum, z_win * 2)
    e = pd.DataFrame(0.0, index=zz.index, columns=zz.columns)
    e[zz >= z] = -1.0; e[zz <= -z] = 1.0
    return _fwd_hold(e, hold)


def E04_btc_leadlag(p: Panel, lag=1, frac=0.2, hold=2) -> pd.DataFrame:
    """If BTC moved last bar, alts should follow this bar."""
    if "BTCUSDT" not in p.close.columns:
        return pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    b = p.close["BTCUSDT"].pct_change().shift(lag)
    W = pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    for c in p.close.columns:
        if c == "BTCUSDT":
            continue
        W[c] = np.sign(b)
    W = W.where(p.close.notna(), 0.0)
    return _fwd_hold(normalize_weights(W), hold)


def E09_alt_btc_ratio_revert(p: Panel, win=24*14, z=2.0, hold=24) -> pd.DataFrame:
    if "BTCUSDT" not in p.close.columns:
        return pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    ratio = p.close.div(p.close["BTCUSDT"], axis=0)
    zz = _zscore(np.log(ratio.replace(0, np.nan)), win)
    e = pd.DataFrame(0.0, index=zz.index, columns=zz.columns)
    e[zz >= z] = -1.0; e[zz <= -z] = 1.0
    e["BTCUSDT"] = 0.0
    return _fwd_hold(e, hold)


# ---------------------------------------------------------------------------
# FAMILY H — event-driven (derivable from the archive)
# ---------------------------------------------------------------------------

def H02_new_listing_drift(p: Panel, days=14, direction=1, hold=24) -> pd.DataFrame:
    """First `days` of a symbol's life: leverage arrives on a previously spot-only asset."""
    first = p.close.notna().idxmax()
    e = pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    for c in p.close.columns:
        f0 = first[c]
        if pd.isna(f0):
            continue
        m = (p.index >= f0) & (p.index < f0 + pd.Timedelta(days=days))
        if p.close[c].notna().iloc[0]:      # already listed at sample start -> not an event
            continue
        e.loc[m, c] = float(direction)
    return _fwd_hold(e, hold)


def H04_delisting_runup(p: Panel, days=14, direction=-1, hold=24) -> pd.DataFrame:
    """Final `days` before a symbol vanishes: everyone must close, price-insensitively."""
    e = pd.DataFrame(0.0, index=p.index, columns=p.close.columns)
    last_valid = p.close.apply(lambda s: s.last_valid_index())
    end = p.index.max()
    for c in p.close.columns:
        lv = last_valid[c]
        if pd.isna(lv) or lv >= end - pd.Timedelta(days=2):
            continue                        # still alive -> not a delisting event
        m = (p.index >= lv - pd.Timedelta(days=days)) & (p.index <= lv)
        e.loc[m, c] = float(direction)
    return _fwd_hold(e, hold)

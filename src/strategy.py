"""Signal logic. Pure functions, no side effects (Section 10 requirement).

=============================================================================
IMPORTANT -- READ BEFORE INTERPRETING ANY RESULT
The Section-1 STRATEGY SPEC in the task prompt was left as unfilled template
placeholders (`[e.g. ...]` for hypothesis/universe/timeframe, and pure
descriptions -- not rules -- for entry/exit logic). No actual strategy was
specified. Rather than block overnight, this module implements the prompt's
OWN worked example hypothesis, verbatim:

  "Forced liquidation sellers are price-insensitive, so violent moves
   accompanied by OI collapse overshoot fair value and revert within N hours."

The signal layer is deliberately isolated behind `build_signal()` so a real
spec can be swapped in by editing one function.
=============================================================================

OPEN-INTEREST LEG IS NOT TESTABLE ON FREE DATA.
The hypothesis names OI collapse as the confirming condition. Measured limits:
OKX rubik OI history returns 29 days at 1H granularity and 179 days at 1D.
Against a 3-year 1h study that is unusable, and no other reachable venue
(Binance futures 451, Bybit 403) exposes deep OI. We therefore test the
PRICE+VOLUME half of the hypothesis only, using a volume spike as the
forced-flow proxy, and we say so in the report rather than quietly
substituting a proxy and calling it the hypothesis. This weakens the test:
volume spikes occur for many reasons other than forced liquidation, so the
signal is a noisier version of the intended one.

Entry (all computable at bar t close, from trailing data only):
  cascade_down = ret_k <= -z * trailing_sigma_k  AND  volume >= vmult * trailing_median_volume
  cascade_up   = ret_k >= +z * trailing_sigma_k  AND  volume >= vmult * trailing_median_volume
  signal = +1 on cascade_down (fade the drop), -1 on cascade_up (fade the pop)

Exit (precedence, enforced in backtest.py):
  1. stop  = entry -/+ atr_multiple_stop * ATR14      (gap-through fills at the open)
  2. target= entry +/- target_take_profit_atr * ATR14
  3. time stop at max_holding_bars
  If stop and target are both touched inside one bar, the STOP is assumed to
  fill first (worse outcome).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SignalParams:
    lookback_bars: int = 3       # k: horizon of the "violent move"
    z_threshold: float = 3.0     # how many trailing sigmas
    vol_multiple: float = 2.0    # volume spike vs trailing median
    vol_window: int = 24 * 14    # trailing window for sigma / median volume (14 days)
    both_directions: bool = True

    def tag(self) -> str:
        return (f"k{self.lookback_bars}_z{self.z_threshold}_v{self.vol_multiple}"
                f"_w{self.vol_window}_{'both' if self.both_directions else 'longonly'}")


def build_signal(df: pd.DataFrame, p: SignalParams) -> pd.Series:
    """Return a signal series aligned to df: +1 long, -1 short, 0 flat.

    PURITY / NO-LOOKAHEAD CONTRACT:
      * every statistic is a TRAILING rolling window, closed on the left
        (`.shift(1)` applied to all normalising statistics so bar t's own
        value never enters its own threshold);
      * the value at index i depends only on rows <= i;
      * therefore truncating df after row i cannot change signal[i], which is
        exactly what `assert_no_lookahead` verifies.
    """
    d = df.reset_index(drop=True)
    close = d["close"].astype(float)
    vol = d["volume"].astype(float)

    ret_k = close.pct_change(p.lookback_bars)

    # trailing sigma of the k-bar return, shifted so the current bar is excluded
    sigma_k = ret_k.rolling(p.vol_window, min_periods=p.vol_window // 4).std().shift(1)
    med_vol = vol.rolling(p.vol_window, min_periods=p.vol_window // 4).median().shift(1)

    vol_spike = vol >= (p.vol_multiple * med_vol)
    cascade_down = (ret_k <= -p.z_threshold * sigma_k) & vol_spike
    cascade_up = (ret_k >= p.z_threshold * sigma_k) & vol_spike

    sig = pd.Series(0.0, index=d.index)
    sig[cascade_down] = 1.0
    if p.both_directions:
        sig[cascade_up] = -1.0
    sig[~np.isfinite(sigma_k) | sigma_k.isna() | med_vol.isna()] = 0.0
    sig.index = df.index
    sig.attrs["rebuild"] = lambda truncated, _p=p: build_signal(truncated, _p)
    sig.attrs["params"] = p.tag()
    return sig


def build_signals_for_panel(panel: dict, p: SignalParams) -> dict:
    return {a: build_signal(df, p) for a, df in panel.items()}


# ---------------------------------------------------------------------------
# Benchmarks (Section 7) -- kept here because they are signal-shaped
# ---------------------------------------------------------------------------

def random_signal(df: pd.DataFrame, n_signals: int, seed: int, both: bool = True) -> pd.Series:
    """Random entries matched to a target count. Same downstream holding/sizing/costs."""
    rng = np.random.default_rng(seed)
    sig = pd.Series(0.0, index=df.index)
    if n_signals <= 0 or len(df) == 0:
        return sig
    warm = min(len(df) - 1, 24 * 14)
    pool = np.arange(warm, len(df))
    if len(pool) == 0:
        return sig
    picks = rng.choice(pool, size=min(n_signals, len(pool)), replace=False)
    vals = rng.choice([1.0, -1.0], size=len(picks)) if both else np.ones(len(picks))
    sig.iloc[picks] = vals
    return sig


def shifted_signal(sig: pd.Series, shift_bars: int) -> pd.Series:
    """Entry-timing placebo: same signal, entries displaced by +/-N bars.
    Similar performance => regime/beta effect, not a timing edge."""
    out = sig.shift(shift_bars).fillna(0.0)
    out.attrs["params"] = f"shift{shift_bars}"
    return out

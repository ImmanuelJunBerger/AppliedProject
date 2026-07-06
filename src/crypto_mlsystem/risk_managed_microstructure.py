"""Risk-managed crypto momentum with Binance Futures microstructure inventory.

The module separates two questions:

1. Can risk-managed cross-sectional momentum pass the existing locked-holdout
   paper-trading criteria using only the established OHLCV panel?
2. Is Binance Futures public microstructure data sufficiently historical and
   complete to test microstructure-confirmed overlays without contaminating the
   locked holdout?

If microstructure data is only snapshot/recent or unavailable, the module writes
a prospective collection plan instead of running an invalid final backtest.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .metrics import performance_metrics
from .volatility_breakout import deflated_sharpe_probability, probability_backtest_overfitting
from .volatility_expansion import point_in_time_liquid_universe


BINANCE_FUTURES_BASE = "https://fapi.binance.com"
DEVELOPMENT_START = pd.Timestamp("2020-01-01")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")


@dataclass(frozen=True)
class RiskManagedMomentumCandidate:
    name: str
    universe_size: int
    rebalance_days: int
    momentum_days: int
    top_k: int
    volatility_lookback: int
    target_volatility: float
    max_asset_weight: float = 0.50
    turnover_cap: float = 0.75


@dataclass
class RiskManagedMomentumDataset:
    panel: pd.DataFrame
    close: pd.DataFrame
    returns: pd.DataFrame
    universe_weights: dict[int, pd.DataFrame]
    metadata: dict[str, Any]


@dataclass
class PortfolioResult:
    returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    metrics: dict[str, float]


def _request_json(url: str, timeout: int = 20) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "crypto-ml-research/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _pivot(panel: pd.DataFrame, column: str) -> pd.DataFrame:
    return panel.pivot(index="date", columns="symbol", values=column).sort_index()


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def build_risk_managed_momentum_dataset(panel: pd.DataFrame) -> RiskManagedMomentumDataset:
    clean = panel.copy().sort_values(["date", "symbol"])
    clean["date"] = pd.to_datetime(clean.date)
    close = _pivot(clean, "close")
    returns = close.pct_change(fill_method=None).fillna(0.0)
    universe_weights = {
        size: point_in_time_liquid_universe(clean, top_n=size, min_history_days=180, max_asset_weight=0.20)[0]
        for size in (10, 20, 30)
    }
    return RiskManagedMomentumDataset(
        panel=clean,
        close=close,
        returns=returns,
        universe_weights=universe_weights,
        metadata={
            "start": str(close.index.min().date()),
            "end": str(close.index.max().date()),
            "development_end": str(DEVELOPMENT_END.date()),
            "holdout_start": str(HOLDOUT_START.date()),
            "holdout_end": str(HOLDOUT_END.date()),
        },
    )


def risk_managed_momentum_candidates() -> list[RiskManagedMomentumCandidate]:
    candidates: list[RiskManagedMomentumCandidate] = []
    for universe, rebalance, momentum, top_k, vol_lookback, target_vol in product(
        (10, 20, 30),
        (7, 14),
        (21, 63, 126),
        (3, 5, 10),
        (30, 60),
        (0.25, 0.35),
    ):
        if top_k > universe:
            continue
        candidates.append(RiskManagedMomentumCandidate(
            name=f"rm_mom_u{universe}_r{rebalance}_m{momentum}_k{top_k}_vol{vol_lookback}_tv{int(target_vol*100)}",
            universe_size=universe,
            rebalance_days=rebalance,
            momentum_days=momentum,
            top_k=top_k,
            volatility_lookback=vol_lookback,
            target_volatility=target_vol,
        ))
    return candidates


def _momentum_scores(dataset: RiskManagedMomentumDataset, momentum_days: int) -> pd.DataFrame:
    return dataset.close.pct_change(momentum_days, fill_method=None).shift(1)


def _basket_volatility(returns: pd.DataFrame, date_: pd.Timestamp, assets: list[str], weights: pd.Series, lookback: int) -> float:
    position = returns.index.get_loc(date_)
    if isinstance(position, slice):
        return np.nan
    start = max(0, int(position) - lookback)
    sample = returns.iloc[start:int(position)][assets].dropna(how="all")
    if len(sample) < max(10, lookback // 3):
        return np.nan
    basket = sample.fillna(0.0).dot(weights.reindex(assets).fillna(0.0))
    vol = basket.std(ddof=1) * np.sqrt(365)
    return float(vol) if np.isfinite(vol) else np.nan


def build_risk_managed_weights(
    dataset: RiskManagedMomentumDataset,
    candidate: RiskManagedMomentumCandidate,
    score_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    scores = score_frame if score_frame is not None else _momentum_scores(dataset, candidate.momentum_days)
    dates = _rebalance_dates(dataset.close.index, candidate.rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    universe = dataset.universe_weights[candidate.universe_size]
    for date_ in dates:
        eligible = universe.columns[universe.loc[date_] > 0]
        ranked = scores.loc[date_, eligible].dropna().sort_values(ascending=False)
        chosen = ranked.head(candidate.top_k).index.tolist()
        if not chosen:
            continue
        raw_weight = min(candidate.max_asset_weight, 1.0 / len(chosen))
        raw = pd.Series(raw_weight, index=chosen, dtype=float)
        gross = float(raw.sum())
        if gross > 1.0:
            raw = raw / gross
        basket_vol = _basket_volatility(dataset.returns, date_, chosen, raw, candidate.volatility_lookback)
        if not np.isfinite(basket_vol) or basket_vol <= 0:
            continue
        exposure = min(1.0, candidate.target_volatility / basket_vol)
        weights.loc[date_, chosen] = raw * exposure
    return weights


def backtest_weights(
    dataset: RiskManagedMomentumDataset,
    target_weights: pd.DataFrame,
    cost_bps: int,
    turnover_cap: float = 0.75,
) -> PortfolioResult:
    returns = dataset.returns.reindex(columns=target_weights.columns).fillna(0.0)
    start = target_weights.index.min()
    returns = returns.loc[start:min(HOLDOUT_END, returns.index.max())]
    targets = target_weights.reindex(target_weights.index.intersection(returns.index)).fillna(0.0)
    index = returns.index
    columns = returns.columns
    returns_array = returns.to_numpy(dtype=float)
    target_map = {
        date_: row.to_numpy(dtype=float)
        for date_, row in targets.reindex(columns=columns).iterrows()
    }
    executed_array = np.zeros((len(index), len(columns)), dtype=float)
    gross_array = np.zeros(len(index), dtype=float)
    net_array = np.zeros(len(index), dtype=float)
    turnover_array = np.zeros(len(index), dtype=float)
    costs_array = np.zeros(len(index), dtype=float)
    previous = np.zeros(len(columns), dtype=float)
    cost_rate = cost_bps / 10000.0
    for i, date_ in enumerate(index):
        gross_array[i] = float(np.dot(previous, returns_array[i]))
        target = previous
        requested = target_map.get(date_)
        if requested is not None:
            change = requested - previous
            requested_turnover = float(np.abs(change).sum())
            if requested_turnover > turnover_cap and requested_turnover > 0:
                target = previous + change * turnover_cap / requested_turnover
            else:
                target = requested
            turnover_array[i] = float(np.abs(target - previous).sum())
            costs_array[i] = turnover_array[i] * cost_rate
        net_array[i] = gross_array[i] - costs_array[i]
        executed_array[i] = target
        previous = target
    net = pd.Series(net_array, index=index)
    gross = pd.Series(gross_array, index=index)
    turnover = pd.Series(turnover_array, index=index)
    costs = pd.Series(costs_array, index=index)
    weights = pd.DataFrame(executed_array, index=index, columns=columns)
    return PortfolioResult(net, gross, weights, turnover, costs, portfolio_metrics(net, turnover, costs, weights))


def portfolio_metrics(returns: pd.Series, turnover: pd.Series, costs: pd.Series, weights: pd.DataFrame) -> dict[str, float]:
    metrics = performance_metrics(returns, turnover, costs)
    elapsed_years = max(len(returns) / 365.0, 1 / 365.0)
    exposure = weights.sum(axis=1).clip(0, 1)
    monthly = returns.resample("ME").apply(lambda values: (1 + values).prod() - 1)
    metrics.update({
        "Exposure": float(exposure.mean()),
        "Cash Allocation": float(1.0 - exposure.mean()),
        "Annual Turnover": float(turnover.sum() / elapsed_years),
        "Worst Month": float(monthly.min()) if len(monthly) else np.nan,
        "Average Holdings": float((weights > 1e-6).sum(axis=1).mean()),
    })
    return metrics


def period_metrics(result: PortfolioResult, start: str | pd.Timestamp, end: str | pd.Timestamp) -> dict[str, float]:
    returns = result.returns.loc[pd.Timestamp(start):pd.Timestamp(end)]
    return portfolio_metrics(
        returns,
        result.turnover.reindex(returns.index).fillna(0.0),
        result.costs.reindex(returns.index).fillna(0.0),
        result.weights.reindex(returns.index).fillna(0.0),
    )


def _weekly_returns(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1 + values).prod() - 1).dropna()


def _period_sharpe(weekly: pd.Series, indices: tuple[int, ...]) -> float:
    subset = weekly.iloc[list(indices)]
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else -np.inf


def select_candidate_cpcv(
    candidates: list[RiskManagedMomentumCandidate],
    results: dict[str, PortfolioResult],
) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows = []
    fold_rows = []
    config_returns = {}
    for candidate in candidates:
        result = results[candidate.name]
        weekly = _weekly_returns(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        config_returns[candidate.name] = weekly
        if len(weekly) < 30:
            continue
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_sharpes = []
        for number, split in enumerate(splits):
            sharpe = _period_sharpe(weekly, split.test_indices)
            fold_sharpes.append(sharpe)
            fold_rows.append({"candidate": candidate.name, "fold": number, "fold_sharpe": sharpe})
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        rows.append({
            "candidate": candidate.name,
            "universe_size": candidate.universe_size,
            "rebalance_days": candidate.rebalance_days,
            "momentum_days": candidate.momentum_days,
            "top_k": candidate.top_k,
            "volatility_lookback": candidate.volatility_lookback,
            "target_volatility": candidate.target_volatility,
            "median_fold_sharpe": float(np.nanmedian(fold_sharpes)),
            "worst_fold_sharpe": float(np.nanmin(fold_sharpes)),
            "positive_fold_fraction": float(np.mean(np.asarray(fold_sharpes) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
        })
    selection = pd.DataFrame(rows).sort_values(
        ["median_fold_sharpe", "worst_fold_sharpe", "development_sharpe", "development_turnover"],
        ascending=[False, False, False, True],
    )
    winner = str(selection.iloc[0].candidate)
    aligned = pd.concat(config_returns, axis=1).sort_index()
    pbo = probability_backtest_overfitting(aligned, blocks=8)
    return selection, pd.DataFrame(fold_rows), winner, pbo


def _benchmark_weights(dataset: RiskManagedMomentumDataset, name: str) -> pd.DataFrame:
    dates = dataset.close.index
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    if name == "btc_buy_hold":
        if "BTC" in weights:
            weights["BTC"] = 1.0
    elif name == "eth_buy_hold":
        if "ETH" in weights:
            weights["ETH"] = 1.0
    elif name == "btc_eth_50_50":
        for symbol in ("BTC", "ETH"):
            if symbol in weights:
                weights[symbol] = 0.50
    elif name == "equal_weight_top10":
        active = dataset.universe_weights[10] > 0
        denominator = active.sum(axis=1).replace(0, np.nan)
        weights = active.div(denominator, axis=0).fillna(0.0).clip(upper=0.20)
    elif name == "equal_weight_top30":
        active = dataset.universe_weights[30] > 0
        denominator = active.sum(axis=1).replace(0, np.nan)
        weights = active.div(denominator, axis=0).fillna(0.0).clip(upper=0.20)
    else:
        raise ValueError(name)
    return weights


def aggregate_agg_trades_to_microstructure_features(trades: pd.DataFrame, frequency: str = "1h") -> pd.DataFrame:
    """Aggregate Binance Futures aggTrades to scale-invariant flow features.

    Binance uses `m=True` when the buyer is the maker, so the taker is selling.
    """
    if trades.empty:
        return pd.DataFrame()
    frame = trades.copy()
    if "timestamp" not in frame and "T" in frame:
        frame["timestamp"] = pd.to_datetime(frame["T"], unit="ms", utc=True).dt.tz_localize(None)
    if "price" not in frame and "p" in frame:
        frame["price"] = frame["p"].astype(float)
    if "quantity" not in frame and "q" in frame:
        frame["quantity"] = frame["q"].astype(float)
    if "is_buyer_maker" not in frame and "m" in frame:
        frame["is_buyer_maker"] = frame["m"].astype(bool)
    frame = frame.dropna(subset=["timestamp", "price", "quantity"]).sort_values("timestamp")
    if frame.empty:
        return pd.DataFrame()
    frame["taker_buy_volume"] = np.where(frame.is_buyer_maker, 0.0, frame.quantity)
    frame["taker_sell_volume"] = np.where(frame.is_buyer_maker, frame.quantity, 0.0)
    frame["buy_notional"] = frame.taker_buy_volume * frame.price
    frame["sell_notional"] = frame.taker_sell_volume * frame.price
    frame = frame.set_index("timestamp")

    def summarize(group: pd.DataFrame) -> pd.Series:
        total_volume = group.quantity.sum()
        buy_volume = group.taker_buy_volume.sum()
        sell_volume = group.taker_sell_volume.sum()
        buy_count = int((group.taker_buy_volume > 0).sum())
        sell_count = int((group.taker_sell_volume > 0).sum())
        buy_vwap = group.buy_notional.sum() / buy_volume if buy_volume > 0 else np.nan
        sell_vwap = group.sell_notional.sum() / sell_volume if sell_volume > 0 else np.nan
        mid_proxy = group.price.mean()
        returns = group.price.pct_change(fill_method=None).dropna()
        return pd.Series({
            "trade_count": int(len(group)),
            "total_volume": float(total_volume),
            "taker_buy_sell_imbalance": float((buy_volume - sell_volume) / total_volume) if total_volume > 0 else np.nan,
            "trade_count_imbalance": float((buy_count - sell_count) / max(buy_count + sell_count, 1)),
            "buy_vwap_to_mid": float(buy_vwap / mid_proxy - 1.0) if np.isfinite(buy_vwap) and mid_proxy else np.nan,
            "sell_vwap_to_mid": float(sell_vwap / mid_proxy - 1.0) if np.isfinite(sell_vwap) and mid_proxy else np.nan,
            "net_order_flow": float(buy_volume - sell_volume),
            "short_horizon_volatility": float(returns.std(ddof=1)) if len(returns) > 1 else 0.0,
            "volume_concentration": float(group.quantity.max() / total_volume) if total_volume > 0 else np.nan,
        })

    return frame.resample(frequency).apply(summarize).dropna(how="all").reset_index()


def _coverage_row(
    endpoint: str,
    url: str,
    status: str,
    observations: int,
    historical_depth: str,
    usable_for_holdout_backtest: bool,
    limitation: str,
    sample: Any = None,
) -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "url": url,
        "status": status,
        "observations": int(observations),
        "historical_depth": historical_depth,
        "usable_for_holdout_backtest": bool(usable_for_holdout_backtest),
        "limitation": limitation,
        "sample": "" if sample is None else json.dumps(sample)[:500],
    }


def probe_binance_futures_microstructure(symbol: str = "BTCUSDT") -> pd.DataFrame:
    old_start = int(pd.Timestamp("2025-01-02T00:00:00Z").timestamp() * 1000)
    old_end = int(pd.Timestamp("2025-01-02T01:00:00Z").timestamp() * 1000)
    endpoints = [
        (
            "depth_snapshot",
            f"{BINANCE_FUTURES_BASE}/fapi/v1/depth?{urllib.parse.urlencode({'symbol': symbol, 'limit': 20})}",
            "current_snapshot",
            False,
            "Current order-book snapshot only; not historical through REST.",
        ),
        (
            "book_ticker",
            f"{BINANCE_FUTURES_BASE}/fapi/v1/ticker/bookTicker?{urllib.parse.urlencode({'symbol': symbol})}",
            "current_snapshot",
            False,
            "Current top-of-book only; not historical through REST.",
        ),
        (
            "recent_agg_trades",
            f"{BINANCE_FUTURES_BASE}/fapi/v1/aggTrades?{urllib.parse.urlencode({'symbol': symbol, 'limit': 20})}",
            "recent_or_query_limited",
            False,
            "Useful for prospective collection; full historical backtest requires archived/backfilled data.",
        ),
        (
            "historical_agg_trades_2025_sample",
            f"{BINANCE_FUTURES_BASE}/fapi/v1/aggTrades?{urllib.parse.urlencode({'symbol': symbol, 'startTime': old_start, 'endTime': old_end, 'limit': 20})}",
            "one_hour_query_sample",
            False,
            "Even if sample is available, full 2025+ holdout across assets requires large systematic backfill.",
        ),
        (
            "historical_1m_klines_2025_sample",
            f"{BINANCE_FUTURES_BASE}/fapi/v1/klines?{urllib.parse.urlencode({'symbol': symbol, 'interval': '1m', 'startTime': old_start, 'endTime': old_end, 'limit': 20})}",
            "one_hour_query_sample",
            False,
            "1m klines provide high-frequency OHLCV, not book/trade-flow microstructure.",
        ),
        (
            "taker_long_short_ratio",
            f"{BINANCE_FUTURES_BASE}/futures/data/takerlongshortRatio?{urllib.parse.urlencode({'symbol': symbol, 'period': '1h', 'limit': 20})}",
            "recent_public_ratio",
            False,
            "Ratio endpoint is useful context but not sufficient order-book/trade-flow history.",
        ),
    ]
    rows = []
    for endpoint, url, depth, usable, limitation in endpoints:
        try:
            payload = _request_json(url)
            time.sleep(0.10)
            if isinstance(payload, dict) and "code" in payload and int(payload.get("code", 0)) < 0:
                rows.append(_coverage_row(endpoint, url, "api_error", 0, depth, False, payload.get("msg", limitation), payload))
                continue
            observations = len(payload) if isinstance(payload, list) else 1
            status = "empty_response" if observations == 0 else "available"
            rows.append(_coverage_row(endpoint, url, status, observations, depth, usable, limitation, payload[0] if isinstance(payload, list) and payload else payload))
        except Exception as exc:  # pragma: no cover - network and geography dependent
            rows.append(_coverage_row(endpoint, url, "connection_failed", 0, depth, False, f"{type(exc).__name__}: {exc}", None))
    return pd.DataFrame(rows)


def microstructure_feature_inventory() -> pd.DataFrame:
    rows = [
        ("spread_over_mid", "best_ask - best_bid divided by mid", "depth/bookTicker", "current only unless collected", "Not valid for locked holdout without historical snapshots."),
        ("l1_imbalance", "bid_qty - ask_qty divided by bid_qty + ask_qty", "depth/bookTicker", "current only unless collected", "Needs synchronized book snapshots."),
        ("depth_imbalance", "sum bid depth - sum ask depth over top levels divided by total depth", "depth", "current only unless collected", "Sensitive to chosen depth levels and snapshot timing."),
        ("taker_buy_sell_imbalance", "taker buy volume - taker sell volume divided by total volume", "aggTrades", "query/prospective", "Historically backfillable only with systematic archived trade data."),
        ("trade_count_imbalance", "buy trade count - sell trade count divided by total trade count", "aggTrades", "query/prospective", "Requires reliable buyer-maker flag handling."),
        ("volume_imbalance", "buy volume - sell volume divided by total volume", "aggTrades", "query/prospective", "Same as taker imbalance when using taker-classified aggTrades."),
        ("buy_vwap_to_mid", "taker-buy VWAP divided by mid minus one", "aggTrades + book mid", "prospective", "Needs synchronized midquote."),
        ("sell_vwap_to_mid", "taker-sell VWAP divided by mid minus one", "aggTrades + book mid", "prospective", "Needs synchronized midquote."),
        ("net_order_flow", "taker buy volume minus taker sell volume", "aggTrades", "query/prospective", "Must be normalized by volume or volatility for cross-asset use."),
        ("short_horizon_volatility", "1m/5m/15m/1h realized volatility", "klines/aggTrades", "query/prospective", "Can be built from 1m futures klines but is not book flow."),
        ("volume_concentration", "largest trade or bar volume divided by total interval volume", "aggTrades/klines", "query/prospective", "Trade-level version requires aggTrades."),
        ("aggregated_1m_5m_15m_1h_features", "resample raw trades/book data into deployable bars", "bookTicker/depth/aggTrades/klines", "prospective", "Requires raw data retention before aggregation; cannot reconstruct historical book snapshots later."),
    ]
    return pd.DataFrame(rows, columns=["feature", "formula", "source", "availability", "limitation"])


def run_risk_managed_microstructure_study(
    panel: pd.DataFrame,
    probe_microstructure: bool = True,
) -> dict[str, Any]:
    dataset = build_risk_managed_momentum_dataset(panel)
    candidates = risk_managed_momentum_candidates()
    results_25: dict[str, PortfolioResult] = {}
    weights_cache: dict[str, pd.DataFrame] = {}
    score_cache: dict[int, pd.DataFrame] = {}
    for candidate in candidates:
        if candidate.momentum_days not in score_cache:
            score_cache[candidate.momentum_days] = _momentum_scores(dataset, candidate.momentum_days)
        weights = build_risk_managed_weights(dataset, candidate, score_cache[candidate.momentum_days])
        weights_cache[candidate.name] = weights
        results_25[candidate.name] = backtest_weights(dataset, weights, 25, candidate.turnover_cap)
    selection, folds, winner_name, pbo = select_candidate_cpcv(candidates, results_25)
    by_name = {candidate.name: candidate for candidate in candidates}
    winner = by_name[winner_name]
    metrics_rows = []
    result_by_cost: dict[int, PortfolioResult] = {}
    for cost in COST_LEVELS:
        result = results_25[winner.name] if cost == 25 else backtest_weights(
            dataset, weights_cache[winner.name], cost, winner.turnover_cap
        )
        result_by_cost[cost] = result
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            metrics_rows.append({"name": winner.name, "category": "risk_managed_momentum", "split": split, "cost_bps": cost, **period_metrics(result, start, end)})
    for name in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top10", "equal_weight_top30"):
        result = backtest_weights(dataset, _benchmark_weights(dataset, name), 0)
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            metrics_rows.append({"name": name, "category": "benchmark", "split": split, "cost_bps": 0, **period_metrics(result, start, end)})
    metrics = pd.DataFrame(metrics_rows)
    coverage = probe_binance_futures_microstructure() if probe_microstructure else pd.DataFrame()
    inventory = microstructure_feature_inventory()
    microstructure_backtest_status = "not_run"
    microstructure_reason = (
        "No complete local historical Binance Futures order-book/trade-flow feature panel covering the locked holdout. "
        "The module therefore does not run microstructure-confirmed overlays B/C/D as final backtests."
    )
    holdout_25 = metrics[(metrics.name == winner.name) & (metrics.split == "holdout") & (metrics.cost_bps == 25)].iloc[0]
    holdout_50 = metrics[(metrics.name == winner.name) & (metrics.split == "holdout") & (metrics.cost_bps == 50)].iloc[0]
    btc_holdout = metrics[(metrics.name == "btc_buy_hold") & (metrics.split == "holdout")].iloc[0]
    failures = []
    if holdout_25.Sharpe <= 0.5:
        failures.append("holdout Sharpe <= 0.5")
    if holdout_25.CAGR <= 0:
        failures.append("holdout CAGR <= 0")
    if holdout_25["Maximum Drawdown"] <= btc_holdout["Maximum Drawdown"]:
        failures.append("max drawdown not better than BTC")
    if holdout_50.Sharpe <= 0 or holdout_50.CAGR <= 0:
        failures.append("does not survive 50 bps")
    if holdout_25["Annual Turnover"] > 12:
        failures.append("annual turnover > 12x")
    selected = result_by_cost[25]
    dsr = deflated_sharpe_probability(selected.returns.loc[HOLDOUT_START:HOLDOUT_END], len(candidates))
    return {
        "dataset": dataset,
        "candidates": candidates,
        "selection": selection,
        "folds": folds,
        "winner": winner,
        "metrics": metrics,
        "microstructure_coverage": coverage,
        "feature_inventory": inventory,
        "microstructure_backtest_status": microstructure_backtest_status,
        "microstructure_reason": microstructure_reason,
        "acceptance": {
            "passes": not failures,
            "failures": "; ".join(failures),
            "holdout_sharpe": float(holdout_25.Sharpe),
            "holdout_cagr": float(holdout_25.CAGR),
            "holdout_max_drawdown": float(holdout_25["Maximum Drawdown"]),
            "holdout_turnover": float(holdout_25["Annual Turnover"]),
        },
        "statistics": {
            "tested_configurations": len(candidates),
            "pbo": pbo,
            "deflated_sharpe_probability": dsr,
        },
    }


def _fmt(value: Any, percent: bool = False) -> str:
    if value is None or (isinstance(value, (float, np.floating)) and not np.isfinite(value)):
        return "N/A"
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if value else "No"
    if isinstance(value, (float, np.floating)):
        return f"{value:.2%}" if percent else f"{value:.3f}"
    return str(value)


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]], percent: set[str] | None = None, limit: int | None = None) -> str:
    percent = percent or set()
    view = frame.head(limit) if limit else frame
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in view.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def write_risk_managed_microstructure_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    winner: RiskManagedMomentumCandidate = result["winner"]
    metrics: pd.DataFrame = result["metrics"]
    selection: pd.DataFrame = result["selection"]
    coverage: pd.DataFrame = result["microstructure_coverage"]
    inventory: pd.DataFrame = result["feature_inventory"]
    acceptance = result["acceptance"]
    statistics = result["statistics"]
    holdout = metrics[(metrics.split == "holdout") & ((metrics.cost_bps == 25) | (metrics.category == "benchmark"))].sort_values("Sharpe", ascending=False)
    development = metrics[(metrics.split == "development") & ((metrics.cost_bps == 25) | (metrics.category == "benchmark"))].sort_values("Sharpe", ascending=False)
    columns = [("name", "Strategy"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Sortino", "Sortino"), ("Maximum Drawdown", "Max DD"), ("Calmar", "Calmar"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure")]
    percent = {"CAGR", "Maximum Drawdown", "Exposure"}

    coverage_text = _table(
        coverage,
        [("endpoint", "Endpoint"), ("status", "Status"), ("observations", "Obs"), ("historical_depth", "Historical depth"), ("usable_for_holdout_backtest", "Usable holdout"), ("limitation", "Limitation")],
    ) if not coverage.empty else "Microstructure probe was not run."
    (output / "data_coverage.md").write_text(f"""# Binance Futures microstructure data coverage

The study probes public Binance Futures endpoints but does not assume full
one-second/order-book history is available.

{coverage_text}

## Coverage decision

{result['microstructure_reason']}

## Prospective collection path

For a valid future test, collect and store timestamped data prospectively:

- `bookTicker` or depth snapshots every 1-5 seconds for BTCUSDT/ETHUSDT and selected top futures symbols.
- `aggTrades` continuously for taker buy/sell imbalance and trade-count imbalance.
- 1m futures klines for deployable 1h/4h volatility and volume concentration features.
- Aggregate raw data to immutable 1h and 4h feature tables before strategy testing.
- Lock thresholds using only the collection development window; keep a future untouched paper holdout.
""", encoding="utf-8")

    (output / "feature_inventory.md").write_text(f"""# Microstructure feature inventory

{_table(inventory, [('feature', 'Feature'), ('formula', 'Formula'), ('source', 'Source'), ('availability', 'Availability'), ('limitation', 'Limitation')])}
""", encoding="utf-8")

    holdout_cost = metrics[(metrics.name == winner.name) & (metrics.split == "holdout")].sort_values("cost_bps")
    (output / "baseline_momentum_results.md").write_text(f"""# Risk-managed momentum baseline

## Protocol

- Development period: 2020-01-01 through 2024-12-31.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: CPCV on development returns only.
- No holdout threshold tuning or holdout cell selection.
- Tested baseline configurations: {statistics['tested_configurations']}.
- Selected candidate: **{winner.name}**.

```json
{json.dumps(asdict(winner), indent=2)}
```

## Development comparison at 25 bps

{_table(development, columns, percent)}

## Locked holdout comparison

{_table(holdout, columns, percent)}

## Cost sensitivity for selected baseline

{_table(holdout_cost, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Statistical controls

- PBO: {_fmt(statistics['pbo'], True)}.
- Deflated Sharpe probability: {_fmt(statistics['deflated_sharpe_probability'], True)}.
""", encoding="utf-8")

    (output / "microstructure_results.md").write_text(f"""# Microstructure strategy results

## Requested comparisons

| Variant | Status | Reason |
|---|---|---|
| A. Pure risk-managed momentum | Run | See `baseline_momentum_results.md`. |
| B. Risk-managed momentum with microstructure confirmation | Not run as final backtest | {result['microstructure_reason']} |
| C. Risk-managed momentum with microstructure risk-off filter | Not run as final backtest | {result['microstructure_reason']} |
| D. BTC/ETH-only microstructure-confirmed trend | Not run as final backtest | {result['microstructure_reason']} |

The correct next step for microstructure is prospective data collection or a
separate historical archive backfill. It would be invalid to tune or evaluate
microstructure overlays on the locked holdout without a complete point-in-time
feature panel.
""", encoding="utf-8")

    selected_holdout = holdout[holdout.name == winner.name]
    selected_sharpe = float(selected_holdout.iloc[0].Sharpe) if len(selected_holdout) else np.nan
    selected_cagr = float(selected_holdout.iloc[0].CAGR) if len(selected_holdout) else np.nan
    recommendation = "paper trading" if acceptance["passes"] else "prospective data collection"
    if not acceptance["passes"] and selected_cagr <= 0 and selected_sharpe <= 0:
        recommendation = "prospective data collection, not capital paper trading"
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Decision

Evidence supports **{recommendation}**.

## Baseline risk-managed momentum

- Selected holdout Sharpe: {selected_sharpe:.3f}
- Selected holdout CAGR: {selected_cagr:.2%}
- Acceptance pass: {_fmt(acceptance['passes'])}
- Failures: {acceptance['failures'] or 'None'}

## Microstructure evidence

Microstructure overlays were not run as final locked-holdout strategies because
complete historical Binance Futures order-book/trade-flow features were not
available locally. Current/recent public endpoints are useful for prospective
collection, but they do not by themselves create a valid 2025+ holdout feature
panel.

## Bottom line

Do not allocate capital based on this module yet. If continuing, collect
microstructure data prospectively and evaluate it only after a separately locked
future paper holdout exists.
""", encoding="utf-8")

    selection.to_csv(output / "candidate_selection.csv", index=False)
    result["folds"].to_csv(output / "cpcv_folds.csv", index=False)
    metrics.to_csv(output / "metrics.csv", index=False)
    coverage.to_csv(output / "microstructure_coverage.csv", index=False)
    inventory.to_csv(output / "feature_inventory.csv", index=False)
    payload = {
        "winner": asdict(winner),
        "acceptance": acceptance,
        "statistics": statistics,
        "microstructure_backtest_status": result["microstructure_backtest_status"],
        "microstructure_reason": result["microstructure_reason"],
        "metrics": metrics.to_dict("records"),
        "selection": selection.to_dict("records"),
        "microstructure_coverage": coverage.to_dict("records"),
    }
    (output / "results.json").write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value)
    return value


__all__ = [
    "RiskManagedMomentumCandidate",
    "RiskManagedMomentumDataset",
    "aggregate_agg_trades_to_microstructure_features",
    "build_risk_managed_momentum_dataset",
    "build_risk_managed_weights",
    "microstructure_feature_inventory",
    "probe_binance_futures_microstructure",
    "risk_managed_momentum_candidates",
    "run_risk_managed_microstructure_study",
    "write_risk_managed_microstructure_reports",
]

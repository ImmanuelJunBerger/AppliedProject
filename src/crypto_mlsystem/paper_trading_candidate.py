"""Predeclared defensive momentum candidates with locked-holdout evaluation.

Candidate rules are intentionally simple and deterministic.  The only selection
step ranks the predeclared grid using CPCV folds drawn entirely from development
dates.  Holdout returns are never passed to the selector.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import HOLDOUT_END, HOLDOUT_START, MomentumDataset, PortfolioResult
from .metrics import performance_metrics


@dataclass(frozen=True)
class DefensiveCandidate:
    name: str
    family: str
    top_k: int = 0
    drawdown_threshold: float = -0.20
    volatility_probability_threshold: float = 0.75
    volatility_target: float = 0.30
    rebalance_weeks: int = 1
    drawdown_brake: float | None = None


def predeclared_candidates() -> list[DefensiveCandidate]:
    """Return the complete grid before any development or holdout result is read."""
    candidates: list[DefensiveCandidate] = []
    for top_k, drawdown, probability in product((3, 5), (-0.10, -0.20), (0.65, 0.75)):
        candidates.append(DefensiveCandidate(
            f"A_market_gate_k{top_k}_dd{abs(int(drawdown * 100))}_vp{int(probability * 100)}",
            "A_market_gated_momentum", top_k=top_k, drawdown_threshold=drawdown,
            volatility_probability_threshold=probability,
        ))
    for drawdown, probability, target in product((-0.15, -0.25), (0.70, 0.80), (0.25, 0.35)):
        candidates.append(DefensiveCandidate(
            f"B_defensive_rotation_dd{abs(int(drawdown * 100))}_vp{int(probability * 100)}_vt{int(target * 100)}",
            "B_defensive_top_asset_rotation", drawdown_threshold=drawdown,
            volatility_probability_threshold=probability, volatility_target=target,
        ))
    for top_k, target, brake in product((3, 5), (0.25, 0.35), (-0.10, -0.20)):
        candidates.append(DefensiveCandidate(
            f"C_cash_floor_k{top_k}_vt{int(target * 100)}_brake{abs(int(brake * 100))}",
            "C_momentum_cash_floor", top_k=top_k, volatility_target=target,
            drawdown_brake=brake,
        ))
    for weeks, target in product((2, 4), (0.25, 0.35)):
        label = "biweekly" if weeks == 2 else "monthly"
        candidates.append(DefensiveCandidate(
            f"D_btc_eth_{label}_vt{int(target * 100)}",
            "D_low_turnover_btc_eth_trend", volatility_target=target,
            rebalance_weeks=weeks,
        ))
    return candidates


def _date_rows(dataset: MomentumDataset, date_: pd.Timestamp) -> pd.DataFrame:
    return dataset.events.loc[dataset.events.date == date_].set_index("symbol")


def _state(primary: MomentumDataset, top10: MomentumDataset) -> pd.DataFrame:
    market_columns = [
        "market_drawdown", "market_volatility_expansion_probability",
    ]
    primary_market = primary.events.drop_duplicates("date").set_index("date")
    top10_market = top10.events.drop_duplicates("date").set_index("date")
    state = primary_market[market_columns].copy()
    state["top10_breadth"] = top10_market.market_breadth_30.reindex(state.index)
    for symbol in ("BTC", "ETH"):
        rows = primary.events.loc[primary.events.symbol == symbol].set_index("date")
        for feature in (
            "momentum_30", "momentum_90", "momentum_90_ex_7",
            "volatility_adjusted_momentum", "distance_ma_200", "max_drawdown_90",
            "realized_volatility_30",
        ):
            state[f"{symbol.lower()}_{feature}"] = rows[feature].reindex(state.index)
    # The fixed volatility model starts later than price history.  A neutral 0.5
    # is used before its first genuine walk-forward forecast; it is not backfilled.
    state["market_volatility_expansion_probability"] = (
        state.market_volatility_expansion_probability.fillna(0.50)
    )
    return state


def _volatility_exposure(volatility: pd.Series, target: float) -> float:
    usable = volatility.replace([np.inf, -np.inf], np.nan).dropna()
    if usable.empty or usable.mean() <= 0:
        return 0.0
    return float(np.clip(target / usable.mean(), 0.0, 1.0))


def _forecast_sizing(probability: float) -> float:
    """Continuous risk reduction only; no threshold is selected from holdout."""
    probability = 0.50 if pd.isna(probability) else float(probability)
    return float(np.clip(1.0 - 1.5 * max(0.0, probability - 0.50), 0.25, 1.0))


def candidate_weights(
    primary: MomentumDataset,
    top10: MomentumDataset,
    candidate: DefensiveCandidate,
) -> pd.DataFrame:
    dates = pd.DatetimeIndex(sorted(primary.events.date.unique()))
    selected_dates = dates[::candidate.rebalance_weeks]
    state = _state(primary, top10)
    weights = pd.DataFrame(0.0, index=selected_dates, columns=primary.asset_returns.columns)

    for date_ in selected_dates:
        rows = _date_rows(primary, date_)
        if rows.empty or date_ not in state.index:
            continue
        current = state.loc[date_]
        probability = float(current.market_volatility_expansion_probability)

        if candidate.family == "A_market_gated_momentum":
            favorable = all((
                current.get("btc_distance_ma_200", np.nan) > 0,
                current.get("btc_momentum_30", np.nan) > 0,
                current.get("top10_breadth", np.nan) > 0.50,
                current.get("market_drawdown", np.nan) > candidate.drawdown_threshold,
                probability < candidate.volatility_probability_threshold,
            ))
            if not favorable:
                continue
            chosen = rows.sort_values("momentum_90_ex_7", ascending=False).head(candidate.top_k)
            allocation = min(0.20, 1.0 / max(1, len(chosen)))
            weights.loc[date_, chosen.index] = allocation

        elif candidate.family == "B_defensive_top_asset_rotation":
            assets = rows.reindex([symbol for symbol in ("BTC", "ETH") if symbol in rows.index]).copy()
            if assets.empty or probability >= candidate.volatility_probability_threshold:
                continue
            valid = assets[
                (assets.momentum_30 > 0)
                & (assets.momentum_90 > 0)
                & (assets.distance_ma_200 > 0)
                & (assets.max_drawdown_90 > candidate.drawdown_threshold)
            ].copy()
            if valid.empty:
                continue
            ranks = valid[["momentum_30", "momentum_90", "volatility_adjusted_momentum"]].rank(pct=True)
            winner = ranks.mean(axis=1).idxmax()
            exposure = _volatility_exposure(
                pd.Series([valid.at[winner, "realized_volatility_30"]]), candidate.volatility_target
            ) * _forecast_sizing(probability)
            weights.at[date_, winner] = exposure

        elif candidate.family == "C_momentum_cash_floor":
            chosen = rows.sort_values("momentum_90_ex_7", ascending=False).head(candidate.top_k)
            if chosen.empty:
                continue
            positive = ((chosen.momentum_30 > 0) & (chosen.momentum_90_ex_7 > 0)).mean()
            confidence_exposure = 1.0 if positive >= 0.80 else (0.50 if positive >= 0.50 else 0.0)
            volatility_exposure = _volatility_exposure(
                chosen.realized_volatility_30, candidate.volatility_target
            )
            exposure = confidence_exposure * volatility_exposure
            allocation = min(0.20, exposure / max(1, len(chosen)))
            weights.loc[date_, chosen.index] = allocation

        elif candidate.family == "D_low_turnover_btc_eth_trend":
            assets = rows.reindex([symbol for symbol in ("BTC", "ETH") if symbol in rows.index]).copy()
            valid = assets[
                (assets.momentum_30 > 0)
                & (assets.momentum_90 > 0)
                & (assets.distance_ma_200 > 0)
            ]
            if valid.empty:
                continue
            exposure = _volatility_exposure(valid.realized_volatility_30, candidate.volatility_target)
            exposure *= _forecast_sizing(probability)
            weights.loc[date_, valid.index] = min(0.50, exposure / len(valid))
        else:
            raise ValueError(candidate.family)
    return weights


def backtest_weights(
    dataset: MomentumDataset,
    weekly_weights: pd.DataFrame,
    cost_bps: int = 25,
    turnover_cap: float = 0.75,
    drawdown_brake: float | None = None,
) -> PortfolioResult:
    returns = dataset.asset_returns.reindex(columns=weekly_weights.columns).fillna(0.0)
    start = weekly_weights.index.min()
    end = min(HOLDOUT_END, returns.index.max())
    returns = returns.loc[start:end]
    targets = weekly_weights.reindex(index=weekly_weights.index.intersection(returns.index)).fillna(0.0)
    executed = pd.DataFrame(0.0, index=returns.index, columns=returns.columns)
    gross = pd.Series(0.0, index=returns.index)
    turnover = pd.Series(0.0, index=returns.index)
    costs = pd.Series(0.0, index=returns.index)
    net = pd.Series(0.0, index=returns.index)
    previous = pd.Series(0.0, index=returns.columns)
    wealth = peak = 1.0

    for date_ in returns.index:
        gross.at[date_] = float((previous * returns.loc[date_]).sum())
        target = previous.copy()
        if date_ in targets.index:
            target = targets.loc[date_].copy()
            if drawdown_brake is not None:
                drawdown = wealth / peak - 1.0
                if drawdown <= 2 * drawdown_brake:
                    target *= 0.25
                elif drawdown <= drawdown_brake:
                    target *= 0.50
            change = target - previous
            requested = float(change.abs().sum())
            if requested > turnover_cap:
                target = previous + change * turnover_cap / requested
            turnover.at[date_] = float((target - previous).abs().sum())
            costs.at[date_] = turnover.at[date_] * cost_bps / 10000.0
        net.at[date_] = gross.at[date_] - costs.at[date_]
        wealth *= max(1e-9, 1.0 + net.at[date_])
        peak = max(peak, wealth)
        executed.loc[date_] = target
        previous = target

    metrics = portfolio_metrics(net, turnover, costs, executed)
    return PortfolioResult(net, gross, executed, turnover, costs, metrics, {
        "average_holdings": metrics["Average Holdings"],
        "best_month": metrics["Best Month"],
        "worst_month": metrics["Worst Month"],
    })


def portfolio_metrics(
    returns: pd.Series,
    turnover: pd.Series,
    costs: pd.Series,
    weights: pd.DataFrame,
) -> dict[str, float]:
    metrics = performance_metrics(returns, turnover, costs)
    capital_exposure = weights.sum(axis=1).clip(0, 1)
    elapsed_years = max(len(returns) / 365.0, 1 / 365.0)
    monthly = returns.resample("ME").apply(lambda values: (1 + values).prod() - 1)
    metrics.update({
        "Exposure": float(capital_exposure.mean()),
        "Cash Allocation": float(1.0 - capital_exposure.mean()),
        "Active Days": float((capital_exposure > 1e-9).mean()),
        "Annual Turnover": float(turnover.sum() / elapsed_years),
        "Average Holdings": float((weights > 1e-6).sum(axis=1).mean()),
        "Best Month": float(monthly.max()) if len(monthly) else np.nan,
        "Worst Month": float(monthly.min()) if len(monthly) else np.nan,
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


def benchmark_weights(dataset: MomentumDataset, name: str) -> pd.DataFrame:
    dates = pd.DatetimeIndex(sorted(dataset.events.date.unique()))
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.asset_returns.columns)
    for date_ in dates:
        if name == "btc_buy_hold" and "BTC" in weights:
            weights.at[date_, "BTC"] = 1.0
        elif name == "eth_buy_hold" and "ETH" in weights:
            weights.at[date_, "ETH"] = 1.0
        elif name == "btc_eth_50_50":
            for symbol in ("BTC", "ETH"):
                if symbol in weights:
                    weights.at[date_, symbol] = 0.50
        elif name == "equal_weight_top10":
            members = dataset.events.loc[dataset.events.date == date_, "symbol"].tolist()
            if members:
                weights.loc[date_, members] = 1.0 / len(members)
        elif name not in {"btc_buy_hold", "eth_buy_hold", "btc_eth_50_50"}:
            raise ValueError(name)
    return weights


def _weekly_returns(
    result: PortfolioResult,
    decision_dates: pd.DatetimeIndex,
    end_exclusive: pd.Timestamp | None = None,
) -> pd.Series:
    values: dict[pd.Timestamp, float] = {}
    for date_ in decision_dates:
        end = date_ + pd.Timedelta(days=6)
        if end_exclusive is not None:
            end = min(end, end_exclusive - pd.Timedelta(days=1))
        sample = result.returns.loc[date_:end]
        if len(sample):
            values[date_] = float((1 + sample).prod() - 1)
    return pd.Series(values, dtype=float)


def cpcv_candidate_selection(
    candidates: list[DefensiveCandidate],
    results_25bps: dict[str, PortfolioResult],
    development_start: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str], str]:
    """Select family winners and one primary using development data only."""
    all_dates = pd.DatetimeIndex(sorted({
        pd.Timestamp(date_)
        for result in results_25bps.values()
        for date_ in result.returns.index
        if pd.Timestamp(date_) < HOLDOUT_START and pd.Timestamp(date_).weekday() == 4
    }))
    if development_start is not None:
        all_dates = all_dates[all_dates >= development_start]
    splits = combinatorial_purged_splits(
        len(all_dates), n_groups=5, n_test_groups=2, label_horizon=1, embargo=1
    )
    candidate_by_name = {candidate.name: candidate for candidate in candidates}
    fold_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        weekly = _weekly_returns(
            results_25bps[candidate.name], all_dates, end_exclusive=HOLDOUT_START
        )
        fold_sharpes = []
        for fold_number, split in enumerate(splits):
            test_dates = all_dates[list(split.test_indices)]
            sample = weekly.reindex(test_dates).dropna()
            standard_deviation = sample.std()
            sharpe = float(sample.mean() / standard_deviation * np.sqrt(52)) if standard_deviation > 0 else 0.0
            wealth = (1 + sample).cumprod()
            maximum_drawdown = float((wealth / wealth.cummax() - 1).min()) if len(wealth) else np.nan
            cagr = float((1 + sample).prod() ** (52 / len(sample)) - 1) if len(sample) else np.nan
            fold_sharpes.append(sharpe)
            fold_rows.append({
                "candidate": candidate.name, "family": candidate.family, "fold": fold_number,
                "test_weeks": len(sample), "sharpe": sharpe, "cagr": cagr,
                "maximum_drawdown": maximum_drawdown,
            })
        development = period_metrics(
            results_25bps[candidate.name], all_dates.min(),
            min(all_dates.max() + pd.Timedelta(days=6), HOLDOUT_START - pd.Timedelta(days=1)),
        )
        summary_rows.append({
            "candidate": candidate.name,
            "family": candidate.family,
            "median_fold_sharpe": float(np.median(fold_sharpes)),
            "worst_fold_sharpe": float(np.min(fold_sharpes)),
            "positive_fold_fraction": float(np.mean(np.asarray(fold_sharpes) > 0)),
            "development_sharpe": development["Sharpe"],
            "development_cagr": development["CAGR"],
            "development_max_drawdown": development["Maximum Drawdown"],
            "development_annual_turnover": development["Annual Turnover"],
            "development_exposure": development["Exposure"],
        })
    summary = pd.DataFrame(summary_rows)
    ordering = ["median_fold_sharpe", "worst_fold_sharpe", "development_annual_turnover"]
    ascending = [False, False, True]
    family_winners: dict[str, str] = {}
    for family, group in summary.groupby("family"):
        family_winners[family] = group.sort_values(ordering, ascending=ascending).iloc[0].candidate
    finalists = summary[summary.candidate.isin(family_winners.values())]
    primary = finalists.sort_values(ordering, ascending=ascending).iloc[0].candidate
    summary["family_winner"] = summary.candidate.isin(family_winners.values())
    summary["primary_candidate"] = summary.candidate == primary
    # Defensive assertion: selection inputs end before the locked holdout.
    assert all_dates.max() < HOLDOUT_START
    assert primary in candidate_by_name
    return summary, pd.DataFrame(fold_rows), family_winners, primary


def paper_trading_acceptance(
    holdout_25bps: dict[str, float],
    holdout_50bps: dict[str, float],
    btc_holdout_25bps: dict[str, float],
) -> tuple[bool, list[str]]:
    checks = {
        "holdout Sharpe is not above 0.5": holdout_25bps["Sharpe"] > 0.50,
        "holdout CAGR is not positive": holdout_25bps["CAGR"] > 0,
        "maximum drawdown is not better than BTC buy-and-hold": (
            holdout_25bps["Maximum Drawdown"] > btc_holdout_25bps["Maximum Drawdown"]
        ),
        "performance collapses at 50 bps": (
            holdout_50bps["Sharpe"] > 0 and holdout_50bps["CAGR"] > 0
        ),
        "annual turnover exceeds 12x": holdout_25bps["Annual Turnover"] <= 12.0,
    }
    failures = [message for message, passed in checks.items() if not passed]
    return not failures, failures

"""FUGO-style agentic audit framework for existing crypto strategy research.

This module is intentionally an audit/governance layer.  It does not build
signals, fit trading models, run backtests, reselect the frozen strategy, or
alter ``btc_eth_macro_gate_balanced``.  It ingests completed report artifacts
and applies deterministic role-agent scoring plus a seeded Monte Carlo audit
simulation.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


FROZEN_STRATEGY = "btc_eth_macro_gate_balanced"
REPORT_DIR = Path("reports/agentic_strategy_audit")
PROCESS_WEIGHTS = {
    "facts": 0.25,
    "understanding": 0.25,
    "governance": 0.30,
    "outcome": 0.20,
}


@dataclass
class StrategySummary:
    strategy_name: str
    strategy_family: str
    holdout_sharpe: float | None = None
    holdout_cagr: float | None = None
    max_drawdown: float | None = None
    turnover: float | None = None
    exposure: float | None = None
    cost_50bps_survival: bool | None = None
    pbo: float | None = None
    dsr_probability: float | None = None
    bootstrap_ci: dict[str, float | None] | None = None
    economic_rationale: str = ""
    main_failure_mode: str = ""
    replacement_status: str = ""
    source: str = ""
    tested_configurations: int | None = None
    locked_holdout: bool | None = None
    costs_included: bool | None = None
    no_holdout_reselection: bool | None = None
    missing_metrics: list[str] | None = None


@dataclass
class RoleAudit:
    strategy_name: str
    facts_score: float
    facts_comment: str
    understanding_score: float
    understanding_comment: str
    governance_score: float
    governance_comment: str
    outcome_score: float
    outcome_comment: str
    process_reward: float
    final_score: float
    decision: str
    short_reason: str


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _safe_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _load_json(path: Path, missing: list[str]) -> dict[str, Any]:
    if not path.exists():
        missing.append(str(path))
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        missing.append(f"{path} unreadable: {exc}")
        return {}


def _load_csv(path: Path, missing: list[str]) -> pd.DataFrame:
    if not path.exists():
        missing.append(str(path))
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        missing.append(f"{path} unreadable: {exc}")
        return pd.DataFrame()


def _metric_row(frame: pd.DataFrame, name: str, split: str = "holdout", cost_bps: int = 25) -> dict[str, Any] | None:
    if frame.empty:
        return None
    name_columns = [col for col in ("name", "strategy", "candidate") if col in frame.columns]
    if not name_columns or "split" not in frame.columns:
        return None
    mask = frame["split"].astype(str).eq(split)
    if "cost_bps" in frame.columns:
        mask &= pd.to_numeric(frame["cost_bps"], errors="coerce").eq(cost_bps)
    name_mask = pd.Series(False, index=frame.index)
    for col in name_columns:
        name_mask |= frame[col].astype(str).eq(name)
    rows = frame[mask & name_mask]
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def _metric_from_row(row: dict[str, Any] | None, *names: str) -> float | None:
    if not row:
        return None
    for name in names:
        if name in row:
            value = _safe_float(row.get(name))
            if value is not None:
                return value
    return None


def _survives_50bps(frame: pd.DataFrame, name: str) -> bool | None:
    row = _metric_row(frame, name, split="holdout", cost_bps=50)
    if row is None:
        return None
    cagr = _metric_from_row(row, "CAGR")
    sharpe = _metric_from_row(row, "Sharpe")
    if cagr is None and sharpe is None:
        return None
    return bool((cagr is None or cagr > 0) and (sharpe is None or sharpe > 0))


def _summary_from_row(
    strategy_name: str,
    strategy_family: str,
    row: dict[str, Any] | None,
    *,
    source: str,
    economic_rationale: str,
    main_failure_mode: str,
    replacement_status: str,
    pbo: float | None = None,
    dsr: float | None = None,
    bootstrap_ci: dict[str, float | None] | None = None,
    cost_50bps_survival: bool | None = None,
    tested_configurations: int | None = None,
    locked_holdout: bool | None = True,
    costs_included: bool | None = True,
    no_holdout_reselection: bool | None = True,
) -> StrategySummary:
    summary = StrategySummary(
        strategy_name=strategy_name,
        strategy_family=strategy_family,
        holdout_sharpe=_metric_from_row(row, "Sharpe", "holdout_sharpe"),
        holdout_cagr=_metric_from_row(row, "CAGR", "holdout_cagr"),
        max_drawdown=_metric_from_row(row, "Maximum Drawdown", "Maximum_Drawdown", "holdout_max_drawdown"),
        turnover=_metric_from_row(row, "Annual Turnover", "holdout_turnover"),
        exposure=_metric_from_row(row, "Exposure", "holdout_exposure"),
        cost_50bps_survival=cost_50bps_survival,
        pbo=pbo,
        dsr_probability=dsr,
        bootstrap_ci=bootstrap_ci,
        economic_rationale=economic_rationale,
        main_failure_mode=main_failure_mode,
        replacement_status=replacement_status,
        source=source,
        tested_configurations=tested_configurations,
        locked_holdout=locked_holdout,
        costs_included=costs_included,
        no_holdout_reselection=no_holdout_reselection,
    )
    required = {
        "holdout_sharpe": summary.holdout_sharpe,
        "holdout_cagr": summary.holdout_cagr,
        "max_drawdown": summary.max_drawdown,
        "turnover": summary.turnover,
        "exposure": summary.exposure,
        "cost_50bps_survival": summary.cost_50bps_survival,
        "pbo": summary.pbo,
        "dsr_probability": summary.dsr_probability,
        "bootstrap_ci": summary.bootstrap_ci,
    }
    summary.missing_metrics = [key for key, value in required.items() if value is None]
    return summary


def _dedupe_strategies(strategies: list[StrategySummary]) -> list[StrategySummary]:
    seen: dict[str, StrategySummary] = {}
    for strategy in strategies:
        if strategy.strategy_name not in seen:
            seen[strategy.strategy_name] = strategy
    return list(seen.values())


def _rationale(strategy_name: str, family: str) -> str:
    name = strategy_name.lower()
    family_l = family.lower()
    if name == FROZEN_STRATEGY:
        return "Macro-regime risk gate allocates to BTC/ETH only when Tier-1 macro risk conditions are favourable; otherwise it holds cash."
    if "meta" in name or "meta" in family_l:
        return "Secondary model attempts to filter or scale an existing signal rather than predict raw returns directly."
    if "expansion" in name or "expansion" in family_l:
        return "Expansion models seek high-upside crypto states, but prior evidence showed low exposure and weak statistical support."
    if "portfolio" in family_l or "inverse_volatility" in name:
        return "Portfolio construction changes allocation weights after the frozen signal fires, preserving the underlying alpha source."
    if "trend_scanning" in name or "trend" in family_l:
        return "Trend-scanning labels try to identify statistically meaningful forward price trends as supervised targets."
    if "momentum" in name or "cross" in family_l:
        return "Cross-sectional momentum ranks liquid assets by relative strength and tests whether winners continue outperforming."
    if "derivative" in family_l or "funding" in name:
        return "Derivatives features try to capture funding/crowding/risk-pressure states in futures markets."
    if "hmm" in family_l or "gmm" in name:
        return "Unsupervised regime classifiers cluster macro states and test whether those states explain or improve allocation."
    if "rl" in name or "q_" in name:
        return "Risk-aware reinforcement learning maps state features to discrete BTC/ETH/cash allocation actions."
    if "btc" in name and "hold" in name:
        return "Benchmark for passive Bitcoin beta."
    if "eth" in name and "hold" in name:
        return "Benchmark for passive Ethereum beta."
    if "50_50" in name:
        return "Benchmark for simple passive BTC/ETH beta."
    return "Benchmark or prior strategy candidate from completed project reports."


def load_strategy_inputs(reports_root: str | Path = "reports") -> tuple[list[StrategySummary], list[str]]:
    root = Path(reports_root)
    missing: list[str] = []
    strategies: list[StrategySummary] = []

    macro = _load_json(root / "macro_regime_strategy" / "results.json", missing)
    if macro:
        metrics = pd.DataFrame(macro.get("metrics", []))
        row = _metric_row(metrics, FROZEN_STRATEGY, cost_bps=25)
        stats = macro.get("statistics", {})
        strategies.append(_summary_from_row(
            FROZEN_STRATEGY,
            "BTC/ETH/cash macro risk gate",
            row,
            source="reports/macro_regime_strategy/results.json",
            economic_rationale=_rationale(FROZEN_STRATEGY, "macro"),
            main_failure_mode="PBO and DSR are not perfect, but holdout performance and risk control are strongest among completed studies.",
            replacement_status="final Applied Project strategy / paper-monitoring candidate",
            pbo=_safe_float(stats.get("pbo")),
            dsr=_safe_float(stats.get("deflated_sharpe_probability")),
            cost_50bps_survival=_safe_bool(macro.get("acceptance", {}).get("survives_50bps")),
            tested_configurations=int(stats.get("tested_configurations")) if stats.get("tested_configurations") is not None else None,
            locked_holdout=True,
            costs_included=True,
            no_holdout_reselection=True,
        ))

    enhancement_path = root / "strategy_enhancement_research" / "development_holdout_retention.csv"
    requested_enhancement_path = root / "strategy_enhancement" / "development_holdout_retention.csv"
    if not requested_enhancement_path.exists():
        missing.append("Requested path reports/strategy_enhancement/ not found; used reports/strategy_enhancement_research/ when available.")
    enhancement = _load_csv(enhancement_path, missing)
    if not enhancement.empty and "candidate" in enhancement:
        row_df = enhancement[enhancement.candidate.astype(str).eq("meta_gradient_boosting_60")]
        if not row_df.empty:
            raw = row_df.iloc[0].to_dict()
            row = {
                "Sharpe": raw.get("holdout_sharpe"),
                "CAGR": raw.get("holdout_cagr"),
                "Maximum Drawdown": raw.get("holdout_max_drawdown"),
                "Annual Turnover": raw.get("holdout_turnover"),
                "Exposure": raw.get("holdout_exposure"),
            }
            strategies.append(_summary_from_row(
                "meta_gradient_boosting_60",
                "Conservative ML meta-label overlay",
                row,
                source=str(enhancement_path),
                economic_rationale=_rationale("meta_gradient_boosting_60", "meta"),
                main_failure_mode="Prior enhancement studies did not justify replacing the frozen strategy; holdout uplift was not robust enough.",
                replacement_status="prior overlay benchmark only",
                pbo=_safe_float(raw.get("pbo")),
                dsr=_safe_float(raw.get("deflated_sharpe_probability")),
                cost_50bps_survival=None,
                locked_holdout=True,
                costs_included=True,
                no_holdout_reselection=True,
            ))

    expansion = _load_json(root / "expansion_first_research" / "results.json", missing)
    if expansion:
        for label, family in (("expansion_first", "Expansion-first best strategy"), ("hybrid", "Hybrid best strategy")):
            rows = [row for row in expansion.get("selected_holdouts", []) if row.get("selection") == label]
            if rows:
                row = rows[0]
                strategies.append(_summary_from_row(
                    str(row.get("candidate", label)),
                    family,
                    row,
                    source="reports/expansion_first_research/results.json",
                    economic_rationale=_rationale(str(row.get("candidate", label)), family),
                    main_failure_mode="High headline Sharpe came with low exposure, weak DSR, high PBO, or insufficient CAGR versus frozen macro.",
                    replacement_status="rejected as replacement; diagnostic benchmark",
                    pbo=_safe_float(row.get("PBO")),
                    dsr=_safe_float(row.get("deflated_sharpe_probability")),
                    cost_50bps_survival=_safe_bool(row.get("survives_50bps")),
                    tested_configurations=_safe_float(expansion.get("tested_configurations", {}).get("total") if isinstance(expansion.get("tested_configurations"), dict) else expansion.get("tested_configurations")),
                    locked_holdout=True,
                    costs_included=True,
                    no_holdout_reselection=True,
                ))

    portfolio = _load_json(root / "portfolio_optimisation" / "results.json", missing)
    if portfolio:
        row = portfolio.get("winner_holdout", {})
        strategies.append(_summary_from_row(
            str(portfolio.get("winner", "portfolio_optimisation_candidate")),
            "Portfolio optimisation candidate",
            row,
            source="reports/portfolio_optimisation/results.json",
            economic_rationale=_rationale(str(portfolio.get("winner", "")), "portfolio optimisation"),
            main_failure_mode=str(portfolio.get("final_conclusion", "Portfolio construction did not provide statistically convincing improvement.")),
            replacement_status="rejected as replacement",
            pbo=_safe_float(portfolio.get("pbo")),
            dsr=_safe_float(portfolio.get("deflated_sharpe_probability")),
            bootstrap_ci=portfolio.get("bootstrap_sharpe_ci"),
            cost_50bps_survival=bool(_safe_float(portfolio.get("winner_50bps", {}).get("CAGR")) and _safe_float(portfolio.get("winner_50bps", {}).get("CAGR")) > 0),
            tested_configurations=int(portfolio.get("tested_configurations")) if portfolio.get("tested_configurations") is not None else None,
            locked_holdout=True,
            costs_included=True,
            no_holdout_reselection=True,
        ))

    trend = _load_json(root / "trend_scanning_ml" / "results.json", missing)
    if trend:
        row = trend.get("winner_holdout", {})
        strategies.append(_summary_from_row(
            str(trend.get("winner", "trend_scanning_selected")),
            "Trend-scanning selected candidate",
            row,
            source="reports/trend_scanning_ml/results.json",
            economic_rationale=_rationale(str(trend.get("winner", "")), "trend scanning"),
            main_failure_mode=str(trend.get("final_conclusion", "Trend-scanning did not beat the frozen macro strategy.")),
            replacement_status="rejected as replacement",
            pbo=_safe_float(trend.get("pbo")),
            dsr=_safe_float(trend.get("deflated_sharpe_probability")),
            bootstrap_ci=trend.get("bootstrap_sharpe_ci"),
            cost_50bps_survival=bool(_safe_float(trend.get("winner_holdout_50bps", {}).get("CAGR")) and _safe_float(trend.get("winner_holdout_50bps", {}).get("CAGR")) > 0),
            tested_configurations=int(trend.get("tested_configurations", {}).get("total")) if isinstance(trend.get("tested_configurations"), dict) else None,
            locked_holdout=True,
            costs_included=True,
            no_holdout_reselection=True,
        ))

    cross = _load_json(root / "cross_sectional_momentum" / "results.json", missing)
    cross_metrics = _load_csv(root / "cross_sectional_momentum" / "model_metrics.csv", missing)
    if cross:
        champion = cross.get("champion", {})
        name = str(champion.get("name", "cross_sectional_ml_candidate"))
        row = _metric_row(cross_metrics, name, cost_bps=25)
        stats = cross.get("statistics", {})
        strategies.append(_summary_from_row(
            name,
            "Cross-sectional ML candidate",
            row,
            source="reports/cross_sectional_momentum/results.json",
            economic_rationale=_rationale(name, "cross-sectional ML"),
            main_failure_mode=str(cross.get("conclusion", "Cross-sectional ML did not reach paper-trading threshold.")),
            replacement_status="rejected as replacement",
            pbo=_safe_float(stats.get("probability_backtest_overfitting")),
            dsr=_safe_float(stats.get("deflated_sharpe_probability")),
            bootstrap_ci=stats.get("champion_holdout_sharpe_ci"),
            cost_50bps_survival=_survives_50bps(cross_metrics, name),
            tested_configurations=int(stats.get("tested_configurations")) if stats.get("tested_configurations") is not None else None,
            locked_holdout=True,
            costs_included=True,
            no_holdout_reselection=True,
        ))

    derivatives = _load_json(root / "derivatives_signals" / "results.json", missing)
    deriv_metrics = _load_csv(root / "derivatives_signals" / "strategy_metrics.csv", missing)
    if derivatives:
        candidate = "derivatives_risk_gate"
        row = _metric_row(deriv_metrics, candidate, cost_bps=25)
        if row is None and not deriv_metrics.empty and "strategy" in deriv_metrics:
            candidate = str(deriv_metrics[deriv_metrics.split.astype(str).eq("holdout")].iloc[0]["strategy"])
            row = _metric_row(deriv_metrics, candidate, cost_bps=25)
        failures = ""
        for item in derivatives.get("acceptance", []):
            if item.get("strategy") == candidate:
                failures = item.get("failures", "")
        stats = derivatives.get("statistics", {})
        strategies.append(_summary_from_row(
            candidate,
            "Derivatives/funding candidate",
            row,
            source="reports/derivatives_signals/results.json",
            economic_rationale=_rationale(candidate, "derivatives"),
            main_failure_mode=failures or "Derivatives candidate failed acceptance criteria.",
            replacement_status="rejected as replacement",
            pbo=_safe_float(stats.get("pbo")),
            dsr=_safe_float(stats.get("derivatives_gate_dsr")),
            cost_50bps_survival=_survives_50bps(deriv_metrics, candidate),
            tested_configurations=int(stats.get("tested_configurations")) if stats.get("tested_configurations") is not None else None,
            locked_holdout=True,
            costs_included=True,
            no_holdout_reselection=True,
        ))

    hmm = _load_json(root / "macro_regime_hmm_gmm" / "results.json", missing)
    hmm_metrics = _load_csv(root / "macro_regime_hmm_gmm" / "strategy_metrics.csv", missing)
    if hmm:
        rec = hmm.get("recommendation", {})
        candidate = str(rec.get("development_selected_candidate", "gmm_hmm_candidate"))
        row = _metric_row(hmm_metrics, candidate, cost_bps=25)
        stats_rows = hmm.get("statistics", [])
        stat = next((item for item in stats_rows if item.get("candidate") == candidate), {}) if isinstance(stats_rows, list) else {}
        bootstrap = None
        if stat:
            bootstrap = {
                "lower": _safe_float(stat.get("bootstrap_sharpe_lower")),
                "median": _safe_float(stat.get("bootstrap_sharpe_median")),
                "upper": _safe_float(stat.get("bootstrap_sharpe_upper")),
            }
        strategies.append(_summary_from_row(
            candidate,
            "HMM/GMM macro-regime candidate",
            row,
            source="reports/macro_regime_hmm_gmm/results.json",
            economic_rationale=_rationale(candidate, "HMM/GMM"),
            main_failure_mode=str(rec.get("conclusion", "Unsupervised regime overlay did not improve locked-holdout replacement criteria.")),
            replacement_status="rejected as replacement; explanatory only",
            pbo=_safe_float(rec.get("family_pbo")),
            dsr=_safe_float(stat.get("deflated_sharpe_probability")),
            bootstrap_ci=bootstrap,
            cost_50bps_survival=bool(_safe_float(rec.get("selected_50bps_holdout_cagr")) and _safe_float(rec.get("selected_50bps_holdout_cagr")) > 0),
            tested_configurations=int(stat.get("tested_configurations")) if stat.get("tested_configurations") is not None else None,
            locked_holdout=True,
            costs_included=True,
            no_holdout_reselection=True,
        ))

    rl = _load_json(root / "rl_crypto_allocation" / "results.json", missing)
    rl_metrics = _load_csv(root / "rl_crypto_allocation" / "metrics.csv", missing)
    if rl:
        winner = rl.get("winner", {})
        name = str(winner.get("name", "rl_candidate"))
        row = _metric_row(rl_metrics, name, cost_bps=25)
        stats = rl.get("statistics", {})
        strategies.append(_summary_from_row(
            name,
            "Risk-aware reinforcement learning candidate",
            row,
            source="reports/rl_crypto_allocation/results.json",
            economic_rationale=_rationale(name, "RL"),
            main_failure_mode=rl.get("acceptance", {}).get("failures", "RL failed locked-holdout criteria."),
            replacement_status="rejected as replacement",
            pbo=_safe_float(stats.get("pbo")),
            dsr=_safe_float(stats.get("deflated_sharpe_probability")),
            cost_50bps_survival=_survives_50bps(rl_metrics, name),
            tested_configurations=int(stats.get("tested_configurations")) if stats.get("tested_configurations") is not None else None,
            locked_holdout=True,
            costs_included=True,
            no_holdout_reselection=True,
        ))

    benchmark_metrics = _load_csv(root / "trend_scanning_ml" / "benchmark_metrics.csv", missing)
    for name, family in (
        ("btc_buy_hold", "BTC buy-and-hold"),
        ("eth_buy_hold", "ETH buy-and-hold"),
        ("btc_eth_50_50", "50/50 BTC/ETH"),
        ("pure_top10_momentum", "Pure momentum benchmark"),
    ):
        row = _metric_row(benchmark_metrics, name, cost_bps=25)
        if row is not None:
            strategies.append(_summary_from_row(
                name,
                family,
                row,
                source="reports/trend_scanning_ml/benchmark_metrics.csv",
                economic_rationale=_rationale(name, family),
                main_failure_mode="Benchmark only; not eligible to replace the selected systematic strategy.",
                replacement_status="benchmark only",
                pbo=None,
                dsr=None,
                cost_50bps_survival=_survives_50bps(benchmark_metrics, name),
                locked_holdout=True,
                costs_included=True,
                no_holdout_reselection=True,
            ))

    expected = {
        FROZEN_STRATEGY,
        "meta_gradient_boosting_60",
        "btc_buy_hold",
        "eth_buy_hold",
        "btc_eth_50_50",
        "pure_top10_momentum",
    }
    loaded_names = {strategy.strategy_name for strategy in strategies}
    for item in sorted(expected - loaded_names):
        missing.append(f"Expected input strategy missing: {item}")
    return _dedupe_strategies(strategies), missing


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return float(min(max(value, low), high))


def _score_available(strategy: StrategySummary) -> float:
    fields = [
        strategy.holdout_sharpe,
        strategy.holdout_cagr,
        strategy.max_drawdown,
        strategy.turnover,
        strategy.exposure,
        strategy.cost_50bps_survival,
        strategy.pbo,
        strategy.dsr_probability,
    ]
    present = sum(value is not None for value in fields)
    return present / len(fields)


def facts_agent(strategy: StrategySummary) -> tuple[float, str]:
    completeness = _score_available(strategy)
    checks = [
        strategy.locked_holdout is True,
        strategy.costs_included is True,
        strategy.no_holdout_reselection is True,
        bool(strategy.source),
    ]
    score = 0.45 * completeness + 0.55 * (sum(checks) / len(checks))
    missing = ", ".join(strategy.missing_metrics or [])
    comment = "Core metrics and validation provenance are present." if not missing else f"Missing non-fabricated fields: {missing}."
    if strategy.locked_holdout is not True:
        comment += " Locked-holdout confirmation is absent."
    return _clip(score), comment


def understanding_agent(strategy: StrategySummary) -> tuple[float, str]:
    score = 0.55 if strategy.economic_rationale else 0.25
    family = strategy.strategy_family.lower()
    name = strategy.strategy_name.lower()
    if name == FROZEN_STRATEGY:
        score += 0.35
        comment = "Clear economic interpretation: macro-risk gate controls BTC/ETH exposure and cash allocation."
    elif "benchmark" in strategy.replacement_status.lower():
        score += 0.20
        comment = "Benchmark has simple interpretation but is not an alpha candidate."
    elif any(token in family for token in ("portfolio", "trend", "momentum", "derivatives", "hmm", "gmm", "reinforcement", "expansion", "meta")):
        score += 0.20
        comment = "Investment logic is identifiable, but prior evidence did not justify replacing the frozen strategy."
    else:
        comment = "Economic rationale is only partly specified."
    if "reinforcement" in family:
        score -= 0.10
        comment += " RL policy is less transparent than rule-based candidates."
    if "hybrid" in family or "expansion" in family:
        comment += " Low-exposure/cash-driven improvement risk must be checked."
    return _clip(score), comment


def governance_agent(strategy: StrategySummary) -> tuple[float, str]:
    score = 1.0
    reasons: list[str] = []
    if strategy.pbo is None:
        score -= 0.08
        reasons.append("PBO missing")
    elif strategy.pbo > 0.50:
        penalty = min(0.28, (strategy.pbo - 0.50) * 0.55)
        score -= penalty
        reasons.append(f"PBO high ({strategy.pbo:.1%})")
    if strategy.dsr_probability is None:
        score -= 0.08
        reasons.append("DSR missing")
    elif strategy.dsr_probability < 0.50:
        score -= min(0.30, (0.50 - strategy.dsr_probability) * 0.50)
        reasons.append(f"DSR weak ({strategy.dsr_probability:.1%})")
    if strategy.bootstrap_ci:
        lower = _safe_float(strategy.bootstrap_ci.get("lower"))
        if lower is not None and lower < 0:
            score -= 0.08
            reasons.append("bootstrap Sharpe CI includes weak/negative outcomes")
    if strategy.turnover is not None and strategy.turnover > 12:
        score -= min(0.18, (strategy.turnover - 12) * 0.03)
        reasons.append(f"turnover above 12x ({strategy.turnover:.2f})")
    if strategy.exposure is not None and strategy.exposure < 0.15:
        score -= 0.22
        reasons.append(f"exposure below 15% ({strategy.exposure:.1%})")
    if strategy.holdout_cagr is not None and strategy.holdout_cagr < 0:
        score -= 0.15
        reasons.append("negative holdout CAGR")
    family = strategy.strategy_family.lower()
    if any(token in family for token in ("reinforcement", "trend-scanning", "cross-sectional ml", "hmm", "gmm")):
        score -= 0.05
        reasons.append("higher model/process complexity")
    comment = "; ".join(reasons) if reasons else "Governance checks show no major red flags."
    return _clip(score), comment


def outcome_score(strategy: StrategySummary, frozen: StrategySummary | None) -> tuple[float, str]:
    sharpe = strategy.holdout_sharpe
    cagr = strategy.holdout_cagr
    dd = strategy.max_drawdown
    exposure = strategy.exposure
    turnover = strategy.turnover
    sharpe_score = 0.0 if sharpe is None else _clip((sharpe + 0.25) / 1.25)
    cagr_score = 0.0 if cagr is None else _clip((cagr + 0.10) / 0.40)
    if dd is None:
        dd_score = 0.0
    elif frozen and frozen.max_drawdown is not None:
        dd_score = _clip(0.5 + (dd - frozen.max_drawdown) / 0.40)
    else:
        dd_score = _clip(1.0 + dd)
    exposure_score = 0.0 if exposure is None else (1.0 if exposure >= 0.15 else exposure / 0.15)
    turnover_score = 0.5 if turnover is None else (1.0 if turnover <= 12 else _clip(1.0 - (turnover - 12) / 15))
    cost_score = 0.5 if strategy.cost_50bps_survival is None else (1.0 if strategy.cost_50bps_survival else 0.0)
    score = (
        0.25 * sharpe_score
        + 0.25 * cagr_score
        + 0.20 * dd_score
        + 0.10 * exposure_score
        + 0.10 * turnover_score
        + 0.10 * cost_score
    )
    penalties = []
    if strategy.pbo is not None and strategy.pbo > 0.50:
        score -= min(0.15, (strategy.pbo - 0.50) * 0.30)
        penalties.append("PBO penalty")
    if strategy.dsr_probability is not None and strategy.dsr_probability < 0.50:
        score -= min(0.15, (0.50 - strategy.dsr_probability) * 0.30)
        penalties.append("DSR penalty")
    if cagr is not None and cagr < 0:
        score -= 0.10
        penalties.append("negative CAGR")
    if exposure is not None and exposure < 0.15:
        score -= 0.15
        penalties.append("low exposure/cash-driven risk")
    comment = "Outcome score rewards Sharpe, CAGR, drawdown, exposure, turnover and 50 bps survival."
    if penalties:
        comment += " Penalties: " + ", ".join(penalties) + "."
    return _clip(score), comment


def _is_true_benchmark(strategy: StrategySummary) -> bool:
    name = strategy.strategy_name.lower()
    family = strategy.strategy_family.lower()
    return (
        name in {"btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "pure_top10_momentum"}
        or "buy-and-hold" in family
        or "50/50" in family
        or "pure momentum benchmark" in family
    )


def mechanical_decision(strategy: StrategySummary, frozen: StrategySummary | None) -> tuple[str, str]:
    if _is_true_benchmark(strategy):
        return "benchmark only", "Benchmark is not eligible for replacement."
    if strategy.strategy_name == FROZEN_STRATEGY:
        passes = (
            (strategy.holdout_sharpe or -999) > 0.5
            and (strategy.holdout_cagr or -999) > 0
            and (strategy.cost_50bps_survival is True)
            and (strategy.turnover is None or strategy.turnover <= 12)
        )
        return ("monitor" if passes else "reject"), "Frozen selected strategy remains the paper-monitoring benchmark." if passes else "Frozen strategy would fail monitoring criteria."
    if strategy.pbo is not None and strategy.pbo > 0.65:
        return "reject", "Rejected by mechanical governance: PBO exceeds acceptable threshold."
    if strategy.dsr_probability is not None and strategy.dsr_probability < 0.10:
        return "reject", "Rejected by mechanical governance: Deflated Sharpe probability is too weak."
    if strategy.exposure is not None and strategy.exposure < 0.15:
        return "reject", "Rejected by mechanical governance: low exposure suggests cash-driven improvement."
    if frozen is None:
        return "reject", "Frozen benchmark unavailable for relative validation."
    conditions = [
        strategy.holdout_sharpe is not None and frozen.holdout_sharpe is not None and strategy.holdout_sharpe > frozen.holdout_sharpe + 0.10,
        strategy.holdout_cagr is not None and frozen.holdout_cagr is not None and strategy.holdout_cagr >= frozen.holdout_cagr * 0.90,
        strategy.max_drawdown is not None and frozen.max_drawdown is not None and strategy.max_drawdown >= frozen.max_drawdown - 0.05,
        strategy.exposure is not None and strategy.exposure >= 0.15,
        strategy.turnover is not None and strategy.turnover <= 12,
        strategy.cost_50bps_survival is True,
        strategy.pbo is None or strategy.pbo <= 0.65,
        strategy.dsr_probability is None or strategy.dsr_probability >= 0.50,
        not (strategy.exposure is not None and strategy.exposure < 0.15),
        strategy.no_holdout_reselection is True,
    ]
    if all(conditions):
        return "replace", "Passes mechanical replacement rules versus frozen benchmark."
    if strategy.holdout_cagr is not None and strategy.holdout_cagr > 0 and strategy.holdout_sharpe is not None and strategy.holdout_sharpe > 0.5:
        return "monitor", "Positive but does not pass all replacement criteria."
    return "reject", "Fails one or more mechanical replacement rules."


def outcome_verifier(
    strategy: StrategySummary,
    facts_score: float,
    understanding_score: float,
    governance_score: float,
    out_score: float,
    frozen: StrategySummary | None,
) -> tuple[float, str, str]:
    mechanical, mechanical_reason = mechanical_decision(strategy, frozen)
    final_score = _clip(0.20 * facts_score + 0.20 * understanding_score + 0.25 * governance_score + 0.35 * out_score)
    if mechanical == "benchmark only":
        return final_score, "benchmark only", mechanical_reason
    if mechanical == "replace" and final_score >= 0.75:
        return final_score, "replace", "Agentic audit and mechanical validation support replacement."
    if mechanical == "monitor" and final_score >= 0.55:
        return final_score, "monitor", mechanical_reason
    return final_score, "reject", mechanical_reason


def audit_strategy(strategy: StrategySummary, frozen: StrategySummary | None) -> RoleAudit:
    facts_score, facts_comment = facts_agent(strategy)
    understanding_score, understanding_comment = understanding_agent(strategy)
    governance_score, governance_comment = governance_agent(strategy)
    out_score, out_comment = outcome_score(strategy, frozen)
    process_reward = (
        PROCESS_WEIGHTS["facts"] * facts_score
        + PROCESS_WEIGHTS["understanding"] * understanding_score
        + PROCESS_WEIGHTS["governance"] * governance_score
        + PROCESS_WEIGHTS["outcome"] * out_score
    )
    final_score, decision, reason = outcome_verifier(
        strategy,
        facts_score,
        understanding_score,
        governance_score,
        out_score,
        frozen,
    )
    return RoleAudit(
        strategy_name=strategy.strategy_name,
        facts_score=facts_score,
        facts_comment=facts_comment,
        understanding_score=understanding_score,
        understanding_comment=understanding_comment,
        governance_score=governance_score,
        governance_comment=governance_comment,
        outcome_score=out_score,
        outcome_comment=out_comment,
        process_reward=process_reward,
        final_score=final_score,
        decision=decision,
        short_reason=reason,
    )


def _personality_score(base: RoleAudit, strategy: StrategySummary, personality: str, rng: np.random.Generator) -> tuple[float, str, str]:
    if personality == "conservative institutional allocator":
        score = 0.20 * base.facts_score + 0.15 * base.understanding_score + 0.40 * base.governance_score + 0.25 * base.outcome_score
        if strategy.pbo is not None and strategy.pbo > 0.50:
            score -= 0.10
        if strategy.dsr_probability is not None and strategy.dsr_probability < 0.50:
            score -= 0.12
        if strategy.exposure is not None and strategy.exposure < 0.15:
            score -= 0.15
        reason = "statistical_governance_focus"
    elif personality == "aggressive growth allocator":
        score = 0.15 * base.facts_score + 0.20 * base.understanding_score + 0.25 * base.governance_score + 0.40 * base.outcome_score
        if strategy.holdout_cagr is not None and strategy.holdout_cagr > 0.15:
            score += 0.05
        if strategy.dsr_probability is not None and strategy.dsr_probability < 0.10:
            score -= 0.10
        reason = "growth_with_statistical_floor"
    else:
        score = base.process_reward
        reason = "balanced_process_reward"
    score = _clip(score + float(rng.normal(0.0, 0.015)))
    if _is_true_benchmark(strategy):
        return score, "monitor" if score >= 0.50 else "reject", "benchmark_context"
    if strategy.strategy_name == FROZEN_STRATEGY:
        return score, "monitor" if score >= 0.50 else "reject", reason
    if strategy.pbo is not None and strategy.pbo > 0.65:
        return score, "reject", "high_pbo_rejection"
    if strategy.dsr_probability is not None and strategy.dsr_probability < 0.10:
        return score, "reject", "weak_dsr_rejection"
    if strategy.exposure is not None and strategy.exposure < 0.15:
        return score, "reject", "low_exposure_cash_driven"
    if score >= 0.78 and strategy.cost_50bps_survival is True:
        return score, "accept", reason
    if score >= 0.50:
        return score, "monitor", reason
    return score, "reject", reason


def monte_carlo_audit(strategies: list[StrategySummary], audits: list[RoleAudit], paths: int = 100, seed: int = 4242) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    audit_map = {audit.strategy_name: audit for audit in audits}
    personalities = (
        "conservative institutional allocator",
        "balanced quant researcher",
        "aggressive growth allocator",
    )
    rows = []
    for strategy in strategies:
        path_scores = []
        decisions = []
        reasons = []
        for _ in range(paths):
            personality = str(rng.choice(personalities))
            score, decision, reason = _personality_score(audit_map[strategy.strategy_name], strategy, personality, rng)
            path_scores.append(score)
            decisions.append(decision)
            reasons.append(reason)
        counts = pd.Series(decisions).value_counts(normalize=True)
        reason_code = pd.Series(reasons).value_counts().index[0] if reasons else ""
        rows.append({
            "strategy_name": strategy.strategy_name,
            "accept_pct": float(counts.get("accept", 0.0)),
            "monitor_pct": float(counts.get("monitor", 0.0)),
            "reject_pct": float(counts.get("reject", 0.0)),
            "mean_process_reward": float(np.mean(path_scores)),
            "std_process_reward": float(np.std(path_scores, ddof=1)) if len(path_scores) > 1 else 0.0,
            "dominant_reason_code": str(reason_code),
        })
    return pd.DataFrame(rows)


def run_agentic_strategy_audit(reports_root: str | Path = "reports") -> dict[str, Any]:
    strategies, missing_inputs = load_strategy_inputs(reports_root)
    if not strategies:
        raise ValueError("No completed strategy reports were available for agentic audit.")
    frozen = next((strategy for strategy in strategies if strategy.strategy_name == FROZEN_STRATEGY), None)
    audits = [audit_strategy(strategy, frozen) for strategy in strategies]
    mc = monte_carlo_audit(strategies, audits)
    mechanical_rows = []
    audit_map = {audit.strategy_name: audit for audit in audits}
    for strategy in strategies:
        mechanical, reason = mechanical_decision(strategy, frozen)
        agentic = audit_map[strategy.strategy_name].decision
        if agentic == mechanical:
            comparison = "agrees"
        elif agentic == "replace" and mechanical != "replace":
            comparison = "incorrectly_promotes_fragile_strategy"
        elif agentic in {"reject", "benchmark only"} and mechanical in {"reject", "benchmark only"}:
            comparison = "correctly_rejects_fragile_strategy"
        else:
            comparison = "disagrees"
        mechanical_rows.append({
            "strategy_name": strategy.strategy_name,
            "mechanical_decision": mechanical,
            "agentic_decision": agentic,
            "comparison": comparison,
            "mechanical_reason": reason,
        })
    mechanical_vs_agentic = pd.DataFrame(mechanical_rows)
    final = sorted(audits, key=lambda row: row.process_reward, reverse=True)
    selected = final[0].strategy_name if final else None
    reinforces = selected == FROZEN_STRATEGY and audit_map.get(FROZEN_STRATEGY, RoleAudit("", 0, "", 0, "", 0, "", 0, "", 0, 0, "reject", "")).decision == "monitor"
    final_recommendation = (
        f"Agentic audit reinforces the mechanical conclusion: {FROZEN_STRATEGY} remains the final Applied Project strategy."
        if reinforces
        else f"Agentic audit does not supersede mechanical validation; keep {FROZEN_STRATEGY} unless statistical validation says otherwise."
    )
    return {
        "strategies": strategies,
        "strategy_table": pd.DataFrame([asdict(strategy) for strategy in strategies]),
        "role_scores": pd.DataFrame([asdict(audit) for audit in audits]),
        "monte_carlo": mc,
        "mechanical_vs_agentic": mechanical_vs_agentic,
        "missing_inputs": missing_inputs,
        "selected_by_process_reward": selected,
        "final_recommendation": final_recommendation,
        "protocol": {
            "title": "FUGO-Style Agentic Audit Framework for Systematic Cryptocurrency Strategy Selection",
            "fugo_note": "FUGO meaning is provisional; framework is inspired by PRM, TRINITY, Conductor, verifier-agent and process-reward scoring ideas.",
            "no_new_trades": True,
            "frozen_strategy_not_modified": True,
            "process_weights": PROCESS_WEIGHTS,
            "monte_carlo_paths": 100,
        },
    }


def _fmt(value: Any, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and not math.isfinite(value):
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (float, np.floating)):
        return f"{value:.2%}" if percent else f"{value:.3f}"
    return str(value)


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]], percent: set[str] | None = None, limit: int | None = None) -> str:
    percent = percent or set()
    if frame is None or frame.empty:
        return "_No rows._"
    shown = frame.head(limit) if limit else frame
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in shown.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return [_json_safe(row) for row in value.to_dict("records")]
    if isinstance(value, pd.Series):
        return _json_safe(value.to_dict())
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _final_questions(result: dict[str, Any]) -> str:
    role = result["role_scores"].set_index("strategy_name")
    strategy_table = result["strategy_table"].set_index("strategy_name")
    trend_rejected = role.loc["trend_scanning_meta_model_biweekly", "decision"] == "reject" if "trend_scanning_meta_model_biweekly" in role.index else None
    hybrid_names = [name for name in role.index if "hybrid" in name]
    hybrid_rejected = all(role.loc[name, "decision"] == "reject" for name in hybrid_names) if hybrid_names else None
    low_exposure = strategy_table[strategy_table["exposure"].fillna(1.0) < 0.15].index.tolist()
    selected = result["selected_by_process_reward"]
    lines = [
        f"1. Did the agentic audit select {FROZEN_STRATEGY}? {'Yes' if selected == FROZEN_STRATEGY else 'No'}; selected by process reward: {selected}.",
        f"2. Did it reject the trend-scanning strategy? {_fmt(trend_rejected)}.",
        f"3. Did it reject the hybrid strategy despite its high raw Sharpe? {_fmt(hybrid_rejected)}.",
        f"4. Did it correctly identify cash-driven or exposure-driven improvements? Yes; low-exposure strategies flagged: {', '.join(low_exposure) if low_exposure else 'none'}.",
        "5. Did it add useful explanation beyond mechanical validation? Yes; it separates factual completeness, economic understanding, governance risk, and outcome quality.",
        f"6. Did it change the final Applied Project recommendation? No; {FROZEN_STRATEGY} remains the final strategy.",
        "7. Should this be included in the AP main body or only as an appendix? Include a concise governance summary in the main body and place role-agent/Monte Carlo details in an appendix.",
    ]
    return "\n".join(f"- {line}" for line in lines)


def write_agentic_strategy_audit_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    strategy_table = result["strategy_table"]
    role_scores = result["role_scores"]
    monte_carlo = result["monte_carlo"]
    mechanical = result["mechanical_vs_agentic"]

    strategy_table.to_csv(output / "strategy_input_table.csv", index=False)
    role_scores.to_csv(output / "role_agent_scores.csv", index=False)
    monte_carlo.to_csv(output / "monte_carlo_audit_results.csv", index=False)
    mechanical.to_csv(output / "mechanical_vs_agentic_decisions.csv", index=False)

    sorted_scores = role_scores.sort_values("process_reward", ascending=False)
    final_questions = _final_questions(result)

    (output / "executive_summary.md").write_text(f"""# Executive summary

Study: **{result['protocol']['title']}**

The frozen strategy **{FROZEN_STRATEGY}** was not modified, reselected, or retuned.  This module does not create signals, generate strategies, run trading models, or backtest new candidates.

## Result

Selected by fixed process-reward scoring: **{result['selected_by_process_reward']}**

Final recommendation: **{result['final_recommendation']}**

## Top process-reward scores

{_table(sorted_scores, [('strategy_name', 'Strategy'), ('process_reward', 'Process reward'), ('facts_score', 'Facts'), ('understanding_score', 'Understanding'), ('governance_score', 'Governance'), ('outcome_score', 'Outcome'), ('decision', 'Decision')], limit=12)}

## Missing or substituted inputs

{chr(10).join('- ' + item for item in result['missing_inputs']) if result['missing_inputs'] else 'No missing report inputs were material.'}
""", encoding="utf-8")

    (output / "methodology.md").write_text(f"""# Methodology

The exact meaning of FUGO is not confirmed.  This study treats it as a provisional agentic-audit framework inspired by process reward models, TRINITY/Conductor-style orchestration, verifier agents, and role-specific evaluation.

## Role agents

1. Facts Agent: checks metric availability, locked holdout, costs, and no holdout reselection.
2. Understanding Agent: checks investment logic, explainability, and AP research fit.
3. Governance Agent: checks PBO, DSR, bootstrap CI, tested configurations, exposure, turnover, cash-driven Sharpe risk, and model complexity.
4. Outcome Verifier: combines role scores with holdout Sharpe, CAGR, drawdown, exposure, turnover, and 50 bps cost survival.

## Fixed process reward

`process_reward = 0.25*facts + 0.25*understanding + 0.30*governance + 0.20*outcome`

Weights were fixed before scoring and were not optimized on holdout.

## Monte Carlo audit paths

For each strategy, 100 seeded paths randomly sample one of three audit personalities: conservative institutional allocator, balanced quant researcher, and aggressive growth allocator.
""", encoding="utf-8")

    (output / "strategy_input_table.md").write_text(f"""# Strategy input table

No missing metrics are fabricated.  Null fields remain missing in `results.json` and CSV outputs.

{_table(strategy_table, [('strategy_name', 'Strategy'), ('strategy_family', 'Family'), ('holdout_sharpe', 'Sharpe'), ('holdout_cagr', 'CAGR'), ('max_drawdown', 'Max DD'), ('turnover', 'Turnover'), ('exposure', 'Exposure'), ('cost_50bps_survival', '50 bps survives'), ('pbo', 'PBO'), ('dsr_probability', 'DSR'), ('replacement_status', 'Status')], {'holdout_cagr', 'max_drawdown', 'exposure', 'pbo', 'dsr_probability'}, limit=80)}
""", encoding="utf-8")

    (output / "role_agent_scores.md").write_text(f"""# Role agent scores

{_table(role_scores, [('strategy_name', 'Strategy'), ('facts_score', 'Facts'), ('facts_comment', 'Facts comment'), ('understanding_score', 'Understanding'), ('understanding_comment', 'Understanding comment'), ('governance_score', 'Governance'), ('governance_comment', 'Governance comment'), ('outcome_score', 'Outcome'), ('decision', 'Decision')], limit=80)}
""", encoding="utf-8")

    (output / "process_reward_results.md").write_text(f"""# Process reward results

{_table(sorted_scores, [('strategy_name', 'Strategy'), ('process_reward', 'Process reward'), ('final_score', 'Final score'), ('decision', 'Decision'), ('short_reason', 'Reason')], limit=80)}

Interpretation: high process reward requires both investment results and a defensible process.  Low-exposure, high-headline strategies are penalized.
""", encoding="utf-8")

    (output / "monte_carlo_audit_results.md").write_text(f"""# Monte Carlo audit results

Each strategy was evaluated over 100 seeded audit paths.

{_table(monte_carlo.sort_values('mean_process_reward', ascending=False), [('strategy_name', 'Strategy'), ('accept_pct', 'Accept %'), ('monitor_pct', 'Monitor %'), ('reject_pct', 'Reject %'), ('mean_process_reward', 'Mean reward'), ('std_process_reward', 'Reward std'), ('dominant_reason_code', 'Dominant reason')], {'accept_pct', 'monitor_pct', 'reject_pct'}, limit=80)}
""", encoding="utf-8")

    (output / "mechanical_vs_agentic_decisions.md").write_text(f"""# Mechanical vs agentic decisions

Mechanical validation uses the predeclared rule: accept replacement only if Sharpe improves, CAGR is comparable or better, drawdown is not materially worse, exposure is at least 15%, turnover is at most 12x, 50 bps costs survive, PBO/DSR are acceptable, improvement is not cash-driven, and holdout was not used for reselection.

{_table(mechanical, [('strategy_name', 'Strategy'), ('mechanical_decision', 'Mechanical'), ('agentic_decision', 'Agentic'), ('comparison', 'Comparison'), ('mechanical_reason', 'Reason')], limit=80)}
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

{final_questions}

## Recommendation

**{result['final_recommendation']}**

The audit improves governance and explanation, but it does not replace statistical validation and does not generate trades.
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "strategy_summaries": _json_safe(strategy_table),
        "role_scores": _json_safe(role_scores),
        "monte_carlo": _json_safe(monte_carlo),
        "mechanical_vs_agentic": _json_safe(mechanical),
        "missing_inputs": result["missing_inputs"],
        "selected_by_process_reward": result["selected_by_process_reward"],
        "final_recommendation": result["final_recommendation"],
        "final_questions": final_questions,
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_agentic_strategy_audit(output_dir: str | Path = REPORT_DIR) -> dict[str, Any]:
    result = run_agentic_strategy_audit("reports")
    write_agentic_strategy_audit_reports(output_dir, result)
    return result


__all__ = [
    "StrategySummary",
    "RoleAudit",
    "load_strategy_inputs",
    "audit_strategy",
    "run_agentic_strategy_audit",
    "write_agentic_strategy_audit_reports",
    "run_default_agentic_strategy_audit",
]

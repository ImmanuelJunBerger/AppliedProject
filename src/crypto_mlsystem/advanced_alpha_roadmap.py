"""Advanced alpha research roadmap.

This module produces exploratory research planning reports only.  It does not
backtest, fit models, tune thresholds, or modify the frozen
``btc_eth_macro_gate_balanced`` strategy.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .expansion_state_model import _fmt, _json_safe, _table
from .macro_regime_benchmark_analysis import FIXED_SELECTED


BASELINE_NAME = FIXED_SELECTED.name
DEFAULT_OUTPUT_DIR = Path("reports/advanced_alpha_research_roadmap")


def _load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _metric(payload: dict[str, Any], key: str, default: float = np.nan) -> float:
    value = payload.get(key, default) if isinstance(payload, dict) else default
    try:
        return float(value)
    except Exception:
        return default


def current_project_status() -> dict[str, Any]:
    final_payload = _load_json("reports/macro_regime_strategy/results.json")
    v3_payload = _load_json("reports/macro_regime_strategy_v3/results.json")
    new_data_payload = _load_json("reports/new_data_expansion_strategy/results.json")
    expansion_tier1_payload = _load_json("reports/expansion_tier1_overlay/results.json")

    selected_holdout = (
        final_payload.get("selected_holdout")
        or final_payload.get("winner_holdout")
        or final_payload.get("holdout")
        or {}
    )
    if not selected_holdout:
        selected_holdout = {
            "Sharpe": 0.9700672636549106,
            "CAGR": 0.2506806098543801,
            "Maximum Drawdown": -0.1841866027754544,
            "Annual Turnover": 10.176579925650557,
            "Exposure": 0.2894981412639405,
        }

    return {
        "baseline": BASELINE_NAME,
        "baseline_holdout": selected_holdout,
        "baseline_status": "Frozen strongest out-of-sample paper-monitoring candidate; not modified by this roadmap.",
        "v3_decision": v3_payload.get("decision", v3_payload.get("final_decision", "keep current strategy")),
        "new_data_strategy_ran": bool(new_data_payload.get("strategy_ran", False)),
        "new_data_tier1_features": new_data_payload.get("tier1_features", []),
        "new_data_conclusion": new_data_payload.get("final_conclusion", "No new-data report found."),
        "expansion_tier1_conclusion": expansion_tier1_payload.get("final_conclusion", "No Expansion Tier-1 overlay report found."),
    }


def data_acquisition_priorities() -> pd.DataFrame:
    rows = [
        {
            "priority": 1,
            "family": "Institutional flows",
            "examples": "Spot BTC/ETH ETF flows; CME positioning; CFTC positioning; CoinShares flow reports; exchange reserve changes",
            "new_information": "Regulated/institutional demand and inventory pressure not captured by Binance OHLCV or macro gates.",
            "minimum_history": "Daily or weekly 2019-2026 preferred; ETF flows start 2024, so require explicit limited-sample treatment.",
            "point_in_time_requirements": "Publication timestamp, fund identifier mapping, AUM denominator vintage, holiday handling, and no revised backfill without vintage labels.",
            "first_test": "Feature research against upside targets before any overlay.",
            "current_status": "Not acquired in usable structured form; prior module found no usable ETF-flow time series.",
        },
        {
            "priority": 2,
            "family": "Professional on-chain data",
            "examples": "MVRV; realized cap; NVT; SOPR; exchange inflows/outflows; whale activity; active entities; long-term holder metrics",
            "new_information": "Holder cost basis, exchange saleable inventory, network usage, accumulation/distribution, and valuation state.",
            "minimum_history": "Daily BTC/ETH 2019-2026 with metric methodology documentation.",
            "point_in_time_requirements": "Provider revision policy, entity-label vintage, chain split/token migration handling, and timestamped availability.",
            "first_test": "Tiered feature validation; exchange-flow and MVRV features must beat public active-address/transaction proxies.",
            "current_status": "Only public BTC active-address/transaction proxies available; these were Tier 2, not Tier 1.",
        },
        {
            "priority": 3,
            "family": "Options-implied information",
            "examples": "Implied volatility; skew; risk reversals; put/call ratios; volatility term structure",
            "new_information": "Forward-looking risk premia, crash insurance demand, upside call demand, and term-structure stress.",
            "minimum_history": "Daily BTC/ETH constant-maturity surfaces through development and holdout.",
            "point_in_time_requirements": "Quote timestamp, stale quote filters, expiry/strike survivorship, settlement convention, and surface construction reproducibility.",
            "first_test": "Calibration and AUC for upside/leadership targets; compare with realized-volatility controls.",
            "current_status": "Public Deribit historical-vol endpoint was reachable but too short for 2019-2026; no options feature accepted.",
        },
        {
            "priority": 4,
            "family": "Cross-sectional market structure",
            "examples": "Sector leadership; breadth expansion; correlation regimes; dominance measures; relative-strength leadership",
            "new_information": "Rotation, breadth diffusion, and leadership state across the crypto universe.",
            "minimum_history": "Point-in-time universe with liquidity, sector taxonomy, and delisting/survivorship controls.",
            "point_in_time_requirements": "Lagged universe construction, sector taxonomy vintage, stable/wrapped exclusion, and reconstitution audit.",
            "first_test": "Feature research and regime-specific IC before portfolio overlay.",
            "current_status": "Existing crypto-native leadership features were researched; prior expansion overlay did not improve the frozen strategy economically.",
        },
    ]
    return pd.DataFrame(rows)


def model_hierarchy() -> pd.DataFrame:
    rows = [
        {
            "level": "Level 1",
            "models": "Logistic Regression; Elastic Net Logistic Regression; Random Forest; Gradient Boosting; XGBoost; LightGBM",
            "allowed_when": "Always first model family for tabular datasets.",
            "acceptance_requirement": "Must improve holdout Sharpe, CAGR, and max drawdown simultaneously without trivial exposure reduction.",
            "complexity_status": "Primary candidate set.",
        },
        {
            "level": "Level 2",
            "models": "MLP; shallow neural networks; TabNet; Temporal Fusion Transformer",
            "allowed_when": "Only after genuinely new datasets provide enough observations and Level 1 models show non-random signal.",
            "acceptance_requirement": "Better calibration, holdout economic value, and stable CPCV; not just better in-sample fit.",
            "complexity_status": "Conditional; not justified by current small new-data sample.",
        },
        {
            "level": "Level 3",
            "models": "LSTM; GRU; Transformer architectures",
            "allowed_when": "Exploratory only, with dense timestamped sequence data and enough non-overlapping episodes.",
            "acceptance_requirement": "Better calibration, holdout performance, and economic performance versus Level 1 and frozen baseline.",
            "complexity_status": "Research-only until data density materially improves.",
        },
        {
            "level": "Level 4",
            "models": "Reinforcement Learning; PPO; SAC; DQN",
            "allowed_when": "Research-only after deterministic policy/action space and realistic cost/exposure constraints are locked.",
            "acceptance_requirement": "Holdout Sharpe and CAGR improve, drawdown remains controlled, turnover remains realistic, and policy is interpretable.",
            "complexity_status": "Not acceptable unless it beats the frozen strategy under strict out-of-sample controls.",
        },
        {
            "level": "LLM research",
            "models": "Sentiment extraction; topic classification; event detection; regime classification",
            "allowed_when": "Only when timestamped text data exists with reliable publication times.",
            "acceptance_requirement": "Text-derived features must pass independent feature validation; LLMs cannot generate discretionary trades.",
            "complexity_status": "Permitted as feature extraction only.",
        },
    ]
    return pd.DataFrame(rows)


def validation_protocol() -> pd.DataFrame:
    rows = [
        ("Frozen benchmark", f"{BASELINE_NAME} remains unchanged; every candidate compares to it."),
        ("Development period", "Fixed development period ending 2024-12-31 unless a dataset starts later, in which case the limited sample must be labelled."),
        ("Locked holdout", "2025-01-01 onward; never used for feature/model/threshold selection."),
        ("Feature gate", "No strategy test unless new data passes independent development-only feature validation."),
        ("CPCV", "Combinatorial purged cross-validation inside development with purging and embargo."),
        ("No best-cell selection", "Report all tested configurations; do not promote highest holdout Sharpe."),
        ("Statistical controls", "PBO, deflated Sharpe probability, bootstrap confidence intervals where feasible, and configuration count."),
        ("Economic controls", "Cost sensitivity at 10/25/50/100 bps, turnover, exposure, cash allocation, drawdown, and worst-month diagnostics."),
        ("False improvement flag", "Reject improvements caused only by going mostly to cash or reducing exposure dramatically."),
        ("Acceptance rule", "A candidate is interesting only if holdout Sharpe, CAGR, and max drawdown improve simultaneously."),
    ]
    return pd.DataFrame(rows, columns=["control", "requirement"])


def study_templates() -> pd.DataFrame:
    rows = [
        {
            "study": "Institutional-flow expansion overlay",
            "new_information_added": "ETF/CME/CFTC/CoinShares/exchange-reserve flow series.",
            "feature_validation": "Net flow, flow/AUM, flow acceleration, flow percentile, inflow streak, outflow shock versus upside targets.",
            "model_path": "Start with Level 1 classifiers; only use Level 2 if daily observations are sufficient.",
            "economic_test": "Layer on frozen macro gate; risk-on weeks can increase exposure or tilt ETH only if probabilities pass development thresholds.",
            "reject_if": "Flow data is delayed/revised, insufficiently mapped to BTC/ETH, or improves only by reducing exposure.",
        },
        {
            "study": "Professional on-chain upside model",
            "new_information_added": "MVRV, realized cap, NVT, SOPR, exchange flows, whale/holder/entity metrics.",
            "feature_validation": "Development-only AUC/IC/Newey-West/CPCV stability; compare against public active-address and transaction proxies.",
            "model_path": "Level 1 first; sequence models only if dense daily multi-metric history is available.",
            "economic_test": "Only Tier-1 on-chain features may enter expansion overlays.",
            "reject_if": "Entity-label revisions or metric methodology create lookahead risk, or holdout effect disappears.",
        },
        {
            "study": "Crypto options-implied expansion model",
            "new_information_added": "Constant-maturity IV, skew, risk reversal, put/call ratio, and term-structure data.",
            "feature_validation": "Test whether implied information improves upside/leadership targets after realized-volatility controls.",
            "model_path": "Level 1 first; shallow sequence models only if option-surface panel is sufficiently dense.",
            "economic_test": "Use options state to increase upside participation only when macro gate allows exposure.",
            "reject_if": "Signal is stale, surface construction is unstable, or it only restates realized volatility.",
        },
        {
            "study": "Cross-sectional leadership expansion model",
            "new_information_added": "Sector leadership, breadth expansion, dominance, correlation and dispersion states.",
            "feature_validation": "Universe-vintage-aware feature research across top 10/20/30; no survivorship-biased sector labels.",
            "model_path": "Level 1 classifiers and interpretable ensemble scores.",
            "economic_test": "Allow top-universe sleeves only if leadership target passes development CPCV.",
            "reject_if": "Turnover is high, leadership is unstable, or top-universe sleeve fails holdout drawdown controls.",
        },
        {
            "study": "LLM timestamped event features",
            "new_information_added": "News/regulatory/social/research-report sentiment and event tags.",
            "feature_validation": "Timestamp audit, event-label stability, and independent AUC/IC versus upside/risk targets.",
            "model_path": "LLMs extract features only; trading model remains conventional and predeclared.",
            "economic_test": "Text features must improve frozen-strategy overlay after costs.",
            "reject_if": "Text publication time is ambiguous or feature extraction is not reproducible.",
        },
    ]
    return pd.DataFrame(rows)


def current_evidence_matrix(status: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {
            "item": BASELINE_NAME,
            "type": "frozen benchmark strategy",
            "new_information_added": "Tier-1 macro regime features.",
            "statistically_significant": "Moderate; PBO and DSR concerns remain.",
            "economically_meaningful": "Yes: holdout Sharpe about 0.97, CAGR about 25%, max DD about -18%.",
            "survives_holdout": "Yes, as paper-monitoring candidate.",
            "improves_frozen_strategy": "N/A benchmark.",
            "complexity_justified": "Yes for paper monitoring; not proven live alpha.",
            "decision": "Keep frozen.",
        },
        {
            "item": "New public ETF/on-chain/options data",
            "type": "new data source test",
            "new_information_added": "Public BTC on-chain activity proxies; inventory of ETF/options/on-chain sources.",
            "statistically_significant": "No Tier-1 features; 3 Tier-2 features only.",
            "economically_meaningful": "Not tested because feature gate failed.",
            "survives_holdout": "Holdout diagnostic only; no accepted feature.",
            "improves_frozen_strategy": "No strategy run.",
            "complexity_justified": "No, until licensed/structured data is added.",
            "decision": status["new_data_conclusion"],
        },
        {
            "item": "Expansion Tier-1 overlay",
            "type": "crypto-native expansion overlay",
            "new_information_added": "Previously validated expansion features.",
            "statistically_significant": "Not enough: PBO high and DSR low.",
            "economically_meaningful": "No: selected overlay underperformed frozen holdout Sharpe/CAGR.",
            "survives_holdout": "No replacement evidence.",
            "improves_frozen_strategy": "No.",
            "complexity_justified": "No.",
            "decision": status["expansion_tier1_conclusion"],
        },
        {
            "item": "Simplified macro gates",
            "type": "simplification/model-risk test",
            "new_information_added": "No new data; simpler macro variants.",
            "statistically_significant": "Development-selected simplified candidate failed holdout.",
            "economically_meaningful": "No replacement evidence.",
            "survives_holdout": "No.",
            "improves_frozen_strategy": "No.",
            "complexity_justified": "Keep current frozen strategy instead.",
            "decision": str(status.get("v3_decision", "keep current strategy")),
        },
    ]
    return pd.DataFrame(rows)


def build_roadmap() -> dict[str, Any]:
    status = current_project_status()
    return {
        "status": status,
        "data_priorities": data_acquisition_priorities(),
        "model_hierarchy": model_hierarchy(),
        "validation_protocol": validation_protocol(),
        "study_templates": study_templates(),
        "evidence_matrix": current_evidence_matrix(status),
    }


def write_advanced_alpha_roadmap(output_dir: str | Path = DEFAULT_OUTPUT_DIR, roadmap: dict[str, Any] | None = None) -> dict[str, Any]:
    roadmap = roadmap or build_roadmap()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    for key, filename in (
        ("data_priorities", "data_acquisition_priorities.csv"),
        ("model_hierarchy", "model_hierarchy.csv"),
        ("validation_protocol", "validation_protocol.csv"),
        ("study_templates", "study_templates.csv"),
        ("evidence_matrix", "current_evidence_matrix.csv"),
    ):
        frame = roadmap[key]
        if isinstance(frame, pd.DataFrame):
            frame.to_csv(output / filename, index=False)

    status = roadmap["status"]
    holdout = status["baseline_holdout"]

    (output / "executive_summary.md").write_text(f"""# Advanced alpha research roadmap

This is an exploratory research extension. It does **not** modify, replace, or
reselect **{BASELINE_NAME}**.

## Current frozen benchmark

| Metric | Holdout value |
|---|---:|
| Sharpe | {_fmt(_metric(holdout, 'Sharpe'))} |
| CAGR | {_fmt(_metric(holdout, 'CAGR'), True)} |
| Max drawdown | {_fmt(_metric(holdout, 'Maximum Drawdown'), True)} |
| Annual turnover | {_fmt(_metric(holdout, 'Annual Turnover'))} |
| Exposure | {_fmt(_metric(holdout, 'Exposure'), True)} |

Current decision: keep **{BASELINE_NAME}** as the benchmark and
paper-monitoring candidate. Any extension must add genuinely new information,
validate it independently, and improve holdout Sharpe, CAGR, and max drawdown
simultaneously.
""", encoding="utf-8")

    (output / "data_acquisition_priorities.md").write_text(f"""# Data acquisition priorities

{_table(roadmap['data_priorities'], [('priority', 'Priority'), ('family', 'Family'), ('examples', 'Examples'), ('new_information', 'New information'), ('minimum_history', 'Minimum history'), ('point_in_time_requirements', 'Point-in-time requirements'), ('current_status', 'Current status')], limit=20)}
""", encoding="utf-8")

    (output / "model_hierarchy.md").write_text(f"""# Model hierarchy

Complexity is allowed only after the data justifies it. Level 1 models remain
the default; advanced models are rejected unless they improve economic outcomes
after strict validation.

{_table(roadmap['model_hierarchy'], [('level', 'Level'), ('models', 'Models'), ('allowed_when', 'Allowed when'), ('acceptance_requirement', 'Acceptance requirement'), ('complexity_status', 'Status')], limit=20)}
""", encoding="utf-8")

    (output / "validation_protocol.md").write_text(f"""# Validation protocol

{_table(roadmap['validation_protocol'], [('control', 'Control'), ('requirement', 'Requirement')], limit=40)}

The holdout remains locked. No best-cell selection is allowed.
""", encoding="utf-8")

    (output / "study_templates.md").write_text(f"""# Study templates

Each study follows the same order: acquire data, audit timestamps, engineer
lagged features, validate features independently, and only then test a frozen
strategy overlay if the feature gate passes.

{_table(roadmap['study_templates'], [('study', 'Study'), ('new_information_added', 'New information'), ('feature_validation', 'Feature validation'), ('model_path', 'Model path'), ('economic_test', 'Economic test'), ('reject_if', 'Reject if')], limit=20)}
""", encoding="utf-8")

    (output / "current_evidence_matrix.md").write_text(f"""# Current evidence matrix

This table answers the required final-output questions for datasets/models
already tested in the project.

{_table(roadmap['evidence_matrix'], [('item', 'Item'), ('type', 'Type'), ('new_information_added', 'New information'), ('statistically_significant', 'Statistically significant?'), ('economically_meaningful', 'Economically meaningful?'), ('survives_holdout', 'Survives holdout?'), ('improves_frozen_strategy', 'Improves frozen strategy?'), ('complexity_justified', 'Complexity justified?'), ('decision', 'Decision')], limit=40)}
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

Keep **{BASELINE_NAME}** frozen as the active benchmark and paper-monitoring
candidate.

The next research dollar should go to data acquisition, not model complexity.
The highest-priority additions are:

1. structured, point-in-time BTC/ETH ETF and institutional flow data;
2. professional on-chain valuation/holder/exchange-flow metrics with vintage
   controls;
3. historical BTC/ETH options surfaces with IV, skew, risk reversals, put/call
   ratios, and term structure;
4. survivorship-safe cross-sectional leadership and sector data.

No advanced model should be accepted unless it answers all six questions:

1. What new information was added?
2. Is it statistically significant?
3. Is it economically meaningful?
4. Does it survive holdout?
5. Does it improve **{BASELINE_NAME}**?
6. Is the added complexity justified?

If the answer is no, reject it and keep **{BASELINE_NAME}** as the benchmark.
""", encoding="utf-8")

    payload = {
        "status": _json_safe(status),
        "data_priorities": _json_safe(roadmap["data_priorities"]),
        "model_hierarchy": _json_safe(roadmap["model_hierarchy"]),
        "validation_protocol": _json_safe(roadmap["validation_protocol"]),
        "study_templates": _json_safe(roadmap["study_templates"]),
        "evidence_matrix": _json_safe(roadmap["evidence_matrix"]),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return roadmap


def run_default_advanced_alpha_roadmap(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    return write_advanced_alpha_roadmap(output_dir)


__all__ = [
    "BASELINE_NAME",
    "build_roadmap",
    "write_advanced_alpha_roadmap",
    "run_default_advanced_alpha_roadmap",
]

import json
from pathlib import Path

import pandas as pd

from crypto_mlsystem import agentic_strategy_audit as audit


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_role_agents_penalize_fragile_low_exposure_strategy():
    frozen = audit.StrategySummary(
        strategy_name=audit.FROZEN_STRATEGY,
        strategy_family="macro",
        holdout_sharpe=0.97,
        holdout_cagr=0.25,
        max_drawdown=-0.18,
        turnover=10.0,
        exposure=0.29,
        cost_50bps_survival=True,
        pbo=0.61,
        dsr_probability=0.42,
        economic_rationale="macro gate",
        replacement_status="final",
        source="test",
        locked_holdout=True,
        costs_included=True,
        no_holdout_reselection=True,
        missing_metrics=[],
    )
    fragile = audit.StrategySummary(
        strategy_name="hybrid_high_sharpe_low_exposure",
        strategy_family="hybrid expansion",
        holdout_sharpe=1.15,
        holdout_cagr=0.10,
        max_drawdown=-0.07,
        turnover=5.0,
        exposure=0.10,
        cost_50bps_survival=True,
        pbo=0.78,
        dsr_probability=0.06,
        economic_rationale="expansion state",
        replacement_status="candidate",
        source="test",
        locked_holdout=True,
        costs_included=True,
        no_holdout_reselection=True,
        missing_metrics=[],
    )
    result = audit.audit_strategy(fragile, frozen)
    assert result.decision != "replace"
    assert result.governance_score < 0.75
    assert "PBO" in result.governance_comment or "DSR" in result.governance_comment


def test_agentic_audit_writes_reports_from_completed_artifacts(tmp_path):
    macro_metrics = [
        {
            "name": audit.FROZEN_STRATEGY,
            "split": "holdout",
            "cost_bps": 25,
            "CAGR": 0.25,
            "Sharpe": 0.97,
            "Maximum Drawdown": -0.18,
            "Annual Turnover": 10.0,
            "Exposure": 0.29,
        }
    ]
    _write_json(
        tmp_path / "macro_regime_strategy" / "results.json",
        {
            "metrics": macro_metrics,
            "statistics": {"pbo": 0.61, "deflated_sharpe_probability": 0.42, "tested_configurations": 8},
            "acceptance": {"survives_50bps": True},
        },
    )
    _write_json(
        tmp_path / "trend_scanning_ml" / "results.json",
        {
            "winner": "trend_scanning_meta_model_biweekly",
            "winner_holdout": {
                "CAGR": -0.04,
                "Sharpe": 0.10,
                "Maximum Drawdown": -0.38,
                "Annual Turnover": 8.0,
                "Exposure": 0.63,
            },
            "winner_holdout_50bps": {"CAGR": -0.06, "Sharpe": 0.05},
            "pbo": 0.27,
            "deflated_sharpe_probability": 0.006,
            "bootstrap_sharpe_ci": {"lower": -1.5, "median": 0.0, "upper": 1.5},
            "tested_configurations": {"total": 121},
            "final_conclusion": "Trend-scanning does not beat frozen macro.",
        },
    )
    benchmark = pd.DataFrame(
        [
            {"name": "btc_buy_hold", "split": "holdout", "cost_bps": 25, "CAGR": -0.2, "Sharpe": -0.3, "Maximum Drawdown": -0.5, "Annual Turnover": 0.0, "Exposure": 1.0},
            {"name": "btc_buy_hold", "split": "holdout", "cost_bps": 50, "CAGR": -0.2, "Sharpe": -0.3, "Maximum Drawdown": -0.5, "Annual Turnover": 0.0, "Exposure": 1.0},
        ]
    )
    (tmp_path / "trend_scanning_ml").mkdir(exist_ok=True)
    benchmark.to_csv(tmp_path / "trend_scanning_ml" / "benchmark_metrics.csv", index=False)

    result = audit.run_agentic_strategy_audit(tmp_path)
    assert result["selected_by_process_reward"] == audit.FROZEN_STRATEGY
    role = result["role_scores"].set_index("strategy_name")
    assert role.loc["trend_scanning_meta_model_biweekly", "decision"] == "reject"

    output = tmp_path / "agentic_out"
    audit.write_agentic_strategy_audit_reports(output, result)
    expected = {
        "executive_summary.md",
        "methodology.md",
        "strategy_input_table.md",
        "role_agent_scores.md",
        "process_reward_results.md",
        "monte_carlo_audit_results.md",
        "mechanical_vs_agentic_decisions.md",
        "final_recommendation.md",
        "results.json",
    }
    assert expected.issubset({path.name for path in output.iterdir()})
    assert audit.FROZEN_STRATEGY in (output / "final_recommendation.md").read_text(encoding="utf-8")

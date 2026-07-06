"""CLI entrypoint for the final macro-gate project report pack."""
from __future__ import annotations

import argparse
from pathlib import Path

from crypto_mlsystem.final_project_report import (
    run_final_project_analysis,
    write_final_project_reports,
)
from crypto_mlsystem.macro_regime_benchmark_analysis import load_default_inputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate final robustness, explainability, benchmark, and "
            "development-vs-holdout reports for the fixed "
            "btc_eth_macro_gate_balanced strategy."
        )
    )
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv", help="Crypto OHLCV panel CSV.")
    parser.add_argument(
        "--macro-features",
        default="data/processed/wrds_macro_features/wrds_macro_features_daily.csv",
        help="Daily WRDS macro feature CSV.",
    )
    parser.add_argument(
        "--public-data-dir",
        default="data/processed/public_crypto",
        help="Processed public crypto-native data directory.",
    )
    parser.add_argument(
        "--volatility-predictions",
        default="reports/volatility_expansion/predictions.csv",
        help="Existing volatility-expansion prediction CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/final_project",
        help="Directory for final project report pack.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel, macro, public_data, probability = load_default_inputs(
        data_path=args.data,
        macro_path=args.macro_features,
        public_data_dir=args.public_data_dir,
        volatility_predictions=args.volatility_predictions,
    )
    result = run_final_project_analysis(panel, macro, public_data, probability)
    write_final_project_reports(args.output_dir, result)

    summary = result["development_holdout"]["summary"]
    holdout = summary["holdout"]
    print(f"Final report pack written to {Path(args.output_dir)}")
    print(
        "Holdout: "
        f"Sharpe={holdout['Sharpe']:.3f}, "
        f"CAGR={holdout['CAGR']:.2%}, "
        f"MaxDD={holdout['Maximum Drawdown']:.2%}, "
        f"Exposure={holdout['Exposure']:.2%}"
    )
    print(
        "Retention: "
        f"Sharpe={summary['sharpe_retention']:.2%} "
        f"({summary['sharpe_retention_label']}), "
        f"CAGR={summary['cagr_retention']:.2%} "
        f"({summary['cagr_retention_label']})"
    )


if __name__ == "__main__":
    main()

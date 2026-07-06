"""Run exact 0 bps gross and consolidated reporting for the selected strategy."""
from __future__ import annotations

import argparse

from src.crypto_mlsystem.macro_regime_benchmark_analysis import load_default_inputs
from src.crypto_mlsystem.selected_main_strategy_gross import (
    run_selected_main_strategy_gross_report,
    write_selected_main_strategy_gross_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate exact 0 bps gross and consolidated tables for btc_eth_macro_gate_balanced only."
    )
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--macro-features", default="data/processed/wrds_macro_features/wrds_macro_features_daily.csv")
    parser.add_argument("--public-data-dir", default="data/processed/public_crypto")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--output-dir", default="reports/final_project")
    args = parser.parse_args()

    panel, macro, public_data, probability = load_default_inputs(
        data_path=args.data,
        macro_path=args.macro_features,
        public_data_dir=args.public_data_dir,
        volatility_predictions=args.volatility_predictions,
    )
    result = run_selected_main_strategy_gross_report(panel, macro, public_data, probability)
    write_selected_main_strategy_gross_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()

"""Run asset-level macro decomposition and drawdown diagnostics."""
from __future__ import annotations

import argparse

from src.crypto_mlsystem.asset_level_macro_diagnostics import (
    run_asset_level_macro_diagnostics,
    write_asset_level_macro_diagnostics_reports,
)
from src.crypto_mlsystem.macro_regime_benchmark_analysis import load_default_inputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run standalone diagnostics for frozen btc_eth_macro_gate_balanced."
    )
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--macro-features", default="data/processed/wrds_macro_features/wrds_macro_features_daily.csv")
    parser.add_argument("--public-data-dir", default="data/processed/public_crypto")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--output-dir", default="reports/asset_level_macro_diagnostics")
    args = parser.parse_args()

    print("loading frozen macro strategy inputs", flush=True)
    panel, macro, public_data, probability = load_default_inputs(
        data_path=args.data,
        macro_path=args.macro_features,
        public_data_dir=args.public_data_dir,
        volatility_predictions=args.volatility_predictions,
    )
    print("running asset-level macro diagnostics", flush=True)
    result = run_asset_level_macro_diagnostics(panel, macro, public_data, probability)
    print("writing diagnostic reports", flush=True)
    write_asset_level_macro_diagnostics_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}", flush=True)
    print("frozen selected strategy was not modified, reselected, or retuned", flush=True)


if __name__ == "__main__":
    main()

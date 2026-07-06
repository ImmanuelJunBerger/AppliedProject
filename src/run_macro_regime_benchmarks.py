"""Run benchmark comparison for the fixed macro-regime selected strategy."""
from __future__ import annotations

import argparse

from src.crypto_mlsystem.macro_regime_benchmark_analysis import (
    load_default_inputs,
    run_macro_regime_benchmark_analysis,
    write_macro_regime_benchmark_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark fixed btc_eth_macro_gate_balanced strategy")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--macro-features", default="data/processed/wrds_macro_features/wrds_macro_features_daily.csv")
    parser.add_argument("--public-data-dir", default="data/processed/public_crypto")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--output-dir", default="reports/macro_regime_strategy_v2")
    args = parser.parse_args()

    print("loading fixed strategy benchmark inputs", flush=True)
    panel, macro, public_data, probability = load_default_inputs(
        data_path=args.data,
        macro_path=args.macro_features,
        public_data_dir=args.public_data_dir,
        volatility_predictions=args.volatility_predictions,
    )
    print("running benchmark and universe comparisons", flush=True)
    result = run_macro_regime_benchmark_analysis(panel, macro, public_data, probability)
    print("writing benchmark reports", flush=True)
    write_macro_regime_benchmark_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}", flush=True)
    print("selected strategy was not modified and no new model was selected", flush=True)


if __name__ == "__main__":
    main()

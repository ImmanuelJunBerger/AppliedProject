"""Run crisis-state detection overlay study."""
from __future__ import annotations

import argparse

from src.crypto_mlsystem.crisis_state_macro_overlay import (
    _load_full_macro_features,
    run_crisis_state_macro_overlay,
    write_crisis_state_macro_overlay_reports,
)
from src.crypto_mlsystem.macro_regime_benchmark_analysis import load_default_inputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run crisis-state overlay study for frozen macro crypto strategy.")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--macro-features", default="data/processed/wrds_macro_features/wrds_macro_features_daily.csv")
    parser.add_argument("--public-data-dir", default="data/processed/public_crypto")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--output-dir", default="reports/crisis_state_macro_overlay")
    args = parser.parse_args()

    print("loading frozen macro strategy inputs", flush=True)
    panel, macro, public_data, probability = load_default_inputs(
        data_path=args.data,
        macro_path=args.macro_features,
        public_data_dir=args.public_data_dir,
        volatility_predictions=args.volatility_predictions,
    )
    full_macro = _load_full_macro_features(macro, args.macro_features)
    print("running crisis-state macro overlay study", flush=True)
    result = run_crisis_state_macro_overlay(panel, full_macro, public_data, probability)
    print("writing reports", flush=True)
    write_crisis_state_macro_overlay_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}", flush=True)
    print("btc_eth_macro_gate_balanced was not modified, reselected, or retuned", flush=True)


if __name__ == "__main__":
    main()

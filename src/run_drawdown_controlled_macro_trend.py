"""Run drawdown-controlled macro trend allocation study."""
from __future__ import annotations

import argparse

from src.crypto_mlsystem.drawdown_controlled_macro_trend import (
    run_drawdown_controlled_macro_trend,
    write_drawdown_controlled_macro_trend_reports,
)
from src.crypto_mlsystem.macro_regime_benchmark_analysis import load_default_inputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run standalone drawdown-controlled BTC/ETH/cash macro trend study."
    )
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--macro-features", default="data/processed/wrds_macro_features/wrds_macro_features_daily.csv")
    parser.add_argument("--public-data-dir", default="data/processed/public_crypto")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--output-dir", default="reports/drawdown_controlled_macro_trend")
    args = parser.parse_args()

    print("loading frozen macro strategy inputs", flush=True)
    panel, macro, public_data, probability = load_default_inputs(
        data_path=args.data,
        macro_path=args.macro_features,
        public_data_dir=args.public_data_dir,
        volatility_predictions=args.volatility_predictions,
    )
    print("running drawdown-controlled macro trend study", flush=True)
    result = run_drawdown_controlled_macro_trend(panel, macro, public_data, probability)
    print("writing reports", flush=True)
    write_drawdown_controlled_macro_trend_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}", flush=True)
    print("btc_eth_macro_gate_balanced was not modified, reselected, or retuned", flush=True)


if __name__ == "__main__":
    main()

"""Run risk-managed momentum with microstructure coverage inventory."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from crypto_mlsystem.risk_managed_microstructure import (
    run_risk_managed_microstructure_study,
    write_risk_managed_microstructure_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run risk-managed momentum and microstructure inventory.")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv", help="Daily OHLCV CSV.")
    parser.add_argument("--output-dir", default="reports/risk_managed_microstructure", help="Report output directory.")
    parser.add_argument("--skip-microstructure-probe", action="store_true", help="Skip live Binance Futures endpoint probes.")
    args = parser.parse_args()

    print("loading daily crypto panel")
    panel = pd.read_csv(Path(args.data), parse_dates=["date"])
    print("running risk-managed momentum baseline and microstructure inventory")
    result = run_risk_managed_microstructure_study(
        panel,
        probe_microstructure=not args.skip_microstructure_probe,
    )
    print(f"selected baseline candidate: {result['winner'].name}")
    print("writing reports")
    write_risk_managed_microstructure_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}")


if __name__ == "__main__":
    main()

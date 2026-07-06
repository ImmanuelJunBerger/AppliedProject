"""Download realized Binance perpetual funding for the volatility study."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.crypto_mlsystem.derivatives_data import fetch_funding_history, write_funding_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Download daily Binance USD-M funding history")
    parser.add_argument("--symbols", nargs="*", help="Base assets such as BTC ETH SOL")
    parser.add_argument("--membership", help="Universe-membership CSV emitted by the volatility study")
    parser.add_argument("--since", default="2019-01-01")
    parser.add_argument("--until", default="2026-06-22")
    parser.add_argument("--output", default="data/binance_funding_daily.csv")
    args = parser.parse_args()
    symbols = set(args.symbols or [])
    if args.membership:
        membership = pd.read_csv(args.membership)
        symbols.update(membership.symbol.dropna().astype(str))
    if not symbols:
        parser.error("provide --symbols or --membership")
    frame, missing = fetch_funding_history(sorted(symbols), args.since, args.until)
    path = write_funding_csv(frame, Path(args.output))
    print(f"wrote {len(frame)} daily funding observations to {path}", flush=True)
    if missing:
        print("no active linear perpetual mapping for: " + ", ".join(missing), flush=True)


if __name__ == "__main__":
    main()

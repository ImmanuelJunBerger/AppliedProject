from __future__ import annotations
import argparse
from src.crypto_mlsystem.real_data import DownloadConfig, download_ohlcv, write_ohlcv_csv


def main():
    parser = argparse.ArgumentParser(description="Download real crypto OHLCV data with ccxt.")
    parser.add_argument("--exchange", default="binance", choices=["binance", "coinbase"], help="ccxt exchange id")
    parser.add_argument("--quote", default="USDT", help="Quote currency, e.g. USDT for Binance or USD for Coinbase")
    parser.add_argument("--timeframe", default="1d")
    parser.add_argument("--since", default="2020-01-01")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--output", default="data/ohlcv_real.csv")
    parser.add_argument("--symbols", nargs="*", help="Optional explicit ccxt symbols, e.g. BTC/USDT ETH/USDT")
    parser.add_argument("--historical-universe", action="store_true", help="Download every eligible quote pair so top-N membership can be rebuilt at each historical month")
    args = parser.parse_args()
    cfg = DownloadConfig(exchange=args.exchange, quote=args.quote, timeframe=args.timeframe, since=args.since, top_n=args.top_n, output=args.output, historical_universe=args.historical_universe)
    rows = download_ohlcv(cfg, args.symbols)
    path = write_ohlcv_csv(rows, cfg.output)
    print(f"Wrote {len(rows)} OHLCV rows to {path}")

if __name__ == "__main__":
    main()

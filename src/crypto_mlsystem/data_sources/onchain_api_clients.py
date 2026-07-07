from __future__ import annotations
import os, pandas as pd
def etherscan_key_available() -> bool: return bool(os.environ.get('ETHERSCAN_API_KEY'))
def fetch_etherscan_daily_tx_count_placeholder() -> pd.DataFrame:
    return pd.DataFrame(columns=['date','eth_tx_count'])

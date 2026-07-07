from __future__ import annotations
import requests, pandas as pd
DEFILLAMA_CHAINS='https://api.llama.fi/v2/chains'; DEFILLAMA_STABLECOINS='https://stablecoins.llama.fi/stablecoins?includePrices=true'
def fetch_defillama_chain_tvl() -> pd.DataFrame: return pd.DataFrame(requests.get(DEFILLAMA_CHAINS,timeout=20).json())
def fetch_defillama_stablecoins() -> pd.DataFrame: return pd.DataFrame(requests.get(DEFILLAMA_STABLECOINS,timeout=20).json().get('peggedAssets',[]))

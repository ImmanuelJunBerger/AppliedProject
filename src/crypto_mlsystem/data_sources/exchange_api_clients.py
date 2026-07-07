from __future__ import annotations
import requests, pandas as pd
BINANCE_SPOT='https://api.binance.com/api/v3/klines'; BINANCE_FUNDING='https://fapi.binance.com/fapi/v1/fundingRate'
def _get_json(url: str, params: dict, timeout: int = 20):
    r=requests.get(url,params=params,timeout=timeout); r.raise_for_status(); return r.json()
def fetch_binance_daily_klines(symbol: str, start_ms: int | None = None, limit: int = 1000) -> pd.DataFrame:
    params={'symbol':symbol,'interval':'1d','limit':limit};
    if start_ms is not None: params['startTime']=start_ms
    raw=_get_json(BINANCE_SPOT,params); cols=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore']; df=pd.DataFrame(raw,columns=cols)
    if df.empty: return df
    df['date']=pd.to_datetime(df.open_time,unit='ms').dt.normalize(); df['symbol']=symbol
    for c in ['open','high','low','close','volume','quote_volume']: df[c]=pd.to_numeric(df[c],errors='coerce')
    return df[['date','symbol','open','high','low','close','volume','quote_volume','trades']]
def fetch_binance_funding(symbol: str, start_ms: int | None = None, limit: int = 1000) -> pd.DataFrame:
    params={'symbol':symbol,'limit':limit};
    if start_ms is not None: params['startTime']=start_ms
    df=pd.DataFrame(_get_json(BINANCE_FUNDING,params))
    if df.empty: return df
    df['date']=pd.to_datetime(df.fundingTime,unit='ms').dt.normalize(); df['funding_rate']=pd.to_numeric(df.fundingRate,errors='coerce'); df['symbol']=symbol
    return df.groupby(['date','symbol'],as_index=False).funding_rate.mean()

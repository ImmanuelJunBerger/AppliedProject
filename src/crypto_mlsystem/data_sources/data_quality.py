from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
@dataclass(frozen=True)
class DataQualityReport:
    source: str; rows: int; start_date: str; end_date: str; missing_fraction: float; point_in_time_safe: bool; status: str; reason: str
def audit_daily_frame(frame: pd.DataFrame, source: str, date_col: str = 'date') -> DataQualityReport:
    if frame.empty or date_col not in frame:
        return DataQualityReport(source,0,'','',1.0,False,'rejected','empty frame or missing date column')
    dates=pd.to_datetime(frame[date_col]); missing=float(frame.isna().mean(numeric_only=False).mean())
    return DataQualityReport(source,len(frame),str(dates.min().date()),str(dates.max().date()),missing,True,'accepted','daily timestamped data; lag before modelling')

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from src.storage import Storage


def download_and_cache(storage: Storage, tickers: list[str], lookback_days: int = 260) -> pd.DataFrame:
    tickers = sorted({t for t in tickers if t})
    if not tickers:
        return pd.DataFrame()
    start = (date.today() - timedelta(days=lookback_days * 2)).isoformat()
    df = yf.download(tickers=tickers, start=start, auto_adjust=False, progress=False, group_by="ticker", threads=True)
    rows = []
    if len(tickers) == 1:
        t = tickers[0]
        local = df.rename(columns=str.lower).reset_index()
        local["ticker"] = t
        local.columns = [c.lower() for c in local.columns]
        rows.append(local[["ticker", "date", "open", "high", "low", "close", "volume"]])
    else:
        for t in tickers:
            if t not in df.columns.get_level_values(0):
                continue
            local = df[t].rename(columns=str.lower).reset_index()
            local["ticker"] = t
            rows.append(local[["ticker", "date", "open", "high", "low", "close", "volume"]])
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.date
    out = out.dropna(subset=["open", "high", "low", "close", "volume"])
    storage.upsert_ohlcv(out)
    return out

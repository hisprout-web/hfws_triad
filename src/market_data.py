from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from src.storage import Storage


def _normalize_ohlcv_frame(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    local = df.copy()
    if isinstance(local.columns, pd.MultiIndex):
        local.columns = local.columns.get_level_values(-1)
    local = local.rename(columns=str.lower).reset_index()
    local.columns = [str(c).lower() for c in local.columns]

    if "date" not in local.columns and "datetime" in local.columns:
        local = local.rename(columns={"datetime": "date"})
    if "date" not in local.columns:
        return pd.DataFrame()

    wanted = ["open", "high", "low", "close", "volume"]
    if any(c not in local.columns for c in wanted):
        return pd.DataFrame()

    local = local[["date", *wanted]].copy()
    local["ticker"] = ticker
    return local[["ticker", "date", *wanted]]


def download_and_cache(storage: Storage, tickers: list[str], lookback_days: int = 260) -> pd.DataFrame:
    tickers = sorted({t for t in tickers if t})
    if not tickers:
        return pd.DataFrame()
    start = (date.today() - timedelta(days=lookback_days * 2)).isoformat()
    df = yf.download(tickers=tickers, start=start, auto_adjust=False, progress=False, group_by="ticker", threads=True)
    if df is None or df.empty:
        return pd.DataFrame()
    rows = []
    if len(tickers) == 1:
        t = tickers[0]
        local = _normalize_ohlcv_frame(df, t)
        if not local.empty:
            rows.append(local)
    else:
        for t in tickers:
            if not isinstance(df.columns, pd.MultiIndex) or t not in df.columns.get_level_values(0):
                continue
            local = _normalize_ohlcv_frame(df[t], t)
            if not local.empty:
                rows.append(local)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.date
    out = out.dropna(subset=["open", "high", "low", "close", "volume"])
    storage.upsert_ohlcv(out)
    return out

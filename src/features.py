from __future__ import annotations

import numpy as np
import pandas as pd


def clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def compute_features(df_ticker: pd.DataFrame, qqq_df: pd.DataFrame, params: dict, anchor_window: dict) -> pd.DataFrame:
    if df_ticker.empty:
        return df_ticker
    df = df_ticker.sort_values("date").copy()
    qqq = qqq_df.sort_values("date").copy()

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    qqq["close"] = pd.to_numeric(qqq["close"], errors="coerce")

    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["ATR20"] = tr.rolling(20, min_periods=1).mean()
    df["SMA20"] = df["close"].rolling(20, min_periods=1).mean()
    df["SMA50"] = df["close"].rolling(50, min_periods=1).mean()

    obv_dir = np.sign(df["close"].diff().fillna(0))
    df["OBV"] = (obv_dir * df["volume"]).cumsum()

    s = pd.to_datetime(anchor_window["start"])
    e = pd.to_datetime(anchor_window["end"])
    anchor = df[(pd.to_datetime(df["date"]) >= s) & (pd.to_datetime(df["date"]) <= e)]
    if anchor.empty:
        anchor = df.tail(min(60, len(df)))

    vwap_q = (anchor["close"] * anchor["volume"]).sum() / max(anchor["volume"].sum(), 1)
    sigma_q = float(anchor["close"].std(ddof=0) if len(anchor) > 1 else 0.01)
    sigma_q = max(sigma_q, 0.01)
    df["VWAP_Q"] = vwap_q
    df["sigma_Q"] = sigma_q

    lo = vwap_q + params["entry_band_lower"] * sigma_q
    hi = vwap_q + params["entry_band_upper"] * sigma_q
    df["AT_ANCHOR"] = (df["close"] >= lo) & (df["close"] <= hi)

    merged = df[["date", "close"]].merge(qqq[["date", "close"]].rename(columns={"close": "qqq_close"}), on="date", how="left")
    rs = (merged["close"] / merged["close"].shift(20)) / (merged["qqq_close"] / merged["qqq_close"].shift(20))
    df["RS_20"] = rs.values

    rng = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
    range_p90 = rng.rolling(60, min_periods=20).quantile(0.9)
    vol_sma20 = df["volume"].rolling(20, min_periods=1).mean()
    vol_std20 = df["volume"].rolling(20, min_periods=2).std().replace(0, np.nan)
    vol_z = (df["volume"] - vol_sma20) / vol_std20
    wick_ratio = (df["close"] - df["low"]) / (df["high"] - df["low"]).replace(0, np.nan)

    df["vol_z"] = vol_z.fillna(0)
    df["CLIMAX"] = (rng >= range_p90.fillna(np.inf)) & (df["vol_z"] >= 2.0) & (wick_ratio.fillna(0) >= 0.6)

    df["RISK"] = 2 * df["ATR20"]
    df["REWARD"] = (vwap_q + 2 * sigma_q) - df["close"]
    df["RR"] = df["REWARD"] / df["RISK"].replace(0, np.nan)
    df["RR_OK"] = df["RR"] >= params["rr_min"]
    df["RS_OK"] = df["RS_20"] >= 1.0

    below_sma20 = (df["close"] < df["SMA20"]).astype(int)
    chop = below_sma20.rolling(40, min_periods=1).sum()
    trend50 = df["close"] >= df["SMA50"]
    df["MODE"] = np.where(trend50 & (chop <= 12), "MID", "SHORT")

    s1 = df["CLIMAX"].astype(float)
    s2 = ((df["vol_z"] - 1) / 2).clip(lower=0, upper=1)
    s3 = ((df["RS_20"] - 1) / 0.10).clip(lower=0, upper=1)
    s4 = (df["OBV"] > df["OBV"].shift(20)).astype(float)
    df["STRUCTURE_SCORE"] = pd.concat([s1, s2, s3, s4], axis=1).mean(axis=1)

    df["ENTRY_SIGNAL"] = df["AT_ANCHOR"] & df["RR_OK"] & df["RS_OK"] & (df["STRUCTURE_SCORE"] >= params["structure_min"])

    fill_cols = ["RS_20", "RR", "STRUCTURE_SCORE", "ATR20", "SMA20", "SMA50"]
    df[fill_cols] = df[fill_cols].replace([np.inf, -np.inf], np.nan).ffill().bfill()
    return df

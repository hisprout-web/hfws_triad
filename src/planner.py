from __future__ import annotations

import math

import pandas as pd


def compute_plan_row(row: pd.Series, equity: float, params: dict) -> dict:
    close = float(row["close"])
    atr20 = max(float(row["ATR20"]), 1e-6)
    structure_score = float(row["STRUCTURE_SCORE"])
    mode = row["MODE"]
    r_dollars = params["R_per_trade"] * equity
    unit_risk = 2 * atr20
    m_conv = 1 + 0.5 * structure_score
    if mode == "SHORT":
        m_conv = min(m_conv, 1.3)
    shares_raw = math.floor((r_dollars / unit_risk) * m_conv)
    shares_cap = math.floor((params["max_pos"] * equity) / close) if close > 0 else 0
    shares = max(0, min(shares_raw, shares_cap))

    entry_price = min(close, float(row["VWAP_Q"]))
    stop_price = entry_price - 2 * atr20
    tp1 = float(row["VWAP_Q"]) + 1 * float(row["sigma_Q"])
    tp2 = float(row["VWAP_Q"]) + 2 * float(row["sigma_Q"])
    position_pct = (shares * close) / equity if equity > 0 else 0.0
    risk_dollars = shares * (entry_price - stop_price)

    return {
        "shares": shares,
        "position_pct": position_pct,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "tp1": tp1,
        "tp2": tp2,
        "risk_dollars": risk_dollars,
    }


def build_plan(df: pd.DataFrame, equity: float, params: dict) -> pd.DataFrame:
    if df.empty:
        return df
    plans = df.apply(lambda r: compute_plan_row(r, equity, params), axis=1, result_type="expand")
    return pd.concat([df.reset_index(drop=True), plans], axis=1)

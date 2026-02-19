from __future__ import annotations

import pandas as pd


def build_universe(holdings_by_fund: dict, funds_cfg: list[dict]) -> pd.DataFrame:
    rows = []
    enabled = [f for f in funds_cfg if f.get("enabled", True)]
    enabled_count = max(len(enabled), 1)

    for fund in enabled:
        fund_id = fund["fund_id"]
        weight = float(fund.get("weight", 0))
        h = holdings_by_fund.get(fund_id, pd.DataFrame())
        if h.empty:
            continue

        total = h["value_usd"].sum()
        if total <= 0:
            continue

        h = h.copy().sort_values("value_usd", ascending=False)
        h["w"] = h["value_usd"] / total
        delta = pd.to_numeric(h["delta_shares_pct"], errors="coerce") if "delta_shares_pct" in h.columns else pd.Series(0.0, index=h.index)
        is_new = h["is_new"].astype(float) if "is_new" in h.columns else pd.Series(0.0, index=h.index)

        h["delta"] = delta.fillna(0).clip(lower=0, upper=1)
        h["new"] = is_new.fillna(0)
        h["fund_score_i"] = 0.45 * h["w"] + 0.35 * h["delta"] + 0.20 * h["new"]
        h["fund_weight"] = weight
        h["fund_id"] = fund_id
        rows.append(h[["ticker", "fund_score_i", "fund_weight", "fund_id"]])

    if not rows:
        return pd.DataFrame(columns=["ticker", "TAS", "Participation"])

    all_rows = pd.concat(rows, ignore_index=True)
    tas = (
        all_rows.assign(weighted=all_rows["fund_score_i"] * all_rows["fund_weight"])
        .groupby("ticker", as_index=False)
        .agg(weighted_sum=("weighted", "sum"), weight_sum=("fund_weight", "sum"))
    )
    tas["TAS"] = tas["weighted_sum"] / tas["weight_sum"].replace(0, 1e-9)
    tas = tas[["ticker", "TAS"]]

    participation = all_rows.groupby("ticker", as_index=False)["fund_id"].nunique().rename(columns={"fund_id": "holders"})
    participation["Participation"] = participation["holders"] / enabled_count

    out = tas.merge(participation[["ticker", "Participation"]], on="ticker", how="left")
    out = out[(out["TAS"] >= 0.25) | (out["Participation"] >= 0.30)].sort_values(["TAS", "Participation"], ascending=False)
    return out

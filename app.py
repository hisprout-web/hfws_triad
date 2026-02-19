from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.edgar_13f import fetch_latest_13f_holdings
from src.executor import log_event, upsert_ticket
from src.features import compute_features
from src.market_data import download_and_cache
from src.planner import build_plan
from src.schemas import now_iso
from src.scoring import merge_scores
from src.storage import Storage, load_json, load_yaml, save_json
from src.universe import build_universe

st.set_page_config(page_title="HFWS-TRIAD Dashboard v1", layout="wide")


@st.cache_data
def get_configs():
    params = load_yaml("config/params.yaml")
    funds = load_yaml("config/funds.yaml").get("funds", [])
    blocklist = set(load_yaml("config/blocklist.yaml").get("blocklist", []))
    anchors = load_yaml("config/anchor_windows.yaml")
    window = anchors["windows"][anchors["active_window"]]
    return params, funds, blocklist, window


def load_all(equity: float):
    params, funds, blocklist, anchor_window = get_configs()
    storage = Storage()

    holdings_by_fund = {}
    for fund in funds:
        cik = str(fund.get("cik", "")).strip()
        if not cik.isdigit() or len(cik) != 10:
            continue
        holdings = fetch_latest_13f_holdings(cik)
        if not holdings.empty:
            holdings_by_fund[fund["fund_id"]] = holdings

    universe = build_universe(holdings_by_fund, funds)
    if universe.empty:
        universe = pd.DataFrame(columns=["ticker", "TAS", "Participation"])

    tickers = universe["ticker"].dropna().astype(str).tolist()
    if "QQQ" not in tickers:
        tickers.append("QQQ")
    if "^VIX" not in tickers:
        tickers.append("^VIX")

    download_and_cache(storage, tickers)
    ohlcv = storage.load_ohlcv(tickers)

    qqq = ohlcv[ohlcv["ticker"] == "QQQ"].copy()
    latest_rows = []
    for t in universe["ticker"].tolist():
        tdf = ohlcv[ohlcv["ticker"] == t].copy()
        if tdf.empty or qqq.empty:
            continue
        feat = compute_features(tdf, qqq, params, anchor_window)
        if feat.empty:
            continue
        latest = feat.sort_values("date").iloc[-1].copy()
        latest["ticker"] = t
        latest_rows.append(latest)

    latest_features = pd.DataFrame(latest_rows)
    scored = merge_scores(universe, latest_features)
    planned = build_plan(scored, equity, params)

    if not planned.empty:
        planned["status"] = "WATCH"
        planned.loc[planned["ENTRY_SIGNAL"], "status"] = "DRAFT"

    planned["ticker"] = planned.get("ticker", pd.Series(dtype=str)).astype(str)
    planned = planned.sort_values(["ENTRY_SIGNAL", "WSS", "RR"], ascending=[False, False, False]) if not planned.empty else planned

    Path("outputs").mkdir(exist_ok=True)
    universe.to_csv("outputs/universe.csv", index=False)
    planned.to_csv("outputs/signals_today.csv", index=False)
    return planned, params, blocklist


def sync_drafts(df: pd.DataFrame, params: dict):
    if df is None or df.empty:
        return
    if "ENTRY_SIGNAL" not in df.columns:
        return

    tickets = load_json("outputs/trade_tickets.json", default=[])
    by_ticker = {t["ticker"]: t for t in tickets}

    for _, row in df[df["ENTRY_SIGNAL"] == True].iterrows():
        ticker = row["ticker"]
        existing = by_ticker.get(ticker)
        status = existing.get("status", "DRAFT") if existing else "DRAFT"
        status = "FINAL" if status == "FINAL" else "DRAFT"
        ticket = {
            "ticker": ticker,
            "status": status,
            "mode": row["MODE"],
            "tas": float(row["TAS"]),
            "participation": float(row["Participation"]),
            "structure_score": float(row["STRUCTURE_SCORE"]),
            "wss": float(row["WSS"]),
            "rr": float(row["RR"]),
            "entry_signal": bool(row["ENTRY_SIGNAL"]),
            "entry_price": float(row["entry_price"]),
            "stop_price": float(row["stop_price"]),
            "tp1": float(row["tp1"]),
            "tp2": float(row["tp2"]),
            "shares": int(row["shares"]),
            "position_pct": float(row["position_pct"]),
            "risk_dollars": float(row["risk_dollars"]),
            "created_at": existing.get("created_at", now_iso()) if existing else now_iso(),
            "updated_at": now_iso(),
            "metadata": {
                "agility_tp1_pct": params["agility_tp1_pct"],
                "agility_tp2_pct": params["agility_tp2_pct"],
                "agility_tp1_sell_pct": params["agility_tp1_sell_pct"],
                "agility_tp2_sell_pct": params["agility_tp2_sell_pct"],
                "fast_exit_rules": [
                    f"Exit if RS_20 < {params['fast_exit_rs_threshold']}",
                    f"Exit if close < SMA20 for {params['fast_exit_sma20_consecutive_days']} consecutive sessions",
                ],
            },
        }
        upsert_ticket(ticket)
        log_event({"timestamp": now_iso(), "ticker": ticker, "event": "draft_created_or_updated", "status": status})


def render_table(df: pd.DataFrame, status: str):
    view = df.copy()
    if status != "ALL":
        view = view[view["status"] == status]
    if not view.empty:
        view = view.sort_values(["status", "ENTRY_SIGNAL", "WSS", "RR"], ascending=[False, False, False, False])
    cols = [
        "ticker","TAS","Participation","STRUCTURE_SCORE","WSS","MODE","RR","ENTRY_SIGNAL","status",
        "entry_price","stop_price","tp1","tp2","shares","position_pct","risk_dollars",
    ]
    st.dataframe(view[[c for c in cols if c in view.columns]], use_container_width=True)


st.title("HFWS-TRIAD Dashboard v1")
equity = st.number_input("Portfolio Equity (E)", value=100000.0, min_value=1000.0, step=1000.0)
if st.button("Refresh Data"):
    st.cache_data.clear()

signals, params, blocklist = load_all(equity)
if signals.empty:
    st.warning("No universe candidates found. Fill config/funds.yaml with valid 10-digit CIK values.")
else:
    sync_drafts(signals, params)
tickets = pd.DataFrame(load_json("outputs/trade_tickets.json", default=[]))

if not tickets.empty:
    signals = signals.merge(tickets[["ticker", "status"]], on="ticker", how="left", suffixes=("", "_ticket"))
    signals["status"] = signals["status_ticket"].fillna(signals.get("status", "WATCH"))
    signals = signals.drop(columns=[c for c in ["status_ticket"] if c in signals.columns])

for col in ["status"]:
    if col not in signals.columns:
        signals[col] = "WATCH"

finals = signals[signals["status"] == "FINAL"]
others = signals[signals["status"] != "FINAL"]
signals = pd.concat([finals, others], ignore_index=True)


tab_draft, tab_final, tab_all = st.tabs(["Draft", "Final", "All"])
with tab_draft:
    render_table(signals, "DRAFT")
with tab_final:
    render_table(signals, "FINAL")
with tab_all:
    render_table(signals, "ALL")

if not tickets.empty:
    st.subheader("Ticket Detail")
    ticker = st.selectbox("Select ticker", options=tickets["ticker"].tolist())
    ticket = tickets[tickets["ticker"] == ticker].iloc[0].to_dict()
    st.json(ticket)

    earnings_within_7d = st.selectbox(
        "A) Earnings within 7 days?",
        options=[None, True, False],
        index=0,
        format_func=lambda x: "Select..." if x is None else ("Yes" if x else "No"),
    )
    blocklist_hit = st.selectbox(
        "B) Blocklist?",
        options=[None, True, False],
        index=0,
        format_func=lambda x: "Select..." if x is None else ("Yes" if x else "No"),
    )
    st.caption(f"Configured blocklist contains {len(blocklist)} symbol(s).")
    recompute = st.button("Recompute (stays DRAFT)")

    block_approval = (
        (earnings_within_7d is True and params["approval_block_on_earnings"])
        or (blocklist_hit is True)
    )
    approved = st.button(
        "Approve Entry",
        disabled=not (earnings_within_7d is not None and blocklist_hit is not None),
    )

    if recompute:
        ticket["status"] = "DRAFT"
        ticket["updated_at"] = now_iso()
        upsert_ticket(ticket)
        st.success("Ticket recomputed/kept as DRAFT.")

    if approved:
        event = {"timestamp": now_iso(), "ticker": ticker, "event": "approval_attempt", "earnings_7d": earnings_within_7d, "blocklist": blocklist_hit}
        if block_approval:
            event["result"] = "blocked"
            log_event(event)
            st.error("Approval blocked by risk checks.")
        else:
            if earnings_within_7d is True and not params["approval_block_on_earnings"]:
                ticket["shares"] = int(ticket["shares"] * params["approval_reduce_shares_on_earnings"])
            ticket["status"] = "FINAL"
            ticket["updated_at"] = now_iso()
            upsert_ticket(ticket)
            event["result"] = "approved_final"
            log_event(event)
            st.success("Ticket set to FINAL.")

save_json("outputs/trade_tickets.json", load_json("outputs/trade_tickets.json", default=[]))

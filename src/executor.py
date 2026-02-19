from __future__ import annotations

import pandas as pd

from src.storage import append_csv, load_json, save_json


TICKETS_PATH = "outputs/trade_tickets.json"
SIGNALS_LOG = "outputs/signals_log.csv"


def upsert_ticket(ticket: dict) -> None:
    tickets = load_json(TICKETS_PATH, default=[])
    existing_idx = None
    for i, t in enumerate(tickets):
        if t.get("ticker") == ticket.get("ticker"):
            existing_idx = i
            break
    if existing_idx is None:
        tickets.append(ticket)
    else:
        tickets[existing_idx] = ticket
    save_json(TICKETS_PATH, tickets)


def log_event(event: dict) -> None:
    append_csv(SIGNALS_LOG, pd.DataFrame([event]))

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import requests


HEADERS = {"User-Agent": "hfws-triad-dashboard/1.0 (demo@example.com)"}


def _valid_cik(cik: str) -> bool:
    return bool(cik and re.fullmatch(r"\d{10}", cik.strip()))


def _sec_get_json(url: str) -> dict[str, Any]:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_latest_13f_holdings(cik: str) -> pd.DataFrame:
    if not _valid_cik(cik):
        return pd.DataFrame(columns=["ticker", "value_usd", "shares"])
    try:
        sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        submissions = _sec_get_json(sub_url)
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        idx = next(i for i, form in enumerate(forms) if form.startswith("13F"))
        accession = accession_numbers[idx].replace("-", "")
        primary = primary_docs[idx]
        xml_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary}"

        text = requests.get(xml_url, headers=HEADERS, timeout=20).text
        table = pd.read_xml(text, xpath=".//infoTable")
        if table is None or table.empty:
            return pd.DataFrame(columns=["ticker", "value_usd", "shares"])

        out = pd.DataFrame(
            {
                "ticker": table.get("cusip", "").astype(str),
                "value_usd": pd.to_numeric(table.get("value", 0), errors="coerce").fillna(0) * 1000,
                "shares": pd.to_numeric(table.get("sshPrnamt", 0), errors="coerce").fillna(0),
            }
        )
        return out[out["ticker"] != ""]
    except Exception:
        return pd.DataFrame(columns=["ticker", "value_usd", "shares"])

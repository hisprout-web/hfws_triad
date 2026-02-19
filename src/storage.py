from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd


class Storage:
    def __init__(self, db_path: str = "outputs/cache.duckdb") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._init_tables()

    def _init_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ohlcv (
                ticker VARCHAR,
                date DATE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                PRIMARY KEY (ticker, date)
            )
            """
        )

    def upsert_ohlcv(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        self.conn.register("ohlcv_df", df)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO ohlcv
            SELECT ticker, date, open, high, low, close, volume
            FROM ohlcv_df
            """
        )

    def load_ohlcv(self, tickers: list[str], start: str | None = None) -> pd.DataFrame:
        if not tickers:
            return pd.DataFrame()
        placeholders = ",".join(["?"] * len(tickers))
        query = f"SELECT * FROM ohlcv WHERE ticker IN ({placeholders})"
        params: list[str] = tickers.copy()
        if start:
            query += " AND date >= ?"
            params.append(start)
        return self.conn.execute(query, params).fetchdf()



def load_yaml(path: str) -> dict:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}



def load_json(path: str, default):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))



def save_json(path: str, data) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")



def append_csv(path: str, row_df: pd.DataFrame) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    exists = p.exists()
    row_df.to_csv(path, mode="a", index=False, header=not exists)

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class FundConfig:
    fund_id: str
    name: str
    cik: str
    weight: float
    enabled: bool = True


@dataclass
class Ticket:
    ticker: str
    status: str
    mode: str
    tas: float
    participation: float
    structure_score: float
    wss: float
    rr: float
    entry_signal: bool
    entry_price: float
    stop_price: float
    tp1: float
    tp2: float
    shares: int
    position_pct: float
    risk_dollars: float
    created_at: str
    updated_at: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Ticket":
        data = data.copy()
        data.setdefault("metadata", {})
        return cls(**data)



def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

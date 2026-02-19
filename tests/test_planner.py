import pandas as pd

from src.planner import build_plan


def test_plan_constraints():
    df = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "close": 100.0,
                "ATR20": 2.0,
                "STRUCTURE_SCORE": 0.8,
                "MODE": "MID",
                "VWAP_Q": 102.0,
                "sigma_Q": 3.0,
            }
        ]
    )
    params = {"R_per_trade": 0.006, "max_pos": 0.12}
    out = build_plan(df, equity=100000, params=params)
    row = out.iloc[0]
    assert row["shares"] >= 0
    assert row["position_pct"] <= params["max_pos"] + 1e-9
    assert row["stop_price"] < row["entry_price"] < row["tp1"] < row["tp2"]

import pandas as pd

from src.market_data import _normalize_ohlcv_frame


def test_normalize_ohlcv_frame_handles_capitalized_and_adj_close():
    idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
    raw = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Adj Close": [100.5, 101.5],
            "Volume": [1_000, 1_100],
        },
        index=idx,
    )
    raw.index.name = "Date"

    out = _normalize_ohlcv_frame(raw, "AAPL")

    assert list(out.columns) == ["ticker", "date", "open", "high", "low", "close", "volume"]
    assert out["ticker"].eq("AAPL").all()
    assert len(out) == 2


def test_normalize_ohlcv_frame_handles_multiindex_columns():
    idx = pd.to_datetime(["2024-01-02"])
    cols = pd.MultiIndex.from_product([["AAPL"], ["Open", "High", "Low", "Close", "Adj Close", "Volume"]])
    raw = pd.DataFrame([[100.0, 101.0, 99.0, 100.5, 100.1, 1_000]], index=idx, columns=cols)
    raw.index.name = "Date"

    out = _normalize_ohlcv_frame(raw, "AAPL")

    assert list(out.columns) == ["ticker", "date", "open", "high", "low", "close", "volume"]
    assert out.iloc[0]["close"] == 100.5

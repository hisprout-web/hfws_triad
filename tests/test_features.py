import numpy as np
import pandas as pd

from src.features import compute_features


def test_compute_features_no_nans_core_columns():
    n = 120
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    price = np.linspace(100, 130, n)
    df = pd.DataFrame(
        {
            "date": dates,
            "open": price,
            "high": price + 1,
            "low": price - 1,
            "close": price,
            "volume": np.linspace(1_000_000, 1_300_000, n),
        }
    )
    qqq = df[["date", "close"]].copy()
    params = {"entry_band_lower": -1.0, "entry_band_upper": 0.3, "rr_min": 2.0, "structure_min": 0.5}
    anchor = {"start": "2025-02-01", "end": "2025-03-31"}

    out = compute_features(df, qqq, params, anchor)
    for c in ["ATR20", "SMA20", "SMA50", "RS_20", "STRUCTURE_SCORE", "RR"]:
        assert out[c].notna().all()

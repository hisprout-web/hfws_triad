from __future__ import annotations

import pandas as pd


def merge_scores(universe_df: pd.DataFrame, latest_features: pd.DataFrame) -> pd.DataFrame:
    if universe_df.empty or latest_features.empty:
        return pd.DataFrame()
    merged = universe_df.merge(latest_features, on="ticker", how="inner")
    merged["WSS"] = 0.60 * merged["TAS"] + 0.40 * merged["STRUCTURE_SCORE"]
    return merged

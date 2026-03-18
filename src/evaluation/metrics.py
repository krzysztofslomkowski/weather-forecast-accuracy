"""Metrics for forecast evaluation."""

from __future__ import annotations

import pandas as pd


def add_abs_error(evaluation_df: pd.DataFrame) -> pd.DataFrame:
    """Add absolute error column: abs(forecast_tmax_c - actual_tmax_c)."""
    result = evaluation_df.copy()
    result["abs_error_c"] = (result["forecast_tmax_c"] - result["actual_tmax_c"]).abs()
    return result


def mae_by_provider(evaluation_df: pd.DataFrame) -> pd.DataFrame:
    """Compute MAE grouped by provider."""
    mae = (
        evaluation_df.groupby("provider", as_index=False)["abs_error_c"]
        .mean()
        .rename(columns={"abs_error_c": "mae_c"})
    )
    return mae

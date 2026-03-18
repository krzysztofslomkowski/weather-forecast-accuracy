"""Utilities for loading and matching forecast and actual datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_forecasts(forecast_dir: str) -> pd.DataFrame:
    """Load and combine all forecast parquet files from a directory."""
    files = sorted(Path(forecast_dir).glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No forecast parquet files found in: {forecast_dir}")

    frames = [pd.read_parquet(file) for file in files]
    forecasts = pd.concat(frames, ignore_index=True)
    forecasts["run_date"] = pd.to_datetime(forecasts["run_date"]).dt.date
    forecasts["target_date"] = pd.to_datetime(forecasts["target_date"]).dt.date
    return forecasts


def load_actuals(actuals_dir: str) -> pd.DataFrame:
    """Load and combine all actuals parquet files from a directory."""
    files = sorted(Path(actuals_dir).glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No actuals parquet files found in: {actuals_dir}")

    frames = [pd.read_parquet(file) for file in files]
    actuals = pd.concat(frames, ignore_index=True)
    actuals["date"] = pd.to_datetime(actuals["date"]).dt.date
    return actuals


def match_forecasts_with_actuals(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Match forecast rows to actual rows on target_date == date."""
    merged = forecasts.merge(
        actuals,
        left_on="target_date",
        right_on="date",
        how="inner",
    )

    result = merged.rename(columns={"tmax_c_x": "forecast_tmax_c", "tmax_c_y": "actual_tmax_c"})

    return result[["provider", "run_date", "target_date", "forecast_tmax_c", "actual_tmax_c"]]

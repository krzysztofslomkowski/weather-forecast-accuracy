"""Supabase persistence helpers."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from supabase import create_client


def load_local_env(path: str = ".env") -> None:
    """Load simple KEY=value pairs from a local .env file."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_supabase_client():
    """Create a Supabase client when SUPABASE_URL and SUPABASE_KEY exist."""
    load_local_env()
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_KEY") or "").strip()

    if not url or not key:
        return None

    return create_client(url, key)


def normalize_value(value: Any) -> Any:
    """Convert pandas/date values to JSON-safe values for Supabase API."""
    if pd.isna(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame into JSON-safe dictionaries."""
    return [
        {column: normalize_value(value) for column, value in row.items()}
        for row in df.to_dict(orient="records")
    ]


def upsert_dataframe(table_name: str, df: pd.DataFrame, conflict_columns: str) -> None:
    """Upsert a DataFrame into a Supabase table."""
    client = get_supabase_client()
    if client is None:
        print(f"Skipping Supabase save for {table_name} (SUPABASE_URL or SUPABASE_KEY not configured).")
        return

    if df.empty:
        print(f"Skipping Supabase save for {table_name} (empty DataFrame).")
        return

    records = dataframe_to_records(df)
    client.table(table_name).upsert(records, on_conflict=conflict_columns).execute()
    print(f"Saved {len(records)} rows to Supabase table: {table_name}.")


def save_forecasts_to_supabase(df: pd.DataFrame) -> None:
    """Save forecast records to Supabase."""
    upsert_dataframe(
        table_name="forecast_records",
        df=df,
        conflict_columns="provider,run_date,target_date,horizon_days",
    )


def save_actuals_to_supabase(df: pd.DataFrame) -> None:
    """Save actual weather observation records to Supabase."""
    upsert_dataframe(
        table_name="actual_records",
        df=df,
        conflict_columns="date",
    )


def save_evaluation_to_supabase(detailed_df: pd.DataFrame, mae_df: pd.DataFrame) -> None:
    """Save detailed evaluation and MAE summary to Supabase."""
    upsert_dataframe(
        table_name="evaluation_detailed_records",
        df=detailed_df,
        conflict_columns="provider,run_date,target_date",
    )

    mae_to_save = mae_df.copy()
    mae_to_save["evaluation_run_date"] = pd.Timestamp.utcnow().date()
    counts = detailed_df.groupby("provider").size().reset_index(name="observations_count")
    mae_to_save = mae_to_save.merge(counts, on="provider", how="left")
    mae_to_save["observations_count"] = mae_to_save["observations_count"].fillna(0).astype(int)

    upsert_dataframe(
        table_name="evaluation_mae_records",
        df=mae_to_save,
        conflict_columns="provider,evaluation_run_date",
    )

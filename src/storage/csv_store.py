"""CSV-backed storage for public, versioned project data.

These helpers keep a small cumulative dataset in ``reports/data`` so the
project can be inspected directly from GitHub without requiring an active
Supabase instance.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DATE_FORMAT = "%Y-%m-%d"


def _as_path(path: str | Path) -> Path:
    """Return a normalized Path object."""
    return path if isinstance(path, Path) else Path(path)


def normalize_date_columns(df: pd.DataFrame, date_columns: list[str] | None = None) -> pd.DataFrame:
    """Convert selected date columns to ISO date strings for stable CSV output."""
    result = df.copy()
    for column in date_columns or []:
        if column in result.columns:
            result[column] = pd.to_datetime(result[column]).dt.strftime(DATE_FORMAT)
    return result


def load_csv(path: str | Path, date_columns: list[str] | None = None) -> pd.DataFrame | None:
    """Load a CSV file if it exists; otherwise return None."""
    file_path = _as_path(path)
    if not file_path.exists():
        return None

    df = pd.read_csv(file_path)
    for column in date_columns or []:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column]).dt.date
    return df


def write_csv(
    df: pd.DataFrame,
    path: str | Path,
    date_columns: list[str] | None = None,
    sort_columns: list[str] | None = None,
) -> Path:
    """Write a DataFrame as a stable CSV file."""
    file_path = _as_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    output = normalize_date_columns(df, date_columns=date_columns)
    if sort_columns:
        existing_sort_columns = [column for column in sort_columns if column in output.columns]
        if existing_sort_columns:
            output = output.sort_values(existing_sort_columns)

    output.to_csv(file_path, index=False)
    return file_path


def upsert_csv(
    new_rows: pd.DataFrame,
    path: str | Path,
    keys: list[str],
    date_columns: list[str] | None = None,
    sort_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Append/update records in a cumulative CSV store.

    Rows are deduplicated by ``keys`` and the last occurrence wins.
    """
    file_path = _as_path(path)
    existing = load_csv(file_path, date_columns=date_columns)

    if existing is None or existing.empty:
        combined = new_rows.copy()
    elif new_rows.empty:
        combined = existing.copy()
    else:
        combined = pd.concat([existing, new_rows], ignore_index=True)

    if not combined.empty:
        missing_keys = [key for key in keys if key not in combined.columns]
        if missing_keys:
            raise KeyError(f"CSV upsert is missing key columns: {missing_keys}")
        combined = combined.drop_duplicates(subset=keys, keep="last")

    write_csv(combined, file_path, date_columns=date_columns, sort_columns=sort_columns)
    return combined

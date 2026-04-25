"""Pipeline: fetch daily actual tmax values for Torrevieja and save to parquet."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml
from meteostat import Daily, Point

from src.database.postgres import save_actuals_to_db

HISTORY_DAYS = 30


def load_settings(path: str = "configs/settings.yaml") -> dict:
    """Load YAML settings from config file."""
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def fetch_actuals(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch daily actual weather observations from Meteostat."""
    location = Point(latitude, longitude)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.min.time())

    daily = Daily(location, start_dt, end_dt)
    return daily.fetch().reset_index()


def normalize_actuals(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Meteostat output to the project contract: date, tmax_c."""
    if raw_df.empty or "tmax" not in raw_df.columns:
        raise ValueError("Meteostat response does not include daily tmax data.")

    normalized = raw_df[["time", "tmax"]].rename(columns={"time": "date", "tmax": "tmax_c"})
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.date
    normalized = normalized.dropna(subset=["tmax_c"]).sort_values("date").reset_index(drop=True)

    if normalized.empty:
        raise ValueError("No non-null tmax values found in Meteostat response.")

    return normalized


def save_actuals(df: pd.DataFrame, output_dir: str) -> Path:
    """Save normalized actuals DataFrame to parquet file."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_date_str = datetime.now(timezone.utc).date().isoformat()
    file_path = out_dir / f"actuals_meteostat_{run_date_str}.parquet"
    df.to_parquet(file_path, index=False)
    return file_path


def main() -> None:
    settings = load_settings("configs/settings.yaml")

    latitude = float(settings["latitude"])
    longitude = float(settings["longitude"])

    today_utc = datetime.now(timezone.utc).date()
    end_date = today_utc - timedelta(days=1)
    start_date = end_date - timedelta(days=HISTORY_DAYS - 1)

    raw_actuals = fetch_actuals(latitude, longitude, start_date, end_date)
    actuals_df = normalize_actuals(raw_actuals)
    output_path = save_actuals(actuals_df, settings["paths"]["actuals_raw"])
    save_actuals_to_db(actuals_df)

    print(f"Saved actuals to: {output_path}")
    print(actuals_df.tail())


if __name__ == "__main__":
    main()

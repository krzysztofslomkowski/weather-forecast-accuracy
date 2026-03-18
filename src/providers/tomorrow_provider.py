"""Tomorrow.io provider functions for daily maximum temperature forecasts."""

from __future__ import annotations

from datetime import datetime
from typing import List

import pandas as pd
import requests

TOMORROW_URL = "https://api.tomorrow.io/v4/timelines"
PROVIDER_NAME = "tomorrow"


def fetch_daily_tmax_forecast(
    api_key: str,
    latitude: float,
    longitude: float,
    forecast_days: int,
) -> pd.DataFrame:
    """Fetch daily max temperature forecast from Tomorrow.io Timelines API.

    Returns a DataFrame with columns:
    - target_date
    - tmax_c
    """
    if not api_key:
        raise ValueError("Tomorrow.io API key is required.")

    params = {
        "location": f"{latitude},{longitude}",
        "fields": "temperatureMax",
        "timesteps": "1d",
        "units": "metric",
        "apikey": api_key,
    }

    response = requests.get(TOMORROW_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    timelines: List[dict] = payload.get("data", {}).get("timelines", [])
    if not timelines:
        raise ValueError("Tomorrow.io response does not include timelines data.")

    intervals: List[dict] = timelines[0].get("intervals", [])
    if not intervals:
        raise ValueError("Tomorrow.io response does not include daily intervals.")

    rows = []
    for interval in intervals[:forecast_days]:
        start_time = interval.get("startTime")
        values = interval.get("values", {})
        tmax_c = values.get("temperatureMax")

        if start_time is None or tmax_c is None:
            continue

        target_date = datetime.fromisoformat(start_time.replace("Z", "+00:00")).date()
        rows.append({"target_date": target_date, "tmax_c": float(tmax_c)})

    if not rows:
        raise ValueError("Tomorrow.io response did not return valid daily max temperature values.")

    return pd.DataFrame(rows)

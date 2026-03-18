"""Visual Crossing provider functions for daily maximum temperature forecasts."""

from __future__ import annotations

from datetime import date
from typing import List

import pandas as pd
import requests

VISUALCROSSING_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
PROVIDER_NAME = "visualcrossing"


def fetch_daily_tmax_forecast(
    api_key: str,
    latitude: float,
    longitude: float,
    forecast_days: int,
) -> pd.DataFrame:
    """Fetch daily max temperature forecast from Visual Crossing.

    Returns a DataFrame with columns:
    - target_date
    - tmax_c
    """
    if not api_key:
        raise ValueError("Visual Crossing API key is required.")

    location = f"{latitude},{longitude}"
    url = f"{VISUALCROSSING_URL}/{location}"

    params = {
        "unitGroup": "metric",
        "include": "days",
        "key": api_key,
        "contentType": "json",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    day_items: List[dict] = payload.get("days", [])
    if not day_items:
        raise ValueError("Visual Crossing response does not include daily forecast data.")

    rows = []
    for day in day_items[:forecast_days]:
        day_date = day.get("datetime")
        tmax_c = day.get("tempmax")

        if day_date is None or tmax_c is None:
            continue

        rows.append(
            {
                "target_date": date.fromisoformat(day_date),
                "tmax_c": float(tmax_c),
            }
        )

    if not rows:
        raise ValueError("Visual Crossing response did not return valid daily max temperature values.")

    return pd.DataFrame(rows)

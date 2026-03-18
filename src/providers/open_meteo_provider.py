"""Open-Meteo provider functions for daily maximum temperature forecasts."""

from __future__ import annotations

from datetime import date
from typing import List

import pandas as pd
import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
PROVIDER_NAME = "open-meteo"


def fetch_daily_tmax_forecast(latitude: float, longitude: float, forecast_days: int) -> pd.DataFrame:
    """Fetch daily max temperature forecast from Open-Meteo.

    Returns a DataFrame with columns:
    - target_date
    - tmax_c
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max",
        "forecast_days": forecast_days,
        "timezone": "UTC",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    daily = payload.get("daily", {})
    dates: List[str] = daily.get("time", [])
    tmax_values: List[float] = daily.get("temperature_2m_max", [])

    if not dates or not tmax_values:
        raise ValueError("Open-Meteo response does not include daily temperature data.")

    if len(dates) != len(tmax_values):
        raise ValueError("Open-Meteo response has mismatched daily arrays.")

    return pd.DataFrame(
        {
            "target_date": [date.fromisoformat(day) for day in dates],
            "tmax_c": tmax_values,
        }
    )

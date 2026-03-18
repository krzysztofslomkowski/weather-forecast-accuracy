"""OpenWeatherMap provider functions for daily maximum temperature forecasts."""

from __future__ import annotations

from datetime import datetime
from typing import List

import pandas as pd
import requests

OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/3.0/onecall"
PROVIDER_NAME = "openweathermap"


def fetch_daily_tmax_forecast(
    api_key: str,
    latitude: float,
    longitude: float,
    forecast_days: int,
) -> pd.DataFrame:
    """Fetch daily max temperature forecast from OpenWeather One Call 3.0.

    Returns a DataFrame with columns:
    - target_date
    - tmax_c
    """
    if not api_key:
        raise ValueError("OpenWeatherMap API key is required.")

    params = {
        "lat": latitude,
        "lon": longitude,
        "exclude": "current,minutely,hourly,alerts",
        "units": "metric",
        "appid": api_key,
    }

    response = requests.get(OPENWEATHERMAP_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    daily_items: List[dict] = payload.get("daily", [])
    if not daily_items:
        raise ValueError("OpenWeatherMap One Call response does not include daily forecast data.")

    rows = []
    for item in daily_items[:forecast_days]:
        unix_dt = item.get("dt")
        temp_info = item.get("temp", {})
        tmax_c = temp_info.get("max")

        if unix_dt is None or tmax_c is None:
            continue

        rows.append(
            {
                "target_date": datetime.utcfromtimestamp(unix_dt).date(),
                "tmax_c": float(tmax_c),
            }
        )

    if not rows:
        raise ValueError("OpenWeatherMap One Call response did not return valid daily max temperature values.")

    return pd.DataFrame(rows)

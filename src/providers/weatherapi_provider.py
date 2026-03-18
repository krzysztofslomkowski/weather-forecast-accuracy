"""WeatherAPI provider functions for daily maximum temperature forecasts."""

from __future__ import annotations

from datetime import date
from typing import List

import pandas as pd
import requests

WEATHERAPI_URL = "https://api.weatherapi.com/v1/forecast.json"
PROVIDER_NAME = "weatherapi"


def fetch_daily_tmax_forecast(
    api_key: str,
    latitude: float,
    longitude: float,
    forecast_days: int,
) -> pd.DataFrame:
    """Fetch daily max temperature forecast from WeatherAPI.

    Returns a DataFrame with columns:
    - target_date
    - tmax_c
    """
    if not api_key:
        raise ValueError("WeatherAPI key is required.")

    params = {
        "key": api_key,
        "q": f"{latitude},{longitude}",
        "days": forecast_days,
        "aqi": "no",
        "alerts": "no",
    }

    response = requests.get(WEATHERAPI_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    forecast_days_data: List[dict] = payload.get("forecast", {}).get("forecastday", [])
    if not forecast_days_data:
        raise ValueError("WeatherAPI response does not include forecastday data.")

    rows = []
    for day in forecast_days_data:
        day_date = day.get("date")
        day_info = day.get("day", {})
        tmax_c = day_info.get("maxtemp_c")

        if day_date is None or tmax_c is None:
            continue

        rows.append({"target_date": date.fromisoformat(day_date), "tmax_c": float(tmax_c)})

    if not rows:
        raise ValueError("WeatherAPI response did not return valid daily max temperature values.")

    return pd.DataFrame(rows)

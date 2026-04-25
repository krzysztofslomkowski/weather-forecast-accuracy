"""Pipeline: fetch D+3 forecasts for Torrevieja and save to parquet."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

from src.providers.open_meteo_provider import fetch_daily_tmax_forecast as fetch_open_meteo_forecast
from src.providers.open_meteo_provider import PROVIDER_NAME as OPEN_METEO_PROVIDER
from src.providers.weatherapi_provider import fetch_daily_tmax_forecast as fetch_weatherapi_forecast
from src.providers.weatherapi_provider import PROVIDER_NAME as WEATHERAPI_PROVIDER
from src.providers.openweathermap_provider import fetch_daily_tmax_forecast as fetch_openweathermap_forecast
from src.providers.openweathermap_provider import PROVIDER_NAME as OPENWEATHERMAP_PROVIDER
from src.providers.visualcrossing_provider import fetch_daily_tmax_forecast as fetch_visualcrossing_forecast
from src.providers.visualcrossing_provider import PROVIDER_NAME as VISUALCROSSING_PROVIDER
from src.providers.tomorrow_provider import fetch_daily_tmax_forecast as fetch_tomorrow_forecast
from src.providers.tomorrow_provider import PROVIDER_NAME as TOMORROW_PROVIDER


def load_local_env(path: str = ".env") -> None:
    """Load simple KEY=value pairs from local .env into environment variables."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_settings(path: str = "configs/settings.yaml") -> dict:
    """Load YAML settings from config file."""
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_api_key(provider_name: str, provider_cfg: dict) -> str:
    """Read provider API key from environment variable named in settings.yaml."""
    env_var_name = (provider_cfg.get("api_key_env") or "").strip()
    if not env_var_name:
        print(f"Skipping {provider_name} (missing api_key_env in config).")
        return ""

    api_key = (os.getenv(env_var_name) or "").strip()
    if not api_key:
        print(f"Skipping {provider_name} (missing environment variable: {env_var_name}).")
        return ""

    return api_key


def build_provider_record(provider: str, forecast_df: pd.DataFrame, run_date, target_date, horizon_days: int) -> pd.DataFrame:
    """Build one-row forecast record for a single provider."""
    matched = forecast_df[forecast_df["target_date"] == target_date]
    if matched.empty:
        raise ValueError(f"No forecast value found for provider={provider}, target_date={target_date}.")

    tmax_c = float(matched.iloc[0]["tmax_c"])
    return pd.DataFrame(
        [
            {
                "provider": provider,
                "run_date": run_date,
                "target_date": target_date,
                "horizon_days": horizon_days,
                "tmax_c": tmax_c,
            }
        ]
    )


def fetch_provider_forecast(provider_name: str, provider_cfg: dict, latitude: float, longitude: float, horizon_days: int) -> pd.DataFrame | None:
    """Fetch daily forecast for one provider using configuration."""
    if not provider_cfg.get("enabled", True):
        print(f"Skipping {provider_name} (disabled in config).")
        return None

    forecast_days = horizon_days + 1

    if provider_name == OPEN_METEO_PROVIDER:
        return fetch_open_meteo_forecast(latitude=latitude, longitude=longitude, forecast_days=forecast_days)

    if provider_name == WEATHERAPI_PROVIDER:
        api_key = get_api_key(provider_name, provider_cfg)
        return None if not api_key else fetch_weatherapi_forecast(api_key, latitude, longitude, forecast_days)

    if provider_name == OPENWEATHERMAP_PROVIDER:
        api_key = get_api_key(provider_name, provider_cfg)
        return None if not api_key else fetch_openweathermap_forecast(api_key, latitude, longitude, forecast_days)

    if provider_name == VISUALCROSSING_PROVIDER:
        api_key = get_api_key(provider_name, provider_cfg)
        return None if not api_key else fetch_visualcrossing_forecast(api_key, latitude, longitude, forecast_days)

    if provider_name == TOMORROW_PROVIDER:
        api_key = get_api_key(provider_name, provider_cfg)
        return None if not api_key else fetch_tomorrow_forecast(api_key, latitude, longitude, forecast_days)

    print(f"Skipping unknown provider '{provider_name}'.")
    return None


def collect_forecasts(settings: dict) -> pd.DataFrame:
    """Collect forecasts from enabled providers and return one combined DataFrame."""
    latitude = float(settings["latitude"])
    longitude = float(settings["longitude"])
    horizon_days = int(settings["forecast_horizon_days"])

    run_date = datetime.now(timezone.utc).date()
    target_date = run_date + timedelta(days=horizon_days)

    providers_cfg = settings.get("forecast_providers", {})
    records: list[pd.DataFrame] = []

    for provider_name, provider_cfg in providers_cfg.items():
        forecast_df = fetch_provider_forecast(provider_name, provider_cfg, latitude, longitude, horizon_days)
        if forecast_df is None:
            continue

        try:
            provider_record = build_provider_record(provider_name, forecast_df, run_date, target_date, horizon_days)
            records.append(provider_record)
        except ValueError as error:
            print(f"Skipping {provider_name}: {error}")

    if not records:
        raise ValueError("No forecast records collected. Check provider configuration and API keys.")

    return pd.concat(records, ignore_index=True)


def save_forecast(df: pd.DataFrame, output_dir: str) -> Path:
    """Save combined forecast DataFrame to a parquet file."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_date_str = df.iloc[0]["run_date"].isoformat()
    file_path = out_dir / f"forecast_providers_{run_date_str}.parquet"
    df.to_parquet(file_path, index=False)
    return file_path


def main() -> None:
    load_local_env()
    settings = load_settings("configs/settings.yaml")
    result_df = collect_forecasts(settings)
    output_path = save_forecast(result_df, settings["paths"]["forecasts_raw"])

    print(f"Saved forecasts to: {output_path}")
    print(result_df)


if __name__ == "__main__":
    main()

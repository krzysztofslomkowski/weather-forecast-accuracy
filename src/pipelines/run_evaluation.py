"""Pipeline: compare forecasts vs actuals and calculate error metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from src.evaluation.compare import load_actuals, load_forecasts, match_forecasts_with_actuals
from src.evaluation.metrics import add_abs_error, mae_by_provider


def load_settings(path: str = "configs/settings.yaml") -> dict:
    """Load YAML settings from config file."""
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def save_results(detailed_df, mae_df, output_dir: str) -> tuple[Path, Path]:
    """Save detailed evaluation rows and MAE aggregation to parquet files."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_date_str = datetime.now(timezone.utc).date().isoformat()
    detailed_path = out_dir / f"evaluation_detailed_{run_date_str}.parquet"
    mae_path = out_dir / f"evaluation_mae_{run_date_str}.parquet"

    detailed_df.to_parquet(detailed_path, index=False)
    mae_df.to_parquet(mae_path, index=False)

    return detailed_path, mae_path


def main() -> None:
    settings = load_settings("configs/settings.yaml")

    forecasts = load_forecasts(settings["paths"]["forecasts_raw"])
    actuals = load_actuals(settings["paths"]["actuals_raw"])

    matched = match_forecasts_with_actuals(forecasts, actuals)
    detailed = add_abs_error(matched)
    mae = mae_by_provider(detailed)

    detailed_path, mae_path = save_results(detailed, mae, settings["paths"]["evaluation_processed"])

    print(f"Saved detailed evaluation to: {detailed_path}")
    print(f"Saved MAE summary to: {mae_path}")
    print("\nDetailed sample:")
    print(detailed.tail())
    print("\nMAE by provider:")
    print(mae)


if __name__ == "__main__":
    main()

"""Pipeline: compare forecasts vs actuals and calculate error metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from src.database.supabase_client import (
    load_actuals_from_supabase,
    load_forecasts_from_supabase,
    save_evaluation_to_supabase,
)
from src.evaluation.compare import load_actuals, load_forecasts, match_forecasts_with_actuals
from src.evaluation.metrics import add_abs_error, mae_by_provider
from src.reporting.evaluation_report import write_report
from src.storage.csv_store import load_csv, upsert_csv, write_csv


def load_settings(path: str = "configs/settings.yaml") -> dict:
    """Load YAML settings from config file."""
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_csv_evaluation_inputs(settings: dict) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Load cumulative public CSV data when available."""
    report_paths = settings.get("reports_data", {})
    forecasts_path = report_paths.get("forecasts", "reports/data/forecasts.csv")
    actuals_path = report_paths.get("actuals", "reports/data/actuals.csv")

    forecasts = load_csv(forecasts_path, date_columns=["run_date", "target_date"])
    actuals = load_csv(actuals_path, date_columns=["date"])

    if forecasts is not None and actuals is not None and not forecasts.empty and not actuals.empty:
        print("Loaded evaluation inputs from versioned CSV files.")
        return forecasts, actuals

    return None


def load_evaluation_inputs(settings: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load forecast and actual records for evaluation.

    Prefer versioned CSV files in reports/data so GitHub remains the public source
    of truth. Supabase is now optional and only used as a fallback.
    """
    csv_inputs = load_csv_evaluation_inputs(settings)
    if csv_inputs is not None:
        return csv_inputs

    forecasts = load_forecasts_from_supabase()
    actuals = load_actuals_from_supabase()

    if forecasts is not None and actuals is not None and not forecasts.empty and not actuals.empty:
        print("Loaded evaluation inputs from Supabase.")
        return forecasts, actuals

    print("Falling back to local parquet files for evaluation inputs.")
    return load_forecasts(settings["paths"]["forecasts_raw"]), load_actuals(settings["paths"]["actuals_raw"])


def save_results(detailed_df: pd.DataFrame, mae_df: pd.DataFrame, settings: dict) -> tuple[Path, Path, Path, Path]:
    """Save detailed evaluation rows and MAE aggregation to parquet and public CSV."""
    output_dir = settings["paths"]["evaluation_processed"]
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_date_str = datetime.now(timezone.utc).date().isoformat()
    detailed_path = out_dir / f"evaluation_detailed_{run_date_str}.parquet"
    mae_path = out_dir / f"evaluation_mae_{run_date_str}.parquet"

    detailed_df.to_parquet(detailed_path, index=False)
    mae_df.to_parquet(mae_path, index=False)

    report_paths = settings.get("reports_data", {})
    detailed_csv_path = report_paths.get("evaluation_detailed", "reports/data/evaluation_detailed.csv")
    mae_csv_path = report_paths.get("evaluation_mae", "reports/data/evaluation_mae.csv")

    detailed_history = upsert_csv(
        new_rows=detailed_df,
        path=detailed_csv_path,
        keys=["provider", "run_date", "target_date"],
        date_columns=["run_date", "target_date"],
        sort_columns=["target_date", "run_date", "provider"],
    )

    counts = detailed_history.groupby("provider").size().reset_index(name="observations_count")
    mae_history = mae_by_provider(detailed_history).merge(counts, on="provider", how="left")
    mae_history = mae_history.sort_values(["mae_c", "provider"]).reset_index(drop=True)
    mae_history["rank"] = mae_history.index + 1
    mae_history = mae_history[["rank", "provider", "observations_count", "mae_c"]]
    mae_csv = write_csv(mae_history, mae_csv_path, sort_columns=["rank", "provider"])

    return detailed_path, mae_path, Path(detailed_csv_path), mae_csv


def main() -> None:
    settings = load_settings("configs/settings.yaml")

    forecasts, actuals = load_evaluation_inputs(settings)

    matched = match_forecasts_with_actuals(forecasts, actuals)
    detailed = add_abs_error(matched)
    mae = mae_by_provider(detailed)

    detailed_path, mae_path, detailed_csv_path, mae_csv_path = save_results(detailed, mae, settings)
    save_evaluation_to_supabase(detailed, mae)

    summary_path = settings.get("reports_data", {}).get("summary", "reports/evaluation_summary.md")
    report_path = write_report(detailed, settings, summary_path)

    print(f"Saved detailed evaluation to: {detailed_path}")
    print(f"Saved MAE summary to: {mae_path}")
    print(f"Updated public detailed CSV: {detailed_csv_path}")
    print(f"Updated public MAE CSV: {mae_csv_path}")
    print(f"Updated Markdown report: {report_path}")
    print("\nDetailed sample:")
    print(detailed.tail())
    print("\nMAE by provider:")
    print(mae)


if __name__ == "__main__":
    main()

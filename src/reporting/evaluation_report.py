"""Generate a human-readable evaluation summary report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from src.storage.csv_store import load_csv


def load_settings(path: str = "configs/settings.yaml") -> dict:
    """Load YAML settings from config file."""
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _format_float(value: float | int | None, digits: int = 2) -> str:
    """Format a number for Markdown tables."""
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.{digits}f}"


def build_provider_ranking(detailed: pd.DataFrame) -> pd.DataFrame:
    """Calculate ranking table by provider."""
    ranking = (
        detailed.groupby("provider", as_index=False)
        .agg(
            observations_count=("abs_error_c", "size"),
            mae_c=("abs_error_c", "mean"),
            bias_c=("forecast_tmax_c", lambda values: 0.0),
        )
    )

    bias = (
        detailed.assign(error_c=detailed["forecast_tmax_c"] - detailed["actual_tmax_c"])
        .groupby("provider", as_index=False)["error_c"]
        .mean()
        .rename(columns={"error_c": "bias_c"})
    )

    ranking = ranking.drop(columns=["bias_c"]).merge(bias, on="provider", how="left")
    ranking = ranking.sort_values(["mae_c", "provider"]).reset_index(drop=True)
    ranking["rank"] = ranking.index + 1
    return ranking[["rank", "provider", "observations_count", "mae_c", "bias_c"]]


def build_daily_wins(detailed: pd.DataFrame) -> pd.DataFrame:
    """Count how often each provider has the lowest absolute error per target date."""
    if detailed.empty:
        return pd.DataFrame(columns=["provider", "daily_wins"])

    min_errors = detailed.groupby("target_date")["abs_error_c"].transform("min")
    winners = detailed[detailed["abs_error_c"] == min_errors]
    wins = winners.groupby("provider", as_index=False).size().rename(columns={"size": "daily_wins"})
    return wins.sort_values(["daily_wins", "provider"], ascending=[False, True])


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    """Render a compact Markdown table."""
    if df.empty:
        return "_No rows yet._\n"

    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = []
    for _, row in df.iterrows():
        values = [str(row[column]) for column in columns]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, divider, *rows]) + "\n"


def build_report(detailed: pd.DataFrame, settings: dict) -> str:
    """Build the Markdown evaluation report."""
    city = settings.get("city", "configured location")
    country = settings.get("country", "")
    horizon_days = settings.get("forecast_horizon_days", "?")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        f"# Weather Forecast Accuracy — {city}, {country}",
        "",
        f"Generated automatically: **{generated_at}**.",
        "",
        "## Business question",
        "",
        f"Which forecast provider is most accurate for daily maximum temperature in {city} at D+{horizon_days}?",
        "",
        "## Method",
        "",
        "The pipeline stores daily provider forecasts, stores observed daily maximum temperatures, matches `target_date` to the actual observation date, and ranks providers by MAE.",
        "",
        "Lower MAE means a more accurate provider for this location and horizon.",
        "",
    ]

    if detailed.empty:
        lines.extend(
            [
                "## Current result",
                "",
                "No completed comparisons yet.",
                "",
                "This is expected until a stored D+3 forecast has a matching observed actual temperature.",
                "",
                "## Public data files",
                "",
                "- `reports/data/forecasts.csv`",
                "- `reports/data/actuals.csv`",
                "- `reports/data/evaluation_detailed.csv`",
                "- `reports/data/evaluation_mae.csv`",
                "",
            ]
        )
        return "\n".join(lines)

    detailed = detailed.copy()
    detailed["run_date"] = pd.to_datetime(detailed["run_date"]).dt.date
    detailed["target_date"] = pd.to_datetime(detailed["target_date"]).dt.date

    ranking = build_provider_ranking(detailed)
    daily_wins = build_daily_wins(detailed)

    best_provider = ranking.iloc[0]["provider"]
    best_mae = ranking.iloc[0]["mae_c"]
    providers_count = detailed["provider"].nunique()
    comparisons_count = len(detailed)
    first_target = detailed["target_date"].min().isoformat()
    last_target = detailed["target_date"].max().isoformat()

    ranking_display = ranking.copy()
    ranking_display["mae_c"] = ranking_display["mae_c"].map(lambda value: _format_float(value))
    ranking_display["bias_c"] = ranking_display["bias_c"].map(lambda value: _format_float(value))

    lines.extend(
        [
            "## Current result",
            "",
            f"Best provider so far: **{best_provider}** with MAE **{_format_float(best_mae)}°C**.",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Providers compared | {providers_count} |",
            f"| Completed comparisons | {comparisons_count} |",
            f"| Target-date range | {first_target} → {last_target} |",
            "",
            "## Provider ranking",
            "",
            markdown_table(ranking_display, ["rank", "provider", "observations_count", "mae_c", "bias_c"]),
            "## Daily wins",
            "",
            markdown_table(daily_wins, ["provider", "daily_wins"]),
            "## Public data files",
            "",
            "- `reports/data/forecasts.csv`",
            "- `reports/data/actuals.csv`",
            "- `reports/data/evaluation_detailed.csv`",
            "- `reports/data/evaluation_mae.csv`",
            "",
            "## Limitations",
            "",
            "This result is specific to one location, one forecast horizon, and the available sample size. It should be treated as an empirical local benchmark, not as a universal ranking of weather providers.",
            "",
        ]
    )

    return "\n".join(lines)


def write_report(detailed: pd.DataFrame, settings: dict, output_path: str | Path) -> Path:
    """Write the Markdown report to disk."""
    report_path = Path(output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(detailed, settings), encoding="utf-8")
    return report_path


def main() -> None:
    settings = load_settings()
    report_paths = settings.get("reports_data", {})
    detailed_path = report_paths.get("evaluation_detailed", "reports/data/evaluation_detailed.csv")
    summary_path = report_paths.get("summary", "reports/evaluation_summary.md")

    detailed = load_csv(detailed_path, date_columns=["run_date", "target_date"])
    if detailed is None:
        detailed = pd.DataFrame(
            columns=["provider", "run_date", "target_date", "forecast_tmax_c", "actual_tmax_c", "abs_error_c"]
        )

    report_path = write_report(detailed, settings, summary_path)
    print(f"Saved evaluation report to: {report_path}")


if __name__ == "__main__":
    main()

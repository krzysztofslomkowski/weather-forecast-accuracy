# Weather Forecast Accuracy (Torrevieja, Spain)

## In 20 Seconds

- Goal: compare **5 forecast providers** for Torrevieja and identify which is most reliable for **D+3 daily max temperature (`tmax`)**.
- Method: ingest forecasts + Meteostat actuals, match by date, compute **absolute error** and **MAE**.
- Output: parquet datasets plus a provider ranking based on MAE.

## Key Insight (Early Results)

- Current status: evaluation pipeline is implemented and ready; production-like historical collection is still growing.
- Early runs show that provider rankings can differ once matched rows start to accumulate.
- At this stage, MAE differences should be treated as directional, not final.
- Caution: this is an **early signal** until we accumulate more matched rows across more days/seasons.

A portfolio-ready data analytics project that evaluates which weather forecast provider is most reliable for predicting **daily maximum temperature (`tmax`) 3 days ahead (D+3)** in **Torrevieja, Spain**.

---

## 1) Project Overview

This project builds a simple but realistic forecast evaluation workflow:

1. collect daily forecasts from multiple providers,
2. collect observed daily weather data,
3. compare forecast vs actual on matching dates,
4. calculate error metrics (absolute error and MAE),
5. produce output files ready for reporting.

The project is intentionally practical, readable, and easy to explain in a portfolio or interview.
This project is designed as a minimal, reproducible evaluation system rather than a one-off analysis.

## 2) Business Question

> Which weather forecast provider should we trust for Torrevieja when predicting maximum temperature 3 days ahead?

## 3) Why This Project Matters

Forecast quality has direct impact on planning decisions (travel, outdoor events, operations, staffing, and risk management).

This project demonstrates how to evaluate forecast quality in a disciplined way:
- consistent data contract,
- same forecast horizon for all providers,
- reproducible pipeline,
- clear metric for comparison.

## 4) Tech Stack

- **Python**
- **pandas**
- **requests**
- **meteostat**
- **pyyaml**
- **parquet** via `pyarrow`

## 5) Data Sources

- **Forecast APIs (Version 1.0):**
  - Open-Meteo
  - WeatherAPI
  - OpenWeatherMap
  - Visual Crossing
  - Tomorrow.io
- **Actual observations:**
  - Meteostat (daily observed weather)

## 6) Project Structure

```text
/
  README.md
  requirements.txt
  .gitignore
  LICENSE

  /configs
    settings.yaml

  /data
    /raw
      /forecasts
      /actuals
    /processed
      /evaluation

  /reports
    evaluation_summary.md
    run_checklist.md
    /figures

  /src
    /providers
      open_meteo_provider.py
      weatherapi_provider.py
      openweathermap_provider.py
      visualcrossing_provider.py
      tomorrow_provider.py
    /pipelines
      ingest_forecast.py
      ingest_actuals.py
      run_evaluation.py
    /evaluation
      compare.py
      metrics.py
    /utils
      io.py
      dates.py

  /notebooks
  /sql
```

## 7) Forecast Providers Used in Version 1.0

The forecast ingestion pipeline is config-driven and supports these providers:

1. `open-meteo`
2. `weatherapi`
3. `openweathermap`
4. `visualcrossing`
5. `tomorrow`

Providers that require API keys are skipped gracefully when key is missing.

## 8) Data Contract

### Forecast records
- `provider`
- `run_date` (when forecast was fetched)
- `target_date` (date being predicted)
- `horizon_days`
- `tmax_c`

### Actual records
- `date`
- `tmax_c`

### Evaluation records
- `provider`
- `run_date`
- `target_date`
- `forecast_tmax_c`
- `actual_tmax_c`
- `abs_error_c`

### MAE summary
- `provider`
- `mae_c`

## 9) Methodology

1. **Ingest forecasts** for the same location and forecast horizon (D+3).
2. **Ingest actuals** from Meteostat.
3. **Match rows** where `forecast.target_date == actual.date`.
4. **Compute absolute error** per row:
   `abs_error_c = |forecast_tmax_c - actual_tmax_c|`
5. **Aggregate MAE** per provider:
   `mae_c = mean(abs_error_c)`
6. Save detailed and aggregated outputs as parquet files.

## 10) How to Run

From repository root:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Update `configs/settings.yaml`:
   - location and horizon values,
   - provider `enabled` flags,
   - API keys where required.
3. Run forecast ingestion:
   ```bash
   python -m src.pipelines.ingest_forecast
   ```
4. Run actuals ingestion:
   ```bash
   python -m src.pipelines.ingest_actuals
   ```
5. Run evaluation:
   ```bash
   python -m src.pipelines.run_evaluation
   ```

For a beginner-friendly operational guide, see:
- `reports/run_checklist.md`

## 11) Expected Outputs

After successful runs, expect parquet files in:

- Forecasts:
  - `data/raw/forecasts/forecast_providers_<run_date>.parquet`
- Actuals:
  - `data/raw/actuals/actuals_meteostat_<run_date>.parquet`
- Evaluation:
  - `data/processed/evaluation/evaluation_detailed_<run_date>.parquet`
  - `data/processed/evaluation/evaluation_mae_<run_date>.parquet`

You can also review:
- `reports/evaluation_summary.md`

## 12) How to Interpret MAE

- **Lower MAE means better forecast accuracy.**
- MAE is in °C, so it is directly interpretable.

Example:
- Provider A: `mae_c = 1.2`
- Provider B: `mae_c = 2.0`

Provider A performs better (smaller average error).

## 13) Operational Notes

- The pipeline is config-driven (`configs/settings.yaml`).
- Forecast providers can be enabled/disabled without code changes.
- Missing API key does **not** stop the whole forecast ingestion process; that provider is skipped.
- Matching forecast vs actual requires that actuals for the forecast target date already exist.

## 14) Limitations

- Current scope focuses on one city (Torrevieja).
- Current metric scope is centered on `tmax` and MAE.
- API-based providers may have usage limits or plan restrictions.
- Early runs may produce limited evaluation rows because D+3 actuals are not immediately available.

## 15) Next Steps

- Add richer validation and tests.
- Add simple visualizations for error trends.
- Expand comparison windows and segmentation (seasonality, month, lead-time buckets).
- Add automation (scheduled ingestion/evaluation).
- Add Version 2.0 data layer extensions (separate phase).

---

If you want a quick operational start, begin with `reports/run_checklist.md`, then review `reports/evaluation_summary.md` for interpretation.

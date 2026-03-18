# Run Checklist (End-to-End)

This checklist helps you run the full MVP flow and validate that everything works.

## 1) Update `configs/settings.yaml`

Before running pipelines, confirm these fields:

- `city`
- `country`
- `latitude`
- `longitude`
- `forecast_horizon_days`
- paths under `paths`:
  - `forecasts_raw`
  - `actuals_raw`
  - `evaluation_processed`

In `forecast_providers`, confirm `enabled` flags and API keys.

## 2) Providers that require API keys

### No API key required
- `open-meteo`

### API key required
- `weatherapi`
- `openweathermap`
- `visualcrossing`
- `tomorrow`

If a provider is enabled but `api_key` is empty, the forecast pipeline should skip it with a clear message.

## 3) Run order

From repository root, run in this order:

1. Forecast ingestion
   ```bash
   python -m src.pipelines.ingest_forecast
   ```
2. Actuals ingestion
   ```bash
   python -m src.pipelines.ingest_actuals
   ```
3. Evaluation
   ```bash
   python -m src.pipelines.run_evaluation
   ```

## 4) What to expect after each step

### After `ingest_forecast`
- A parquet file should appear in `data/raw/forecasts/`.
- Output should show which providers were used and which were skipped.

### After `ingest_actuals`
- A parquet file should appear in `data/raw/actuals/`.
- Data should include `date` and `tmax_c`.

### After `run_evaluation`
- Two parquet files should appear in `data/processed/evaluation/`:
  - `evaluation_detailed_<run_date>.parquet`
  - `evaluation_mae_<run_date>.parquet`

## 5) Quick parquet file checks

Use these commands from repo root:

```bash
ls data/raw/forecasts/*.parquet
ls data/raw/actuals/*.parquet
ls data/processed/evaluation/*.parquet
```

If files exist, the step produced output successfully.

## 6) If evaluation returns no results yet

This is common at the beginning.

Possible reason:
- Forecast rows are for `target_date = run_date + horizon_days` (for example D+3),
- but actual observations for that target date are not available yet.

In this case:
- ingestion can be correct,
- but matching forecast vs actual can still be empty.

This is expected until enough days pass and actuals become available for forecasted dates.

## 7) Troubleshooting

### A) Missing API key

Symptom:
- provider is skipped with a message about missing key.

Fix:
- add API key in `configs/settings.yaml`,
- or set `enabled: false` for that provider.

### B) No parquet files found

Symptom:
- `ls .../*.parquet` returns no files.

Fix:
- make sure you ran the correct module command,
- check Python environment and installed dependencies,
- verify output paths in `configs/settings.yaml`.

### C) No matched forecast/actual rows yet

Symptom:
- evaluation runs but outputs empty or very small results.

Fix:
- wait until actuals exist for forecasted target dates,
- rerun ingestion and evaluation on later dates,
- confirm date columns are populated correctly (`target_date` vs `date`).

---

Portfolio note: this checklist demonstrates practical operational understanding, not only code implementation.

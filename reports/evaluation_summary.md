# Evaluation Summary — Torrevieja Weather Forecast Accuracy

## Project Goal

This project checks how accurate weather forecasts are for **Torrevieja (Spain)** when predicting **daily maximum temperature (`tmax`) 3 days ahead (D+3)**.

Main business question:

> Which forecast provider should we trust more for D+3 maximum temperature in Torrevieja?

## Metric Used: MAE (Mean Absolute Error)

We use:

- **Absolute error** for each forecasted day:
  `abs_error_c = |forecast_tmax_c - actual_tmax_c|`
- **MAE** as the average of all absolute errors for a provider.

In simple words:

- MAE tells us, on average, how many °C the forecast misses by.
- If MAE = 1.5, the provider is wrong by about **1.5°C** on average.

## How to run

From the repository root:

1. Ingest forecasts:
   ```bash
   python -m src.pipelines.ingest_forecast
   ```
2. Ingest actual observations:
   ```bash
   python -m src.pipelines.ingest_actuals
   ```
3. Run evaluation:
   ```bash
   python -m src.pipelines.run_evaluation
   ```

## Expected outputs

After running the full flow, you should get:

- Forecast raw data in:
  - `data/raw/forecasts/*.parquet`
- Actuals raw data in:
  - `data/raw/actuals/*.parquet`
- Evaluation outputs in:
  - `data/processed/evaluation/evaluation_detailed_<run_date>.parquet`
  - `data/processed/evaluation/evaluation_mae_<run_date>.parquet`

## How to interpret results

1. Open `evaluation_mae_<run_date>.parquet`.
2. Compare `mae_c` values by provider.
3. Rank providers from lowest MAE to highest MAE.

### Example interpretation

- **Lower MAE = better forecast quality**.
- If provider A has MAE = 1.2 and provider B has MAE = 2.0,
  provider A is more accurate for this evaluation period.

## Portfolio note

This MVP is intentionally simple and transparent:

- clear data contract,
- reproducible pipelines,
- easy-to-explain metric,
- direct business interpretation.

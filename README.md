# Weather Forecast Accuracy (Torrevieja, Spain)

## In 20 Seconds

- Goal: compare **5 forecast providers** for Torrevieja and identify which is most reliable for **D+3 daily maximum temperature (`tmax_c`)**.
- Method: ingest forecasts and Meteostat observations, match them by target date, and calculate **absolute error** and **MAE**.
- Automation: run the pipeline on a schedule with GitHub Actions.
- Public outputs: versioned CSV datasets, a Markdown evaluation report, and a static dashboard served by GitHub Pages.

## Live dashboard

The static dashboard is designed to be published at:

**https://krzysztofslomkowski.github.io/weather-forecast-accuracy/**

To enable it in GitHub:

1. Open the repository **Settings**.
2. Select **Pages**.
3. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
4. Select branch **main** and folder **/docs**.
5. Click **Save**.

The dashboard reads local CSV files from `docs/data/`:

- `docs/data/forecasts.csv`
- `docs/data/actuals.csv`
- `docs/data/evaluation_detailed.csv`
- `docs/data/evaluation_mae.csv`

These files are copied from `reports/data/` by `.github/workflows/daily_weather_pipeline.yml` after every successful pipeline run. The frontend contains no API keys and does not query Supabase.

To preview the site locally, serve the repository over HTTP rather than opening `index.html` directly:

```bash
python -m http.server 8000 --directory docs
```

Then open `http://localhost:8000`.

## Key Insight (Early Results)

- The evaluation pipeline is implemented and the production-like historical sample is still growing.
- Provider rankings should be treated as directional until more matched observations accumulate.
- The dashboard does not hard-code a winner. Every KPI, rank and chart is calculated from the public CSV files.
- When no D+3 forecast has a matching actual observation, the dashboard displays an explicit empty state rather than fabricated results.

A portfolio-ready data analytics project that evaluates which weather forecast provider is most reliable for predicting **daily maximum temperature (`tmax_c`) 3 days ahead (D+3)** in **Torrevieja, Spain**.

---

## 1) Project Overview

This project builds a small but realistic forecast evaluation system:

1. collect daily forecasts from multiple providers,
2. collect observed daily weather data,
3. compare forecasts with actuals on matching dates,
4. calculate row-level absolute error and provider-level MAE,
5. write reproducible public datasets and reports,
6. publish the latest results through a static dashboard.

The project is intentionally practical, readable, and suitable for a portfolio discussion or technical interview. It is a reproducible evaluation pipeline rather than a one-off notebook analysis.

## 2) Business Question

> Which weather forecast provider is most accurate for daily maximum temperature in Torrevieja at D+3?

## 3) Why This Project Matters

Forecast quality affects planning decisions in travel, outdoor events, operations, staffing, and risk management.

This project demonstrates a disciplined comparison based on:

- a consistent data contract,
- the same forecast horizon for every provider,
- reproducible ingestion and evaluation,
- an interpretable metric,
- automated, versioned public outputs.

## 4) Tech Stack

- **Python 3.11**
- **pandas**
- **requests**
- **Meteostat**
- **PyYAML**
- **Parquet** via `pyarrow`
- **GitHub Actions**
- **HTML, CSS and vanilla JavaScript**
- **GitHub Pages**

## 5) Data Sources

### Forecast providers

1. Open-Meteo
2. WeatherAPI
3. OpenWeatherMap
4. Visual Crossing
5. Tomorrow.io

Providers that require API keys are skipped gracefully when their key is unavailable.

### Actual observations

- Meteostat daily observed weather

## 6) Architecture

The active mode is configured in `configs/settings.yaml`:

```yaml
pipeline_mode: github_csv
```

In this mode:

- GitHub Actions runs the pipeline,
- cumulative public datasets are stored in `reports/data/`,
- the workflow copies dashboard datasets to `docs/data/`,
- GitHub Pages serves the static frontend from `docs/`.

Supabase was used in an earlier data-layer iteration and remains optional. The pipeline and dashboard must not require an active Supabase project.

## 7) Project Structure

```text
/
  README.md
  requirements.txt
  .github/
    workflows/
      daily_weather_pipeline.yml

  configs/
    settings.yaml

  data/
    raw/
      forecasts/
      actuals/
    processed/
      evaluation/

  reports/
    evaluation_summary.md
    run_checklist.md
    data/
      forecasts.csv
      actuals.csv
      evaluation_detailed.csv
      evaluation_mae.csv

  docs/
    index.html
    styles.css
    app.js
    .nojekyll
    data/
      forecasts.csv
      actuals.csv
      evaluation_detailed.csv
      evaluation_mae.csv

  src/
    providers/
    pipelines/
    evaluation/
    reporting/
    storage/
    utils/
```

## 8) Data Contract

### Forecast records

- `provider`
- `run_date`
- `target_date`
- `horizon_days`
- `tmax_c`

### Actual records

- `date`
- `tmax_c`

### Detailed evaluation records

- `provider`
- `run_date`
- `target_date`
- `forecast_tmax_c`
- `actual_tmax_c`
- `abs_error_c`

### MAE summary

- `rank`
- `provider`
- `observations_count`
- `mae_c`

The dashboard derives provider bias from the detailed evaluation rows:

```text
bias_c = mean(forecast_tmax_c - actual_tmax_c)
```

## 9) Methodology

1. Ingest forecasts for Torrevieja at latitude `37.9780`, longitude `-0.6822`.
2. Keep the configured forecast horizon fixed at D+3.
3. Ingest observed daily maximum temperature from Meteostat.
4. Match records where `forecast.target_date == actual.date`.
5. Calculate row-level absolute error:

   ```text
   abs_error_c = |forecast_tmax_c - actual_tmax_c|
   ```

6. Aggregate provider-level MAE:

   ```text
   mae_c = mean(abs_error_c)
   ```

7. Rank providers from lowest to highest MAE.

Lower MAE means better accuracy for this specific location, horizon and sample.

## 10) How to Run

From the repository root:

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Confirm the location, horizon, provider flags and mode in `configs/settings.yaml`.
3. Export API keys for providers that require them.
4. Run forecast ingestion:

   ```bash
   python -m src.pipelines.ingest_forecast
   ```

5. Run actual ingestion:

   ```bash
   python -m src.pipelines.ingest_actuals
   ```

6. Run evaluation and reporting:

   ```bash
   python -m src.pipelines.run_evaluation
   ```

For a beginner-friendly operational guide, see `reports/run_checklist.md`.

## 11) Automated Workflow

`.github/workflows/daily_weather_pipeline.yml` runs:

- manually through `workflow_dispatch`,
- daily on a UTC cron schedule,
- after relevant changes to pipeline code, configuration, workflow files, or static dashboard source files.

After a successful run, the workflow:

1. updates `reports/data/*.csv`,
2. updates `reports/evaluation_summary.md`,
3. copies the four public CSV files to `docs/data/`,
4. commits generated report and dashboard data when they changed,
5. uploads pipeline outputs as a workflow artifact.

Generated commits do not create a workflow loop because the `push.paths` filter excludes changes limited to `reports/**` and `docs/data/**`.

## 12) Public Outputs

### Source-of-truth reporting layer

- `reports/data/forecasts.csv`
- `reports/data/actuals.csv`
- `reports/data/evaluation_detailed.csv`
- `reports/data/evaluation_mae.csv`
- `reports/evaluation_summary.md`

### GitHub Pages data layer

- `docs/data/forecasts.csv`
- `docs/data/actuals.csv`
- `docs/data/evaluation_detailed.csv`
- `docs/data/evaluation_mae.csv`

The duplicated `docs/data/` layer is intentional: it gives the static site stable relative paths while keeping the reporting outputs clearly separated.

## 13) Dashboard Behavior

The dashboard calculates from CSV data at runtime:

- best provider,
- best MAE,
- provider count,
- completed comparison count,
- target-date range,
- latest available data date,
- provider ranking,
- provider bias,
- MAE bars,
- absolute-error time series,
- daily wins.

No winner or metric value is hard-coded. Empty CSV files produce the following state:

> No completed comparisons yet. The dashboard will update automatically once D+3 forecasts have matching actual observations.

## 14) Supabase Status

Supabase is optional and is not a runtime dependency for the public project.

- The static site does not load the Supabase JavaScript client.
- No Supabase URL, anonymous key, service key, or other secret is present in the frontend.
- GitHub-versioned CSV files are the public data interface.
- The scheduled pipeline is designed to operate in `github_csv` mode.

## 15) Limitations

- The benchmark covers one city: Torrevieja.
- The current comparison focuses on one target: daily maximum temperature.
- The current ranking covers one horizon: D+3.
- Early results are based on a limited and growing sample.
- API providers can differ in product definitions, update timing, plan limits and availability.
- The result is not a universal ranking of all weather forecast providers.

## 16) Portfolio Signals

This project demonstrates:

- API ingestion,
- normalization into a shared data contract,
- cumulative CSV and Parquet storage,
- scheduled automation,
- reproducible evaluation logic,
- metric-driven decision making,
- static dashboard engineering,
- graceful empty states,
- secret-free frontend deployment.

## 17) Next Steps

- Accumulate a longer evaluation window across seasons.
- Add automated data-contract and evaluation tests.
- Compare additional horizons such as D+1, D+5 and D+7.
- Add uncertainty intervals and significance-aware provider comparisons.
- Segment results by month, season and temperature regime.

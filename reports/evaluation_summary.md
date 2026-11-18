# Weather Forecast Accuracy — Torrevieja, Spain

Generated automatically: **2026-11-18 01:35 UTC**.

## Business question

Which forecast provider is most accurate for daily maximum temperature in Torrevieja at D+3?

## Method

The pipeline stores daily provider forecasts, stores observed daily maximum temperatures, matches `target_date` to the actual observation date, and ranks providers by MAE.

Lower MAE means a more accurate provider for this location and horizon.

## Current result

Best provider so far: **open-meteo** with MAE **0.94°C**.

| Metric | Value |
| --- | --- |
| Providers compared | 3 |
| Completed comparisons | 223 |
| Target-date range | 2026-08-09 → 2026-11-17 |

## Provider ranking

| rank | provider | observations_count | mae_c | bias_c |
| --- | --- | --- | --- | --- |
| 1 | open-meteo | 92 | 0.94 | -0.45 |
| 2 | weatherapi | 38 | 1.08 | -0.87 |
| 3 | openweathermap | 93 | 1.55 | -1.39 |

## Daily wins

| provider | daily_wins |
| --- | --- |
| open-meteo | 60 |
| openweathermap | 24 |
| weatherapi | 9 |

## Public data files

- `reports/data/forecasts.csv`
- `reports/data/actuals.csv`
- `reports/data/evaluation_detailed.csv`
- `reports/data/evaluation_mae.csv`

## Limitations

This result is specific to one location, one forecast horizon, and the available sample size. It should be treated as an empirical local benchmark, not as a universal ranking of weather providers.

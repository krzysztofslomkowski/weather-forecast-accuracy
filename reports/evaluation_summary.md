# Weather Forecast Accuracy — Torrevieja, Spain

Generated automatically: **2026-08-24 07:36 UTC**.

## Business question

Which forecast provider is most accurate for daily maximum temperature in Torrevieja at D+3?

## Method

The pipeline stores daily provider forecasts, stores observed daily maximum temperatures, matches `target_date` to the actual observation date, and ranks providers by MAE.

Lower MAE means a more accurate provider for this location and horizon.

## Current result

Best provider so far: **open-meteo** with MAE **0.73°C**.

| Metric | Value |
| --- | --- |
| Providers compared | 3 |
| Completed comparisons | 31 |
| Target-date range | 2026-08-09 → 2026-08-23 |

## Provider ranking

| rank | provider | observations_count | mae_c | bias_c |
| --- | --- | --- | --- | --- |
| 1 | open-meteo | 15 | 0.73 | -0.40 |
| 2 | weatherapi | 1 | 1.90 | -1.90 |
| 3 | openweathermap | 15 | 2.25 | -2.25 |

## Daily wins

| provider | daily_wins |
| --- | --- |
| open-meteo | 13 |
| openweathermap | 2 |

## Public data files

- `reports/data/forecasts.csv`
- `reports/data/actuals.csv`
- `reports/data/evaluation_detailed.csv`
- `reports/data/evaluation_mae.csv`

## Limitations

This result is specific to one location, one forecast horizon, and the available sample size. It should be treated as an empirical local benchmark, not as a universal ranking of weather providers.

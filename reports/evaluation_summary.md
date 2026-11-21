# Weather Forecast Accuracy — Torrevieja, Spain

Generated automatically: **2026-11-21 23:46 UTC**.

## Business question

Which forecast provider is most accurate for daily maximum temperature in Torrevieja at D+3?

## Method

The pipeline stores daily provider forecasts, stores observed daily maximum temperatures, matches `target_date` to the actual observation date, and ranks providers by MAE.

Lower MAE means a more accurate provider for this location and horizon.

## Current result

Best provider so far: **open-meteo** with MAE **0.96°C**.

| Metric | Value |
| --- | --- |
| Providers compared | 3 |
| Completed comparisons | 228 |
| Target-date range | 2026-08-09 → 2026-11-20 |

## Provider ranking

| rank | provider | observations_count | mae_c | bias_c |
| --- | --- | --- | --- | --- |
| 1 | open-meteo | 94 | 0.96 | -0.39 |
| 2 | weatherapi | 39 | 1.06 | -0.83 |
| 3 | openweathermap | 95 | 1.57 | -1.31 |

## Daily wins

| provider | daily_wins |
| --- | --- |
| open-meteo | 61 |
| openweathermap | 24 |
| weatherapi | 10 |

## Public data files

- `reports/data/forecasts.csv`
- `reports/data/actuals.csv`
- `reports/data/evaluation_detailed.csv`
- `reports/data/evaluation_mae.csv`

## Limitations

This result is specific to one location, one forecast horizon, and the available sample size. It should be treated as an empirical local benchmark, not as a universal ranking of weather providers.

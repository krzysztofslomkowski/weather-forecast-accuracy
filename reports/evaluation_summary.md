# Weather Forecast Accuracy — Torrevieja, Spain

Generated automatically: **2026-11-13 00:16 UTC**.

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
| Completed comparisons | 214 |
| Target-date range | 2026-08-09 → 2026-11-11 |

## Provider ranking

| rank | provider | observations_count | mae_c | bias_c |
| --- | --- | --- | --- | --- |
| 1 | open-meteo | 88 | 0.96 | -0.39 |
| 2 | weatherapi | 37 | 1.07 | -0.83 |
| 3 | openweathermap | 89 | 1.48 | -1.38 |

## Daily wins

| provider | daily_wins |
| --- | --- |
| open-meteo | 53 |
| openweathermap | 27 |
| weatherapi | 9 |

## Public data files

- `reports/data/forecasts.csv`
- `reports/data/actuals.csv`
- `reports/data/evaluation_detailed.csv`
- `reports/data/evaluation_mae.csv`

## Limitations

This result is specific to one location, one forecast horizon, and the available sample size. It should be treated as an empirical local benchmark, not as a universal ranking of weather providers.

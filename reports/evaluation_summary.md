# Weather Forecast Accuracy — Torrevieja, Spain

Generated automatically: **2026-10-12 15:51 UTC**.

## Business question

Which forecast provider is most accurate for daily maximum temperature in Torrevieja at D+3?

## Method

The pipeline stores daily provider forecasts, stores observed daily maximum temperatures, matches `target_date` to the actual observation date, and ranks providers by MAE.

Lower MAE means a more accurate provider for this location and horizon.

## Current result

Best provider so far: **open-meteo** with MAE **0.98°C**.

| Metric | Value |
| --- | --- |
| Providers compared | 3 |
| Completed comparisons | 142 |
| Target-date range | 2026-08-09 → 2026-10-11 |

## Provider ranking

| rank | provider | observations_count | mae_c | bias_c |
| --- | --- | --- | --- | --- |
| 1 | open-meteo | 60 | 0.98 | -0.50 |
| 2 | weatherapi | 21 | 1.27 | -0.94 |
| 3 | openweathermap | 61 | 1.73 | -1.67 |

## Daily wins

| provider | daily_wins |
| --- | --- |
| open-meteo | 43 |
| openweathermap | 13 |
| weatherapi | 5 |

## Public data files

- `reports/data/forecasts.csv`
- `reports/data/actuals.csv`
- `reports/data/evaluation_detailed.csv`
- `reports/data/evaluation_mae.csv`

## Limitations

This result is specific to one location, one forecast horizon, and the available sample size. It should be treated as an empirical local benchmark, not as a universal ranking of weather providers.

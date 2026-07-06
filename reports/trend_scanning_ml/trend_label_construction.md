# Trend label construction

For each rebalance date and target asset/basket, the module scans forward horizons of 7, 14, 21, 30, 45, 60 calendar days.

For each horizon it regresses the forward log price path on time and computes the slope t-statistic.  The selected horizon is the horizon with the largest absolute t-statistic.  The sign label is:

- `+1` when selected t-stat is above the positive threshold.
- `-1` when selected t-stat is below the negative threshold.
- `0` otherwise.

Thresholds were not selected on holdout.  Threshold candidates were embedded into model configurations and selected only through development-period CPCV.

## Stored label fields

- selected horizon
- t-stat
- sign label
- trend strength
- forward realized return
- label confidence

Raw tables:

- `trend_scan_raw.csv`
- `trend_labels.csv`

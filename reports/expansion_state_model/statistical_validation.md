# Statistical validation

## Strategy-level controls

- PBO across overlay configurations: 58.57%
- Deflated Sharpe probability for selected overlay: 11.95%
- Exposure classification: **risk_monitoring_only**
- Minimum exposure rule for replacement: 15% average holdout exposure

## CPCV fold distribution for selected overlay

| Candidate | Fold | Test groups | Fold Sharpe |
|---|---|---|---|
| expansion_filter_t60_14d | 0 | 0,1 | 2.405 |
| expansion_filter_t60_14d | 1 | 0,2 | 0.451 |
| expansion_filter_t60_14d | 2 | 0,3 | 1.907 |
| expansion_filter_t60_14d | 3 | 0,4 | 2.354 |
| expansion_filter_t60_14d | 4 | 0,5 | 2.248 |
| expansion_filter_t60_14d | 5 | 1,2 | 0.032 |
| expansion_filter_t60_14d | 6 | 1,3 | 1.610 |
| expansion_filter_t60_14d | 7 | 1,4 | 1.314 |
| expansion_filter_t60_14d | 8 | 1,5 | 1.251 |
| expansion_filter_t60_14d | 9 | 2,3 | 0.625 |
| expansion_filter_t60_14d | 10 | 2,4 | -1.006 |
| expansion_filter_t60_14d | 11 | 2,5 | -1.041 |
| expansion_filter_t60_14d | 12 | 3,4 | 1.255 |
| expansion_filter_t60_14d | 13 | 3,5 | 1.231 |
| expansion_filter_t60_14d | 14 | 4,5 | 0.692 |

The holdout period was not used to select prediction models, thresholds, or
overlay candidates.

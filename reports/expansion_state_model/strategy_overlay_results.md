# Strategy overlay results

The existing macro risk engine is Layer 1. Expansion-state predictions are only
Layer 2 overlays.

## Overlay selection using development-only CPCV

| Candidate | Overlay | Selection score | Median fold Sharpe | Worst fold | Positive folds | Dev Sharpe | Dev turnover | Dev exposure |
|---|---|---|---|---|---|---|---|---|
| expansion_filter_t60_14d | expansion_threshold_filter | 1.319 | 1.251 | -1.041 | 86.67% | 1.099 | 2.397 | 11.30% |
| expansion_sizing_eth_tilt_e40_l60_7d | expansion_sizing_eth_tilt | 0.942 | 0.924 | -1.101 | 73.33% | 0.618 | 11.977 | 52.68% |
| expansion_sizing_t40_7d | expansion_probability_sizing | 0.924 | 0.909 | -1.116 | 73.33% | 0.616 | 10.988 | 52.68% |
| expansion_filter_t60_7d | expansion_threshold_filter | 0.914 | 0.976 | -1.330 | 73.33% | 0.732 | 3.296 | 10.44% |
| expansion_sizing_eth_tilt_e40_l50_7d | expansion_sizing_eth_tilt | 0.913 | 0.920 | -1.128 | 73.33% | 0.626 | 12.366 | 52.68% |
| eth_leadership_tilt_l60_7d | eth_leadership_tilt | 0.913 | 0.901 | -1.129 | 73.33% | 0.629 | 11.937 | 49.81% |
| eth_leadership_tilt_l50_7d | eth_leadership_tilt | 0.889 | 0.897 | -1.161 | 73.33% | 0.637 | 12.227 | 49.81% |
| expansion_sizing_eth_tilt_e40_l40_7d | expansion_sizing_eth_tilt | 0.883 | 0.890 | -1.179 | 73.33% | 0.613 | 12.117 | 52.68% |
| expansion_sizing_eth_tilt_e40_l50_14d | expansion_sizing_eth_tilt | 0.867 | 0.847 | -1.201 | 80.00% | 0.767 | 8.081 | 51.92% |
| eth_leadership_tilt_l40_7d | eth_leadership_tilt | 0.861 | 0.870 | -1.208 | 73.33% | 0.626 | 11.977 | 49.81% |
| expansion_sizing_eth_tilt_e60_l50_14d | expansion_sizing_eth_tilt | 0.836 | 0.690 | -0.804 | 86.67% | 0.796 | 6.653 | 38.70% |
| expansion_sizing_eth_tilt_e40_l60_14d | expansion_sizing_eth_tilt | 0.824 | 0.803 | -1.198 | 80.00% | 0.744 | 7.761 | 51.92% |
| expansion_sizing_eth_tilt_e50_l50_14d | expansion_sizing_eth_tilt | 0.820 | 0.799 | -1.193 | 80.00% | 0.721 | 7.122 | 47.13% |
| expansion_filter_t40_14d | expansion_threshold_filter | 0.819 | 0.591 | -0.474 | 86.67% | 0.582 | 5.894 | 31.23% |
| expansion_sizing_t40_14d | expansion_probability_sizing | 0.817 | 0.801 | -1.219 | 80.00% | 0.746 | 7.192 | 51.92% |
| expansion_sizing_eth_tilt_e40_l40_14d | expansion_sizing_eth_tilt | 0.799 | 0.785 | -1.227 | 80.00% | 0.761 | 7.722 | 51.92% |
| expansion_sizing_eth_tilt_e60_l60_14d | expansion_sizing_eth_tilt | 0.789 | 0.641 | -0.796 | 86.67% | 0.773 | 6.403 | 38.70% |
| expansion_sizing_eth_tilt_e50_l60_14d | expansion_sizing_eth_tilt | 0.777 | 0.754 | -1.188 | 80.00% | 0.695 | 6.813 | 47.13% |
| expansion_sizing_t50_14d | expansion_probability_sizing | 0.769 | 0.752 | -1.212 | 80.00% | 0.693 | 6.493 | 47.13% |
| eth_leadership_tilt_l50_14d | eth_leadership_tilt | 0.756 | 0.734 | -1.193 | 80.00% | 0.829 | 7.662 | 48.85% |
| expansion_sizing_eth_tilt_e50_l40_14d | expansion_sizing_eth_tilt | 0.752 | 0.735 | -1.213 | 80.00% | 0.706 | 7.012 | 47.13% |
| expansion_sizing_t60_14d | expansion_probability_sizing | 0.750 | 0.639 | -0.836 | 80.00% | 0.778 | 6.093 | 38.70% |
| expansion_sizing_eth_tilt_e60_l40_14d | expansion_sizing_eth_tilt | 0.728 | 0.614 | -0.824 | 80.00% | 0.774 | 6.453 | 38.70% |
| eth_leadership_tilt_l60_14d | eth_leadership_tilt | 0.708 | 0.685 | -1.188 | 80.00% | 0.804 | 7.462 | 48.85% |
| expansion_sizing_eth_tilt_e50_l60_7d | expansion_sizing_eth_tilt | 0.702 | 0.748 | -1.253 | 66.67% | 0.461 | 11.627 | 46.55% |
| expansion_sizing_eth_tilt_e50_l50_7d | expansion_sizing_eth_tilt | 0.686 | 0.738 | -1.274 | 66.67% | 0.473 | 11.967 | 46.55% |
| eth_leadership_tilt_l40_14d | eth_leadership_tilt | 0.686 | 0.671 | -1.218 | 80.00% | 0.822 | 7.492 | 48.85% |
| expansion_sizing_t50_7d | expansion_probability_sizing | 0.678 | 0.730 | -1.273 | 66.67% | 0.455 | 10.888 | 46.55% |
| expansion_sizing_eth_tilt_e50_l40_7d | expansion_sizing_eth_tilt | 0.636 | 0.697 | -1.314 | 66.67% | 0.460 | 11.767 | 46.55% |
| expansion_sizing_eth_tilt_e60_l50_7d | expansion_sizing_eth_tilt | 0.632 | 0.550 | -0.950 | 80.00% | 0.428 | 11.018 | 39.27% |
| expansion_sizing_t60_7d | expansion_probability_sizing | 0.624 | 0.541 | -0.948 | 80.00% | 0.414 | 10.189 | 39.27% |
| expansion_sizing_eth_tilt_e60_l40_7d | expansion_sizing_eth_tilt | 0.612 | 0.542 | -0.999 | 80.00% | 0.413 | 10.768 | 39.27% |
| expansion_sizing_eth_tilt_e60_l60_7d | expansion_sizing_eth_tilt | 0.602 | 0.539 | -0.922 | 73.33% | 0.421 | 10.778 | 39.27% |
| expansion_filter_t50_14d | expansion_threshold_filter | 0.442 | 0.429 | -1.120 | 73.33% | 0.589 | 5.194 | 22.41% |
| expansion_filter_t50_7d | expansion_threshold_filter | 0.380 | 0.380 | -1.066 | 66.67% | 0.279 | 8.690 | 19.83% |
| expansion_filter_t40_7d | expansion_threshold_filter | 0.225 | 0.148 | -0.757 | 66.67% | 0.181 | 9.689 | 32.47% |

## Holdout cost sensitivity for selected overlay

| Cost bps | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure |
|---|---|---|---|---|---|---|---|
| 10 | 5.98% | 0.943 | 0.814 | -5.06% | 1.182 | 2.035 | 4.55% |
| 25 | 5.65% | 0.894 | 0.779 | -5.16% | 1.095 | 2.035 | 4.55% |
| 50 | 5.12% | 0.812 | 0.718 | -5.34% | 0.958 | 2.035 | 4.55% |
| 100 | 4.05% | 0.649 | 0.586 | -5.83% | 0.694 | 2.035 | 4.55% |

## Selected overlay decision frequencies in holdout

| Decision | Frequency |
|---|---|
| macro_risk_off_cash | 55.26% |
| expansion_not_confirmed_reduced | 44.74% |

# Untouched holdout results

The champion was selected using 2022–2024 validation only. No model, label, rejection, or risk-mode choice was changed after inspecting 2025–2026. The pre-specified model may refit quarterly using information whose labels had matured before each live decision.

| Configuration | CAGR | Sharpe | Max DD | Volatility |
|---|---|---|---|---|
| no_ml_filter | -3.83% | -0.123 | -26.99% | 18.22% |
| gradient_boosting__binary_filter | -12.23% | -0.805 | -22.58% | 14.84% |

- Champion holdout rejection rate: 35.92%
- Holdout start: 2025-01-01
- Holdout end: 2026-06-22

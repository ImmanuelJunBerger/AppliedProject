# Research Report Template

## Research question

Can machine learning dynamically allocate capital across multiple cryptocurrency trading strategies to improve risk-adjusted returns relative to static allocations, standalone strategies, and buy-and-hold benchmarks?

## Hypotheses

- Null: ML allocation does not improve after-cost risk-adjusted performance versus strong baselines.
- Alternative: ML allocation improves after-cost risk-adjusted performance with robustness across universes, costs, and regimes.

## Required evidence before deployment

- Walk-forward results with stored historical predictions and allocations.
- After-cost performance at 0, 10, 25, 50, and 100 bps.
- Baseline comparisons against BTC, ETH, 50/50 BTC/ETH, equal-weight universe, equal-weight strategies, and standalone strategies.
- Ablations by feature group and strategy.
- Subperiod analysis for bull, bear, and sideways regimes.
- Capacity estimates based on turnover and ADV participation.

## Deployment architecture

1. Daily data ingestion and validation.
2. Monthly universe reconstruction.
3. Feature generation with enforced lagging.
4. Scheduled model retraining and weekly prediction.
5. Reasoning-layer approval with position, strategy, volatility, and turnover controls.
6. Paper-trading execution adapter.
7. Monitoring for slippage, drift, drawdown, and data-quality failures.

## Conclusion policy

The final conclusion must state whether ML adds value only after reviewing robust, after-cost walk-forward evidence. If evidence is mixed or weak, the correct conclusion is non-deployment and further research.

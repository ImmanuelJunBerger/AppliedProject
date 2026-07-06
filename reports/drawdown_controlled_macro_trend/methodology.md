# Methodology

The study tests predeclared BTC/ETH/cash architectures only:

- BTC-only macro trend with drawdown control.
- ETH-only macro trend with drawdown control.
- 50/50 BTC/ETH macro trend with drawdown control.
- BTC/ETH dual-momentum macro trend with drawdown control.
- Frozen macro allocation plus drawdown-control overlay.
- Frozen macro allocation plus volatility-managed exposure overlay.
- Frozen macro allocation plus CPPI/TIPP-style portfolio-insurance overlay.

Allowed inputs are lagged macro-regime state, BTC/ETH trend confirmation, realized volatility, and portfolio drawdown state.  No trend-scanning labels, future labels, ETF/options/on-chain data, LLM signals, leverage, shorts, or top-universe allocation are used.

Development period: 2019-07-05 to 2024-12-31.
Locked holdout: 2025-01-01 to 2026-06-22.

Selection uses a predeclared development score:

- 35% CPCV median Sharpe.
- 20% development max-drawdown improvement.
- 15% CPCV worst-fold Sharpe.
- 10% exposure quality.
- 10% turnover.
- 10% simplicity / interpretability.

Holdout is reported only after development selection.

Portfolio-insurance limitation: CPPI/TIPP is path-dependent and can suffer gap risk.  A weekly rebalance cannot guarantee the floor through overnight or multi-day crypto crashes.

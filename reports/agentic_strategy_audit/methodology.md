# Methodology

The exact meaning of FUGO is not confirmed.  This study treats it as a provisional agentic-audit framework inspired by process reward models, TRINITY/Conductor-style orchestration, verifier agents, and role-specific evaluation.

## Role agents

1. Facts Agent: checks metric availability, locked holdout, costs, and no holdout reselection.
2. Understanding Agent: checks investment logic, explainability, and AP research fit.
3. Governance Agent: checks PBO, DSR, bootstrap CI, tested configurations, exposure, turnover, cash-driven Sharpe risk, and model complexity.
4. Outcome Verifier: combines role scores with holdout Sharpe, CAGR, drawdown, exposure, turnover, and 50 bps cost survival.

## Fixed process reward

`process_reward = 0.25*facts + 0.25*understanding + 0.30*governance + 0.20*outcome`

Weights were fixed before scoring and were not optimized on holdout.

## Monte Carlo audit paths

For each strategy, 100 seeded paths randomly sample one of three audit personalities: conservative institutional allocator, balanced quant researcher, and aggressive growth allocator.

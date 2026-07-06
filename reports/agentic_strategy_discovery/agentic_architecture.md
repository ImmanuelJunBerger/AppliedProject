# Agentic architecture

The workflow is deterministic and auditable.

1. Strategy Thinker: generates economically motivated hypotheses from prior evidence.
2. Feature Worker: maps each hypothesis to existing point-in-time-safe local features.
3. Strategy Worker: converts each hypothesis into a deterministic BTC/ETH/cash rule.
4. Verifier: rejects lookahead, unavailable data, broad kitchen-sink feature use, holdout tuning, low exposure, excessive turnover, unclear rationale, and similarity to rejected full-feature ML.

No LLM calls occur inside historical backtest loops. Final trading rules are reproducible without live LLM calls.

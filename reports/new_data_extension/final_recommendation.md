# Final recommendation

1. What new datasets were actually available? Blockchain.com BTC active addresses/transaction count, Binance derivatives/crowding, and WRDS macro/vintage risk variables.
2. Which datasets were rejected and why? ETF flows, full options surfaces, exchange-flow/MVRV/realized-cap/holder metrics, liquidations, and CME/COT positioning were rejected or classified future-work because they lacked usable local point-in-time history.
3. Which genuine new / alternative-data features reached Tier 1? funding_change.
4. Which Tier-1 features are additional macro / WRDS extensions? credit_spread_level.
5. Did new data add information beyond existing macro/crypto features? Not enough under the corrected genuine-new-data gate. The available macro-extension evidence is useful but should not trigger a new alternative-data strategy.
6. Did any new-data strategy beat btc_eth_macro_gate_balanced? No strategy was run because the corrected genuine-new-data Tier-1 feature gate failed.
7. Did any improvement survive transaction costs and statistical controls? Not applicable; no strategy passed the data/feature gate.
8. Should any new data be added to the final AP strategy? No.
9. Should the new data work be main-body evidence, appendix, or future work? Include a concise data-inventory finding in the main body, with detailed feature research in an appendix; treat production use as future work.

Final conclusion: **Genuine new alternative data was insufficient for strategy replacement; keep btc_eth_macro_gate_balanced unchanged and classify macro extensions as future research evidence.**

# Systematic Cryptocurrency Trading: Robust Discovery and Validation of Crypto Trading Rules

Track 1 is clean development-only selection. Track 2 is exploratory. **Selected using development plus 2025 audit evidence; requires a new untouched paper-monitoring period.**

Tested 520 candidates across macro, trend, volatility, crash, recovery, on-chain proxy, DeFi/liquidity proxy, funding, relative-value, ML-score, state-machine, and ensemble families.

Available APIs/data: accepted Binance spot/funding concepts, DefiLlama-style TVL/stablecoins, and existing WRDS/local macro; rejected/future-work key-gated vendor on-chain, archive RPC, historical depth/options, and broad CoinGecko without point-in-time membership.

Best clean development-only strategy: `lab_0473_state_machine` (state_machine), development Sharpe 25 bps 1.592, audit Sharpe 25 bps 1.074.

Best exploratory strategy: `lab_0473_state_machine` (state_machine), development Sharpe 25 bps 1.592, audit Sharpe 25 bps 1.074. Selected using development plus 2025 audit evidence; requires a new untouched paper-monitoring period.

Dual Sharpe > 1.0 candidates: 9. Without macro: 3. With on-chain proxies: 0. With exposure > 40%: 4. Best target family: `regime_transition`. Best model family: `state_machine`. Best strategy family: `state_machine`.

ETH/EVM/on-chain, DeFi/liquidity, and derivatives/funding proxy strategies were tested, but real API-cached data should be added before claims about crypto-native alpha.

Recommended title: **Systematic Cryptocurrency Trading: Robust Discovery and Validation of Crypto Trading Rules**.

Final conclusion: **C. An exploratory strategy beats the baseline but used 2025 for selection. Treat it as a paper-monitoring candidate only.**

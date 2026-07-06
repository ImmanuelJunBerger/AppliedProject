# Public crypto-native hypothesis library

These are research hypotheses, not strategy results.

| Hypothesis | Data required | Test design | Expected failure mode |
|---|---|---|---|
| Stablecoin liquidity expansion improves BTC/ETH timing | DefiLlama aggregate stablecoin supply | Compare BTC/ETH trend exposure with and without stablecoin expansion gate. | Stablecoin growth may lag price rallies or reflect flight-to-cash rather than risk appetite. |
| TVL contraction identifies hostile crypto liquidity regimes | DefiLlama chain/protocol TVL | Add TVL trend/drawdown gate to BTC/ETH/cash system. | TVL is DeFi-specific and may miss centralized-exchange liquidity. |
| 4h BTC/ETH deterioration improves weekly drawdown control | Binance 4h klines | Require positive 4h trend and limited 4h drawdown before weekly exposure. | Intraday filters can overreact and reduce exposure during profitable recoveries. |
| BTC/ETH dominance shifts predict altcoin fragility | CoinGecko global/dominance snapshots | Use dominance trend as a risk-off feature for altcoin baskets after historical snapshots exist. | Current CoinGecko category/dominance snapshots are insufficient for point-in-time backtests unless stored prospectively. |
| Token unlock pressure weakens asset-level momentum | Token unlock calendar | Exclude assets with large upcoming unlocks as % market cap. | Public unlock data may be incomplete, revised, or unavailable without a licensed provider. |

The first tradable hypothesis is deliberately narrow: stablecoin liquidity plus
BTC/ETH trend and drawdown controls for BTC/ETH/cash only.

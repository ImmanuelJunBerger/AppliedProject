# Testable hypothesis library

## Test contract

These are hypotheses, not findings. Unless specified otherwise, the decision timestamp is 00:00 UTC, features use only records published by that time, and the primary horizon is the next seven days. Each hypothesis is tested first as an incremental feature block against a price-only baseline containing lagged realized volatility (1/7/30 days), returns, volume, turnover, liquidity proxies, breadth, dispersion, correlation and BTC dominance.

For every test:

- freeze transforms, direction and horizon before the untouched holdout;
- lag vendor data by its observed publication delay;
- report rolling-fold effect sign, forecast-loss change and calibration;
- repeat with a second reasonable definition, not an open-ended search;
- control false discovery across all hypotheses and configurations;
- reject the hypothesis if the incremental gain is unstable, economically negligible, or dependent on one episode/provider.

Priority **A** hypotheses are candidates for the first study; B are secondary extensions; C require costly or fragile data.

## Hypotheses

| ID | Priority | Testable hypothesis and expected direction | Rationale | Required data | Expected mechanism | Primary falsification test |
|---|:---:|---|---|---|---|---|
| H1 | A | **Funding × OI predicts volatility expansion:** extreme absolute funding combined with rising aggregate OI increases next-7-day realized volatility. | Funding measures crowded directional demand; OI measures leverage outstanding. Either alone is ambiguous. | Multi-venue funding, contract OI, spot prices, contract metadata | Crowded leveraged positions create liquidation-sensitive inventory and forced trading. | No stable incremental forecast-loss improvement over lagged volatility, or sign reverses after venue/2021 controls. |
| H2 | A | **OI growth with flat spot price predicts later volatility:** unusually high OI growth conditional on small contemporaneous returns raises future volatility. | Leverage can accumulate before price resolves direction. | OI, spot/perpetual returns, volume | Latent position imbalance increases sensitivity to news and margin shocks. | Effect disappears when normalized by dollar volume and contract launches. |
| H3 | A | **Funding dispersion predicts market dispersion:** wider cross-contract funding dispersion raises next-week cross-sectional return dispersion. | Heterogeneous speculative demand should produce heterogeneous asset moves. | Asset-level funding panel, point-in-time universe, returns | Asset-specific crowding and narratives separate winners and losers without predicting their signs. | No gain versus current return/volatility dispersion and volume breadth. |
| H4 | A | **Basis inversion predicts drawdown risk:** broad negative futures basis or rapid basis compression raises 30-day market drawdown probability. | Backwardation can reveal demand for downside protection or acute balance-sheet stress. | Spot/futures prices, expiries, rates, OI | Risk aversion and forced deleveraging move derivatives below spot before or during stress. | Poor calibration outside the 2022 crisis or no lead after excluding contemporaneous crash hours. |
| H5 | A | **Implied-minus-realized volatility predicts realized-volatility expansion:** a high constant-maturity ATM IV premium raises future RV, controlling for current RV. | Options aggregate forward-looking demand and dealer risk. | Deribit BTC/ETH options surface, spot intraday returns | Informed hedging and market-maker repricing anticipate risk not yet realized. | IV adds no out-of-sample value to HAR-RV, or gain vanishes after quote-staleness filters. |
| H6 | A | **Downside skew predicts drawdown probability:** steeper 25-delta put skew raises next-30-day drawdown probability. | Downside insurance demand is directional tail information. | Constant-maturity options skew, term structure, spot state | Hedgers/informed traders bid puts before negative tail events. | No calibration or PR-AUC gain after controlling for current return, RV and funding/basis. |
| H7 | A | **Liquidity deterioration predicts volatility expansion:** widening spreads, falling depth, and rising Amihud illiquidity raise next-week RV. | A thinner market has larger price impact for the same order flow. | Quotes/order books or low-frequency liquidity estimators, volume, returns | Lower risk-bearing capacity amplifies shocks. | Results occur only in stale/small assets or disappear in the top-liquidity universe. |
| H8 | A | **Liquidation imbalance predicts short-horizon continuation of volatility, not direction:** large forced-liquidation volume raises next 1–3 day RV. | Liquidations can cascade through collateral and shared positions. | Long/short liquidations across major venues, OI, intraday returns | Forced orders consume depth and trigger correlated margin events. | Feature is purely contemporaneous once strict event/publication lags are applied. |
| H9 | A | **Correlation concentration predicts systemic volatility:** rising average correlation or first-eigenvalue share increases next-week aggregate RV and drawdown probability. | When a common factor dominates, shocks transmit broadly and diversification fails. | Survivorship-free asset returns, shrinkage covariance/network metrics | Common leverage/liquidity channels synchronize asset responses. | No incremental value over current market RV and breadth; sensitivity to window/asset count is excessive. |
| H10 | A | **Dispersion is persistent but mean-reverting conditionally:** current dispersion predicts next-week dispersion; extreme dispersion with collapsing breadth predicts reversal. | Cross-sectional opportunity states last, but panic dislocations eventually compress. | Point-in-time returns, breadth, volume, sectors/categories | Slow-moving narratives sustain separation; broad deleveraging later restores common-factor dominance. | A simple autoregression is not improved by breadth/regime interactions. |
| H11 | A | **Breadth thrust predicts breadth expansion:** a synchronized rise in positive-volume participation and medium-term trend breadth predicts broader participation next week. | Market participation often diffuses across assets rather than arriving simultaneously. | OHLCV, liquidity-weighted universe, BTC dominance | Marginal capital rotates from leaders to the eligible cross-section. | No improvement over breadth persistence, or apparent effect is caused by newly listed assets. |
| H12 | A | **BTC-dominance decline plus stablecoin exchange inflow predicts breadth expansion.** | Stablecoin buying capacity alongside rotation away from BTC is more specific than either signal alone. | Point-in-time dominance, labeled stablecoin exchange flows, peg status | Deployable quote liquidity enters venues and spreads into altcoins. | Effect disappears after excluding treasury/bridge transfers, depegs, and 2021-specific observations. |
| H13 | B | **BTC exchange net inflow predicts drawdown risk:** unusually high entity-adjusted BTC deposits to exchanges raise next-7/30-day drawdown probability. | Deposits can create immediately saleable inventory. | Point-in-time exchange labels, inflows/outflows, BTC supply/volume | Holders move coins toward venues before selling or collateralizing. | Results vanish using label-vintage data or after removing exchange wallet reshuffles. |
| H14 | B | **Sustained exchange outflow reduces drawdown risk only in calm leverage states.** | Self-custody can reduce liquid sell inventory, but cannot offset a leveraged unwind. | Exchange net flows, funding/OI, RV, entity labels | Lower venue inventory reduces immediate sell capacity when derivatives are not stressed. | Main effect has no interaction with leverage state or is unstable across providers. |
| H15 | B | **Stablecoin net issuance predicts breadth only when supply reaches active venues/protocols.** | Minting at a treasury is not equivalent to deployable demand. | Issuance/burns, treasury and bridge labels, exchange/DEX flows, peg | Newly created stablecoins become purchasing power after distribution. | Raw issuance performs as well as destination-adjusted flow, or neither adds value over volume/liquidity. |
| H16 | B | **Stablecoin peg stress predicts correlation and volatility expansion.** | Stablecoins are settlement and collateral; depeg risk can become a system-wide funding shock. | Stablecoin prices across venues, supply, redemption/flow data, collateral type | Collateral uncertainty and flight to quality propagate across exchanges and DeFi. | Effect is confined to one idiosyncratic algorithmic stablecoin and does not generalize. |
| H17 | B | **Active-address/fee acceleration predicts future dispersion rather than market direction.** | Uneven network adoption should distinguish assets even if it does not forecast aggregate returns. | Chain-normalized activity, fees, transactions, market data | Protocol-specific usage generates heterogeneous attention and capital allocation. | Cross-chain normalization and asset fixed effects eliminate the relationship. |
| H18 | B | **MVRV/SOPR extremes predict downside-tail state, not ordinary returns.** | Broad unrealized profit and realized-profit taking may create fragile holder inventory. | Point-in-time realized cap, MVRV, SOPR, supply age, returns | Profitable holders have greater incentive/capacity to sell during a catalyst. | No drawdown-calibration improvement over trend, RV and age/supply controls; provider revisions explain the result. |
| H19 | C | **Order-flow toxicity predicts intraday volatility:** adverse-selection and order-book imbalance raise next-hour/next-day RV. | Informed or one-sided flow forces liquidity providers to widen/reduce depth. | Sequenced trades, L2 books, venue status, spreads | Market makers infer informed flow and withdraw liquidity, amplifying impact. | No lead after millisecond alignment, or gains fail across venues and are smaller than feed/latency cost. |
| H20 | C | **Cross-venue fragmentation predicts volatility expansion:** wider synchronized spot/perpetual price dispersion raises next-day RV. | Price disagreement can reveal impaired arbitrage capital or venue-specific stress. | Synchronized multi-venue trades/quotes, fees, transfer status | Limits to arbitrage let shocks remain local until they transmit abruptly. | Signal disappears after stale quotes, outages, withdrawal suspensions and non-executable fees are handled. |
| H21 | C | **Whale-to-exchange transfers predict asset-level volatility but not signed return.** | Large transfers are visible inventory shocks, while intent is ambiguous. | Raw transfers, entity labels, exchange wallets, asset liquidity | Anticipated sale/collateral activity increases uncertainty and order-flow response. | No value after internal/custody/bridge transfers are removed or threshold is liquidity-scaled. |
| H22 | B | **Macro stress interacts with crypto leverage:** rising real yields/USD stress has a larger effect on crypto RV when funding and OI are elevated. | External shocks should matter most when internal positioning is fragile. | Pre-scheduled macro data, rates/FX, funding, OI, RV | Tighter global liquidity forces reduction of leveraged risk positions. | Interaction does not beat separate macro and leverage terms across rolling regimes. |

## First-wave experiment set

The initial project should test H1–H12 as four pre-registered feature blocks rather than twelve independent fishing expeditions:

1. **Leverage:** funding, OI, basis and their cross-sectional distributions (H1–H4).
2. **Options/tail pricing:** ATM IV, IV–RV, skew and term structure (H5–H6).
3. **Liquidity/forced flow:** low-frequency liquidity and liquidations (H7–H8).
4. **Market structure:** correlation concentration, dispersion, breadth, dominance and stablecoin destination flow (H9–H12).

Primary target: seven-day realized-volatility expansion. Secondary targets: 30-day 10% drawdown probability and seven-day dispersion expansion. Only the primary target determines the main model decision; secondary results are explicitly exploratory unless separately pre-registered.

## Statistical acceptance rule

A hypothesis graduates only if all of the following hold:

- positive incremental skill in at least 70% of outer walk-forward folds;
- improvement over the matched price-only model in the untouched holdout;
- block-bootstrap 95% confidence interval for the paired loss difference excludes zero, or a pre-declared Bayesian posterior probability above 95%;
- no single crisis episode contributes more than half of total loss improvement;
- same directional conclusion under one alternative label definition and reasonable data lag;
- measurable improvement in a pre-declared risk decision, such as volatility-target error or drawdown-loss utility;
- the benefit exceeds data, operational and turnover costs.

Failure is a useful result: it means the price-only risk model remains the deployable choice and the alternative feed should not be procured or maintained.

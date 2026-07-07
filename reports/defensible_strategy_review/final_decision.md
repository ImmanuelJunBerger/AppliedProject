# Defensible strategy review final decision

## Repository map

| Area | Files |
|---|---|
| Strategy implementation | `src/crypto_mlsystem/macro_regime_strategy.py`, `src/crypto_mlsystem/macro_regime_benchmark_analysis.py`, `src/crypto_mlsystem/selected_main_strategy_gross.py`, `src/crypto_mlsystem/asset_level_macro_diagnostics.py` |
| Feature engineering | `src/crypto_mlsystem/features.py`, `src/crypto_mlsystem/wrds_macro_features.py`, `src/crypto_mlsystem/public_crypto_data.py`, `src/crypto_mlsystem/volatility_expansion.py` |
| Data loading | `src/crypto_mlsystem/data.py`, `src/crypto_mlsystem/macro_regime_benchmark_analysis.py::load_default_inputs` |
| Validation/statistics | `src/crypto_mlsystem/cpcv.py`, `src/crypto_mlsystem/volatility_breakout.py`, `src/crypto_mlsystem/asset_level_macro_diagnostics.py` |
| Benchmarks | `src/crypto_mlsystem/macro_regime_benchmark_analysis.py`, `reports/asset_level_macro_diagnostics/metrics.csv` |
| Transaction costs | `configs/default.yaml`, `src/crypto_mlsystem/cross_sectional_momentum.py::COST_LEVELS`, `src/crypto_mlsystem/macro_regime_strategy.py::backtest_weights` |
| Holdout split | `src/crypto_mlsystem/macro_regime_strategy.py`, `src/crypto_mlsystem/cross_sectional_momentum.py` |
| Frozen selected implementation | `src/crypto_mlsystem/macro_regime_benchmark_analysis.py::FIXED_SELECTED` and `configs/frozen/defensible_final_candidate_2026-07-06.yaml` |
| Existing diagnostics | `reports/asset_level_macro_diagnostics/*.csv`, `reports/final_project/*.csv` |

## Methodology audit

- The current code has two development-start conventions: `macro_regime_strategy.py` uses 2020-01-01; diagnostic reporting uses 2019-07-05. This explains some metric differences and should be stated explicitly.
- The locked holdout starts on 2025-01-01 and is used only for final audit tables in this review.
- Cash is an implicit zero-return residual sleeve. No T-bill or collateral-yield proxy is currently credited.
- Crypto-native features are shifted by one day where constructed in the macro-regime dataset. Macro WRDS features are forward-filled to the daily crypto calendar; the review should describe publication-lag risk for any macro series whose timestamp may not equal point-in-time availability.
- Portfolio returns use previous executed weights before same-day target changes, which avoids same-day execution look-ahead in the backtest loop.
- Momentum scores use lagged 63-day returns.
- The -71% to -74% development drawdown is real in the frozen backtest, not just a formatting error. It occurs in the 2021-11-08 to 2022-11-21 crypto bear-market interval while exposure was mostly permitted by the macro gate.

## Economically justified candidate families

| Family | Hypothesis | Mechanism | Required data | Look-ahead risk | Expected failure mode | Validation plan | Rejection criterion |
|---|---|---|---|---|---|---|---|
| A. Asset-level macro decomposition | Current result may be BTC timing, ETH timing, or simple cash timing. | Same macro gate applied to BTC, ETH, and 50/50 BTC/ETH. | Existing BTC/ETH prices and macro features. | Thresholds must remain development-only; macro timestamps must be point-in-time. | Similar performance across BTC/ETH means no asset-allocation alpha. | Development metrics, CPCV, PBO/DSR, cost sensitivity, holdout audit after freeze. | Reject replacement if improvement is only holdout-specific or worsens drawdown/robustness. |
| B. Volatility targeting/risk budgeting | Sharpe may improve via smoother risk sizing. | Lagged realized-vol estimates scale BTC/ETH exposure. | Existing daily prices only. | Realized vol must be lagged; caps/targets predeclared. | Leveraging or excess turnover creates fragile cost sensitivity. | Small standard targets/caps, CPCV and cost checks. | Reject if parameter-dependent or fails at 50 bps. |
| C. Smoothing/hysteresis | Binary gate may be too cash-heavy and turnover-prone. | Separate entry/exit thresholds or weekly/biweekly rebalance. | Existing macro score. | Threshold mining. | Lower whipsaw but missed recoveries. | Predeclare one or two simple rules only. | Reject if improvement relies on arbitrary thresholds. |
| D. Crash-risk overlay | Macro signals are best framed as crash filters. | Use macro gate plus lagged volatility/trend veto. | Existing macro and price data. | Same-day trend/vol use. | Over-filtering with excessive cash. | Drawdown/downside capture, cost sensitivity, exposure diagnostics. | Reject if only cash exposure explains Sharpe. |
| E. Cash/collateral treatment | Zero cash understates total return but can obscure skill. | Add lagged T-bill proxy as separate contribution. | Clean point-in-time cash-yield data. | Revised yield data or look-ahead publication. | Sharpe improvement is collateral yield, not crypto timing. | Report crypto-only and total-return decomposition. | Reject as alpha claim if improvement is cash yield. |
| F. Broader universe | Diversification/momentum may improve allocation. | Point-in-time top universe or top momentum. | Clean survivorship-aware universe. | Survivorship/listing bias. | High drawdowns and turnover dominate. | Existing top10/top20 diagnostics only. | Reject if data universe is incomplete or costs/drawdowns worsen. |
| G. Regime-specific allocation | Risk-on/neutral/risk-off may warrant fixed BTC/ETH/cash rules. | Simple interpretable allocation table by regime. | Existing macro regimes and BTC/ETH prices. | Optimizing allocations on holdout. | Fragile allocation choices. | One predeclared fixed rule, CPCV/cost tests. | Reject if not robust across folds. |
| H. Framing/title redesign | Honest contribution may be defensive risk management. | Reframe claims around drawdown control and crash avoidance. | All existing diagnostics. | Narrative overclaiming after seeing holdout. | Title too broad for BTC/ETH evidence. | Align title with asset scope and evidence. | Reject broad title if no broader-universe support. |

## Development-only validation at 25 bps

| Strategy | Sharpe | CAGR | Vol | Max DD | Calmar | Exposure | Cash | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BTC/ETH 50/50 buy-hold | 0.992 | 56.1% | 71.0% | -76.3% | 0.736 | 100.0% | 0.0% | 0.0 |
| ETH buy-hold | 0.964 | 56.7% | 83.5% | -79.3% | 0.715 | 100.0% | 0.0% | 0.0 |
| BTC buy-hold | 0.926 | 47.2% | 65.2% | -76.6% | 0.617 | 100.0% | 0.0% | 0.0 |
| Equal-weight top10 | 0.745 | 30.0% | 83.1% | -90.9% | 0.330 | 100.0% | 0.0% | 3.46 |
| Pure top10 momentum | 0.656 | 19.2% | 87.9% | -95.0% | 0.202 | 99.9% | 0.1% | 18.75 |
| Frozen BTC/ETH macro gate | 0.618 | 19.2% | 48.5% | -74.1% | 0.259 | 47.1% | 52.9% | 11.18 |
| BTC-only macro gate | 0.613 | 18.3% | 44.1% | -74.9% | 0.244 | 47.1% | 52.9% | 11.18 |
| ETH-only macro gate | 0.578 | 17.3% | 57.1% | -76.4% | 0.226 | 47.1% | 52.9% | 11.18 |
| Top20 macro-gated momentum | 0.459 | 9.3% | 58.8% | -83.5% | 0.112 | 46.7% | 53.3% | 20.61 |
| Top10 macro-gated momentum | 0.267 | -3.2% | 59.9% | -92.5% | -0.035 | 47.0% | 53.0% | 17.96 |

Development-only evidence does not justify selecting a new replacement. Buy-and-hold variants had higher development Sharpe but materially larger volatility, severe drawdowns, no risk-management contribution, and poor holdout audit. Broader-universe and momentum variants had weaker drawdown and turnover profiles. Asset-level macro variants were too close to the frozen BTC/ETH gate to justify a new title based on asset-selection alpha.

## CPCV/PBO/DSR evidence

| Strategy | Median fold Sharpe | Best | Worst | Positive folds | DSR probability | PBO context |
|---|---:|---:|---:|---:|---:|---:|
| Frozen BTC/ETH macro gate | 0.419 | 2.194 | -0.594 | 60.0% | 0.346 | 0.457 |
| BTC-only macro gate | 0.481 | 2.085 | -0.754 | 66.7% | 0.298 | 0.457 |
| ETH-only macro gate | 0.340 | 2.003 | -0.483 | 60.0% | 0.343 | 0.457 |
| BTC/ETH buy-hold | 0.808 | 2.480 | -0.298 | 66.7% | 0.022 | 0.457 |
| Top10 macro-gated momentum | 0.406 | 2.180 | -1.205 | 46.7% | 0.082 | 0.457 |
| Top20 macro-gated momentum | 0.239 | 2.211 | -0.928 | 53.3% | 0.051 | 0.457 |

The PBO context is not attractive; it reinforces a conservative interpretation. The DSR probabilities in the existing diagnostic are holdout-oriented and not strong enough to claim proven alpha.

## Transaction-cost sensitivity for frozen strategy

| Cost bps | Dev Sharpe | Dev CAGR | Dev Max DD | Holdout Sharpe | Holdout CAGR | Holdout Max DD |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.683 | 23.4% | -73.2% | 1.066 | 28.3% | -17.8% |
| 10 | 0.661 | 22.0% | -73.6% | 1.028 | 27.0% | -18.0% |
| 25 | 0.628 | 20.0% | -74.1% | 0.970 | 25.1% | -18.4% |
| 50 | 0.573 | 16.7% | -75.0% | 0.874 | 21.9% | -19.0% |
| 100 | 0.463 | 10.4% | -77.4% | 0.681 | 15.8% | -20.3% |

The strategy remains positive through 50 bps, but cost drag is meaningful because annual turnover is about 10-11x.

## Exposure, turnover, and cash dependence

| Split | Exposure | Cash | Annual turnover | Conditional Sharpe when invested | Missed upside in cash | Avoided downside in cash |
|---|---:|---:|---:|---:|---:|---:|
| Development | 47.1% | 52.9% | 11.18 | 0.814 | 9.364 | 8.173 |
| Holdout | 28.9% | 71.1% | 10.18 | 1.305 | 2.841 | 3.403 |

The result is materially cash-dependent, especially in holdout. That is acceptable only under a defensive risk-management framing.

## Drawdown forensics

| Rank | Period | Max DD | Avg exposure | Regime mode | Risk-off share | Explanation |
|---:|---|---:|---:|---|---:|---|
| 1 | 2021-11-08 to 2022-11-21 | -74.1% | 73.2% | risk_on | 10.8% | Macro gate stayed mostly risk-on/neutral; BTC and ETH losses dominated. |
| 2 | 2020-01-18 to 2020-03-12 | -51.9% | 24.5% | risk_off | 49.1% | COVID crash occurred around regime transition and residual exposure. |
| 3 | 2021-02-21 to 2021-03-25 | -23.8% | 73.5% | risk_on | 15.2% | Exposure was permitted and ETH contribution dominated. |

## Frozen-candidate specification

The final audited specification is frozen in `configs/frozen/defensible_final_candidate_2026-07-06.yaml` before relying on holdout results in this review.

## Locked-holdout audit at 25 bps

| Strategy | Sharpe | CAGR | Vol | Max DD | Calmar | Exposure | Cash | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Frozen BTC/ETH macro gate | 0.970 | 25.1% | 26.6% | -18.4% | 1.361 | 28.9% | 71.1% | 10.18 |
| ETH-only macro gate | 0.945 | 32.2% | 36.2% | -26.0% | 1.239 | 28.9% | 71.1% | 10.18 |
| BTC-only macro gate | 0.898 | 16.9% | 19.5% | -10.7% | 1.583 | 28.9% | 71.1% | 10.18 |
| Top10 macro-gated momentum | 0.226 | 2.6% | 24.7% | -20.0% | 0.129 | 29.1% | 70.9% | 13.16 |
| BTC buy-hold | -0.332 | -21.8% | 44.4% | -51.2% | -0.427 | 100.0% | 0.0% | 0.00 |
| ETH buy-hold | -0.239 | -35.1% | 72.3% | -67.5% | -0.520 | 100.0% | 0.0% | 0.00 |
| BTC/ETH buy-hold | -0.285 | -27.2% | 56.2% | -59.2% | -0.459 | 100.0% | 0.0% | 0.00 |

Holdout confirms drawdown reduction and crash avoidance, but it must not be used to claim the strategy was selected because of holdout Sharpe.

## Recommendation

### A. Best defensible strategy
Retain `btc_eth_macro_gate_balanced`, but explicitly frame it as a defensive BTC/ETH macro-conditioned risk-management strategy. The evidence does not defensibly support switching to a broader crypto universe, pure momentum, or a new BTC-only/ETH-only replacement.

### B. Best defensible title
**“Macro-Conditioned Risk Management for BTC and ETH Allocation: Crash Avoidance versus Alpha”**. This is narrower and more defensive than the current title.

### C. Best defensible research question
**Can macro-regime conditioning improve risk-adjusted performance and drawdown control for systematic BTC/ETH allocation after realistic transaction costs and robust out-of-sample validation?**

### D. Evidence for the decision
Development Sharpe is modest, development max drawdown is severe, CPCV folds are mixed, PBO is not reassuring, and DSR evidence is not strong enough for an alpha claim. However, the frozen strategy is cost-robust through 50 bps, has much lower volatility than buy-and-hold, and the locked holdout shows better drawdown control during a difficult crypto period. The strongest evidence is risk management, not broad allocation alpha.

### E. What the project can claim
- Macro conditioning can reduce BTC/ETH exposure during some adverse periods.
- The selected rule is interpretable, implementable, and tested under costs, CPCV, PBO, DSR, bootstrap, exposure, turnover, and benchmark diagnostics.
- The 2025+ audit is consistent with defensive crash-avoidance value.

### F. What the project cannot claim
- It cannot claim broad cryptocurrency allocation alpha.
- It cannot claim robust superiority to BTC/ETH buy-and-hold on development-period Sharpe.
- It cannot claim the high holdout Sharpe was discovered without selection risk unless the frozen-spec chronology is documented.
- It cannot claim the macro gate eliminated crypto crash risk; the 2021-2022 drawdown proves otherwise.
- It cannot claim returns are independent of cash exposure.

### G. Remaining weakness
The main weakness is that the best defensible result is cash-heavy defensive timing with mixed development validation and severe historical drawdown, not a clean high-Sharpe allocation-alpha strategy.

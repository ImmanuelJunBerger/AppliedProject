# Model-framework comparison

## Decision principle

Model complexity is justified only by repeatable incremental performance over target-specific statistical and price-only baselines. The problem has a small effective sample: crypto history is short, regimes are autocorrelated, labels overlap, and feature availability shrinks the common sample. Thousands of assets or hourly rows do not create thousands of independent crises. This favors regularization, pooled panels, careful validation and compact models.

## Required non-ML baselines

Before the requested ML models, retain:

- historical mean / class rate and persistence;
- HAR-RV and HAR-RV-J for realized volatility;
- EWMA/GARCH as volatility challengers;
- autoregressive robust dispersion and breadth models;
- shrinkage covariance plus autoregressive average-correlation model;
- calibrated logistic regression for drawdown events.

If an ML model cannot beat these, it has not found useful nonlinear structure.

## Comparative scorecard

| Framework | Suitable targets | Complexity | Compute / data need | Interpretability | Deployment suitability | Research role |
|---|---|---:|---|---|---|---|
| Logistic / elastic-net regression | Volatility expansion, drawdown class, high-correlation/breadth class | Low | CPU; works with modest effective sample | High: signed coefficients, odds ratios, calibration | Excellent | Mandatory transparent baseline and likely production candidate for classification |
| Regularized linear/quantile regression | Continuous RV, dispersion, correlation; conditional quantiles | Low | CPU | High | Excellent | Mandatory continuous-target baseline |
| Random Forest | Nonlinear continuous/class targets | Medium | CPU; moderate memory; tolerates interactions | Medium: permutation importance/SHAP, but correlated-feature attribution is unstable | Good | Robust nonlinear challenger; can be poorly calibrated and weak at extrapolation |
| [XGBoost](https://doi.org/10.1145/2939672.2939785) / LightGBM-style boosting | All tabular targets | Medium | CPU/GPU; efficient on panel data | Medium with SHAP and monotonic constraints | Very good | Preferred nonlinear first-line model after linear baselines |
| [LSTM](https://doi.org/10.1162/neco.1997.9.8.1735) | Sequence-to-one/many RV, dispersion and regime forecasts | Medium–high | GPU helpful; careful scaling and sequence construction | Low | Medium | Challenger only if explicit sequences outperform lag-summary features |
| [Temporal Fusion Transformer](https://doi.org/10.1016/j.ijforecast.2021.03.012) | Mixed-frequency, multi-horizon targets with static/past/known inputs | High | GPU; larger clean panel; expensive nested tuning | Medium relative to deep models; variable selection/attention are descriptive | Medium | Later-stage multi-horizon challenger after feature/data pipeline is stable |
| [PatchTST](https://doi.org/10.48550/arxiv.2211.14730) | Long-context multivariate time-series forecasts | High | GPU; benefits from long regular sequences | Low–medium | Medium | Useful for long lookbacks and many related series; awkward with sparse/revised event features |
| [N-BEATS](https://doi.org/10.48550/arxiv.1905.10437) / N-HiTS | Mostly univariate or panel continuous multi-horizon forecasts | Medium–high | GPU helpful; less feature-rich than TFT | Medium for interpretable N-BEATS variants | Medium–good | Clean neural benchmark for RV trajectories; not the natural first model for heterogeneous alternative data |
| [TimesFM](https://doi.org/10.48550/arxiv.2310.10688) | Zero/few-shot numeric time-series forecasts | High pretraining; low inference | Accelerator helpful; local checkpoint/runtime cost | Low | Medium | Zero-shot benchmark for target history; incremental covariate use and domain shift must be tested |
| [TimeGPT](https://doi.org/10.48550/arxiv.2310.03589) | API-based general time-series forecasting | Low local / opaque remote | Vendor API, data transfer, usage cost | Low | Medium–low for sensitive production data | External benchmark; reproducibility, version drift, data governance and covariate support are concerns |
| [Chronos](https://doi.org/10.48550/arxiv.2403.07815) | Probabilistic zero-shot univariate/panel forecasts | High pretraining; medium inference | Local/cloud accelerator; sampling cost | Low | Medium | Distributional zero-shot benchmark for RV; not evidence that alternative features add value |
| Asset correlation graph + tabular model | Correlation regime, systemic RV, dispersion | Medium | CPU; graph recalculated per date | Medium–high: graph statistics are inspectable | Good | Preferred initial graph approach: feed trailing centrality/eigenvalue/density features to linear/boosted models |
| Graph neural network (GCN/GAT/temporal GNN) | Asset-level volatility/dispersion with dynamic relationships | Very high | GPU; large panel; costly graph construction/tuning | Low | Low–medium | Exploratory only after simple graph statistics show stable value |

## Detailed assessment

### Logistic regression

Use standardized, winsorized features, elastic-net regularization, time-decay only if predeclared, and class/sample weights chosen inside the training fold. For drawdown and regime targets, evaluate probability calibration rather than applying a 0.5 threshold. Advantages are stability, transparent sign checks, fast nested validation and easy monitoring. Main limitation: nonlinear interactions such as high OI *and* weak liquidity must be specified or approximated with splines/interactions.

### Random Forest

Random Forest handles nonlinearities and missing-value preprocessing without strict functional assumptions. It averages decorrelated trees, which helps variance, but time-series dependence reduces the independence implied by ordinary resampling. It can overfit rare crisis leaves, extrapolates poorly beyond training ranges, and usually needs probability calibration. Use shallow depth, large leaves, blocked validation and permutation importance computed only out of sample.

### XGBoost / gradient boosting

This is the strongest initial nonlinear candidate for mixed derivatives, liquidity, on-chain and market-state features. It handles interactions, nonlinear thresholds and missingness indicators efficiently. Limit depth, tune within inner walk-forward folds, and consider monotonic constraints where the economic sign is genuinely defensible. SHAP explains fitted associations, not causality. Rejection criterion: performance depends on a few extreme dates or unstable hyperparameters.

### LSTM

LSTMs can learn temporal dependence without manual lag aggregation, but daily risk targets provide few independent sequences and overlapping windows inflate apparent sample size. Use a pooled asset panel or hourly-to-daily sequence if the data are truly point-in-time. Compare with the same raw history summarized into HAR/boosted-tree features. Do not infer value from lower in-sample reconstruction error.

### Temporal Fusion Transformer

TFT is well matched conceptually to static asset metadata, observed historical covariates, known calendar inputs and multi-horizon quantile forecasts. The [original architecture](https://doi.org/10.1016/j.ijforecast.2021.03.012) combines gating, variable selection, recurrent local processing and attention. Its flexibility also expands the tuning space and backtest-overfitting risk. Use only after a common data panel covers several regimes and simpler models already show alternative-data value.

### PatchTST

PatchTST tokenizes segments of a long series and applies channel-oriented transformer processing. It is attractive for long, regular histories of RV, funding, OI and breadth. Sparse chain events, changing asset membership and vendor revisions do not fit naturally. It should forecast the same predeclared label/horizons as simpler models and must not receive future-normalized patches.

### N-BEATS / N-HiTS

These architectures are strong generic multi-horizon forecasters with less architectural machinery than a feature-rich transformer. They are appropriate challengers for the target’s own history and regular covariates. Because the research question is *incremental alternative-data value*, a good N-BEATS target-history forecast is a baseline rather than proof about on-chain/derivatives features.

### Foundation time-series models

[TimesFM](https://doi.org/10.48550/arxiv.2310.10688), [Chronos](https://doi.org/10.48550/arxiv.2403.07815), and [TimeGPT](https://doi.org/10.48550/arxiv.2310.03589) make useful frozen zero-shot benchmarks. Their pretraining can improve generic seasonal/trend forecasting, but crypto leverage events, token listings and 24/7 microstructure are a domain shift. They also do not automatically solve mixed-frequency covariates, point-in-time correctness, universe churn, calibration, or economic decision design. Treat model/version/API as part of the dataset and freeze it for the holdout.

### Graph frameworks

Build a trailing, shrinkage-based asset graph where nodes are eligible assets and edges are denoised correlations, volatility spillovers, or verified economic links. Start with graph summaries—first eigenvalue share, density, clustering, centrality concentration, community count and change rate—fed to logistic/boosted models. This is interpretable and deployable. A temporal GNN is justified only if these summaries show stable outer-fold value and the GNN beats them on the same fixed graph-generation protocol.

## Compute estimates for scoping

These are order-of-magnitude planning estimates for one primary target, not quotations:

| Stage | Hardware | Typical workload |
|---|---|---|
| Linear/HAR/elastic net | Laptop CPU, 16–32 GB RAM | Hundreds of nested rolling configurations in hours |
| RF/XGBoost | 8–32 CPU cores; 32–64 GB RAM | Hundreds to low thousands of bounded configurations in hours to a day |
| LSTM/N-BEATS/PatchTST/TFT | One modern GPU; 32–64 GB system RAM | Tens—not thousands—of predeclared configurations; hours to days |
| Temporal GNN | One or more GPUs plus fast storage | Dynamic graph construction and training; days, high engineering cost |
| Foundation inference | Local accelerator or paid API | Low tuning but material reproducibility, versioning and governance work |

## Recommended model ladder

1. HAR-RV / persistence / shrinkage target-specific baselines.
2. Elastic-net linear/logistic models.
3. Shallow XGBoost and Random Forest challengers.
4. Simple ensembles formed only from outer-fold predictions.
5. TFT or PatchTST only if tabular models demonstrate robust alternative-data signal and sequence information remains in residuals.
6. Frozen foundation-model forecast as a benchmark, not the project core.
7. Graph features before any GNN.

This ladder makes a negative result interpretable. Starting with a transformer would confound target value, data quality, architecture, and tuning freedom.

## Deployment requirements independent of model

- deterministic feature availability and source-timestamp checks;
- probability/quantile calibration monitored by regime;
- explicit missing-provider fallback to the price-only model;
- feature-range, drift, latency and stale-data alarms;
- model/version/data lineage and reproducible training snapshots;
- challenger comparison and rollback;
- bounded predictions and risk rules outside the ML model;
- scheduled retraining chosen in validation, plus event-driven review—not automatic crisis retuning.

## Framework conclusion

For the recommended volatility study, use **HAR-RV + elastic net + shallow XGBoost** as the core comparison. This set is computationally cheap enough for nested walk-forward testing, expressive enough for nonlinear leverage/liquidity interactions, and substantially easier to diagnose and deploy than deep or foundation models. TFT is the most relevant later-stage deep challenger; graph summary features are preferable to a GNN at this stage.

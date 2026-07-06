# Model hierarchy

Complexity is allowed only after the data justifies it. Level 1 models remain
the default; advanced models are rejected unless they improve economic outcomes
after strict validation.

| Level | Models | Allowed when | Acceptance requirement | Status |
|---|---|---|---|---|
| Level 1 | Logistic Regression; Elastic Net Logistic Regression; Random Forest; Gradient Boosting; XGBoost; LightGBM | Always first model family for tabular datasets. | Must improve holdout Sharpe, CAGR, and max drawdown simultaneously without trivial exposure reduction. | Primary candidate set. |
| Level 2 | MLP; shallow neural networks; TabNet; Temporal Fusion Transformer | Only after genuinely new datasets provide enough observations and Level 1 models show non-random signal. | Better calibration, holdout economic value, and stable CPCV; not just better in-sample fit. | Conditional; not justified by current small new-data sample. |
| Level 3 | LSTM; GRU; Transformer architectures | Exploratory only, with dense timestamped sequence data and enough non-overlapping episodes. | Better calibration, holdout performance, and economic performance versus Level 1 and frozen baseline. | Research-only until data density materially improves. |
| Level 4 | Reinforcement Learning; PPO; SAC; DQN | Research-only after deterministic policy/action space and realistic cost/exposure constraints are locked. | Holdout Sharpe and CAGR improve, drawdown remains controlled, turnover remains realistic, and policy is interpretable. | Not acceptable unless it beats the frozen strategy under strict out-of-sample controls. |
| LLM research | Sentiment extraction; topic classification; event detection; regime classification | Only when timestamped text data exists with reliable publication times. | Text-derived features must pass independent feature validation; LLMs cannot generate discretionary trades. | Permitted as feature extraction only. |

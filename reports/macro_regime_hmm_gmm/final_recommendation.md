# Final recommendation

## Decision

**keep btc_eth_macro_gate_balanced**

## Conclusion

Development-selected unsupervised overlay fails locked-holdout replacement criteria; reject it as a replacement and use regimes only for explanation.

## Summary

- Development-selected candidate: `gmm_macro_crypto_direct`.
- Current holdout Sharpe: 0.970.
- Selected holdout Sharpe: -0.890.
- Selected holdout CAGR: -22.74%.
- Selected holdout max drawdown: -38.69%.
- Selected holdout turnover: 4.071x.
- Family PBO: 7.14%.
- Current PBO reference: 61.43%.

HMM/GMM/KMeans regimes are useful for explanation if their states separate
high-risk from low-risk macro environments. They do **not** improve the selected
strategy in this run. The development-selected overlay is rejected as a
replacement because it fails locked-holdout performance criteria. This decision
does not select the best holdout cell.

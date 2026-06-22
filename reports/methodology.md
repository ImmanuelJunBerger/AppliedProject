# Methodology

The framework uses lagged features, standalone strategy returns, walk-forward outer validation, transaction costs, and benchmark comparisons. Random K-fold is invalid for financial series because labels overlap and temporal dependence can leak future information into training.

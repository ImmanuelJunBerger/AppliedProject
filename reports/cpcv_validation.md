# CPCV Validation

Generated 15 CPCV splits with purging and 7-period embargo. Leakage-free validation result: **True**. CPCV is used only inside a fixed training window for hyperparameter tuning, never on future outer test data. Purging removes training observations whose label interval overlaps validation labels. Embargoing removes observations immediately after validation samples to reduce serial-dependence leakage.

from __future__ import annotations
from dataclasses import dataclass
from statistics import mean
from typing import Any
from .cpcv import combinatorial_purged_splits, assert_no_leakage

@dataclass
class TuningResult:
    method: str
    best_params: dict[str, Any]
    best_score: float
    scores: list[dict[str, Any]]
    n_splits: int
    leakage_free: bool


def _accuracy(y_true, y_pred):
    total = len(y_true)
    return 0.0 if total == 0 else sum(a == b for a, b in zip(y_true, y_pred)) / total


def tune_sklearn_classifier(model_factory, param_grid, X, y, method="cpcv", label_horizon=7, embargo=7):
    """Tune hyperparameters only on the supplied training window.

    `X` and `y` must already exclude the outer walk-forward prediction period.
    Supported methods: no_tuning, timeseries, cpcv.
    """
    if method == "no_tuning" or not param_grid:
        return TuningResult(method, {}, float("nan"), [], 0, True)
    n = len(X)
    if method == "timeseries":
        cut_1, cut_2 = n // 3, 2 * n // 3
        splits = [(tuple(range(0, cut_1)), tuple(range(cut_1, cut_2))), (tuple(range(0, cut_2)), tuple(range(cut_2, n)))]
        leakage_free = all(max(tr) < min(te) for tr, te in splits if tr and te)
    elif method == "cpcv":
        cpcv_splits = combinatorial_purged_splits(n, n_groups=min(6, max(3, n // 30)), n_test_groups=1, label_horizon=label_horizon, embargo=embargo)
        splits = [(s.train_indices, s.test_indices) for s in cpcv_splits]
        leakage_free = all(assert_no_leakage(s, label_horizon, embargo, n) for s in cpcv_splits)
    else:
        raise ValueError(f"Unknown tuning method: {method}")
    candidates = [dict(zip(param_grid, vals)) for vals in __import__('itertools').product(*param_grid.values())]
    rows = []
    for params in candidates:
        fold_scores = []
        for tr, te in splits:
            if not tr or not te:
                continue
            model = model_factory(**params)
            model.fit(X.iloc[list(tr)], y.iloc[list(tr)])
            pred = model.predict(X.iloc[list(te)])
            fold_scores.append(_accuracy(list(y.iloc[list(te)]), list(pred)))
        rows.append({"params": params, "score": mean(fold_scores) if fold_scores else float("-inf")})
    best = max(rows, key=lambda r: r["score"])
    return TuningResult(method, best["params"], best["score"], rows, len(splits), leakage_free)

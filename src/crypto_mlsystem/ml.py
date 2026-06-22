import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MODELS = {
    "equal_weight": None,
    "logistic_regression": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, multi_class="auto")),
    "random_forest": lambda: RandomForestClassifier(n_estimators=150, min_samples_leaf=10, random_state=42),
    "gradient_boosting": lambda: GradientBoostingClassifier(random_state=42),
}

def walk_forward_allocations(features, targets, strategy_names, train_min_days=365, prediction_frequency="W-FRI", model_name="logistic_regression"):
    idx = features.index.intersection(targets.dropna().index)
    X = features.loc[idx]; y = targets.loc[idx]
    pred_dates = X.resample(prediction_frequency).last().index.intersection(X.index)
    allocations = []
    for date in pred_dates:
        train_idx = X.index[X.index < date]
        if len(train_idx) < train_min_days:
            continue
        if model_name == "equal_weight":
            probs = pd.Series(1 / len(strategy_names), index=strategy_names, name=date)
        else:
            model = MODELS[model_name](); model.fit(X.loc[train_idx], y.loc[train_idx])
            if hasattr(model, "predict_proba"):
                p = model.predict_proba(X.loc[[date]])[0]; classes = model.classes_
                probs = pd.Series(0.0, index=strategy_names, name=date); probs.loc[classes] = p
            else:
                pred = model.predict(X.loc[[date]])[0]
                probs = pd.Series(0.0, index=strategy_names, name=date); probs.loc[pred] = 1.0
        allocations.append(probs)
    return pd.DataFrame(allocations).fillna(0)

def feature_importance(model, feature_names):
    estimator = model[-1] if hasattr(model, "__getitem__") else model
    vals = getattr(estimator, "feature_importances_", None)
    if vals is None and hasattr(estimator, "coef_"):
        vals = abs(estimator.coef_).mean(axis=0)
    return pd.Series(vals, index=feature_names).sort_values(ascending=False) if vals is not None else pd.Series(dtype=float)

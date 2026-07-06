"""Feature research and engineering before strategy construction.

The goal is to classify candidate predictors before they are allowed into later
strategy design.  The module evaluates asset-level and market-level features with
IC, Newey-West significance, quantile spreads, regime stability, redundancy, and
model-importance checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import STABLE_OR_WRAPPED
from .volatility_expansion import (
    HOLDOUT_END,
    HOLDOUT_START,
    _correlation_features,
    _weighted_dispersion,
    _weighted_mean,
    point_in_time_liquid_universe,
)


REGIMES = {
    "2020_2021_bull": (pd.Timestamp("2020-01-01"), pd.Timestamp("2021-12-31")),
    "2022_bear": (pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")),
    "2023_2024_recovery": (pd.Timestamp("2023-01-01"), pd.Timestamp("2024-12-31")),
    "2025_2026_holdout": (HOLDOUT_START, HOLDOUT_END),
}
HORIZONS = {7: "1w", 14: "2w", 28: "4w"}


@dataclass
class FeatureResearchResult:
    frame: pd.DataFrame
    feature_metadata: pd.DataFrame
    ic_report: pd.DataFrame
    quantile_analysis: pd.DataFrame
    stability_report: pd.DataFrame
    correlation_analysis: pd.DataFrame
    importance: pd.DataFrame
    tiers: pd.DataFrame


def _rank_spearman(x: pd.Series, y: pd.Series) -> float:
    data = pd.concat([x, y], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 5 or data.iloc[:, 0].nunique() < 3 or data.iloc[:, 1].nunique() < 3:
        return np.nan
    return float(data.iloc[:, 0].rank().corr(data.iloc[:, 1].rank()))


def _normal_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return np.nan
    cdf = 0.5 * (1.0 + erf(abs(float(t_stat)) / sqrt(2.0)))
    return float(2.0 * (1.0 - cdf))


def _newey_west_stats(values: pd.Series, lags: int = 4) -> dict[str, float]:
    series = values.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    n = len(series)
    if n < 8:
        return {"mean": np.nan, "se": np.nan, "t_stat": np.nan, "p_value": np.nan, "ci_low": np.nan, "ci_high": np.nan}
    centered = series - series.mean()
    gamma0 = float((centered @ centered) / n)
    variance = gamma0
    max_lag = min(lags, n - 1)
    for lag in range(1, max_lag + 1):
        cov = float((centered.iloc[lag:].to_numpy() @ centered.iloc[:-lag].to_numpy()) / n)
        variance += 2.0 * (1.0 - lag / (max_lag + 1.0)) * cov
    se = sqrt(max(variance, 0.0) / n)
    mean = float(series.mean())
    t_stat = mean / se if se > 0 else np.nan
    return {
        "mean": mean,
        "se": float(se),
        "t_stat": float(t_stat) if np.isfinite(t_stat) else np.nan,
        "p_value": _normal_pvalue(t_stat),
        "ci_low": float(mean - 1.96 * se) if se > 0 else np.nan,
        "ci_high": float(mean + 1.96 * se) if se > 0 else np.nan,
    }


def _safe_pct_change(frame: pd.DataFrame, periods: int) -> pd.DataFrame:
    return frame.pct_change(periods, fill_method=None)


def _pivot(panel: pd.DataFrame, column: str, like: pd.DataFrame | None = None) -> pd.DataFrame:
    pivoted = panel.pivot(index="date", columns="symbol", values=column).sort_index()
    return pivoted.reindex_like(like) if like is not None else pivoted


def _market_series_from_public(public_data: Any, index: pd.DatetimeIndex) -> dict[str, pd.Series]:
    features: dict[str, pd.Series] = {}
    if public_data is None:
        return features
    stable = getattr(public_data, "stablecoins", pd.DataFrame())
    if isinstance(stable, pd.DataFrame) and not stable.empty:
        stable = stable.set_index("date").sort_index()
        for column in (
            "stablecoin_supply_change_7d",
            "stablecoin_supply_change_30d",
            "stablecoin_supply_change_90d",
            "stablecoin_supply_z_90",
        ):
            if column in stable:
                features[column] = stable[column].reindex(index).ffill().shift(1)
        if "stablecoin_supply_usd" in stable:
            features["stablecoin_supply_growth_30d"] = stable.stablecoin_supply_usd.pct_change(30, fill_method=None).reindex(index).ffill().shift(1)
    chain_tvl = getattr(public_data, "chain_tvl", pd.DataFrame())
    if isinstance(chain_tvl, pd.DataFrame) and not chain_tvl.empty:
        all_tvl = chain_tvl[chain_tvl.chain == "all"].set_index("date").sort_index()
        if "tvl" in all_tvl:
            features["tvl_growth_30d"] = all_tvl.tvl.pct_change(30, fill_method=None).reindex(index).ffill().shift(1)
            features["tvl_momentum_90d"] = all_tvl.tvl.pct_change(90, fill_method=None).reindex(index).ffill().shift(1)
    coin_daily = getattr(public_data, "coingecko_coin_daily", pd.DataFrame())
    if isinstance(coin_daily, pd.DataFrame) and not coin_daily.empty:
        market_cap = coin_daily.pivot(index="date", columns="symbol", values="market_cap").sort_index()
        volume = coin_daily.pivot(index="date", columns="symbol", values="volume").sort_index()
        if {"BTC", "ETH"}.issubset(market_cap.columns):
            stable_supply = stable.stablecoin_supply_usd if isinstance(stable, pd.DataFrame) and "stablecoin_supply_usd" in stable else pd.Series(dtype=float)
            denominator = market_cap.BTC + market_cap.ETH + stable_supply.reindex(market_cap.index).ffill()
            features["stablecoin_market_share_proxy"] = (
                stable_supply.reindex(index).ffill() / denominator.reindex(index).ffill()
            ).shift(1)
            features["btc_eth_market_cap_growth_30d"] = (
                (market_cap.BTC + market_cap.ETH).pct_change(30, fill_method=None)
                .reindex(index).ffill().shift(1)
            )
            features["btc_market_cap_share_of_btc_eth"] = (
                market_cap.BTC / (market_cap.BTC + market_cap.ETH)
            ).reindex(index).ffill().shift(1)
        if {"BTC", "ETH"}.issubset(volume.columns):
            features["btc_eth_volume_growth_30d"] = (
                (volume.BTC + volume.ETH).pct_change(30, fill_method=None)
                .reindex(index).ffill().shift(1)
            )
    return features


def build_feature_research_frame(
    panel: pd.DataFrame,
    public_data: Any | None = None,
    volatility_probability: pd.Series | None = None,
    top_n: int = 20,
    min_history_days: int = 180,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    clean = panel.copy().sort_values(["date", "symbol"])
    clean["date"] = pd.to_datetime(clean.date)
    clean = clean[~clean.symbol.isin(STABLE_OR_WRAPPED)]
    weights, _ = point_in_time_liquid_universe(clean, top_n=top_n, min_history_days=min_history_days)
    close = _pivot(clean, "close").reindex_like(weights)
    high = _pivot(clean, "high", close)
    volume = _pivot(clean, "volume", close)
    market_cap = _pivot(clean, "market_cap", close) if "market_cap" in clean else close * volume
    returns = close.pct_change(fill_method=None)
    dollar_volume = close * volume
    eligible = weights > 0

    feature_frames: dict[str, pd.DataFrame] = {}
    metadata: list[dict[str, str]] = []

    def add(name: str, frame: pd.DataFrame | pd.Series, family: str, level: str, rationale: str) -> None:
        if isinstance(frame, pd.Series):
            expanded = pd.DataFrame({symbol: frame for symbol in close.columns}, index=close.index)
        else:
            expanded = frame.reindex_like(close)
        feature_frames[name] = expanded
        metadata.append({"feature": name, "family": family, "level": level, "rationale": rationale})

    for horizon in (7, 21, 63, 126):
        add(f"momentum_{horizon}d", _safe_pct_change(close, horizon).shift(1), "momentum", "asset", f"{horizon}-day lagged price momentum")
    add("momentum_acceleration", (_safe_pct_change(close, 21) - _safe_pct_change(close, 63)).shift(1), "momentum", "asset", "short momentum minus medium-term momentum")
    add("momentum_consistency_63d", (returns > 0).rolling(63).mean().shift(1), "momentum", "asset", "fraction of positive daily returns")
    add("distance_to_50dma", close.shift(1) / close.rolling(50).mean().shift(1) - 1, "trend", "asset", "distance from medium-term moving average")
    add("distance_to_200dma", close.shift(1) / close.rolling(200).mean().shift(1) - 1, "trend", "asset", "distance from long-term trend")
    add("trend_slope_63d", np.log(close).diff(63).shift(1) / 63.0, "trend", "asset", "log-price slope over 63 days")
    add("trend_persistence_63d", (returns > 0).rolling(63).mean().shift(1), "trend", "asset", "positive-return persistence")
    realized_vol = returns.rolling(30).std().shift(1) * np.sqrt(365)
    add("realized_volatility_30d", realized_vol, "volatility", "asset", "annualized trailing realized volatility")
    add("downside_volatility_30d", returns.where(returns < 0, 0.0).rolling(30).std().shift(1) * np.sqrt(365), "volatility", "asset", "annualized downside volatility")
    add("upside_volatility_30d", returns.where(returns > 0, 0.0).rolling(30).std().shift(1) * np.sqrt(365), "volatility", "asset", "annualized upside volatility")
    add("volatility_of_volatility_30d", realized_vol.rolling(30).std().shift(1), "volatility", "asset", "volatility instability")
    jump_threshold = returns.rolling(30).std().shift(1) * 2.0
    add("jump_intensity_30d", (returns.abs() > jump_threshold).rolling(30).mean().shift(1), "volatility", "asset", "frequency of large daily moves")
    add("amihud_illiquidity_30d", np.log((returns.abs() / dollar_volume.replace(0, np.nan)).rolling(30).mean().shift(1) + 1e-12), "liquidity", "asset", "price impact proxy")
    add("turnover_30d", np.log1p(dollar_volume.rolling(30).median().shift(1)), "liquidity", "asset", "median dollar turnover")
    add("volume_acceleration", np.log1p(dollar_volume.rolling(7).mean().shift(1)) - np.log1p(dollar_volume.rolling(30).mean().shift(1)), "liquidity", "asset", "short-term volume expansion")
    add("volume_concentration_7_30", dollar_volume.rolling(7).sum().shift(1) / dollar_volume.rolling(30).sum().shift(1), "liquidity", "asset", "recent share of monthly volume")
    momentum_63 = _safe_pct_change(close, 63).shift(1)
    add("relative_strength_rank", momentum_63.where(eligible).rank(axis=1, pct=True), "cross_sectional", "asset", "point-in-time momentum rank")
    add("percentile_momentum_63d", momentum_63.where(eligible).rank(axis=1, pct=True), "cross_sectional", "asset", "cross-sectional percentile momentum")
    add("volatility_adjusted_momentum_63d", momentum_63 / realized_vol.replace(0, np.nan), "cross_sectional", "asset", "momentum scaled by risk")
    basket_return = _weighted_mean(returns, weights)
    market_breadth = ((momentum_63 > 0) & eligible).sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)
    add("market_breadth", market_breadth.shift(1), "market_regime", "market", "share of liquid universe in positive trend")
    add("cross_sectional_dispersion", _weighted_dispersion(returns, weights).rolling(30).mean().shift(1), "market_regime", "market", "dispersion of asset returns")
    average_corr, _ = _correlation_features(returns, weights, 30)
    add("average_correlation_30d", average_corr.shift(1), "market_regime", "market", "average pairwise correlation")
    wealth = (1 + basket_return.fillna(0.0)).cumprod()
    add("market_drawdown", (wealth / wealth.cummax() - 1).shift(1), "market_regime", "market", "liquid-universe drawdown")
    if volatility_probability is not None:
        add("volatility_expansion_probability", volatility_probability.reindex(close.index).ffill().shift(1), "market_regime", "market", "fixed volatility-expansion forecast")
    if "funding_rate" in clean.columns and clean.funding_rate.notna().any():
        funding = _pivot(clean, "funding_rate", close).shift(1)
        add("funding_rate", funding, "external", "asset", "Binance funding cost/crowding proxy")
        add("funding_rate_change_7d", funding.diff(7), "external", "asset", "funding crowding acceleration")

    for name, series in _market_series_from_public(public_data, close.index).items():
        add(name, series, "external_new_data", "market", f"public crypto-native feature: {name}")

    intraday = getattr(public_data, "binance_4h_daily_features", pd.DataFrame()) if public_data is not None else pd.DataFrame()
    if isinstance(intraday, pd.DataFrame) and not intraday.empty:
        for column in (
            "trend_4h_7d",
            "trend_4h_14d",
            "volatility_4h_7d",
            "volatility_4h_30d",
            "drawdown_4h_30d",
            "volume_shock_4h",
        ):
            if column not in intraday:
                continue
            pivoted = intraday.pivot(index="date", columns="symbol", values=column).reindex_like(close)
            add(column, pivoted, "external_new_data", "asset", f"Binance 4h lagged daily feature: {column}")

    weekly_dates = pd.DatetimeIndex(close.resample("W-FRI").last().index).intersection(close.index)
    rows = []
    for date_ in weekly_dates:
        members = weights.columns[weights.loc[date_] > 0]
        if len(members) == 0:
            continue
        for symbol in members:
            row = {"date": date_, "symbol": symbol}
            for horizon, label in HORIZONS.items():
                future_idx = close.index.searchsorted(date_ + pd.Timedelta(days=horizon))
                if future_idx < len(close.index) and pd.notna(close.at[date_, symbol]):
                    future_date = close.index[future_idx]
                    row[f"future_return_{label}"] = close.at[future_date, symbol] / close.at[date_, symbol] - 1
                else:
                    row[f"future_return_{label}"] = np.nan
            for feature, frame in feature_frames.items():
                row[feature] = frame.at[date_, symbol] if date_ in frame.index and symbol in frame.columns else np.nan
            rows.append(row)
    frame = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)
    metadata_frame = pd.DataFrame(metadata).drop_duplicates("feature")
    return frame, metadata_frame


def _feature_method(frame: pd.DataFrame, feature: str) -> str:
    unique_by_date = frame.groupby("date")[feature].nunique(dropna=True)
    non_null_by_date = frame.groupby("date")[feature].apply(lambda values: values.notna().sum())
    if non_null_by_date.median() < 5 and non_null_by_date.max() >= 1:
        return "asset_time_series"
    return "market_time_series" if unique_by_date.median() <= 1 else "cross_sectional"


def _ic_series(frame: pd.DataFrame, feature: str, target: str, method: str) -> pd.Series:
    if method == "cross_sectional":
        values = frame.groupby("date").apply(lambda group: _rank_spearman(group[feature], group[target]), include_groups=False)
        return values.dropna()
    if method == "asset_time_series":
        pieces = []
        for symbol, group in frame.sort_values("date").groupby("symbol"):
            data = group[["date", feature, target]].dropna()
            if len(data) < 52:
                continue
            rolling = []
            dates = data.date.to_numpy()
            for position in range(51, len(data)):
                window = data.iloc[position - 51:position + 1]
                rolling.append((dates[position], _rank_spearman(window[feature], window[target])))
            if rolling:
                pieces.append(pd.DataFrame(rolling, columns=["date", symbol]).set_index("date"))
        if not pieces:
            return pd.Series(dtype=float)
        combined = pd.concat(pieces, axis=1)
        return combined.mean(axis=1).dropna()
    by_date = frame.groupby("date")[[feature, target]].mean().dropna()
    if len(by_date) < 20:
        return pd.Series(dtype=float)
    rolling = by_date[feature].rolling(52).corr(by_date[target].rank())
    rolling.name = feature
    return rolling.dropna()


def _full_period_ic(frame: pd.DataFrame, feature: str, target: str, method: str) -> float:
    if method == "cross_sectional":
        return float(_ic_series(frame, feature, target, method).mean())
    if method == "asset_time_series":
        values = []
        for _, group in frame.groupby("symbol"):
            data = group[[feature, target]].dropna()
            if len(data) >= 20:
                values.append(_rank_spearman(data[feature], data[target]))
        return float(np.nanmean(values)) if values else np.nan
    by_date = frame.groupby("date")[[feature, target]].mean().dropna()
    return _rank_spearman(by_date[feature], by_date[target])


def information_coefficient_report(frame: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in metadata.feature:
        method = _feature_method(frame, feature)
        for horizon, label in HORIZONS.items():
            target = f"future_return_{label}"
            series = _ic_series(frame, feature, target, method)
            stats = _newey_west_stats(series)
            full_ic = _full_period_ic(frame, feature, target, method)
            rolling = series.rolling(26).mean().dropna()
            stability = float((np.sign(rolling) == np.sign(full_ic)).mean()) if len(rolling) and np.isfinite(full_ic) and full_ic != 0 else np.nan
            rows.append({
                "feature": feature,
                "horizon": label,
                "method": method,
                "full_sample_ic": full_ic,
                "mean_ic": stats["mean"],
                "n_ic_observations": int(len(series)),
                "newey_west_t": stats["t_stat"],
                "p_value": stats["p_value"],
                "ci_low": stats["ci_low"],
                "ci_high": stats["ci_high"],
                "ic_information_ratio": stats["mean"] / series.std() * np.sqrt(52) if len(series) > 2 and series.std() > 0 else np.nan,
                "rolling_ic_stability": stability,
            })
    return pd.DataFrame(rows)


def quantile_analysis(frame: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in metadata.feature:
        method = _feature_method(frame, feature)
        for horizon, label in HORIZONS.items():
            target = f"future_return_{label}"
            for buckets, bucket_name in ((5, "quintile"), (10, "decile")):
                spreads = []
                monotonic = []
                if method == "cross_sectional":
                    iterator = frame.groupby("date")
                else:
                    iterator = [("all_dates", frame.groupby("date")[[feature, target]].mean().reset_index())]
                for _, group in iterator:
                    data = group[[feature, target]].dropna()
                    if len(data) < buckets or data[feature].nunique() < buckets:
                        continue
                    try:
                        data["bucket"] = pd.qcut(data[feature], buckets, labels=False, duplicates="drop")
                    except ValueError:
                        continue
                    means = data.groupby("bucket")[target].mean()
                    if len(means) < max(3, buckets // 2):
                        continue
                    spreads.append(float(means.iloc[-1] - means.iloc[0]))
                    monotonic.append(_rank_spearman(pd.Series(means.index.astype(float)), means.reset_index(drop=True)))
                rows.append({
                    "feature": feature,
                    "horizon": label,
                    "bucket_type": bucket_name,
                    "method": method,
                    "mean_top_minus_bottom": float(np.nanmean(spreads)) if spreads else np.nan,
                    "positive_spread_fraction": float(np.mean(np.array(spreads) > 0)) if spreads else np.nan,
                    "mean_monotonicity": float(np.nanmean(monotonic)) if monotonic else np.nan,
                    "n_periods": int(len(spreads)),
                })
    return pd.DataFrame(rows)


def regime_stability(frame: pd.DataFrame, metadata: pd.DataFrame, ic_report: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dev_signs = {}
    for feature in metadata.feature:
        method = _feature_method(frame, feature)
        for horizon, label in HORIZONS.items():
            target = f"future_return_{label}"
            dev = frame[(frame.date >= pd.Timestamp("2020-01-01")) & (frame.date <= pd.Timestamp("2024-12-31"))]
            dev_signs[(feature, label)] = np.sign(_full_period_ic(dev, feature, target, method))
            for regime, (start, end) in REGIMES.items():
                subset = frame[(frame.date >= start) & (frame.date <= end)]
                series = _ic_series(subset, feature, target, method)
                stats = _newey_west_stats(series)
                full_ic = _full_period_ic(subset, feature, target, method)
                rows.append({
                    "feature": feature,
                    "horizon": label,
                    "regime": regime,
                    "method": method,
                    "full_period_ic": full_ic,
                    "mean_ic": stats["mean"],
                    "newey_west_t": stats["t_stat"],
                    "p_value": stats["p_value"],
                    "n_ic_observations": int(len(series)),
                    "sign_consistent_with_development": bool(np.sign(full_ic) == dev_signs[(feature, label)]) if np.isfinite(full_ic) and dev_signs[(feature, label)] != 0 else False,
                })
    stability = pd.DataFrame(rows)
    summary = classify_features(ic_report, stability, quantile_frame=None)
    return stability.merge(summary[["feature", "feature_tier", "tier_reason"]], on="feature", how="left")


def correlation_analysis(frame: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    features = metadata.feature.tolist()
    development = frame[(frame.date >= pd.Timestamp("2020-01-01")) & (frame.date <= pd.Timestamp("2024-12-31"))]
    matrix = development[features].replace([np.inf, -np.inf], np.nan)
    matrix = matrix.dropna(axis=1, thresh=max(20, int(0.30 * len(matrix))))
    features = matrix.columns.tolist()
    if not features:
        return pd.DataFrame()
    sample = matrix.fillna(matrix.median(numeric_only=True)).iloc[:: max(1, len(matrix) // 5000)]
    corr = sample.corr(method="spearman")
    rows = []
    cluster_id = 0
    assigned: dict[str, int] = {}
    for i, first in enumerate(features):
        for second in features[i + 1:]:
            value = corr.at[first, second]
            if abs(value) >= 0.85:
                if first not in assigned and second not in assigned:
                    cluster_id += 1
                    assigned[first] = cluster_id
                    assigned[second] = cluster_id
                elif first in assigned:
                    assigned[second] = assigned[first]
                else:
                    assigned[first] = assigned[second]
                rows.append({
                    "row_type": "high_correlation_pair",
                    "feature": first,
                    "feature_2": second,
                    "correlation": float(value),
                    "cluster_id": assigned[first],
                    "vif": np.nan,
                    "interpretation": "potential duplicate information content",
                })
    standardized = (sample - sample.mean()) / sample.std(ddof=0).replace(0, np.nan)
    standardized = standardized.dropna(axis=1)
    if len(standardized.columns) >= 2:
        corr_matrix = standardized.corr().fillna(0.0).to_numpy()
        inv = np.linalg.pinv(corr_matrix + np.eye(corr_matrix.shape[0]) * 1e-6)
        for feature, vif in zip(standardized.columns, np.diag(inv)):
            rows.append({
                "row_type": "vif",
                "feature": feature,
                "feature_2": "",
                "correlation": np.nan,
                "cluster_id": assigned.get(feature, 0),
                "vif": float(vif),
                "interpretation": "high multicollinearity" if vif > 10 else "acceptable",
            })
    return pd.DataFrame(rows)


def feature_importance_validation(frame: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    features = metadata.feature.tolist()
    target = "future_return_1w"
    development = frame[(frame.date >= pd.Timestamp("2020-01-01")) & (frame.date <= pd.Timestamp("2024-12-31"))]
    data = development[features + [target]].replace([np.inf, -np.inf], np.nan).dropna(subset=[target])
    usable = [feature for feature in features if data[feature].notna().mean() >= 0.50 and data[feature].nunique(dropna=True) > 5]
    if len(data) < 200 or not usable:
        return pd.DataFrame(columns=["feature", "elastic_net_abs_coef", "random_forest_importance", "gradient_boosting_importance"])
    x = data[usable]
    y = data[target].clip(data[target].quantile(0.01), data[target].quantile(0.99))
    rows = pd.DataFrame({"feature": usable})

    enet = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), ElasticNet(alpha=0.001, l1_ratio=0.5, max_iter=5000, random_state=7))
    enet.fit(x, y)
    rows["elastic_net_abs_coef"] = np.abs(enet.named_steps["elasticnet"].coef_)

    rf = make_pipeline(SimpleImputer(strategy="median"), RandomForestRegressor(n_estimators=150, max_depth=4, min_samples_leaf=25, random_state=7, n_jobs=-1))
    rf.fit(x, y)
    rows["random_forest_importance"] = rf.named_steps["randomforestregressor"].feature_importances_

    gb = make_pipeline(SimpleImputer(strategy="median"), GradientBoostingRegressor(n_estimators=150, max_depth=2, min_samples_leaf=25, random_state=7))
    gb.fit(x, y)
    rows["gradient_boosting_importance"] = gb.named_steps["gradientboostingregressor"].feature_importances_
    for column in ("elastic_net_abs_coef", "random_forest_importance", "gradient_boosting_importance"):
        total = rows[column].sum()
        if total > 0:
            rows[column] = rows[column] / total
    return rows


def classify_features(ic_report: pd.DataFrame, stability_report: pd.DataFrame, quantile_frame: pd.DataFrame | None) -> pd.DataFrame:
    rows = []
    for feature, group in ic_report.groupby("feature"):
        primary = group[group.horizon == "1w"]
        best = primary.iloc[0] if len(primary) else group.iloc[0]
        dev_holdout = stability_report[(stability_report.feature == feature) & (stability_report.horizon == "1w")]
        holdout = dev_holdout[dev_holdout.regime == "2025_2026_holdout"]
        non_holdout = dev_holdout[dev_holdout.regime != "2025_2026_holdout"]
        significant = bool(abs(best.get("newey_west_t", np.nan)) >= 2.0 and abs(best.get("full_sample_ic", np.nan)) >= 0.02)
        stable = bool((np.sign(non_holdout.full_period_ic.dropna()) == np.sign(best.full_sample_ic)).mean() >= 0.60) if len(non_holdout.dropna(subset=["full_period_ic"])) else False
        holdout_ok = bool(len(holdout) and np.sign(holdout.iloc[0].full_period_ic) == np.sign(best.full_sample_ic) and abs(holdout.iloc[0].full_period_ic) >= 0.01)
        quantile_ok = False
        if quantile_frame is not None and not quantile_frame.empty:
            q = quantile_frame[(quantile_frame.feature == feature) & (quantile_frame.horizon == "1w") & (quantile_frame.bucket_type == "quintile")]
            quantile_ok = bool(len(q) and np.sign(q.iloc[0].mean_top_minus_bottom) == np.sign(best.full_sample_ic) and abs(q.iloc[0].mean_monotonicity) >= 0.30)
        if significant and stable and holdout_ok and (quantile_ok or best.method == "market_time_series"):
            tier = "Tier 1"
            reason = "significant, economically meaningful, stable, and holdout-consistent"
        elif significant and np.sign(best.full_sample_ic) != 0:
            tier = "Tier 2"
            reason = "development/full-sample evidence exists but holdout or stability evidence is weaker"
        else:
            tier = "Tier 3"
            reason = "unstable, insignificant, redundant, or no holdout support"
        rows.append({
            "feature": feature,
            "feature_tier": tier,
            "tier_reason": reason,
            "primary_ic": best.get("full_sample_ic", np.nan),
            "primary_t_stat": best.get("newey_west_t", np.nan),
            "holdout_ic": holdout.iloc[0].full_period_ic if len(holdout) else np.nan,
            "stable_across_regimes": stable,
            "holdout_sign_consistent": holdout_ok,
        })
    return pd.DataFrame(rows)


def run_feature_research(
    panel: pd.DataFrame,
    public_data: Any | None = None,
    volatility_probability: pd.Series | None = None,
    output_dir: str | Path = "reports/feature_research",
) -> FeatureResearchResult:
    frame, metadata = build_feature_research_frame(panel, public_data, volatility_probability)
    ic = information_coefficient_report(frame, metadata)
    quantiles = quantile_analysis(frame, metadata)
    stability_raw = regime_stability(frame, metadata, ic)
    tiers = classify_features(ic, stability_raw, quantiles)
    stability = stability_raw.drop(columns=["feature_tier", "tier_reason"], errors="ignore").merge(tiers, on="feature", how="left")
    corr = correlation_analysis(frame, metadata)
    importance = feature_importance_validation(frame, metadata)
    ic = ic.merge(importance, on="feature", how="left").merge(tiers[["feature", "feature_tier", "tier_reason"]], on="feature", how="left")
    write_feature_research_outputs(output_dir, frame, metadata, ic, quantiles, stability, corr, importance, tiers)
    return FeatureResearchResult(frame, metadata, ic, quantiles, stability, corr, importance, tiers)


def write_feature_research_outputs(
    output_dir: str | Path,
    frame: pd.DataFrame,
    metadata: pd.DataFrame,
    ic: pd.DataFrame,
    quantiles: pd.DataFrame,
    stability: pd.DataFrame,
    corr: pd.DataFrame,
    importance: pd.DataFrame,
    tiers: pd.DataFrame,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    ic.to_csv(output / "feature_ic_report.csv", index=False)
    quantiles.to_csv(output / "feature_quantile_analysis.csv", index=False)
    stability.to_csv(output / "feature_stability_report.csv", index=False)
    corr.to_csv(output / "feature_correlation_analysis.csv", index=False)
    metadata.to_csv(output / "feature_metadata.csv", index=False)
    importance.to_csv(output / "feature_importance_validation.csv", index=False)
    tier_counts = tiers.feature_tier.value_counts().to_dict()
    top_tier = tiers.sort_values(["feature_tier", "primary_t_stat"], ascending=[True, False])
    tier_table = _table(top_tier, [("feature", "Feature"), ("feature_tier", "Tier"), ("primary_ic", "1w IC"), ("primary_t_stat", "NW t-stat"), ("holdout_ic", "Holdout IC"), ("tier_reason", "Reason")])
    families = metadata.merge(tiers, on="feature", how="left").groupby(["family", "feature_tier"]).size().reset_index(name="count")
    family_table = _table(families, [("family", "Family"), ("feature_tier", "Tier"), ("count", "Count")])
    (output / "feature_research_summary.md").write_text(f"""# Feature research summary

This phase runs before any new strategy construction. Features classified as
Tier 3 must not be used in subsequent strategy design.

## Scope

- Observations: {len(frame)}
- Features tested: {metadata.feature.nunique()}
- Horizons: 1-week, 2-week, and 4-week forward returns.
- IC method: cross-sectional Spearman IC for asset-level features; rolling
  time-series Spearman IC for market-level features that are constant across
  assets on a date.
- Significance: Newey-West adjusted t-statistics over IC series.
- Regimes: 2020-2021 bull, 2022 bear, 2023-2024 recovery, 2025-2026 holdout.

## Tier counts

- Tier 1: {tier_counts.get('Tier 1', 0)}
- Tier 2: {tier_counts.get('Tier 2', 0)}
- Tier 3: {tier_counts.get('Tier 3', 0)}

## Feature families by tier

{family_table}

## Feature classification

{tier_table}

## Interpretation rule for later strategies

Any future strategy must explicitly list the Tier 1 features motivating its
rules. Tier 2 features may be used only as robustness/context inputs. Tier 3
features are excluded from strategy design unless a later prospective dataset
changes their classification.
""", encoding="utf-8")


def _format(value: Any) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "N/A"
    if isinstance(value, (float, np.floating)):
        return f"{value:.4f}"
    return str(value)


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]]) -> str:
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in frame.to_dict("records"):
        lines.append("| " + " | ".join(_format(row.get(key)) for key, _ in columns) + " |")
    return "\n".join(lines)


__all__ = [
    "FeatureResearchResult",
    "build_feature_research_frame",
    "run_feature_research",
    "information_coefficient_report",
    "quantile_analysis",
    "correlation_analysis",
    "classify_features",
]

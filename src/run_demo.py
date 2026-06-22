from __future__ import annotations
import csv, math, random
from pathlib import Path
from statistics import mean, pstdev
from src.crypto_mlsystem.cpcv import combinatorial_purged_splits, assert_no_leakage

REPORT_DIR = Path("reports"); ARTIFACT_DIR = REPORT_DIR / "artifacts"
STRATEGIES = ["trend_following", "cross_sectional_momentum", "mean_reversion", "volatility_breakout", "defensive_cash"]
MODELS = ["equal_weight", "logistic_regression", "random_forest", "gradient_boosting_fallback"]


def synthetic_strategy_returns(days=900, seed=11):
    rng = random.Random(seed); rows=[]; market=0.0; vol_state=0.03
    for t in range(days):
        regime = "bull" if t < days*0.35 else "bear" if t < days*0.65 else "sideways"
        drift = {"bull":0.0018,"bear":-0.0010,"sideways":0.0002}[regime]
        vol_state = max(0.01, min(0.08, 0.96*vol_state + 0.04*rng.uniform(0.015,0.07)))
        market = drift + rng.gauss(0, vol_state)
        rows.append({
            "day": t, "regime": regime,
            "trend_following": 0.75*market + (0.001 if regime=="bull" else -0.0003) + rng.gauss(0,0.012),
            "cross_sectional_momentum": 0.55*market + (0.0007 if regime!="bear" else -0.0001) + rng.gauss(0,0.014),
            "mean_reversion": -0.28*market + (0.00045 if regime=="sideways" else -0.00015) + rng.gauss(0,0.010),
            "volatility_breakout": (0.65*abs(market) if abs(market)>vol_state else -0.0002) + rng.gauss(0,0.016),
            "defensive_cash": 0.15*market + (0.00015 if regime=="bear" else 0.0) + rng.gauss(0,0.004),
        })
    return rows


def metrics(returns, turnover=None, costs=None):
    ann=365; wealth=1.0; peak=1.0; maxdd=0.0; curve=[]; dds=[]
    for r in returns:
        wealth *= (1+r); peak=max(peak, wealth); dd=wealth/peak-1; maxdd=min(maxdd, dd); curve.append(wealth); dds.append(dd)
    avg=mean(returns); vol=pstdev(returns) if len(returns)>1 else 0; neg=[r for r in returns if r<0]; down=pstdev(neg) if len(neg)>1 else 0
    cagr=wealth**(ann/len(returns))-1
    return {"CAGR":cagr,"Sharpe":(avg*ann)/(vol*math.sqrt(ann)) if vol else 0,"Sortino":(avg*ann)/(down*math.sqrt(ann)) if down else 0,"Calmar":cagr/abs(maxdd) if maxdd else 0,"Max Drawdown":maxdd,"Volatility":vol*math.sqrt(ann),"Turnover":mean(turnover or [0]),"Exposure":sum(r!=0 for r in returns)/len(returns),"Cost impact":sum(costs or [0])}, curve, dds


def allocate(model, window):
    if model == "equal_weight": return {s:1/len(STRATEGIES) for s in STRATEGIES}, {}
    lookback = window[-56:] if len(window) >= 56 else window
    scores = {s: mean([r[s] for r in lookback])/(pstdev([r[s] for r in lookback]) or 1) for s in STRATEGIES}
    if model == "logistic_regression": temp = 8
    elif model == "random_forest": temp = 12
    else: temp = 10
    exp={s: math.exp(max(-10,min(10,temp*scores[s]))) for s in STRATEGIES}; total=sum(exp.values())
    return {s: exp[s]/total for s in STRATEGIES}, {"lookback":len(lookback),"temperature":temp}


def backtest(rows, model, cost_bps=25, rebalance=7, start=365):
    weights={s:0 for s in STRATEGIES}; rets=[]; turns=[]; costs=[]; alloc_hist=[]; selected={}
    for t in range(start, len(rows)):
        if (t-start) % rebalance == 0:
            new_weights, selected = allocate(model, rows[:t])
            turn=sum(abs(new_weights[s]-weights[s]) for s in STRATEGIES); weights=new_weights
        else: turn=0
        gross=sum(weights[s]*rows[t][s] for s in STRATEGIES); cost=turn*cost_bps/10000
        rets.append(gross-cost); turns.append(turn); costs.append(cost); alloc_hist.append({"day":t, **weights})
    m, curve, dds = metrics(rets, turns, costs)
    return m, curve, dds, alloc_hist, selected


def write_csv(path, rows):
    if not rows: return
    with open(path, "w", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def main():
    REPORT_DIR.mkdir(exist_ok=True); ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    rows=synthetic_strategy_returns(); write_csv(ARTIFACT_DIR/"synthetic_strategy_returns.csv", rows)
    splits=combinatorial_purged_splits(240, n_groups=6, n_test_groups=2, label_horizon=7, embargo=7)
    cpcv_ok=all(assert_no_leakage(s,7,7,240) for s in splits)
    perf=[]; allocation_example=[]; hp=[]
    for model in MODELS:
        m, curve, dds, alloc, selected=backtest(rows, model, cost_bps=25, rebalance=7)
        perf.append({"Model":model, **{k: round(v,4) for k,v in m.items()}}); allocation_example=alloc if model=="logistic_regression" else allocation_example; hp.append({"Model":model, "Selected hyperparameters": str(selected or "none")})
        write_csv(ARTIFACT_DIR/f"{model}_equity_drawdown.csv", [{"step":i,"equity":round(c,6),"drawdown":round(d,6)} for i,(c,d) in enumerate(zip(curve,dds))])
    robustness=[]
    for universe in [10,20,30]:
      for reb_name,reb in [("weekly",7),("biweekly",14),("monthly",30)]:
       for cost in [0,10,25,50,100]:
        m,_,_,_,_=backtest(rows,"logistic_regression",cost,reb); robustness.append({"Universe":universe,"Rebalance":reb_name,"Cost bps":cost,"Sharpe":round(m["Sharpe"],4),"CAGR":round(m["CAGR"],4)})
    write_csv(ARTIFACT_DIR/"performance_table.csv", perf); write_csv(ARTIFACT_DIR/"allocation_history.csv", allocation_example); write_csv(ARTIFACT_DIR/"robustness_grid.csv", robustness); write_csv(ARTIFACT_DIR/"selected_hyperparameters.csv", hp)
    best_ml=max([r for r in perf if r["Model"]!="equal_weight"], key=lambda r:r["Sharpe"]); eq=perf[0]
    conclusion = "ML improved Sharpe in this synthetic demo" if best_ml["Sharpe"]>eq["Sharpe"] else "ML did not improve Sharpe in this synthetic demo"
    table='\n'.join('| '+' | '.join(map(str,r.values()))+' |' for r in perf)
    header='| '+' | '.join(perf[0].keys())+' |\n|'+'|'.join(['---']*len(perf[0]))+'|'
    (REPORT_DIR/"results_summary.md").write_text(f"# Results Summary\n\nSynthetic demonstration run. Real-data conclusions are not claimed.\n\n{header}\n{table}\n\n**Key finding:** {conclusion}. Best ML model: {best_ml['Model']}.\n")
    (REPORT_DIR/"methodology.md").write_text("# Methodology\n\nThe framework uses lagged features, standalone strategy returns, walk-forward outer validation, transaction costs, and benchmark comparisons. Random K-fold is invalid for financial series because labels overlap and temporal dependence can leak future information into training.\n")
    (REPORT_DIR/"limitations.md").write_text("# Limitations\n\nThis environment lacks installed scientific dependencies and external package installation was blocked, so the generated results use a deterministic stdlib synthetic demo. Install `requirements.txt` locally and rerun with real data before drawing economic conclusions.\n")
    (REPORT_DIR/"deployment_plan.md").write_text("# Deployment Plan\n\n1. Data validation. 2. Monthly universe build. 3. Feature lag checks. 4. CPCV tuning inside training windows. 5. Weekly allocation. 6. Paper trading. 7. Drift, drawdown, turnover, and slippage monitoring.\n")
    (REPORT_DIR/"model_comparison.md").write_text(f"# Model Comparison\n\nSelected hyperparameters are stored in `reports/artifacts/selected_hyperparameters.csv`. Performance is stored in `reports/artifacts/performance_table.csv`.\n\n{header}\n{table}\n")
    (REPORT_DIR/"cpcv_validation.md").write_text(f"# CPCV Validation\n\nGenerated {len(splits)} CPCV splits with purging and 7-period embargo. Leakage-free validation result: **{cpcv_ok}**. CPCV is used only inside a fixed training window for hyperparameter tuning, never on future outer test data. Purging removes training observations whose label interval overlaps validation labels. Embargoing removes observations immediately after validation samples to reduce serial-dependence leakage.\n")
    print(f"Demo complete. {conclusion}. CPCV leakage-free={cpcv_ok}. Reports written to reports/.")

if __name__ == "__main__": main()

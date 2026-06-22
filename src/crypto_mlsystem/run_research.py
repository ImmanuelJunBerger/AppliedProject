from .config import ResearchConfig
from .data import DataIngestion, UniverseBuilder
from .strategies import strategy_return_frame
from .features import build_features, make_strategy_targets
from .ml import walk_forward_allocations
from .risk import reasoning_layer
from .backtest import apply_allocations, benchmark_returns

def run(config_path="configs/default.yaml", data_path=None, top_n=20, model_name="logistic_regression", cost_bps=25, use_reasoning=True):
    cfg = ResearchConfig.from_yaml(config_path); ingestion = DataIngestion()
    panel = ingestion.load_csv(data_path) if data_path else ingestion.synthetic_panel()
    universes = UniverseBuilder(set(cfg.exclude_symbols), cfg.min_history_days).monthly_universe(panel, top_n)
    selected = sorted(set().union(*universes.values())) if universes else panel.symbol.unique()[:top_n]
    panel = panel[panel.symbol.isin(selected)]
    sret = strategy_return_frame(panel); feats = build_features(panel, sret); target = make_strategy_targets(sret)
    alloc = walk_forward_allocations(feats, target, list(sret.columns), cfg.train_min_days, cfg.prediction_frequency, model_name)
    if use_reasoning:
        alloc = reasoning_layer(alloc, feats, cfg.strategy_limit, cfg.turnover_limit)
    result = apply_allocations(sret, alloc, cost_bps)
    benches = benchmark_returns(panel, sret)
    return {"panel": panel, "strategy_returns": sret, "features": feats, "targets": target, "allocations": alloc, "result": result, "benchmarks": benches, "universes": universes}

if __name__ == "__main__":
    res = run(); print(res["result"]["metrics"])

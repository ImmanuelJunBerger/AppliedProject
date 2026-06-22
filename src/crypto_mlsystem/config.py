from dataclasses import dataclass, field
from pathlib import Path
import yaml

@dataclass
class ResearchConfig:
    universe_sizes: list[int] = field(default_factory=lambda: [10, 20, 30])
    exclude_symbols: list[str] = field(default_factory=list)
    min_history_days: int = 365
    initial_capital: float = 1.0
    rebalance: str = "W-FRI"
    prediction_frequency: str = "W-FRI"
    retrain_frequency: str = "ME"
    train_min_days: int = 365
    transaction_cost_bps: list[int] = field(default_factory=lambda: [0, 10, 25, 50, 100])
    strategy_names: list[str] = field(default_factory=list)
    position_limit: float = 0.25
    strategy_limit: float = 0.45
    target_volatility: float = 0.35
    turnover_limit: float = 0.75
    cash_symbol: str = "CASH"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ResearchConfig":
        data = yaml.safe_load(Path(path).read_text())
        return cls(**data)

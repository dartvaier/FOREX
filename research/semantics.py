"""Versioned declarative semantics for the registered F6 strategy catalog."""

EMA_CROSSOVER_SEMANTICS_VERSION = "EMA_CROSSOVER_SEMANTICS_V1"
EMA_CROSSOVER_SEMANTICS = {
    "signal_timing": "closed H1 bar",
    "fast_crosses_above_slow": "ENTER_LONG",
    "fast_crosses_below_slow": "ENTER_SHORT",
    "trading_style": "DIRECTIONAL_TREND_FOLLOWING",
    "forbidden_execution_semantics": ("COUNTERTREND", "REVERSAL", "MEAN_REVERSION"),
}

METRIC_ALLOWLIST_VERSION = "F6_METRICS_V1"
MEASURABLE_METRICS = (
    "percentage_return", "trade_count", "win_rate", "profit_factor", "sharpe_ratio",
    "maximum_drawdown_percent", "positive_fold_proportion", "median_return_percent",
    "return_dispersion", "worst_return_percent", "median_drawdown_percent",
    "worst_drawdown_percent", "walk_forward_return_degradation", "gate_status",
)
METRIC_TERMS = {
    "percentage return", "trade count", "win rate", "profit factor", "sharpe ratio",
    "maximum drawdown percent", "positive fold proportion", "median return percent",
    "return dispersion", "worst return percent", "median drawdown percent",
    "worst drawdown percent", "walk-forward return degradation", "gate status",
}

"""Versioned declarative semantics for the registered F6 strategy catalog."""

EMA_CROSSOVER_SEMANTICS_VERSION = "EMA_CROSSOVER_SEMANTICS_V1"
EMA_CROSSOVER_SEMANTICS = {
    "signal_timing": "closed H1 bar",
    "fast_crosses_above_slow": "ENTER_LONG",
    "fast_crosses_below_slow": "ENTER_SHORT",
    "trading_style": "DIRECTIONAL_TREND_FOLLOWING",
    "forbidden_execution_semantics": ("COUNTERTREND", "REVERSAL", "MEAN_REVERSION"),
}

from research.falsification import FalsificationMetric
METRIC_ALLOWLIST_VERSION = "F6_METRICS_V1"
MEASURABLE_METRICS = tuple(metric.value for metric in FalsificationMetric)

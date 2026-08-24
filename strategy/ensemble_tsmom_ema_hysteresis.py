from dataclasses import dataclass

from strategy.ensemble_tsmom_ema import TsmomEmaEnsembleStrategy


@dataclass(frozen=True, slots=True)
class TsmomEmaHysteresisEnsembleStrategy(
    TsmomEmaEnsembleStrategy
):
    """
    TSMOM + EMA ensemble preset with explicit hysteresis.

    Entry thresholds are intentionally wider than exit thresholds
    so the strategy does not churn around the entry boundary.
    """

    strategy_id: str = "ENSEMBLE-TSMOM-EMA-HYSTERESIS"
    enter_long: float = 0.40
    enter_short: float = -0.40
    exit_long_below: float = 0.05
    exit_short_above: float = -0.05

from research.runner import (
    STRATEGY_REGISTRY,
    coerce_strategy_params,
    discover_strategy_class,
)
from strategy import TsmomEmaHysteresisEnsembleStrategy


def test_hysteresis_ensemble_uses_explicit_default_bands():
    strategy = TsmomEmaHysteresisEnsembleStrategy(
        symbol="EURUSD",
    )

    assert strategy.strategy_id == "ENSEMBLE-TSMOM-EMA-HYSTERESIS"
    assert strategy.enter_long == 0.40
    assert strategy.enter_short == -0.40
    assert strategy.exit_long_below == 0.05
    assert strategy.exit_short_above == -0.05


def test_hysteresis_ensemble_preserves_param_overrides():
    strategy = TsmomEmaHysteresisEnsembleStrategy(
        symbol="EURUSD",
        enter_long=0.50,
        enter_short=-0.50,
        exit_long_below=0.10,
        exit_short_above=-0.10,
    )

    assert strategy.enter_long == 0.50
    assert strategy.enter_short == -0.50
    assert strategy.exit_long_below == 0.10
    assert strategy.exit_short_above == -0.10


def test_research_runner_discovers_hysteresis_ensemble():
    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY["ensemble_tsmom_ema_hysteresis"]
    )

    assert strategy_class is TsmomEmaHysteresisEnsembleStrategy


def test_research_runner_coerces_hysteresis_params():
    params = coerce_strategy_params(
        TsmomEmaHysteresisEnsembleStrategy,
        {
            "enter_long": "0.5",
            "exit_long_below": "0.1",
            "tsmom_lookback": "12",
        },
    )

    assert params == {
        "enter_long": 0.5,
        "exit_long_below": 0.1,
        "tsmom_lookback": 12,
    }

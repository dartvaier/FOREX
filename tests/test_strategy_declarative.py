from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha.ledger import AlphaLedger
from backtest.context import BacktestContext
from backtest.models import MarketBar, SignalAction
from backtest.models.enums import SimulationPhase
from research.runner import (
    STRATEGY_REGISTRY,
    coerce_strategy_params,
    discover_strategy_class,
)
from strategy import DeclarativeEnsembleStrategy
from strategy.declarative import (
    AlphaEnsembleConfig,
    build_alpha_models,
    load_strategy_config,
)


def utc_time(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        8,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def make_bar(
    index: int,
    close: float,
) -> MarketBar:
    return MarketBar(
        time=utc_time(10)
        + timedelta(minutes=index * 15),
        open=close,
        high=close,
        low=close,
        close=close,
        tick_volume=1000,
    )


def make_context(
    closes: list[float],
) -> BacktestContext:
    bars = tuple(
        make_bar(index, close)
        for index, close in enumerate(closes)
    )
    current_index = len(bars) - 1

    return BacktestContext(
        current_time=(
            utc_time(10)
            + timedelta(
                minutes=(current_index + 1) * 15
            )
        ),
        phase=SimulationPhase.BAR_CLOSE,
        current_bar_index=current_index,
        current_bar=bars[-1],
        closed_bars=bars,
    )


def write_config(
    tmp_path: Path,
    text: str,
) -> Path:
    path = tmp_path / "strategy.yaml"
    path.write_text(
        text,
        encoding="utf-8",
    )
    return path


def valid_config_text(
    *,
    cost_estimate_pips: float = 0.1,
) -> str:
    return f"""
name: test-declarative
strategy_id: TEST-DECLARATIVE
symbol: EURUSD

models:
  - id: time-series-momentum
    weight: 1.0
    params:
      lookback: 3
      score_scale: 0.02
      pip_size: 0.00010

  - id: ema-trend
    weight: 1.0
    params:
      fast_period: 2
      slow_period: 4
      score_scale: 1.0
      pip_size: 0.00010

blend:
  method: weighted_mean
  min_active_models: 2
  min_conviction: 0.1

signal_policy:
  enter_long: 0.25
  enter_short: -0.25
  exit_long_below: 0.0
  exit_short_above: 0.0

cost_gate:
  cost_estimate_pips: {cost_estimate_pips}
  safety_factor: 1.0
"""


def test_load_strategy_config_parses_yaml_subset(tmp_path):
    path = write_config(
        tmp_path,
        valid_config_text(),
    )

    config = load_strategy_config(path)

    assert isinstance(config, AlphaEnsembleConfig)
    assert config.name == "test-declarative"
    assert config.strategy_id == "TEST-DECLARATIVE"
    assert config.symbol == "EURUSD"
    assert config.symbols is None
    assert len(config.models) == 2
    assert config.blend["method"] == "weighted_mean"
    assert config.signal_policy["enter_long"] == 0.25
    assert config.cost_gate["cost_estimate_pips"] == 0.1
    assert config.sha256 is not None


def test_load_strategy_config_loads_default_yaml():
    config = load_strategy_config(
        "config/strategies/ensemble_low_turnover_v1.yaml"
    )

    assert config.name == "ensemble-low-turnover-v1"
    assert config.strategy_id == "ENSEMBLE-LOW-TURNOVER-V1"
    assert config.blend["min_active_models"] == 2
    assert config.cost_gate["cost_estimate_pips"] == 3.7


def test_load_strategy_config_loads_multi_symbol_yaml():
    config = load_strategy_config(
        "config/strategies/ensemble_low_turnover_multi_symbol_v1.yaml"
    )

    assert config.name == "ensemble-low-turnover-multi-symbol-v1"
    assert config.symbol is None
    assert config.symbols == (
        "AUDUSD",
        "EURUSD",
        "GBPUSD",
        "NZDUSD",
        "USDCAD",
        "USDCHF",
        "USDJPY",
    )


def test_build_alpha_models_from_config(tmp_path):
    config = load_strategy_config(
        write_config(
            tmp_path,
            valid_config_text(),
        )
    )

    models, weights = build_alpha_models(
        config,
        symbol="EURUSD",
    )

    assert len(models) == 2
    assert weights == {
        "TIME-SERIES-MOMENTUM-ALPHA": 1.0,
        "EMA-TREND-ALPHA": 1.0,
    }


def test_build_alpha_models_resolves_auto_pip_size_for_usdjpy():
    config = load_strategy_config(
        "config/strategies/ensemble_low_turnover_multi_symbol_v1.yaml"
    )

    models, _ = build_alpha_models(
        config,
        symbol="USDJPY",
    )

    assert all(
        model.inner.pip_size == 0.01
        for model in models
    )


def test_build_alpha_models_resolves_auto_pip_size_for_eurusd():
    config = load_strategy_config(
        "config/strategies/ensemble_low_turnover_multi_symbol_v1.yaml"
    )

    models, _ = build_alpha_models(
        config,
        symbol="EURUSD",
    )

    assert all(
        model.inner.pip_size == 0.00010
        for model in models
    )


def test_declarative_ensemble_enters_when_yaml_models_agree(tmp_path):
    ledger = AlphaLedger()
    strategy = DeclarativeEnsembleStrategy(
        symbol="EURUSD",
        config_path=str(
            write_config(
                tmp_path,
                valid_config_text(),
            )
        ),
        alpha_ledger=ledger,
    )

    signal = strategy.on_bar(
        make_context(
            [
                10.0,
                10.0,
                10.0,
                10.0,
                12.0,
            ]
        )
    )

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.strategy_id == "TEST-DECLARATIVE"
    assert signal.metadata["strategy_config_name"] == "test-declarative"
    assert signal.metadata["strategy_config_sha256"] == strategy.config.sha256
    assert ledger.count == 2


def test_declarative_ensemble_holds_when_cost_gate_blocks_all(tmp_path):
    strategy = DeclarativeEnsembleStrategy(
        symbol="EURUSD",
        config_path=str(
            write_config(
                tmp_path,
                valid_config_text(
                    cost_estimate_pips=1_000_000.0,
                ),
            )
        ),
    )

    signal = strategy.on_bar(
        make_context(
            [
                10.0,
                10.0,
                10.0,
                10.0,
                12.0,
            ]
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "All alpha models abstained"
    assert signal.metadata["blended_abstained"] is True


def test_declarative_ensemble_rejects_symbol_mismatch(tmp_path):
    path = write_config(
        tmp_path,
        valid_config_text().replace(
            "symbol: EURUSD",
            "symbol: GBPUSD",
        ),
    )

    with pytest.raises(ValueError, match="symbol"):
        DeclarativeEnsembleStrategy(
            symbol="EURUSD",
            config_path=str(path),
        )


def test_declarative_ensemble_rejects_symbol_outside_config_symbols(
    tmp_path,
):
    path = write_config(
        tmp_path,
        valid_config_text().replace(
            "symbol: EURUSD",
            "symbols: [GBPUSD, USDJPY]",
        ),
    )

    with pytest.raises(ValueError, match="config symbols"):
        DeclarativeEnsembleStrategy(
            symbol="EURUSD",
            config_path=str(path),
        )


def test_load_strategy_config_rejects_symbol_and_symbols(tmp_path):
    path = write_config(
        tmp_path,
        valid_config_text().replace(
            "symbol: EURUSD",
            "symbol: EURUSD\nsymbols: [EURUSD, GBPUSD]",
        ),
    )

    with pytest.raises(ValueError, match="either symbol or symbols"):
        load_strategy_config(path)


def test_load_strategy_config_rejects_unknown_model(tmp_path):
    path = write_config(
        tmp_path,
        valid_config_text().replace(
            "id: ema-trend",
            "id: unknown-alpha",
        ),
    )
    config = load_strategy_config(path)

    with pytest.raises(ValueError, match="unknown alpha model"):
        build_alpha_models(
            config,
            symbol="EURUSD",
        )


def test_load_strategy_config_rejects_unknown_blend_method(tmp_path):
    path = write_config(
        tmp_path,
        valid_config_text().replace(
            "method: weighted_mean",
            "method: median",
        ),
    )

    with pytest.raises(ValueError, match="weighted_mean"):
        load_strategy_config(path)


def test_research_runner_discovers_declarative_ensemble():
    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY["declarative_ensemble"]
    )

    assert strategy_class is DeclarativeEnsembleStrategy


def test_research_runner_coerces_declarative_params():
    params = coerce_strategy_params(
        DeclarativeEnsembleStrategy,
        {
            "config_path": "config/strategies/ensemble_low_turnover_v1.yaml",
        },
    )

    assert params == {
        "config_path": "config/strategies/ensemble_low_turnover_v1.yaml",
    }

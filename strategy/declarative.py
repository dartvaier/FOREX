import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from alpha.blender import WeightedAlphaBlender
from alpha.cost import CostAwareAlphaModel, MinimumExpectedMoveGate
from alpha.ledger import AlphaLedger
from alpha.protocol import AlphaModel
from alpha.quant import EmaTrendAlphaModel, TimeSeriesMomentumAlphaModel
from alpha.regime import RegimeGatedAlphaModel, TrendVolatilityRegimeGate
from backtest.context import BacktestContext
from backtest.instruments import instrument_specification
from backtest.models import Signal, Timeframe
from strategy.ensemble import EnsembleStrategy

REPO_ROOT = Path(__file__).resolve().parents[1]

MODEL_REGISTRY = {
    "ema-trend": EmaTrendAlphaModel,
    "ema_trend": EmaTrendAlphaModel,
    "time-series-momentum": TimeSeriesMomentumAlphaModel,
    "time_series_momentum": TimeSeriesMomentumAlphaModel,
    "tsmom": TimeSeriesMomentumAlphaModel,
}


@dataclass(frozen=True, slots=True)
class AlphaEnsembleConfig:
    """
    Parsed declarative ensemble strategy configuration.
    """

    name: str
    strategy_id: str
    symbol: str | None
    symbols: tuple[str, ...] | None
    models: tuple[Mapping[str, Any], ...]
    blend: Mapping[str, Any]
    signal_policy: Mapping[str, Any]
    cost_gate: Mapping[str, Any] | None = None
    regime_gate: Mapping[str, Any] | None = None
    source_path: Path | None = None
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class DeclarativeEnsembleStrategy:
    """
    Strategy built from a checked declarative YAML configuration.

    It remains a normal Strategy from the BacktestEngine point of
    view: it emits Signal objects only and leaves risk, sizing and
    execution downstream.
    """

    symbol: str
    config_path: str = "config/strategies/ensemble_low_turnover_v1.yaml"
    strategy_id: str = "DECLARATIVE-ENSEMBLE"
    alpha_ledger: AlphaLedger | None = None

    _config: AlphaEnsembleConfig = field(
        init=False,
        repr=False,
    )
    _ensemble: EnsembleStrategy = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        config = load_strategy_config(
            self.config_path
        )

        if config.symbol is not None and config.symbol != self.symbol:
            raise ValueError(
                "config symbol does not match strategy symbol"
            )

        if (
            config.symbols is not None
            and self.symbol not in config.symbols
        ):
            raise ValueError(
                "strategy symbol is not listed in config symbols"
            )

        models, weights = build_alpha_models(
            config,
            symbol=self.symbol,
        )

        signal_policy = dict(
            config.signal_policy
        )
        blend = dict(
            config.blend
        )

        object.__setattr__(
            self,
            "strategy_id",
            config.strategy_id,
        )
        object.__setattr__(
            self,
            "_config",
            config,
        )
        object.__setattr__(
            self,
            "_ensemble",
            EnsembleStrategy(
                symbol=self.symbol,
                strategy_id=config.strategy_id,
                models=models,
                blender=WeightedAlphaBlender(weights),
                min_conviction=float(
                    blend.get(
                        "min_conviction",
                        0.0,
                    )
                ),
                min_active_models=int(
                    blend.get(
                        "min_active_models",
                        1,
                    )
                ),
                enter_long=float(
                    signal_policy.get(
                        "enter_long",
                        0.30,
                    )
                ),
                enter_short=float(
                    signal_policy.get(
                        "enter_short",
                        -0.30,
                    )
                ),
                exit_long_below=float(
                    signal_policy.get(
                        "exit_long_below",
                        0.0,
                    )
                ),
                exit_short_above=float(
                    signal_policy.get(
                        "exit_short_above",
                        0.0,
                    )
                ),
                alpha_ledger=self.alpha_ledger,
            ),
        )

    @property
    def config(self) -> AlphaEnsembleConfig:
        return self._config

    @property
    def closed_bar_limit(self) -> int | None:
        return self._ensemble.closed_bar_limit

    @property
    def higher_timeframe_bar_limits(
        self,
    ) -> dict[Timeframe, int]:
        return self._ensemble.higher_timeframe_bar_limits

    def reset(self) -> None:
        self._ensemble.reset()

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        signal = self._ensemble.on_bar(context)

        return Signal(
            signal_id=signal.signal_id,
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            action=signal.action,
            reason=signal.reason,
            metadata={
                **signal.metadata,
                "strategy_config_name": self._config.name,
                "strategy_config_path": str(
                    self._config.source_path
                ),
                "strategy_config_sha256": self._config.sha256,
                "strategy_config_symbols": self._config.symbols,
            },
        )


def load_strategy_config(
    path: str | Path,
) -> AlphaEnsembleConfig:
    config_path = _resolve_config_path(path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"strategy config not found: {config_path}"
        )

    text = config_path.read_text(
        encoding="utf-8"
    )
    payload = _parse_yaml_subset(text)

    if not isinstance(payload, Mapping):
        raise ValueError(
            "strategy config must be a mapping"
        )

    return _strategy_config_from_mapping(
        payload,
        source_path=config_path,
        sha256=hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest().upper(),
    )


def build_alpha_models(
    config: AlphaEnsembleConfig,
    *,
    symbol: str,
) -> tuple[tuple[AlphaModel, ...], dict[str, float]]:
    models = []
    weights: dict[str, float] = {}

    for model_config in config.models:
        if not isinstance(model_config, Mapping):
            raise ValueError(
                "model entries must be mappings"
            )

        model_key = _required_string(
            model_config,
            "id",
        )
        model_class = MODEL_REGISTRY.get(model_key)

        if model_class is None:
            raise ValueError(
                f"unknown alpha model id: {model_key}"
            )

        params = _resolve_model_params(
            _optional_mapping(
                model_config,
                "params",
            ),
            symbol=symbol,
        )
        model = model_class(
            symbol=symbol,
            **params,
        )

        if "regime_gate" in model_config:
            model = _wrap_regime_gate(
                model,
                _optional_mapping(
                    model_config,
                    "regime_gate",
                ),
            )
        elif config.regime_gate is not None:
            model = _wrap_regime_gate(
                model,
                config.regime_gate,
            )

        if "cost_gate" in model_config:
            model = _wrap_cost_gate(
                model,
                _optional_mapping(
                    model_config,
                    "cost_gate",
                ),
            )
        elif config.cost_gate is not None:
            model = _wrap_cost_gate(
                model,
                config.cost_gate,
            )

        weight = model_config.get(
            "weight",
            1.0,
        )
        _validate_positive_number(
            "weight",
            weight,
        )

        models.append(model)
        weights[model.model_id] = float(weight)

    if len(weights) != len(models):
        raise ValueError(
            "declarative alpha models must have unique model_id values"
        )

    return tuple(models), weights


def _strategy_config_from_mapping(
    payload: Mapping[str, Any],
    *,
    source_path: Path,
    sha256: str,
) -> AlphaEnsembleConfig:
    name = _required_string(
        payload,
        "name",
    )
    strategy_id = str(
        payload.get(
            "strategy_id",
            name.upper().replace("-", "_"),
        )
    )

    if not strategy_id.strip():
        raise ValueError(
            "strategy_id must be a non-empty string"
        )

    symbol = payload.get(
        "symbol",
    )

    if symbol is not None:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(
                "symbol must be a non-empty string or omitted"
            )

        symbol = symbol.strip()

    symbols = payload.get(
        "symbols",
    )

    if symbols is not None:
        if not isinstance(symbols, list) or not symbols:
            raise ValueError(
                "symbols must be a non-empty list or omitted"
            )

        normalized_symbols = []

        for item in symbols:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    "symbols must contain only non-empty strings"
                )

            normalized_symbols.append(item.strip())

        if len(set(normalized_symbols)) != len(normalized_symbols):
            raise ValueError(
                "symbols must not contain duplicates"
            )

        symbols = tuple(normalized_symbols)

    if symbol is not None and symbols is not None:
        raise ValueError(
            "use either symbol or symbols, not both"
        )

    models = payload.get(
        "models",
    )

    if not isinstance(models, list) or not models:
        raise ValueError(
            "models must be a non-empty list"
        )

    blend = _optional_mapping(
        payload,
        "blend",
    )
    method = blend.get(
        "method",
        "weighted_mean",
    )

    if method != "weighted_mean":
        raise ValueError(
            "blend.method must be weighted_mean"
        )

    signal_policy = _optional_mapping(
        payload,
        "signal_policy",
    )

    cost_gate = (
        _optional_mapping(
            payload,
            "cost_gate",
        )
        if "cost_gate" in payload
        else None
    )
    regime_gate = (
        _optional_mapping(
            payload,
            "regime_gate",
        )
        if "regime_gate" in payload
        else None
    )

    return AlphaEnsembleConfig(
        name=name,
        strategy_id=strategy_id.strip(),
        symbol=symbol,
        symbols=symbols,
        models=tuple(models),
        blend=blend,
        signal_policy=signal_policy,
        cost_gate=cost_gate,
        regime_gate=regime_gate,
        source_path=source_path,
        sha256=sha256,
    )


def _resolve_model_params(
    params: Mapping[str, Any],
    *,
    symbol: str,
) -> dict[str, Any]:
    resolved = dict(params)

    if resolved.get("pip_size") == "auto":
        resolved["pip_size"] = instrument_specification(
            symbol
        ).pip_size

    return resolved


def _wrap_cost_gate(
    model: AlphaModel,
    config: Mapping[str, Any],
) -> CostAwareAlphaModel:
    return CostAwareAlphaModel(
        inner=model,
        gate=MinimumExpectedMoveGate(
            cost_estimate_pips=float(
                config.get(
                    "cost_estimate_pips",
                    3.7,
                )
            ),
            safety_factor=float(
                config.get(
                    "safety_factor",
                    1.0,
                )
            ),
            expected_move_key=str(
                config.get(
                    "expected_move_key",
                    "expected_move_pips",
                )
            ),
        ),
    )


def _wrap_regime_gate(
    model: AlphaModel,
    config: Mapping[str, Any],
) -> RegimeGatedAlphaModel:
    kwargs = dict(config)

    if "allowed_regimes" in kwargs:
        allowed_regimes = kwargs["allowed_regimes"]

        if not isinstance(allowed_regimes, list):
            raise ValueError(
                "allowed_regimes must be a list"
            )

        kwargs["allowed_regimes"] = tuple(allowed_regimes)

    return RegimeGatedAlphaModel(
        inner=model,
        gate=TrendVolatilityRegimeGate(**kwargs),
    )


def _resolve_config_path(
    path: str | Path,
) -> Path:
    candidate = Path(path)

    if candidate.is_absolute():
        return candidate

    return REPO_ROOT / candidate


def _optional_mapping(
    payload: Mapping[str, Any],
    key: str,
) -> Mapping[str, Any]:
    value = payload.get(
        key,
        {},
    )

    if value is None:
        return {}

    if not isinstance(value, Mapping):
        raise ValueError(
            f"{key} must be a mapping"
        )

    return value


def _required_string(
    payload: Mapping[str, Any],
    key: str,
) -> str:
    value = payload.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{key} must be a non-empty string"
        )

    return value.strip()


def _validate_positive_number(
    name: str,
    value: Any,
) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(
            f"{name} must be a finite positive number"
        )


def _parse_yaml_subset(
    text: str,
) -> Any:
    lines = _preprocess_yaml_lines(text)

    if not lines:
        raise ValueError(
            "strategy config cannot be empty"
        )

    result, index = _parse_yaml_block(
        lines,
        0,
        lines[0][0],
    )

    if index != len(lines):
        raise ValueError(
            "could not parse complete strategy config"
        )

    return result


def _preprocess_yaml_lines(
    text: str,
) -> list[tuple[int, str]]:
    result = []

    for raw_line in text.splitlines():
        if "\t" in raw_line:
            raise ValueError(
                "tabs are not supported in strategy YAML"
            )

        stripped = raw_line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        result.append((indent, stripped))

    return result


def _parse_yaml_block(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
) -> tuple[Any, int]:
    if lines[index][0] != indent:
        raise ValueError(
            "invalid YAML indentation"
        )

    if lines[index][1].startswith("- "):
        return _parse_yaml_list(
            lines,
            index,
            indent,
        )

    return _parse_yaml_mapping(
        lines,
        index,
        indent,
    )


def _parse_yaml_mapping(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}

    while index < len(lines):
        current_indent, content = lines[index]

        if current_indent < indent:
            break

        if current_indent > indent:
            raise ValueError(
                "invalid YAML indentation"
            )

        if content.startswith("- "):
            break

        key, raw_value = _split_yaml_key_value(content)
        index += 1

        if raw_value == "":
            if index >= len(lines) or lines[index][0] <= indent:
                result[key] = {}
            else:
                child, index = _parse_yaml_block(
                    lines,
                    index,
                    lines[index][0],
                )
                result[key] = child
        else:
            result[key] = _parse_yaml_scalar(raw_value)

    return result, index


def _parse_yaml_list(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
) -> tuple[list[Any], int]:
    result = []

    while index < len(lines):
        current_indent, content = lines[index]

        if current_indent < indent:
            break

        if current_indent > indent:
            raise ValueError(
                "invalid YAML indentation"
            )

        if not content.startswith("- "):
            break

        item = content[2:].strip()
        index += 1

        if item == "":
            if index >= len(lines) or lines[index][0] <= indent:
                result.append(None)
            else:
                child, index = _parse_yaml_block(
                    lines,
                    index,
                    lines[index][0],
                )
                result.append(child)
            continue

        if ":" in item:
            key, raw_value = _split_yaml_key_value(item)
            child_mapping: dict[str, Any] = {}

            if raw_value == "":
                if index >= len(lines) or lines[index][0] <= indent:
                    child_mapping[key] = {}
                else:
                    child, index = _parse_yaml_block(
                        lines,
                        index,
                        lines[index][0],
                    )
                    child_mapping[key] = child
            else:
                child_mapping[key] = _parse_yaml_scalar(raw_value)

            if index < len(lines) and lines[index][0] > indent:
                child, index = _parse_yaml_block(
                    lines,
                    index,
                    lines[index][0],
                )

                if not isinstance(child, Mapping):
                    raise ValueError(
                        "list item continuation must be a mapping"
                    )

                child_mapping.update(child)

            result.append(child_mapping)

        else:
            result.append(
                _parse_yaml_scalar(item)
            )

    return result, index


def _split_yaml_key_value(
    content: str,
) -> tuple[str, str]:
    if ":" not in content:
        raise ValueError(
            f"expected key: value, got {content!r}"
        )

    key, raw_value = content.split(":", 1)
    key = key.strip()

    if not key:
        raise ValueError(
            "YAML key cannot be empty"
        )

    return key, raw_value.strip()


def _parse_yaml_scalar(
    raw_value: str,
) -> Any:
    value = raw_value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in ("'", '"')
    ):
        return value[1:-1]

    if value in ("true", "True"):
        return True

    if value in ("false", "False"):
        return False

    if value in ("null", "Null", "~"):
        return None

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()

        if not inner:
            return []

        return [
            _parse_yaml_scalar(part.strip())
            for part in inner.split(",")
        ]

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        return value

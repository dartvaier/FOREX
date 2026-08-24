"""Pre-declared development-window parameter sensitivity analysis."""

from dataclasses import dataclass, field, replace
from hashlib import sha256
import json
from math import isfinite
from statistics import median, pstdev
from types import MappingProxyType
from typing import Mapping

from backtest.performance import PerformanceReport
from experiments.framework import ExperimentRunner, ExperimentSpec


@dataclass(frozen=True, slots=True)
class ParameterSet:
    strategy_parameters: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.strategy_parameters, Mapping): raise TypeError("strategy_parameters must be a Mapping")
        object.__setattr__(self, "strategy_parameters", MappingProxyType(dict(self.strategy_parameters)))
        json.dumps(dict(self.strategy_parameters), sort_keys=True)

    @property
    def fingerprint(self) -> str:
        return sha256(json.dumps(dict(self.strategy_parameters), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SensitivitySpec:
    experiment_spec: ExperimentSpec
    parameter_sets: tuple[ParameterSet, ...]
    name: str = "ema-development-sensitivity"

    def __post_init__(self) -> None:
        if not isinstance(self.experiment_spec, ExperimentSpec) or not self.parameter_sets: raise ValueError("experiment_spec and at least one ParameterSet are required")
        if len({item.fingerprint for item in self.parameter_sets}) != len(self.parameter_sets): raise ValueError("parameter sets must be unique")

    @property
    def fingerprint(self) -> str:
        payload = {"experiment": self.experiment_spec.fingerprint, "parameters": [item.fingerprint for item in self.parameter_sets], "name": self.name}
        return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SensitivityResult:
    parameter_set: ParameterSet
    fingerprint: str
    report: PerformanceReport


@dataclass(frozen=True, slots=True)
class RobustnessSummary:
    median_return_percent: float
    median_sharpe: float | None
    median_profit_factor: float | None
    median_drawdown_percent: float
    profitable_run_proportion: float
    return_dispersion: float
    neighborhood_stability: float | None


class SensitivityRunner:
    def __init__(self, experiment_runner: ExperimentRunner) -> None:
        if not isinstance(experiment_runner, ExperimentRunner): raise TypeError("experiment_runner must be an ExperimentRunner")
        self._runner = experiment_runner

    def run(self, spec: SensitivitySpec) -> tuple[tuple[SensitivityResult, ...], RobustnessSummary]:
        if not isinstance(spec, SensitivitySpec): raise TypeError("spec must be a SensitivitySpec")
        results = []
        for params in spec.parameter_sets:
            experiment = replace(spec.experiment_spec, strategy_parameters=params.strategy_parameters)
            _, report = self._runner.run_development(experiment)
            results.append(SensitivityResult(params, sha256((spec.fingerprint + params.fingerprint).encode()).hexdigest(), report))
        frozen = tuple(results)
        return frozen, self._summary(frozen)

    @staticmethod
    def _summary(results: tuple[SensitivityResult, ...]) -> RobustnessSummary:
        returns = [item.report.percentage_return for item in results]
        sharpes = [item.report.sharpe_ratio for item in results if item.report.sharpe_ratio is not None]
        factors = [item.report.profit_factor for item in results if item.report.profit_factor is not None and isfinite(item.report.profit_factor)]
        drawdowns = [item.report.maximum_drawdown_percent for item in results]
        signs = [value > 0 for value in returns]
        stability = None if len(signs) < 2 else sum(left == right for left, right in zip(signs, signs[1:])) / (len(signs) - 1)
        return RobustnessSummary(median(returns), None if not sharpes else median(sharpes), None if not factors else median(factors), median(drawdowns), sum(signs) / len(signs), pstdev(returns), stability)

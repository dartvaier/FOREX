"""Immutable, chronological in-sample/out-of-sample experiment framework."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping

import pandas as pd

from backtest.costs import FixedCostModel
from backtest.engine import BacktestEngine, BacktestResult
from backtest.execution import SimulatedExecution
from backtest.feed import HistoricalBarFeed
from backtest.models import BacktestConfig, Timeframe
from backtest.performance import PerformanceAnalytics, PerformanceReport
from backtest.portfolio import Portfolio
from backtest.risk import FixedSizeRiskModel, RiskLimits
from strategies.ema_crossover import EmaCrossoverStrategy


def _utc(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0): raise ValueError(f"{name} must be timezone-aware UTC")


@dataclass(frozen=True, slots=True)
class TemporalSplit:
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    warmup_bars: int = 0

    def __post_init__(self) -> None:
        for name in ("train_start", "train_end", "test_start", "test_end"): _utc(getattr(self, name), name)
        if not self.train_start < self.train_end <= self.test_start < self.test_end: raise ValueError("split windows must be strictly chronological and non-overlapping")
        if not isinstance(self.warmup_bars, int) or isinstance(self.warmup_bars, bool) or self.warmup_bars < 0: raise ValueError("warmup_bars must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    name: str
    dataset_id: str
    symbol: str
    timeframe: Timeframe
    split: TemporalSplit
    strategy_parameters: Mapping[str, object] = field(default_factory=dict)
    risk_parameters: Mapping[str, object] = field(default_factory=dict)
    cost_parameters: Mapping[str, object] = field(default_factory=dict)
    initial_capital: float = 10_000.0

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.dataset_id.strip() or not self.symbol.strip(): raise ValueError("name, dataset_id and symbol must be non-empty")
        if not isinstance(self.timeframe, Timeframe) or not isinstance(self.split, TemporalSplit): raise TypeError("timeframe and split must be valid")
        if self.initial_capital <= 0: raise ValueError("initial_capital must be positive")
        for name in ("strategy_parameters", "risk_parameters", "cost_parameters"):
            value = getattr(self, name)
            if not isinstance(value, Mapping): raise TypeError(f"{name} must be a Mapping")
            object.__setattr__(self, name, MappingProxyType(dict(value)))
        json.dumps(self.payload(), sort_keys=True)

    def payload(self) -> dict[str, object]:
        split = {"train_start": self.split.train_start.isoformat(), "train_end": self.split.train_end.isoformat(), "test_start": self.split.test_start.isoformat(), "test_end": self.split.test_end.isoformat(), "warmup_bars": self.split.warmup_bars}
        return {"name": self.name, "dataset_id": self.dataset_id, "symbol": self.symbol, "timeframe": self.timeframe.value, "split": split, "strategy_parameters": dict(self.strategy_parameters), "risk_parameters": dict(self.risk_parameters), "cost_parameters": dict(self.cost_parameters), "initial_capital": self.initial_capital}

    @property
    def fingerprint(self) -> str:
        return sha256(json.dumps(self.payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    spec: ExperimentSpec
    fingerprint: str
    in_sample_report: PerformanceReport
    out_of_sample_report: PerformanceReport
    in_sample_backtest: BacktestResult
    out_of_sample_backtest: BacktestResult


class ExperimentRunner:
    """Runs an EMA strategy independently in non-overlapping temporal windows."""

    def __init__(self, dataframe: pd.DataFrame) -> None:
        if not isinstance(dataframe, pd.DataFrame): raise TypeError("dataframe must be a pandas DataFrame")
        self._dataframe = dataframe.copy()
        if "time" not in self._dataframe: raise ValueError("dataframe must contain time")
        self._dataframe["time"] = pd.to_datetime(self._dataframe["time"], utc=True)
        if not self._dataframe["time"].is_monotonic_increasing or self._dataframe["time"].duplicated().any(): raise ValueError("dataset timestamps must be strictly increasing")

    def run(self, spec: ExperimentSpec) -> ExperimentResult:
        if not isinstance(spec, ExperimentSpec): raise TypeError("spec must be an ExperimentSpec")
        train = self._run_window(spec, spec.split.train_start, spec.split.train_end)
        test = self._run_window(spec, spec.split.test_start, spec.split.test_end)
        return ExperimentResult(spec, spec.fingerprint, PerformanceAnalytics().analyze(train), PerformanceAnalytics().analyze(test), train, test)

    def _run_window(self, spec: ExperimentSpec, start: datetime, end: datetime) -> BacktestResult:
        before = self._dataframe[self._dataframe.time < pd.Timestamp(start)]
        active = self._dataframe[(self._dataframe.time >= pd.Timestamp(start)) & (self._dataframe.time < pd.Timestamp(end))]
        if active.empty: raise ValueError("split window has no bars")
        frame = pd.concat((before.tail(spec.split.warmup_bars), active), ignore_index=True)
        strategy = EmaCrossoverStrategy(spec.symbol, **dict(spec.strategy_parameters))
        quantity = float(spec.risk_parameters.get("quantity", 1.0))
        costs = FixedCostModel(**dict(spec.cost_parameters))
        feed = HistoricalBarFeed(frame, BacktestConfig(spec.symbol, spec.timeframe, frame.time.iloc[0].to_pydatetime(), end, spec.initial_capital))
        return BacktestEngine(feed=feed, strategy=strategy, risk_model=FixedSizeRiskModel(RiskLimits(spec.symbol), quantity), execution=SimulatedExecution(costs), portfolio=Portfolio(symbol=spec.symbol, initial_cash=spec.initial_capital), context_closed_bar_limit=max(spec.split.warmup_bars, int(spec.strategy_parameters.get("slow_period", 50)) + 1), trading_start=start).run()

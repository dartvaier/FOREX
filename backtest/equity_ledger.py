import math
from dataclasses import dataclass
from datetime import datetime
from numbers import Real

from backtest.models.enums import SimulationPhase


@dataclass(frozen=True, slots=True)
class EquityPoint:
    timestamp: datetime
    bar_index: int
    phase: SimulationPhase

    cash: float
    equity: float

    realized_pnl: float
    unrealized_pnl: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.timestamp, datetime)
            or self.timestamp.tzinfo is None
            or self.timestamp.utcoffset() is None
        ):
            raise ValueError(
                "timestamp must be timezone-aware"
            )

        if (
            not isinstance(self.bar_index, int)
            or isinstance(self.bar_index, bool)
            or self.bar_index < 0
        ):
            raise ValueError(
                "bar_index must be a non-negative integer"
            )

        if not isinstance(
            self.phase,
            SimulationPhase,
        ):
            raise TypeError(
                "phase must be a SimulationPhase"
            )

        for name, value in (
            ("cash", self.cash),
            ("equity", self.equity),
            ("realized_pnl", self.realized_pnl),
            ("unrealized_pnl", self.unrealized_pnl),
        ):
            if (
                not isinstance(value, Real)
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise ValueError(
                    f"{name} must be a finite number"
                )

        expected_equity = (
            self.cash
            + self.unrealized_pnl
        )

        if not math.isclose(
            self.equity,
            expected_equity,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "equity must equal cash + unrealized_pnl"
            )


class EquityLedger:
    """
    Ordered ledger of Portfolio equity snapshots.

    Equal timestamps are allowed because a BAR_CLOSE and the
    next BAR_OPEN may share the same timestamp.

    Insertion order remains authoritative.
    """

    def __init__(self) -> None:
        self._points: list[EquityPoint] = []

    @property
    def points(self) -> tuple[EquityPoint, ...]:
        return tuple(self._points)

    @property
    def count(self) -> int:
        return len(self._points)

    @property
    def is_empty(self) -> bool:
        return not self._points

    @property
    def last_point(self) -> EquityPoint | None:
        if not self._points:
            return None

        return self._points[-1]

    def append(
        self,
        point: EquityPoint,
    ) -> None:
        if not isinstance(
            point,
            EquityPoint,
        ):
            raise TypeError(
                "point must be an EquityPoint"
            )

        if self._points:
            previous = self._points[-1]

            if point.timestamp < previous.timestamp:
                raise ValueError(
                    "EquityPoint timestamp cannot move backward"
                )

        self._points.append(point)

    def __len__(self) -> int:
        return len(self._points)

    def __iter__(self):
        return iter(self.points)
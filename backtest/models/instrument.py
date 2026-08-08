import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True, slots=True)
class InstrumentSpecification:
    """
    Immutable specification of a tradable instrument.

    The BacktestEngine must not hardcode broker-specific
    properties such as contract size, pip size or volume
    constraints.

    tick_value is optional because its monetary meaning may
    depend on broker/account currency and may require dynamic
    currency conversion for some instruments.
    """

    symbol: str

    digits: int

    point: float
    pip_size: float

    contract_size: float

    volume_min: float
    volume_max: float
    volume_step: float

    tick_size: float
    tick_value: float | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.symbol, str)
            or not self.symbol.strip()
        ):
            raise ValueError(
                "symbol must be a non-empty string"
            )

        if (
            not isinstance(self.digits, int)
            or isinstance(self.digits, bool)
            or self.digits < 0
        ):
            raise ValueError(
                "digits must be a non-negative integer"
            )

        self._validate_positive_number(
            "point",
            self.point,
        )

        self._validate_positive_number(
            "pip_size",
            self.pip_size,
        )

        self._validate_positive_number(
            "contract_size",
            self.contract_size,
        )

        self._validate_positive_number(
            "volume_min",
            self.volume_min,
        )

        self._validate_positive_number(
            "volume_max",
            self.volume_max,
        )

        self._validate_positive_number(
            "volume_step",
            self.volume_step,
        )

        self._validate_positive_number(
            "tick_size",
            self.tick_size,
        )

        if self.tick_value is not None:
            self._validate_positive_number(
                "tick_value",
                self.tick_value,
            )

        if self.volume_max < self.volume_min:
            raise ValueError(
                "volume_max cannot be smaller than volume_min"
            )

        if self.volume_step > self.volume_max:
            raise ValueError(
                "volume_step cannot be greater than volume_max"
            )

        if self.pip_size < self.point:
            raise ValueError(
                "pip_size cannot be smaller than point"
            )

        if self.tick_size < self.point:
            raise ValueError(
                "tick_size cannot be smaller than point"
            )

    @staticmethod
    def _validate_positive_number(
        name: str,
        value: Real,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a finite positive number"
            )

    @property
    def points_per_pip(self) -> float:
        """
        Number of broker points contained in one pip.

        Example for a typical 5-digit EURUSD quote:

            point    = 0.00001
            pip_size = 0.00010

            points_per_pip = 10
        """

        return self.pip_size / self.point
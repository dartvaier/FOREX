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

    # Currency legs (roadmap §104 / docs/20-21). Defaults preserve
    # the historical single-pair behavior (USD-quote).
    base_currency: str = "USD"
    quote_currency: str = "USD"

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

        for name in ("base_currency", "quote_currency"):
            currency = getattr(self, name)

            if (
                not isinstance(currency, str)
                or len(currency) != 3
                or not currency.isalpha()
                or currency != currency.upper()
            ):
                raise ValueError(
                    f"{name} must be a 3-letter uppercase "
                    f"currency code, got {currency!r}"
                )

    def quote_to_account_rate(
        self,
        price: float,
    ) -> float:
        """
        Quote-currency to account-currency (USD) conversion rate
        at the given price.

        - USD-quote pairs (EURUSD, GBPUSD, ...): quote == account
          currency -> rate 1.0.
        - USD-base pairs (USDJPY, USDCHF, USDCAD): one unit of
          quote currency equals 1/price USD -> rate 1/price.
        - Any other structure (crosses) requires a triangular
          conversion that is not implemented (docs/20-21).

        The rate is a function of the market price so callers can
        keep it causal (use the price available at the decision
        instant, e.g. the exit fill price for realized PnL).
        """
        if (
            not isinstance(price, Real)
            or isinstance(price, bool)
            or not math.isfinite(price)
            or price <= 0
        ):
            raise ValueError(
                "price must be a finite positive number"
            )

        if self.quote_currency == "USD":
            return 1.0

        if self.base_currency == "USD":
            return 1.0 / price

        raise ValueError(
            "cross currency conversion is not implemented "
            f"({self.base_currency}{self.quote_currency}); "
            "only USD-quote and USD-base pairs are supported "
            "(docs/20-21)"
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
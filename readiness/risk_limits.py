"""
Risk limits for the F10 Live Readiness Review (roadmap §91).

Pure checks on the dimensions the review must cover:

    risk per trade, daily risk, max drawdown, leverage, exposure.

All functions are pure and broker-independent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PIP_DEFAULT = 0.0001


@dataclass(frozen=True, slots=True)
class RiskLimitConfig:
    """Limits used by the readiness risk review."""

    risk_per_trade_pct: float = 0.01
    max_daily_loss_pct: float = 0.03
    max_drawdown_pct: float = 0.10
    max_leverage: float = 20.0
    max_exposure_pct: float = 0.50


@dataclass(frozen=True, slots=True)
class RiskLimitsReport:
    """Verdict of the risk limits review."""

    violations: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.violations


def risk_amount(
    balance: float,
    risk_pct: float,
) -> float:
    """Capital at risk for one trade (balance * risk_pct)."""
    if balance < 0:
        raise ValueError("balance cannot be negative")

    if not (0.0 < risk_pct < 1.0):
        raise ValueError("risk_pct must be in (0, 1)")

    return balance * risk_pct


def stop_distance_pips(
    entry_price: float,
    stop_price: float,
    *,
    pip_size: float = PIP_DEFAULT,
) -> float:
    """Absolute stop distance in pips."""
    if entry_price <= 0 or stop_price <= 0:
        raise ValueError("prices must be positive")

    if pip_size <= 0:
        raise ValueError("pip_size must be positive")

    return abs(entry_price - stop_price) / pip_size


def position_size_for_risk(
    risk_amount_value: float,
    stop_distance_pips: float,
    pip_value_per_lot: float,
) -> float:
    """
    Lot size so that a stop-out loses at most `risk_amount_value`.

    pip_value_per_lot: USD per pip per standard lot (e.g. 10 USD
    for EURUSD). Returns lots (no broker rounding applied here).
    """
    if risk_amount_value <= 0:
        raise ValueError("risk_amount must be positive")

    if stop_distance_pips <= 0:
        raise ValueError("stop_distance_pips must be positive")

    if pip_value_per_lot <= 0:
        raise ValueError("pip_value_per_lot must be positive")

    return risk_amount_value / (
        stop_distance_pips * pip_value_per_lot
    )


def evaluate_risk_limits(
    *,
    balance: float,
    equity: float,
    daily_loss: float,
    current_drawdown_pct: float,
    open_exposure_notional: float,
    config: RiskLimitConfig | None = None,
) -> RiskLimitsReport:
    """
    Evaluate the §91 risk dimensions against configured limits.

    Violations are collected, not raised.
    """
    limits = config or RiskLimitConfig()
    violations: list[str] = []

    if daily_loss > 0:
        daily_loss_pct = daily_loss / balance if balance > 0 else 1.0

        if daily_loss_pct > limits.max_daily_loss_pct:
            violations.append(
                f"daily loss {daily_loss_pct:.2%} exceeds limit "
                f"{limits.max_daily_loss_pct:.2%}"
            )

    if current_drawdown_pct > limits.max_drawdown_pct:
        violations.append(
            f"drawdown {current_drawdown_pct:.2%} exceeds limit "
            f"{limits.max_drawdown_pct:.2%}"
        )

    if equity > 0:
        exposure_pct = open_exposure_notional / equity

        if exposure_pct > limits.max_exposure_pct:
            violations.append(
                f"exposure {exposure_pct:.2%} exceeds limit "
                f"{limits.max_exposure_pct:.2%}"
            )

        leverage = open_exposure_notional / equity

        if leverage > limits.max_leverage:
            violations.append(
                f"leverage {leverage:.2f}x exceeds limit "
                f"{limits.max_leverage:.2f}x"
            )

    return RiskLimitsReport(
        violations=tuple(violations),
    )

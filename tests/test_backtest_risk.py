from datetime import datetime, timezone

import pytest

from backtest.equity_ledger import EquityPoint
from backtest.models import (
    InstrumentSpecification,
    Signal,
    SignalAction,
)
from backtest.models.enums import SimulationPhase
from backtest.risk import (
    DailyLossRiskGate,
    DrawdownRiskGate,
    ExposureLimitRiskGate,
    FixedSizeRiskGate,
    KillSwitchRiskGate,
    RiskDecision,
    StopBasedRiskGate,
    VolumeRules,
)


def timestamp():
    return datetime(
        2026,
        8,
        8,
        10,
        15,
        tzinfo=timezone.utc,
    )


def make_instrument():
    return InstrumentSpecification(
        symbol="EURUSD",
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
    )


def make_signal(
    action: SignalAction,
    *,
    metadata: dict | None = None,
) -> Signal:
    return Signal(
        signal_id="SIG-001",
        strategy_id="TEST",
        symbol="EURUSD",
        timestamp=timestamp(),
        action=action,
        metadata=(
            {}
            if metadata is None
            else metadata
        ),
    )


def make_equity_point(
    *,
    equity: float,
    day: int = 8,
) -> EquityPoint:
    return EquityPoint(
        timestamp=datetime(
            2026,
            8,
            day,
            10,
            15,
            tzinfo=timezone.utc,
        ),
        bar_index=0,
        phase=SimulationPhase.BAR_CLOSE,
        cash=equity,
        equity=equity,
        realized_pnl=equity - 10000.0,
        unrealized_pnl=0.0,
    )


def test_fixed_size_risk_gate_is_created():
    instrument = make_instrument()

    gate = FixedSizeRiskGate(
        instrument=instrument,
        fixed_quantity=0.01,
    )

    assert gate.instrument is instrument
    assert gate.fixed_quantity == 0.01


def test_risk_gate_requires_instrument():
    with pytest.raises(
        TypeError,
        match="InstrumentSpecification",
    ):
        FixedSizeRiskGate(
            instrument=None,  # type: ignore[arg-type]
            fixed_quantity=0.01,
        )


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -0.01,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_risk_gate_requires_positive_finite_quantity(
    quantity,
):
    with pytest.raises(
        ValueError,
        match="fixed_quantity",
    ):
        FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=quantity,
        )


def test_risk_gate_rejects_quantity_below_instrument_min():
    with pytest.raises(
        ValueError,
        match="volume_min",
    ):
        FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.001,
        )


def test_risk_gate_rejects_quantity_above_instrument_max():
    with pytest.raises(
        ValueError,
        match="volume_max",
    ):
        FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=501.0,
        )


def test_risk_gate_rejects_quantity_that_violates_volume_step():
    with pytest.raises(
        ValueError,
        match="volume_step",
    ):
        FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.015,
        )


def test_volume_rules_normalize_quantity_down_to_step():
    rules = VolumeRules(
        make_instrument()
    )

    assert rules.normalize_down(0.019) == 0.01
    assert rules.normalize_down(0.0200000001) == 0.02


def test_risk_gate_approves_long_entry():
    gate = FixedSizeRiskGate(
        instrument=make_instrument(),
        fixed_quantity=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert isinstance(
        decision,
        RiskDecision,
    )

    assert decision.approved is True
    assert decision.quantity == 0.01


def test_risk_gate_approves_short_entry():
    gate = FixedSizeRiskGate(
        instrument=make_instrument(),
        fixed_quantity=0.05,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_SHORT
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.05


def test_risk_gate_hold_requires_no_quantity():
    gate = FixedSizeRiskGate(
        instrument=make_instrument(),
        fixed_quantity=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.HOLD
        )
    )

    assert decision.approved is True
    assert decision.quantity is None

    assert "HOLD" in decision.reason


def test_risk_gate_exit_quantity_is_deferred_to_position():
    gate = FixedSizeRiskGate(
        instrument=make_instrument(),
        fixed_quantity=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.EXIT
        )
    )

    assert decision.approved is True
    assert decision.quantity is None

    assert "Position" in decision.reason


def test_risk_decision_preserves_signal_id():
    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    gate = FixedSizeRiskGate(
        instrument=make_instrument(),
        fixed_quantity=0.01,
    )

    decision = gate.evaluate(signal)

    assert (
        decision.signal_id
        == signal.signal_id
    )


def test_risk_gate_requires_signal():
    gate = FixedSizeRiskGate(
        instrument=make_instrument(),
        fixed_quantity=0.01,
    )

    with pytest.raises(
        TypeError,
        match="Signal",
    ):
        gate.evaluate(
            object()  # type: ignore[arg-type]
        )


def test_risk_gate_rejects_symbol_mismatch():
    signal = Signal(
        signal_id="SIG-001",
        strategy_id="TEST",
        symbol="GBPUSD",
        timestamp=timestamp(),
        action=SignalAction.ENTER_LONG,
    )

    gate = FixedSizeRiskGate(
        instrument=make_instrument(),
        fixed_quantity=0.01,
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        gate.evaluate(signal)


def test_risk_decision_requires_signal_id():
    with pytest.raises(
        ValueError,
        match="signal_id",
    ):
        RiskDecision(
            signal_id="",
            approved=True,
            quantity=0.01,
            reason="Test",
        )


def test_risk_decision_requires_boolean_approved():
    with pytest.raises(
        TypeError,
        match="approved",
    ):
        RiskDecision(
            signal_id="SIG-001",
            approved=1,  # type: ignore[arg-type]
            quantity=0.01,
            reason="Test",
        )


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -0.01,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_risk_decision_validates_quantity(
    quantity,
):
    with pytest.raises(
        ValueError,
        match="quantity",
    ):
        RiskDecision(
            signal_id="SIG-001",
            approved=True,
            quantity=quantity,
            reason="Test",
        )


def test_risk_decision_allows_none_quantity():
    decision = RiskDecision(
        signal_id="SIG-001",
        approved=True,
        quantity=None,
        reason="No quantity required",
    )

    assert decision.quantity is None


def test_risk_decision_requires_reason():
    with pytest.raises(
        ValueError,
        match="reason",
    ):
        RiskDecision(
            signal_id="SIG-001",
            approved=True,
            quantity=0.01,
            reason="",
        )


def test_risk_decision_is_immutable():
    decision = RiskDecision(
        signal_id="SIG-001",
        approved=True,
        quantity=0.01,
        reason="Test",
    )

    with pytest.raises(AttributeError):
        decision.quantity = 1.0  # type: ignore[misc]


def test_stop_based_risk_gate_sizes_long_entry_from_stop_loss():
    gate = StopBasedRiskGate(
        instrument=make_instrument(),
        account_equity=10000.0,
        risk_fraction=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
                "stop_loss": 1.0900,
            },
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.10
    assert "StopBasedRiskGate" in decision.reason


def test_stop_based_risk_gate_sizes_short_entry_from_stop_loss():
    gate = StopBasedRiskGate(
        instrument=make_instrument(),
        account_equity=10000.0,
        risk_fraction=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_SHORT,
            metadata={
                "entry_price": 1.1000,
                "stop_loss": 1.1100,
            },
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.10


def test_stop_based_risk_gate_rejects_missing_entry_price():
    gate = StopBasedRiskGate(
        instrument=make_instrument(),
        account_equity=10000.0,
        risk_fraction=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "stop_loss": 1.0900,
            },
        )
    )

    assert decision.approved is False
    assert decision.quantity is None
    assert "entry_price" in decision.reason


def test_stop_based_risk_gate_rejects_missing_stop_loss():
    gate = StopBasedRiskGate(
        instrument=make_instrument(),
        account_equity=10000.0,
        risk_fraction=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
            },
        )
    )

    assert decision.approved is False
    assert decision.quantity is None
    assert "stop_loss" in decision.reason


def test_stop_based_risk_gate_rejects_invalid_long_stop_side():
    gate = StopBasedRiskGate(
        instrument=make_instrument(),
        account_equity=10000.0,
        risk_fraction=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
                "stop_loss": 1.1010,
            },
        )
    )

    assert decision.approved is False
    assert "below" in decision.reason


def test_stop_based_risk_gate_rejects_invalid_short_stop_side():
    gate = StopBasedRiskGate(
        instrument=make_instrument(),
        account_equity=10000.0,
        risk_fraction=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_SHORT,
            metadata={
                "entry_price": 1.1000,
                "stop_loss": 1.0990,
            },
        )
    )

    assert decision.approved is False
    assert "above" in decision.reason


def test_stop_based_risk_gate_floors_quantity_to_volume_step():
    gate = StopBasedRiskGate(
        instrument=make_instrument(),
        account_equity=10000.0,
        risk_fraction=0.01,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
                "stop_loss": 1.0933,
            },
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.14


def test_stop_based_risk_gate_applies_max_quantity_cap():
    gate = StopBasedRiskGate(
        instrument=make_instrument(),
        account_equity=10000.0,
        risk_fraction=0.05,
        max_quantity=0.03,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
                "stop_loss": 1.0900,
            },
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.03


def test_stop_based_risk_gate_rejects_quantity_below_minimum():
    gate = StopBasedRiskGate(
        instrument=make_instrument(),
        account_equity=10000.0,
        risk_fraction=0.00001,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
                "stop_loss": 1.0900,
            },
        )
    )

    assert decision.approved is False
    assert "volume_min" in decision.reason


def test_stop_based_risk_gate_validates_configuration():
    with pytest.raises(
        ValueError,
        match="risk_fraction",
    ):
        StopBasedRiskGate(
            instrument=make_instrument(),
            account_equity=10000.0,
            risk_fraction=0.0,
        )

    with pytest.raises(
        ValueError,
        match="risk_fraction",
    ):
        StopBasedRiskGate(
            instrument=make_instrument(),
            account_equity=10000.0,
            risk_fraction=1.5,
        )


def test_exposure_limit_gate_approves_quantity_within_limit():
    gate = ExposureLimitRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_quantity=0.05,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.03
    assert "ExposureLimitRiskGate" in decision.reason


def test_exposure_limit_gate_rejects_quantity_above_limit():
    gate = ExposureLimitRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.10,
        ),
        max_quantity=0.05,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is False
    assert decision.quantity is None
    assert "max_quantity" in decision.reason


def test_exposure_limit_gate_allows_hold_and_exit():
    gate = ExposureLimitRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.10,
        ),
        max_quantity=0.05,
    )

    hold_decision = gate.evaluate(
        make_signal(
            SignalAction.HOLD
        )
    )

    exit_decision = gate.evaluate(
        make_signal(
            SignalAction.EXIT
        )
    )

    assert hold_decision.approved is True
    assert hold_decision.quantity is None
    assert exit_decision.approved is True
    assert exit_decision.quantity is None


def test_exposure_limit_gate_preserves_inner_rejection():
    gate = ExposureLimitRiskGate(
        inner=StopBasedRiskGate(
            instrument=make_instrument(),
            account_equity=10000.0,
            risk_fraction=0.01,
        ),
        max_quantity=0.50,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
            },
        )
    )

    assert decision.approved is False
    assert "stop_loss" in decision.reason


def test_exposure_limit_gate_rejects_missing_entry_price_for_notional():
    gate = ExposureLimitRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.10,
        ),
        max_notional=10000.0,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is False
    assert "entry_price" in decision.reason


def test_exposure_limit_gate_approves_notional_within_limit():
    gate = ExposureLimitRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.05,
        ),
        max_notional=10000.0,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
            },
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.05


def test_exposure_limit_gate_rejects_notional_above_limit():
    gate = ExposureLimitRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.10,
        ),
        max_notional=10000.0,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
            },
        )
    )

    assert decision.approved is False
    assert "max_notional" in decision.reason


def test_exposure_limit_gate_validates_configuration():
    with pytest.raises(
        TypeError,
        match="RiskGate",
    ):
        ExposureLimitRiskGate(
            inner=object(),  # type: ignore[arg-type]
            max_quantity=0.10,
        )

    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        ExposureLimitRiskGate(
            inner=FixedSizeRiskGate(
                instrument=make_instrument(),
                fixed_quantity=0.01,
            ),
        )

    with pytest.raises(
        ValueError,
        match="max_notional",
    ):
        ExposureLimitRiskGate(
            inner=FixedSizeRiskGate(
                instrument=make_instrument(),
                fixed_quantity=0.01,
            ),
            max_notional=0.0,
        )


def test_daily_loss_gate_approves_entry_before_limit():
    gate = DailyLossRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_daily_loss=100.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9950.0,
        )
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.03
    assert "DailyLossRiskGate" in decision.reason
    assert gate.daily_loss == pytest.approx(50.0)


def test_daily_loss_gate_rejects_entry_after_absolute_limit():
    gate = DailyLossRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_daily_loss=50.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9950.0,
        )
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is False
    assert decision.quantity is None
    assert "daily loss" in decision.reason
    assert gate.is_locked is True


def test_daily_loss_gate_rejects_entry_after_fraction_limit():
    gate = DailyLossRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_daily_loss_fraction=0.01,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9900.0,
        )
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_SHORT
        )
    )

    assert decision.approved is False
    assert decision.quantity is None
    assert gate.daily_loss_fraction == pytest.approx(0.01)


def test_daily_loss_gate_resets_on_new_utc_day():
    gate = DailyLossRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_daily_loss=50.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
            day=8,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9950.0,
            day=8,
        )
    )

    assert gate.is_locked is True

    gate.observe_equity(
        make_equity_point(
            equity=9950.0,
            day=9,
        )
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert gate.is_locked is False
    assert gate.day_start_equity == pytest.approx(9950.0)
    assert decision.approved is True


def test_daily_loss_gate_allows_hold_and_exit_when_locked():
    gate = DailyLossRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_daily_loss=50.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9900.0,
        )
    )

    hold_decision = gate.evaluate(
        make_signal(
            SignalAction.HOLD
        )
    )

    exit_decision = gate.evaluate(
        make_signal(
            SignalAction.EXIT
        )
    )

    assert hold_decision.approved is True
    assert hold_decision.quantity is None
    assert exit_decision.approved is True
    assert exit_decision.quantity is None


def test_daily_loss_gate_preserves_inner_rejection():
    gate = DailyLossRiskGate(
        inner=StopBasedRiskGate(
            instrument=make_instrument(),
            account_equity=10000.0,
            risk_fraction=0.01,
        ),
        max_daily_loss=50.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
            },
        )
    )

    assert decision.approved is False
    assert "stop_loss" in decision.reason


def test_daily_loss_gate_requires_equity_before_entry():
    gate = DailyLossRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_daily_loss=50.0,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is False
    assert "equity snapshot" in decision.reason


def test_daily_loss_gate_validates_configuration():
    with pytest.raises(
        TypeError,
        match="RiskGate",
    ):
        DailyLossRiskGate(
            inner=object(),  # type: ignore[arg-type]
            max_daily_loss=50.0,
        )

    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        DailyLossRiskGate(
            inner=FixedSizeRiskGate(
                instrument=make_instrument(),
                fixed_quantity=0.01,
            ),
        )

    with pytest.raises(
        ValueError,
        match="max_daily_loss",
    ):
        DailyLossRiskGate(
            inner=FixedSizeRiskGate(
                instrument=make_instrument(),
                fixed_quantity=0.01,
            ),
            max_daily_loss=0.0,
        )

    with pytest.raises(
        ValueError,
        match="max_daily_loss_fraction",
    ):
        DailyLossRiskGate(
            inner=FixedSizeRiskGate(
                instrument=make_instrument(),
                fixed_quantity=0.01,
            ),
            max_daily_loss_fraction=1.5,
        )

    gate = DailyLossRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.01,
        ),
        max_daily_loss=50.0,
    )

    with pytest.raises(
        TypeError,
        match="EquityPoint",
    ):
        gate.observe_equity(
            object()  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# DrawdownRiskGate
# ---------------------------------------------------------------------------


def test_drawdown_gate_approves_entry_when_drawdown_is_within_limit():
    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_drawdown=200.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9850.0,
        )
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.03
    assert "DrawdownRiskGate" in decision.reason
    assert gate.current_drawdown == pytest.approx(150.0)
    assert gate.is_locked is False


def test_drawdown_gate_rejects_entry_after_absolute_drawdown_limit():
    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_drawdown=100.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9890.0,
        )
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is False
    assert decision.quantity is None
    assert "drawdown limit" in decision.reason
    assert gate.is_locked is True
    assert gate.current_drawdown == pytest.approx(110.0)


def test_drawdown_gate_rejects_entry_after_pct_drawdown_limit():
    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_drawdown_pct=2.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9790.0,
        )
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is False
    assert decision.quantity is None
    assert gate.is_locked is True
    assert gate.current_drawdown_pct == pytest.approx(2.1)


def test_drawdown_gate_tracks_peak_and_updates_on_new_high():
    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_drawdown=100.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=10100.0,
        )
    )

    assert gate.peak_equity == pytest.approx(10100.0)
    assert gate.current_drawdown == pytest.approx(0.0)
    assert gate.is_locked is False


def test_drawdown_gate_unlocks_when_equity_recovers():
    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_drawdown=100.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9890.0,
        )
    )

    assert gate.is_locked is True

    gate.observe_equity(
        make_equity_point(
            equity=9920.0,
        )
    )

    assert gate.is_locked is False
    assert gate.current_drawdown == pytest.approx(80.0)


    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is True


def test_drawdown_gate_unlocks_on_new_peak():
    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_drawdown=100.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9890.0,
        )
    )

    assert gate.is_locked is True

    gate.observe_equity(
        make_equity_point(
            equity=10050.0,
        )
    )

    assert gate.is_locked is False
    assert gate.peak_equity == pytest.approx(10050.0)
    assert gate.current_drawdown == pytest.approx(0.0)


def test_drawdown_gate_allows_hold_and_exit_when_locked():
    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_drawdown=100.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    gate.observe_equity(
        make_equity_point(
            equity=9850.0,
        )
    )

    assert gate.is_locked is True

    hold_decision = gate.evaluate(
        make_signal(
            SignalAction.HOLD
        )
    )

    exit_decision = gate.evaluate(
        make_signal(
            SignalAction.EXIT
        )
    )

    assert hold_decision.approved is True
    assert hold_decision.quantity is None
    assert exit_decision.approved is True
    assert exit_decision.quantity is None


def test_drawdown_gate_preserves_inner_rejection():
    gate = DrawdownRiskGate(
        inner=StopBasedRiskGate(
            instrument=make_instrument(),
            account_equity=10000.0,
            risk_fraction=0.01,
        ),
        max_drawdown=200.0,
    )

    gate.observe_equity(
        make_equity_point(
            equity=10000.0,
        )
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
            },
        )
    )

    assert decision.approved is False
    assert "stop_loss" in decision.reason


def test_drawdown_gate_requires_equity_before_entry():
    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        max_drawdown=100.0,
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is False
    assert "equity snapshot" in decision.reason


def test_drawdown_gate_validates_configuration():
    with pytest.raises(
        TypeError,
        match="RiskGate",
    ):
        DrawdownRiskGate(
            inner=object(),  # type: ignore[arg-type]
            max_drawdown=100.0,
        )

    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        DrawdownRiskGate(
            inner=FixedSizeRiskGate(
                instrument=make_instrument(),
                fixed_quantity=0.01,
            ),
        )

    with pytest.raises(
        ValueError,
        match="max_drawdown",
    ):
        DrawdownRiskGate(
            inner=FixedSizeRiskGate(
                instrument=make_instrument(),
                fixed_quantity=0.01,
            ),
            max_drawdown=0.0,
        )

    with pytest.raises(
        ValueError,
        match="max_drawdown_pct",
    ):
        DrawdownRiskGate(
            inner=FixedSizeRiskGate(
                instrument=make_instrument(),
                fixed_quantity=0.01,
            ),
            max_drawdown_pct=150.0,
        )

    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.01,
        ),
        max_drawdown=100.0,
    )

    with pytest.raises(
        TypeError,
        match="EquityPoint",
    ):
        gate.observe_equity(
            object()  # type: ignore[arg-type]
        )


def test_drawdown_gate_current_drawdown_is_zero_when_no_equity_observed():
    gate = DrawdownRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.01,
        ),
        max_drawdown=100.0,
    )

    assert gate.current_drawdown == 0.0
    assert gate.current_drawdown_pct == 0.0
    assert gate.peak_equity is None


# ---------------------------------------------------------------------------
# KillSwitchRiskGate
# ---------------------------------------------------------------------------


def test_kill_switch_starts_inactive():
    gate = KillSwitchRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
    )

    assert gate.is_active is False
    assert gate.block_exits is False


def test_kill_switch_arms_and_resets_latch():
    gate = KillSwitchRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
    )

    gate.kill()
    assert gate.is_active is True

    gate.kill()
    assert gate.is_active is True

    gate.reset()
    assert gate.is_active is False


def test_kill_switch_inactive_delegates_approval():
    gate = KillSwitchRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert decision.approved is True
    assert decision.quantity == 0.03
    assert "KillSwitchRiskGate" in decision.reason


def test_kill_switch_soft_mode_rejects_entries_when_active():
    gate = KillSwitchRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
    )

    gate.kill()

    long_decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    short_decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_SHORT
        )
    )

    assert long_decision.approved is False
    assert long_decision.quantity is None
    assert "kill switch" in long_decision.reason
    assert short_decision.approved is False
    assert short_decision.quantity is None


def test_kill_switch_soft_mode_allows_exit_when_active():
    gate = KillSwitchRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
    )

    gate.kill()

    exit_decision = gate.evaluate(
        make_signal(
            SignalAction.EXIT
        )
    )

    assert exit_decision.approved is True
    assert exit_decision.quantity is None


def test_kill_switch_allows_hold_when_active():
    gate = KillSwitchRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
    )

    gate.kill()

    hold_decision = gate.evaluate(
        make_signal(
            SignalAction.HOLD
        )
    )

    assert hold_decision.approved is True
    assert hold_decision.quantity is None


def test_kill_switch_hard_mode_blocks_exit_when_active():
    gate = KillSwitchRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        block_exits=True,
    )

    gate.kill()

    exit_decision = gate.evaluate(
        make_signal(
            SignalAction.EXIT
        )
    )

    assert exit_decision.approved is False
    assert exit_decision.quantity is None
    assert "kill switch" in exit_decision.reason


def test_kill_switch_hard_mode_allows_hold_when_active():
    gate = KillSwitchRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
        block_exits=True,
    )

    gate.kill()

    hold_decision = gate.evaluate(
        make_signal(
            SignalAction.HOLD
        )
    )

    assert hold_decision.approved is True
    assert hold_decision.quantity is None


def test_kill_switch_after_reset_approves_entries_again():
    gate = KillSwitchRiskGate(
        inner=FixedSizeRiskGate(
            instrument=make_instrument(),
            fixed_quantity=0.03,
        ),
    )

    gate.kill()

    blocked = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert blocked.approved is False

    gate.reset()

    approved = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG
        )
    )

    assert approved.approved is True
    assert approved.quantity == 0.03


def test_kill_switch_preserves_inner_rejection():
    gate = KillSwitchRiskGate(
        inner=StopBasedRiskGate(
            instrument=make_instrument(),
            account_equity=10000.0,
            risk_fraction=0.01,
        ),
    )

    decision = gate.evaluate(
        make_signal(
            SignalAction.ENTER_LONG,
            metadata={
                "entry_price": 1.1000,
            },
        )
    )

    assert decision.approved is False
    assert "stop_loss" in decision.reason


def test_kill_switch_validates_configuration():
    with pytest.raises(
        TypeError,
        match="RiskGate",
    ):
        KillSwitchRiskGate(
            inner=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(
        TypeError,
        match="block_exits",
    ):
        KillSwitchRiskGate(
            inner=FixedSizeRiskGate(
                instrument=make_instrument(),
                fixed_quantity=0.01,
            ),
            block_exits=1,  # type: ignore[arg-type]
        )


def test_kill_switch_delegates_instrument():
    inner = FixedSizeRiskGate(
        instrument=make_instrument(),
        fixed_quantity=0.01,
    )

    gate = KillSwitchRiskGate(
        inner=inner,
    )

    assert gate.instrument is inner.instrument
    assert gate.inner is inner

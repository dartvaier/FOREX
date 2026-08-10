from datetime import datetime, timezone

import pytest

from backtest.models import (
    InstrumentSpecification,
    Signal,
    SignalAction,
)
from backtest.risk import (
    FixedSizeRiskGate,
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

"""Tests for H07 stage-2 trade simulator (synthetic fixtures)."""
import pytest

from research.h07_stage2 import simulate_trade, TIMEOUT_BARS


def bar(open_, high, low, close):
    return {"open": open_, "high": high, "low": low, "close": close}


# ---------- LONG ----------

def test_long_tp():
    # long: entry 1.0000, tp 1.0010 (above), sl 0.9980 (below)
    res = simulate_trade(1.0000, 1.0010, 0.9980, [bar(1.0002, 1.0012, 1.0000, 1.0010)], +1)
    assert res["exit_reason"] == "tp"
    assert res["pnl"] == pytest.approx(1.0010 - 1.0000)


def test_long_sl():
    res = simulate_trade(1.0000, 1.0010, 0.9980, [bar(1.0002, 1.0008, 0.9978, 0.9985)], +1)
    assert res["exit_reason"] == "sl"
    assert res["pnl"] == pytest.approx(0.9980 - 1.0000)


def test_long_sl_first_when_both_touched():
    # bar touches both SL (low) and TP (high) -> SL (worst case)
    res = simulate_trade(1.0000, 1.0010, 0.9980, [bar(1.0002, 1.0012, 0.9978, 1.0005)], +1)
    assert res["exit_reason"] == "sl"
    assert res["pnl"] == pytest.approx(0.9980 - 1.0000)


def test_long_gap_up_to_tp_at_open():
    res = simulate_trade(1.0000, 1.0010, 0.9980, [bar(1.0015, 1.0018, 1.0010, 1.0012)], +1)
    assert res["exit_reason"] == "tp"
    assert res["pnl"] == pytest.approx(1.0015 - 1.0000)


def test_long_gap_down_to_sl_at_open():
    res = simulate_trade(1.0000, 1.0010, 0.9980, [bar(0.9975, 0.9980, 0.9970, 0.9978)], +1)
    assert res["exit_reason"] == "sl"
    assert res["pnl"] == pytest.approx(0.9975 - 1.0000)


# ---------- SHORT ----------

def test_short_tp():
    # short: entry 1.0000, tp 0.9990 (below), sl 1.0020 (above)
    res = simulate_trade(1.0000, 0.9990, 1.0020, [bar(0.9998, 1.0005, 0.9988, 0.9992)], -1)
    assert res["exit_reason"] == "tp"
    assert res["pnl"] == pytest.approx(1.0000 - 0.9990)


def test_short_sl():
    res = simulate_trade(1.0000, 0.9990, 1.0020, [bar(0.9998, 1.0025, 0.9995, 1.0018)], -1)
    assert res["exit_reason"] == "sl"
    assert res["pnl"] == pytest.approx(1.0000 - 1.0020)


def test_short_sl_first_when_both_touched():
    res = simulate_trade(1.0000, 0.9990, 1.0020, [bar(0.9998, 1.0022, 0.9988, 1.0005)], -1)
    assert res["exit_reason"] == "sl"
    assert res["pnl"] == pytest.approx(1.0000 - 1.0020)


def test_short_gap_down_to_tp_at_open():
    res = simulate_trade(1.0000, 0.9990, 1.0020, [bar(0.9985, 0.9990, 0.9980, 0.9988)], -1)
    assert res["exit_reason"] == "tp"
    assert res["pnl"] == pytest.approx(1.0000 - 0.9985)


def test_short_gap_up_to_sl_at_open():
    res = simulate_trade(1.0000, 0.9990, 1.0020, [bar(1.0025, 1.0030, 1.0020, 1.0028)], -1)
    assert res["exit_reason"] == "sl"
    assert res["pnl"] == pytest.approx(1.0000 - 1.0025)


# ---------- TIMEOUT ----------

def test_timeout_long_exits_at_close_of_32nd_bar():
    bars = [bar(1.0000, 1.0004, 0.9996, 0.9998)] * TIMEOUT_BARS
    res = simulate_trade(1.0000, 1.0010, 0.9980, bars, +1)
    assert res["exit_reason"] == "timeout"
    assert res["bars_held"] == TIMEOUT_BARS
    assert res["pnl"] == pytest.approx(0.9998 - 1.0000)


def test_timeout_short_exits_at_close_of_32nd_bar():
    bars = [bar(1.0000, 1.0004, 0.9996, 0.9998)] * TIMEOUT_BARS
    res = simulate_trade(1.0000, 0.9990, 1.0020, bars, -1)
    assert res["exit_reason"] == "timeout"
    assert res["bars_held"] == TIMEOUT_BARS
    assert res["pnl"] == pytest.approx(1.0000 - 0.9998)

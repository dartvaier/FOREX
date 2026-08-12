"""Tests for H09 stage-2 trade simulator (synthetic fixtures)."""
import pytest

from research.h09_stage2 import simulate_short, TIMEOUT_BARS


def bar(open_, high, low, close):
    return {"open": open_, "high": high, "low": low, "close": close}


def test_sl_first_when_both_touched_in_same_bar():
    # short: entry 1.1000, tp 1.0990 (below), sl 1.1010 (above)
    # bar touches both -> SL (worst case)
    res = simulate_short(1.1000, 1.0990, 1.1010, [bar(1.1002, 1.1012, 1.0988, 1.0995)])
    assert res["exit_reason"] == "sl"
    assert res["pnl"] == pytest.approx(1.1000 - 1.1010)
    assert res["bars_held"] == 1


def test_tp_when_only_low_touches():
    res = simulate_short(1.1000, 1.0990, 1.1010, [bar(1.1002, 1.1008, 1.0989, 1.0992)])
    assert res["exit_reason"] == "tp"
    assert res["pnl"] == pytest.approx(1.1000 - 1.0990)


def test_sl_when_only_high_touches():
    res = simulate_short(1.1000, 1.0990, 1.1010, [bar(1.1002, 1.1011, 1.0996, 1.1008)])
    assert res["exit_reason"] == "sl"
    assert res["pnl"] == pytest.approx(1.1000 - 1.1010)


def test_gap_below_tp_exits_at_open():
    res = simulate_short(1.1000, 1.0990, 1.1010, [bar(1.0985, 1.0995, 1.0980, 1.0988)])
    assert res["exit_reason"] == "tp"
    assert res["pnl"] == pytest.approx(1.1000 - 1.0985)


def test_gap_above_sl_exits_at_open():
    res = simulate_short(1.1000, 1.0990, 1.1010, [bar(1.1015, 1.1020, 1.1005, 1.1012)])
    assert res["exit_reason"] == "sl"
    assert res["pnl"] == pytest.approx(1.1000 - 1.1015)


def test_timeout_exits_at_close_of_16th_bar():
    bars = [bar(1.1000, 1.1005, 1.0995, 1.0998)] * TIMEOUT_BARS
    res = simulate_short(1.1000, 1.0990, 1.1010, bars)
    assert res["exit_reason"] == "timeout"
    assert res["bars_held"] == TIMEOUT_BARS
    assert res["pnl"] == pytest.approx(1.1000 - 1.0998)


def test_exit_at_16th_bar_prefers_sl_over_timeout():
    # 15 neutral bars + 16th bar touches SL: exit as SL, not timeout
    bars = [bar(1.1000, 1.1005, 1.0995, 1.0998)] * (TIMEOUT_BARS - 1)
    bars.append(bar(1.1002, 1.1012, 1.0995, 1.1008))
    res = simulate_short(1.1000, 1.0990, 1.1010, bars)
    assert res["exit_reason"] == "sl"
    assert res["bars_held"] == TIMEOUT_BARS

"""
H07 experiment — stage 1 (docs/26 §19): weekly-gap partial reversion,
conditional prediction, NO trade.

    weekly_gap    = first_open_new_week - last_close_previous_week
    normalized    = abs(weekly_gap) / ATR(H1,14)   (ATR causal, before
                    the first bar of the new week)
    event         = normalized >= threshold (0.50 base)

    Forward returns measured from the FIRST available open of the week
    at 1/4/8/16 hours. Reversion: signed = -sign(gap) * fwd.
    Also reports the fraction of the gap closed at each horizon.

    Robustness: exact n, bootstrap CI (h8), leave-one-year-out,
    without the 5 largest gaps. No weekend candles are created.
"""

from __future__ import annotations

import argparse
import io
import json
import random
import sys
from pathlib import Path

import pandas as pd

HOURS = (1, 4, 8, 16)
CANDLES_PER_HOUR = 4
THRESHOLD = 0.50


def _atr_h1_14_before(h1: pd.DataFrame, before_ts) -> float | None:
    prior = h1[h1["time"] < before_ts].tail(14)
    if len(prior) < 14:
        return None
    highs = prior["high"].tolist()
    lows = prior["low"].tolist()
    closes = prior["close"].tolist()
    trs = []
    for i in range(len(prior)):
        if i == 0:
            trs.append(highs[i] - lows[i])
        else:
            trs.append(
                max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1]),
                )
            )
    return sum(trs) / len(trs)


def detect_gaps(
    m15: pd.DataFrame,
    h1: pd.DataFrame,
    *,
    threshold: float,
) -> list[dict]:
    """Detect weekly gaps. Returns event dicts (no forward fills)."""
    m15 = m15.sort_values("time").reset_index(drop=True)
    iso = m15["time"].dt.isocalendar()
    week_key = iso["year"].astype(str) + "-W" + iso["week"].astype(str)

    events: list[dict] = []
    prev_week_close: float | None = None
    prev_week_key: str | None = None

    for wk, group in m15.groupby(week_key, sort=True):
        first = group.iloc[0]
        last = group.iloc[-1]
        if prev_week_close is not None and wk != prev_week_key:
            gap = float(first["open"]) - prev_week_close
            atr = _atr_h1_14_before(h1, first["time"])
            if atr is not None and atr > 0:
                normalized = abs(gap) / atr
                if normalized >= threshold:
                    events.append(
                        {
                            "week": wk,
                            "first_ts": first["time"],
                            "first_idx": int(first.name),
                            "gap": gap,
                            "normalized": float(normalized),
                            "atr": float(atr),
                        }
                    )
        prev_week_close = float(last["close"])
        prev_week_key = wk

    return events


def _stats(vals: list[float]) -> dict:
    if not vals:
        return {"n": 0, "mean_signed_return": None, "positive_rate": None}
    return {
        "n": len(vals),
        "mean_signed_return": sum(vals) / len(vals),
        "positive_rate": sum(1 for v in vals if v > 0) / len(vals),
    }


def run(m15_path: Path, h1_path: Path, *, out_path: Path, threshold: float) -> dict:
    m15 = pd.read_parquet(m15_path)
    h1 = pd.read_parquet(h1_path)
    events = detect_gaps(m15, h1, threshold=threshold)

    closes = m15["close"].reset_index(drop=True)
    opens = m15["open"].reset_index(drop=True)
    times = m15["time"].reset_index(drop=True)

    report: dict = {
        "hypothesis": "H07",
        "stage": 1,
        "threshold": threshold,
        "dataset_m15": str(m15_path),
        "dataset_h1": str(h1_path),
        "events": len(events),
        "horizons": {},
        "gap_close_fraction": {},
        "by_year": {},
        "leave_one_year_out": {},
        "without_top5": {},
    }

    signed_by_h: dict[int, list[float]] = {h: [] for h in HOURS}
    frac_by_h: dict[int, list[float]] = {h: [] for h in HOURS}
    year_map: dict[int, str] = {}

    for ev in events:
        i = ev["first_idx"]
        sign = -1.0 if ev["gap"] > 0 else 1.0
        gap_abs = abs(ev["gap"])
        year = str(ev["week"][:4])
        for h in HOURS:
            j = i + h * CANDLES_PER_HOUR
            if j < len(closes):
                fwd = closes[j] / opens[i] - 1.0
                signed_by_h[h].append(sign * fwd)
                # fraction of the gap closed at horizon h
                # (gap up: (open - close)/|gap| = sign*fwd/|gap|)
                frac_by_h[h].append(
                    sign * fwd / gap_abs if gap_abs else None
                )
        year_map[len(year_map)] = year  # placeholder replaced below

    # rebuild year map aligned with the event list order
    year_map = {k: str(ev["week"][:4]) for k, ev in enumerate(events)}

    for h in HOURS:
        report["horizons"][f"h{h}"] = _stats(signed_by_h[h])
        fracs = [f for f in frac_by_h[h] if f is not None]
        report["gap_close_fraction"][f"h{h}"] = {
            "n": len(fracs),
            "mean_fraction": sum(fracs) / len(fracs) if fracs else None,
        }

    # by year (h8)
    h8 = signed_by_h[8]
    by_year: dict[str, list] = {}
    for k, v in enumerate(h8):
        by_year.setdefault(year_map[k], []).append(v)
    for y, vals in sorted(by_year.items()):
        report["by_year"][y] = _stats(vals)

    # leave-one-year-out (h8)
    for y, vals in sorted(by_year.items()):
        rest = [v for yy, vv in by_year.items() if yy != y for v in vv]
        report["leave_one_year_out"][f"without_{y}"] = _stats(rest)

    # without the 5 largest |gap| (h8)
    big = sorted(events, key=lambda e: -abs(e["gap"]))[:5]
    big_idx = {id(e) for e in big}
    rest = [v for k, v in enumerate(h8) if id(events[k]) not in big_idx]
    report["without_top5"] = _stats(rest)

    # bootstrap 95% CI for h8 (10k resamples)
    if len(h8) >= 10:
        random.seed(42)
        means = []
        for _ in range(10_000):
            sample = [random.choice(h8) for _ in range(len(h8))]
            means.append(sum(sample) / len(sample))
        means.sort()
        report["h8_bootstrap_ci_95"] = {
            "lo": means[250],
            "hi": means[9750],
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H07 stage-1 experiment")
    parser.add_argument("--m15", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--h1", default="data/processed/EURUSD/H1.parquet")
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    parser.add_argument("--out", default="research/reports/h07_experiment.json")
    args = parser.parse_args()

    report = run(
        Path(args.m15),
        Path(args.h1),
        out_path=Path(args.out),
        threshold=args.threshold,
    )

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(
        f"H07 stage-1 | threshold={report['threshold']} | events={report['events']}\n"
    )
    out.write(f"{'h':<3} {'n':>5} {'signed%':>9} {'pos%':>7} {'gap-closed%':>12}\n")
    for h in HOURS:
        s = report["horizons"][f"h{h}"]
        mean = s["mean_signed_return"]
        pos = s["positive_rate"]
        frac = report["gap_close_fraction"][f"h{h}"]["mean_fraction"]
        out.write(
            f"{h:<3} {s['n']:>5} "
            f"{(mean*100 if mean is not None else float('nan')):>9.3f} "
            f"{(pos*100 if pos is not None else float('nan')):>6.2f}% "
            f"{(frac*100 if frac is not None else float('nan')):>11.1f}%\n"
        )
    ci = report.get("h8_bootstrap_ci_95")
    if ci:
        out.write(
            f"h8 bootstrap 95% CI: [{ci['lo']*100:.3f}%, {ci['hi']*100:.3f}%]\n"
        )
    wt = report["without_top5"]
    if wt["n"]:
        out.write(
            f"without top-5 gaps h8: signed={wt['mean_signed_return']*100:.3f}% "
            f"pos={wt['positive_rate']*100:.1f}% (n={wt['n']})\n"
        )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

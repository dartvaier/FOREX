"""
H11 experiment — stage 1 (docs/26 §30): H1 directional efficiency with
volume, next-H1 continuation. NET of calibrated costs.

    DE          = abs(close-open)/(high-low) on H1 (None if range 0)
    TV pct      = slot_percentile of tick_volume (60 H1 slots, causal)
    signal      = DE >= 0.70 AND TV pct >= 0.50
    signed      = sign(candle) * fwd  (fwd = next H1 close/open - 1)
    net         = signed - cost (1.9 pips calibrated round-trip)

Control: candle direction without the DE/TV filter (DE must ADD
predictive power vs the control).
Sensitivity: DE 0.60/0.70/0.80; TV p40/p50/p60.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

from research.features import directional_efficiency, slot_percentile
from research.rare_events import leave_one_year_out, summarize

DE_BASE = 0.70
TV_BASE = 0.50
COST_PIPS = 1.9
PIP_SIZE = 0.0001


def build(m15_path: Path) -> tuple[pd.DataFrame, pd.Series]:
    """Build H1 bars from M15 and compute DE/TV features (causal)."""
    m15 = pd.read_parquet(m15_path).sort_values("time").reset_index(drop=True)
    m15["h1_key"] = m15["time"].dt.floor("1h")

    bars = []
    for _, g in m15.groupby("h1_key"):
        bars.append(
            {
                "time": g["time"].iloc[0],
                "open": float(g["open"].iloc[0]),
                "high": float(g["high"].max()),
                "low": float(g["low"].min()),
                "close": float(g["close"].iloc[-1]),
                "tick_volume": float(g["tick_volume"].sum()),
            }
        )
    h1 = pd.DataFrame(bars).sort_values("time").reset_index(drop=True)

    de = [
        directional_efficiency(o, h, l, c)
        for o, h, l, c in zip(h1["open"], h1["high"], h1["low"], h1["close"])
    ]
    timestamps = [ts.to_pydatetime() for ts in h1["time"]]
    tv_pct = slot_percentile(
        values=h1["tick_volume"].astype(float).tolist(),
        timestamps=timestamps,
        lookback_slots=60,
    )

    h1["de"] = de
    h1["tv_pct"] = tv_pct
    candle_dir = (h1["close"] >= h1["open"]).astype(int) * 2 - 1
    h1["candle_dir"] = candle_dir
    return h1, pd.Series(timestamps)


def run(m15_path: Path, *, out_path: Path, de_th: float = DE_BASE, tv_th: float = TV_BASE) -> dict:
    h1, _ = build(m15_path)

    closes = h1["close"].reset_index(drop=True)
    opens = h1["open"].reset_index(drop=True)
    years = h1["time"].dt.year

    de_ok = h1["de"].notna() & (h1["de"] >= de_th)
    tv_ok = h1["tv_pct"].notna() & (h1["tv_pct"] >= tv_th)
    mask = de_ok & tv_ok

    fwd = closes.shift(-1) / closes - 1.0
    signed = fwd * h1["candle_dir"]

    models: dict[str, pd.Series] = {
        "DE_TV_filter": mask,
        "control_candle_only": pd.Series(True, index=h1.index),
    }

    report: dict = {
        "hypothesis": "H11",
        "stage": 1,
        "dataset": str(m15_path),
        "h1_bars": int(len(h1)),
        "de_threshold": de_th,
        "tv_threshold": tv_th,
        "cost_pips": COST_PIPS,
        "models": {},
    }

    for name, m in models.items():
        sel = signed[m]
        years_sel = years[m]
        by_year: dict[str, list] = {}
        for y, v in zip(years_sel, sel.dropna().index.map(lambda i: signed.iloc[i])):
            pass
        # build by_year properly
        vals = sel.dropna()
        by_year = {}
        for idx, v in vals.items():
            by_year.setdefault(str(years[idx]), []).append(v)

        net_vals = [v - COST_PIPS * PIP_SIZE for v in vals]
        report["models"][name] = {
            "n": int(len(net_vals)),
            "gross_mean": float(vals.mean()) if len(vals) else None,
            "gross_positive_rate": (
                float((vals > 0).mean()) if len(vals) else None
            ),
            "net_mean": (
                sum(net_vals) / len(net_vals) if net_vals else None
            ),
            "by_year": {y: summarize(v) for y, v in sorted(by_year.items())},
            "leave_one_year_out": leave_one_year_out(by_year),
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H11 stage-1 experiment")
    parser.add_argument("--m15", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--de", type=float, default=DE_BASE)
    parser.add_argument("--tv", type=float, default=TV_BASE)
    parser.add_argument("--out", default="research/reports/h11_experiment.json")
    args = parser.parse_args()

    report = run(
        Path(args.m15),
        out_path=Path(args.out),
        de_th=args.de,
        tv_th=args.tv,
    )

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(f"H11 stage-1 | H1 bars={report['h1_bars']} | DE>={args.de} TV>={args.tv}\n")
    out.write(f"{'modelo':<22} {'n':>7} {'bruto%':>9} {'pos%':>7} {'net%':>9}\n")
    for name, m in report["models"].items():
        gross = m["gross_mean"]
        pos = m["gross_positive_rate"]
        net = m["net_mean"]
        out.write(
            f"{name:<22} {m['n']:>7} "
            f"{(gross*100 if gross is not None else float('nan')):>9.3f} "
            f"{(pos*100 if pos is not None else float('nan')):>6.2f}% "
            f"{(net*100 if net is not None else float('nan')):>9.3f}\n"
        )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

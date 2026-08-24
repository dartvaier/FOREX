"""
Summarize research/reports/*.json into a comparison table.

Usage:

    python -m research.summarize
    python -m research.summarize --csv
    python -m research.summarize --out-dir research/reports

Reads every <strategy>_<timeframe>_<cost>.json report produced
by research/runner.py and prints one row per report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parents[1] / "research" / "reports"

COLUMNS = [
    "strategy",
    "tf",
    "cost",
    "cost_multiplier",
    "tag",
    "from",
    "to",
    "trades",
    "net_profit",
    "return_pct",
    "max_dd_pct",
    "win_rate",
    "profit_factor",
    "avg_trade",
    "expectancy",
    "final_equity",
]


def load_reports(reports_dir: Path) -> list[dict]:
    reports: list[dict] = []

    for path in sorted(reports_dir.glob("*.json")):
        reports.append(
            json.loads(
                path.read_text(encoding="utf-8")
            )
        )

    return reports


def extract_row(report: dict) -> dict:
    config = report["config"]
    performance = report["performance"]

    return {
        "strategy": config["strategy_id"],
        "tf": config["timeframe"],
        "cost": config["cost_model"],
        "cost_multiplier": config.get(
            "cost_multiplier",
            1.0,
        ),
        "tag": config.get("tag") or "",
        "from": config["date_from"][:10],
        "to": config["date_to"][:10],
        "trades": performance["trades"],
        "net_profit": round(performance["net_profit"], 2),
        "return_pct": round(performance["total_return_pct"], 4),
        "max_dd_pct": round(performance["max_drawdown_pct"], 4),
        "win_rate": round(performance["win_rate"], 2),
        "profit_factor": round(performance["profit_factor"], 6),
        "avg_trade": round(performance["average_trade"], 4),
        "expectancy": round(performance["expectancy"], 4),
        "final_equity": round(performance["final_equity"], 2),
    }


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "| "
        + " | ".join(COLUMNS)
        + " |",
        "| "
        + " | ".join("---" for _ in COLUMNS)
        + " |",
    ]

    for row in rows:
        lines.append(
            "| "
            + " | ".join(str(row[column]) for column in COLUMNS)
            + " |"
        )

    return "\n".join(lines)


def render_csv(rows: list[dict]) -> str:
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=COLUMNS,
    )
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize research reports into a table."
    )

    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPORTS_DIR,
    )

    parser.add_argument(
        "--csv",
        action="store_true",
        help="emit CSV instead of Markdown",
    )

    args = parser.parse_args()

    reports = load_reports(args.out_dir)

    if not reports:
        print(
            f"no reports found in {args.out_dir} "
            "(run python -m research.runner first)"
        )
        return

    rows = [extract_row(report) for report in reports]
    rows.sort(
        key=lambda row: (
            row["strategy"],
            row["tf"],
            row["cost"],
        )
    )

    if args.csv:
        print(render_csv(rows))
    else:
        print(render_markdown(rows))


if __name__ == "__main__":
    main()

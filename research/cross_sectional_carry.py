"""H16: causal monthly cross-sectional FX carry-proxy research runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.carry_data import load_rate_snapshot, sha256_bytes
from research.cross_sectional_momentum import (
    DEFAULT_ROUND_TRIP_COST_PIPS,
    _validate_monthly_closes,
    foreign_currency_value,
    formation_weights,
    load_monthly_pair_closes,
    summarize_monthly_returns,
    turnover_cost_fraction,
)


CURRENCY_BY_SYMBOL = {
    "AUDUSD": "AUD",
    "EURUSD": "EUR",
    "GBPUSD": "GBP",
    "NZDUSD": "NZD",
    "USDCAD": "CAD",
    "USDCHF": "CHF",
    "USDJPY": "JPY",
}
RATE_CURRENCIES = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")
PRIMARY_N_SELECT = 2
N_SELECT_VALUES = (1, 2, 3)


def rate_observation_month(formation_date: pd.Timestamp) -> pd.Timestamp:
    """Return t-2 rate month for a decision at the end of t-1."""
    timestamp = pd.Timestamp(formation_date)
    if timestamp.tz is None:
        raise ValueError("formation_date must be timezone-aware")
    utc = timestamp.tz_convert("UTC")
    formation_month = pd.Timestamp(
        year=utc.year,
        month=utc.month,
        day=1,
        tz="UTC",
    )
    return formation_month - pd.offsets.MonthBegin(1)


def _validate_rates(rates: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(rates, pd.DataFrame):
        raise TypeError("rates must be a DataFrame")
    if not isinstance(rates.index, pd.DatetimeIndex):
        raise TypeError("rates must use a DatetimeIndex")
    if rates.index.tz is None:
        raise ValueError("rates index must be timezone-aware")
    if not rates.index.is_monotonic_increasing:
        raise ValueError("rates index must be sorted")
    if rates.index.has_duplicates:
        raise ValueError("rates index must be unique")
    missing_columns = set(RATE_CURRENCIES) - set(rates.columns)
    if missing_columns:
        raise ValueError(f"missing rate currencies: {sorted(missing_columns)}")
    result = rates.loc[:, list(RATE_CURRENCIES)].astype(float).copy()
    result.index = result.index.tz_convert("UTC")
    return result


def run_cross_sectional_carry(
    monthly_pair_closes: pd.DataFrame,
    rates: pd.DataFrame,
    *,
    round_trip_cost_pips: float = DEFAULT_ROUND_TRIP_COST_PIPS,
    n_select: int = PRIMARY_N_SELECT,
) -> pd.DataFrame:
    """Run H16 with one-month holding and a fully completed-month rate lag."""
    _validate_monthly_closes(monthly_pair_closes)
    if set(monthly_pair_closes.columns) != set(CURRENCY_BY_SYMBOL):
        raise ValueError("monthly_pair_closes must contain the fixed H16 universe")
    rate_frame = _validate_rates(rates)
    pair_closes = monthly_pair_closes.loc[:, list(CURRENCY_BY_SYMBOL)].astype(float)
    foreign_values = pd.DataFrame(
        {
            symbol: foreign_currency_value(symbol, pair_closes[symbol])
            for symbol in pair_closes.columns
        },
        index=pair_closes.index,
    )
    previous_weights = {symbol: 0.0 for symbol in pair_closes.columns}
    rows: list[dict] = []

    for formation_position in range(len(pair_closes) - 1):
        formation_date = pair_closes.index[formation_position]
        observation_date = rate_observation_month(formation_date)
        if observation_date not in rate_frame.index:
            raise ValueError(
                f"missing rates for {observation_date.strftime('%Y-%m')}"
            )
        observation = rate_frame.loc[observation_date]
        if observation.isna().any() or not np.isfinite(observation.to_numpy()).all():
            raise ValueError(
                f"missing rates for {observation_date.strftime('%Y-%m')}"
            )

        usd_rate = float(observation["USD"])
        differentials = pd.Series(
            {
                symbol: float(observation[currency]) - usd_rate
                for symbol, currency in CURRENCY_BY_SYMBOL.items()
            },
            dtype=float,
        )
        weights = formation_weights(differentials, n_select=n_select)

        formation_values = foreign_values.iloc[formation_position]
        next_values = foreign_values.iloc[formation_position + 1]
        holding_returns = next_values / formation_values - 1.0
        spot_return = sum(
            float(weights[symbol]) * float(holding_returns[symbol])
            for symbol in pair_closes.columns
        )
        carry_accrual = sum(
            float(weights[symbol]) * float(differentials[symbol]) / 100.0 / 12.0
            for symbol in pair_closes.columns
        )
        gross_return = spot_return + carry_accrual
        cost = turnover_cost_fraction(
            previous_weights=previous_weights,
            target_weights=weights,
            pair_prices=pair_closes.iloc[formation_position],
            round_trip_cost_pips=round_trip_cost_pips,
        )

        is_last = formation_position == len(pair_closes) - 2
        if is_last:
            cost += turnover_cost_fraction(
                previous_weights=weights,
                target_weights={symbol: 0.0 for symbol in weights},
                pair_prices=pair_closes.iloc[formation_position + 1],
                round_trip_cost_pips=round_trip_cost_pips,
            )

        rows.append(
            {
                "holding_end": pair_closes.index[formation_position + 1],
                "formation_date": formation_date,
                "rate_observation_date": observation_date,
                "spot_return": spot_return,
                "carry_accrual_return": carry_accrual,
                "gross_return": gross_return,
                "cost_return": cost,
                "net_return": gross_return - cost,
                "turnover": sum(
                    abs(weights[symbol] - previous_weights[symbol])
                    for symbol in weights
                ),
                "weights": weights,
                "rate_differentials": differentials.to_dict(),
            }
        )
        previous_weights = weights

    return pd.DataFrame(rows).set_index("holding_end")


def _period_closes(
    closes: pd.DataFrame,
    *,
    date_from: pd.Timestamp,
    date_to: pd.Timestamp,
) -> pd.DataFrame:
    first_formation = date_from - pd.offsets.MonthEnd(1)
    selected = closes.loc[
        (closes.index >= first_formation) & (closes.index < date_to)
    ].copy()
    if len(selected) < 3:
        raise ValueError("insufficient monthly closes for requested period")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/external/carry/fred_call_money/manifest.json"),
    )
    parser.add_argument("--date-from", default="2015-01-01")
    parser.add_argument("--date-to", default="2021-01-01")
    parser.add_argument("--out-dir", type=Path, default=Path("research/reports"))
    parser.add_argument("--tag", default="dev")
    args = parser.parse_args()

    date_from = pd.Timestamp(args.date_from, tz="UTC")
    date_to = pd.Timestamp(args.date_to, tz="UTC")
    if date_from >= date_to:
        raise ValueError("date_from must be earlier than date_to")
    closes = _period_closes(
        load_monthly_pair_closes(symbols=CURRENCY_BY_SYMBOL),
        date_from=date_from,
        date_to=date_to,
    )
    rates = load_rate_snapshot(args.manifest)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = {
        "hypothesis": "H16",
        "preregistration": "docs/34_H16_CROSS_SECTIONAL_CARRY_PROXY.md",
        "date_from": str(date_from),
        "date_to": str(date_to),
        "symbols": list(closes.columns),
        "round_trip_cost_pips": DEFAULT_ROUND_TRIP_COST_PIPS,
        "rate_publication_lag_policy_months": 1,
        "rate_snapshot_manifest": str(args.manifest),
        "rate_snapshot_manifest_sha256": sha256_bytes(args.manifest.read_bytes()),
        "rate_snapshot_retrieved_at": manifest.get("retrieved_at"),
        "rate_snapshot_point_in_time": manifest.get("point_in_time"),
        "configurations": {},
    }
    output_rows = []
    for n_select in N_SELECT_VALUES:
        baseline = run_cross_sectional_carry(
            closes,
            rates,
            n_select=n_select,
        )
        stressed = run_cross_sectional_carry(
            closes,
            rates,
            n_select=n_select,
            round_trip_cost_pips=1.5 * DEFAULT_ROUND_TRIP_COST_PIPS,
        )
        metrics = summarize_monthly_returns(baseline)
        stress_metrics = summarize_monthly_returns(stressed)
        report["configurations"][str(n_select)] = {
            **metrics,
            "stress_1_5x_net_annualized_return": stress_metrics[
                "net_annualized_return"
            ],
            "stress_1_5x_sharpe": stress_metrics["annualized_sharpe"],
        }
        export = baseline.copy()
        export["n_select"] = n_select
        export["weights"] = export["weights"].map(
            lambda value: json.dumps(value, sort_keys=True)
        )
        export["rate_differentials"] = export["rate_differentials"].map(
            lambda value: json.dumps(value, sort_keys=True)
        )
        output_rows.append(export.reset_index())

    configs = report["configurations"]
    primary = configs[str(PRIMARY_N_SELECT)]
    criteria = {
        "primary_net_return_positive": primary["net_annualized_return"] > 0,
        "primary_sharpe_above_0_50": primary["annualized_sharpe"] > 0.50,
        "primary_positive_at_cost_1_5x": (
            primary["stress_1_5x_net_annualized_return"] > 0
        ),
        "primary_four_positive_years": primary["positive_years"] >= 4,
        "primary_year_concentration_at_most_0_50": (
            primary["max_positive_year_profit_fraction"] is not None
            and primary["max_positive_year_profit_fraction"] <= 0.50
        ),
        "top_bottom_1_positive": configs["1"]["net_annualized_return"] > 0,
        "top_bottom_3_positive": configs["3"]["net_annualized_return"] > 0,
    }
    report["criteria"] = criteria
    report["advance_to_validation"] = all(criteria.values())

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"h16_cross_sectional_carry_{args.tag}"
    json_path = args.out_dir / f"{stem}.json"
    csv_path = args.out_dir / f"{stem}.csv"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.concat(output_rows, ignore_index=True).to_csv(csv_path, index=False)

    for n_select, metrics in report["configurations"].items():
        print(
            f"top/bottom={n_select} months={metrics['months']:>2} "
            f"net={metrics['net_annualized_return']:+.2%} "
            f"Sharpe={metrics['annualized_sharpe']:+.2f} "
            f"stress={metrics['stress_1_5x_net_annualized_return']:+.2%}"
        )
    print(f"advance_to_validation={report['advance_to_validation']}")
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

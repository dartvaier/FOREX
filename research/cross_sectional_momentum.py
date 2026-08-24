"""H15: causal monthly cross-sectional FX momentum research runner."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from backtest.instruments import INSTRUMENT_REGISTRY, MAJOR_SYMBOLS


USD_BASE_SYMBOLS = frozenset({"USDCAD", "USDCHF", "USDJPY"})
FORMATION_MONTHS = (1, 3, 6, 12)
PRIMARY_FORMATION_MONTHS = 6
DEFAULT_ROUND_TRIP_COST_PIPS = 3.7
N_SELECT = 2


def foreign_currency_value(symbol: str, pair_price):
    """Return the USD value of one unit of the non-USD currency."""
    normalized = symbol.upper()
    if normalized not in INSTRUMENT_REGISTRY:
        raise ValueError(f"unknown symbol: {symbol}")
    if normalized in USD_BASE_SYMBOLS:
        return 1.0 / pair_price
    return pair_price


def formation_weights(
    scores: pd.Series,
    *,
    n_select: int = N_SELECT,
) -> dict[str, float]:
    """Create an equal-weight, dollar-neutral winner/loser portfolio."""
    if not isinstance(scores, pd.Series) or scores.empty:
        raise ValueError("scores must be a non-empty Series")
    if scores.isna().any() or not np.isfinite(scores.to_numpy()).all():
        raise ValueError("scores must contain only finite values")
    if n_select <= 0 or 2 * n_select > len(scores):
        raise ValueError("n_select must allow disjoint long and short legs")

    items = [(str(symbol), float(value)) for symbol, value in scores.items()]
    winners = {
        symbol
        for symbol, _ in sorted(items, key=lambda item: (-item[1], item[0]))[
            :n_select
        ]
    }
    losers = {
        symbol
        for symbol, _ in sorted(items, key=lambda item: (item[1], item[0]))[
            :n_select
        ]
    }
    if winners & losers:
        raise ValueError("winner and loser legs must be disjoint")

    leg_weight = 1.0 / (2.0 * n_select)
    return {
        str(symbol): (
            leg_weight
            if str(symbol) in winners
            else -leg_weight
            if str(symbol) in losers
            else 0.0
        )
        for symbol in scores.index
    }


def turnover_cost_fraction(
    *,
    previous_weights: dict[str, float],
    target_weights: dict[str, float],
    pair_prices: pd.Series,
    round_trip_cost_pips: float = DEFAULT_ROUND_TRIP_COST_PIPS,
) -> float:
    """Cost of changing portfolio weights, in portfolio return units."""
    if not math.isfinite(round_trip_cost_pips) or round_trip_cost_pips < 0:
        raise ValueError("round_trip_cost_pips must be finite and non-negative")

    symbols = set(previous_weights) | set(target_weights)
    total = 0.0
    for symbol in symbols:
        if symbol not in pair_prices.index:
            raise ValueError(f"missing pair price for {symbol}")
        price = float(pair_prices[symbol])
        if not math.isfinite(price) or price <= 0:
            raise ValueError(f"invalid pair price for {symbol}")
        pip_size = float(INSTRUMENT_REGISTRY[symbol]["pip_size"])
        weight_change = abs(
            float(target_weights.get(symbol, 0.0))
            - float(previous_weights.get(symbol, 0.0))
        )
        one_way_fraction = 0.5 * round_trip_cost_pips * pip_size / price
        total += weight_change * one_way_fraction
    return total


def _validate_monthly_closes(monthly_pair_closes: pd.DataFrame) -> None:
    if not isinstance(monthly_pair_closes, pd.DataFrame):
        raise TypeError("monthly_pair_closes must be a DataFrame")
    if len(monthly_pair_closes) < 3:
        raise ValueError("monthly_pair_closes needs at least three rows")
    if not isinstance(monthly_pair_closes.index, pd.DatetimeIndex):
        raise TypeError("monthly_pair_closes must use a DatetimeIndex")
    if monthly_pair_closes.index.tz is None:
        raise ValueError("monthly_pair_closes index must be timezone-aware")
    if not monthly_pair_closes.index.is_monotonic_increasing:
        raise ValueError("monthly_pair_closes index must be sorted")
    if monthly_pair_closes.index.has_duplicates:
        raise ValueError("monthly_pair_closes index must be unique")
    unknown = set(monthly_pair_closes.columns) - set(INSTRUMENT_REGISTRY)
    if unknown:
        raise ValueError(f"unknown symbols: {sorted(unknown)}")
    values = monthly_pair_closes.astype(float)
    if values.isna().any().any() or not np.isfinite(values.to_numpy()).all():
        raise ValueError("monthly_pair_closes must contain only finite values")
    if (values <= 0).any().any():
        raise ValueError("monthly_pair_closes must be positive")


def run_cross_sectional_momentum(
    monthly_pair_closes: pd.DataFrame,
    *,
    lookback_months: int,
    round_trip_cost_pips: float = DEFAULT_ROUND_TRIP_COST_PIPS,
    n_select: int = N_SELECT,
) -> pd.DataFrame:
    """Run a causal one-month-holding cross-sectional momentum backtest."""
    _validate_monthly_closes(monthly_pair_closes)
    if not isinstance(lookback_months, int) or lookback_months <= 0:
        raise ValueError("lookback_months must be a positive integer")
    if len(monthly_pair_closes) < lookback_months + 2:
        raise ValueError("insufficient monthly history for lookback")

    pair_closes = monthly_pair_closes.astype(float)
    foreign_values = pd.DataFrame(
        {
            symbol: foreign_currency_value(symbol, pair_closes[symbol])
            for symbol in pair_closes.columns
        },
        index=pair_closes.index,
    )
    previous_weights = {str(symbol): 0.0 for symbol in pair_closes.columns}
    rows: list[dict] = []

    for formation_position in range(
        lookback_months,
        len(pair_closes) - 1,
    ):
        formation_values = foreign_values.iloc[formation_position]
        start_values = foreign_values.iloc[
            formation_position - lookback_months
        ]
        scores = formation_values / start_values - 1.0
        weights = formation_weights(scores, n_select=n_select)

        next_values = foreign_values.iloc[formation_position + 1]
        holding_returns = next_values / formation_values - 1.0
        gross_return = sum(
            float(weights[symbol]) * float(holding_returns[symbol])
            for symbol in pair_closes.columns
        )
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
                "formation_date": pair_closes.index[formation_position],
                "gross_return": gross_return,
                "cost_return": cost,
                "net_return": gross_return - cost,
                "turnover": sum(
                    abs(weights[symbol] - previous_weights[symbol])
                    for symbol in weights
                ),
                "weights": weights,
            }
        )
        previous_weights = weights

    return pd.DataFrame(rows).set_index("holding_end")


def load_monthly_pair_closes(
    *,
    symbols: Iterable[str] = MAJOR_SYMBOLS,
    repo_root: Path | None = None,
) -> pd.DataFrame:
    """Load causal month-end closes from completed H4 bars."""
    root = Path(__file__).resolve().parents[1] if repo_root is None else repo_root
    monthly: dict[str, pd.Series] = {}
    for raw_symbol in symbols:
        symbol = raw_symbol.upper()
        path = root / "data" / "processed" / symbol / "H4.parquet"
        frame = pd.read_parquet(path)
        times = pd.to_datetime(frame["time"], utc=True)
        if "complete" in frame.columns:
            frame = frame.loc[frame["complete"].astype(bool)].copy()
            times = times.loc[frame.index]
        available_at = pd.DatetimeIndex(times + pd.Timedelta(hours=4))
        closes = pd.Series(
            frame["close"].astype(float).to_numpy(),
            index=available_at,
            name=symbol,
        ).sort_index()
        monthly[symbol] = closes.resample("ME").last().dropna()

    result = pd.concat(monthly.values(), axis=1, join="inner").sort_index()
    _validate_monthly_closes(result)
    return result


def summarize_monthly_returns(results: pd.DataFrame) -> dict:
    returns = results["net_return"].astype(float)
    gross = results["gross_return"].astype(float)
    costs = results["cost_return"].astype(float)
    equity = (1.0 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    annualized_return = float(equity.iloc[-1] ** (12.0 / len(returns)) - 1.0)
    annualized_volatility = float(returns.std(ddof=1) * math.sqrt(12.0))
    sharpe = (
        float(returns.mean() / returns.std(ddof=1) * math.sqrt(12.0))
        if returns.std(ddof=1) > 0
        else 0.0
    )
    yearly = returns.groupby(returns.index.year).apply(
        lambda values: float((1.0 + values).prod() - 1.0)
    )
    positive_year_returns = yearly[yearly > 0]
    concentration = (
        float(positive_year_returns.max() / positive_year_returns.sum())
        if not positive_year_returns.empty
        else None
    )
    return {
        "months": int(len(returns)),
        "gross_annualized_return": float(
            (1.0 + gross).prod() ** (12.0 / len(gross)) - 1.0
        ),
        "net_annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "annualized_sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "positive_month_fraction": float((returns > 0).mean()),
        "mean_monthly_cost": float(costs.mean()),
        "mean_turnover": float(results["turnover"].mean()),
        "positive_years": int((yearly > 0).sum()),
        "years": int(len(yearly)),
        "max_positive_year_profit_fraction": concentration,
        "by_year": {str(year): float(value) for year, value in yearly.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-from", default="2015-01-01")
    parser.add_argument("--date-to", default="2021-01-01")
    parser.add_argument("--out-dir", type=Path, default=Path("research/reports"))
    parser.add_argument("--tag", default="dev")
    args = parser.parse_args()

    closes = load_monthly_pair_closes()
    date_from = pd.Timestamp(args.date_from, tz="UTC")
    date_to = pd.Timestamp(args.date_to, tz="UTC")
    report = {
        "hypothesis": "H15",
        "preregistration": "docs/32_H15_CROSS_SECTIONAL_FX_MOMENTUM.md",
        "date_from": str(date_from),
        "date_to": str(date_to),
        "symbols": list(closes.columns),
        "round_trip_cost_pips": DEFAULT_ROUND_TRIP_COST_PIPS,
        "lookbacks": {},
    }
    output_rows = []
    for lookback in FORMATION_MONTHS:
        baseline_all = run_cross_sectional_momentum(
            closes,
            lookback_months=lookback,
        )
        stressed_all = run_cross_sectional_momentum(
            closes,
            lookback_months=lookback,
            round_trip_cost_pips=1.5 * DEFAULT_ROUND_TRIP_COST_PIPS,
        )
        mask = (baseline_all.index >= date_from) & (baseline_all.index < date_to)
        baseline = baseline_all.loc[mask].copy()
        stressed = stressed_all.loc[mask].copy()
        metrics = summarize_monthly_returns(baseline)
        stress_metrics = summarize_monthly_returns(stressed)
        report["lookbacks"][str(lookback)] = {
            **metrics,
            "stress_1_5x_net_annualized_return": stress_metrics[
                "net_annualized_return"
            ],
            "stress_1_5x_sharpe": stress_metrics["annualized_sharpe"],
        }
        export = baseline.drop(columns=["weights"]).copy()
        export["lookback_months"] = lookback
        export["weights"] = baseline["weights"].map(
            lambda value: json.dumps(value, sort_keys=True)
        )
        output_rows.append(export.reset_index())

    metrics_by_lookback = report["lookbacks"]
    primary = metrics_by_lookback[str(PRIMARY_FORMATION_MONTHS)]
    positive_lookbacks = sum(
        item["net_annualized_return"] > 0
        for item in metrics_by_lookback.values()
    )
    criteria = {
        "three_of_four_lookbacks_positive": positive_lookbacks >= 3,
        "primary_sharpe_above_0_50": primary["annualized_sharpe"] > 0.50,
        "primary_positive_at_cost_1_5x": (
            primary["stress_1_5x_net_annualized_return"] > 0
        ),
        "primary_four_positive_years": primary["positive_years"] >= 4,
        "primary_year_concentration_below_0_50": (
            primary["max_positive_year_profit_fraction"] is not None
            and primary["max_positive_year_profit_fraction"] <= 0.50
        ),
    }
    report["criteria"] = criteria
    report["advance_to_validation"] = all(criteria.values())

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"h15_cross_sectional_momentum_{args.tag}"
    json_path = args.out_dir / f"{stem}.json"
    csv_path = args.out_dir / f"{stem}.csv"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.concat(output_rows, ignore_index=True).to_csv(csv_path, index=False)

    for lookback, metrics in report["lookbacks"].items():
        print(
            f"L={lookback:>2}m months={metrics['months']:>2} "
            f"net={metrics['net_annualized_return']:+.2%} "
            f"Sharpe={metrics['annualized_sharpe']:+.2f} "
            f"stress={metrics['stress_1_5x_net_annualized_return']:+.2%}"
        )
    print(f"advance_to_validation={report['advance_to_validation']}")
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

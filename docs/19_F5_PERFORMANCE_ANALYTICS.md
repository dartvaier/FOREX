# F5.8 — Performance Analytics

`PerformanceAnalytics` is a pure, deterministic read layer over an immutable
`BacktestResult`. It does not mutate the result, Portfolio, Fill, Strategy,
RiskModel, CostModel or execution flow. `BacktestResult.initial_equity` is
recorded by the engine so returns and drawdown always have an explicit baseline.

## Closed trades

Trades are reconstructed from the chronological `ExecutionResult` history, not
from individual fills. A filled `ENTER_LONG` or `ENTER_SHORT` opens a pending
analytic trade and the subsequent filled `EXIT` closes it. The baseline permits
one symbol, one position and no partial exits, so an inconsistent sequence is
rejected instead of being silently interpreted. An open position at the end is
not counted as a closed trade; its mark-to-market value remains in equity.

Each closed trade exposes its entry and exit fills, direction, quantity, gross
PnL, commissions and net PnL. Gross profit/loss, win rate, average win/loss,
payoff ratio and streaks are calculated from **net** closed-trade PnL. Total
commissions is reported independently as the sum of all fills, including a
still-open position; it is never added to a trade twice.

## Equity and drawdown

The equity curve begins with `initial_equity`, followed by the immutable
Portfolio snapshots in their recorded order. Return is the final equity less
initial equity; percentage return uses initial equity as denominator.

Maximum drawdown is the largest decline from every running equity peak, reported
both in currency and as a percentage of that peak. Recovery to a new high does
not erase the previously observed maximum drawdown.

## Sharpe convention and edge cases

Sharpe is deliberately unavailable by default. To request it the caller must
provide `PerformanceAnalytics(periods_per_year=N)`, explicitly declaring that
each adjacent equity observation represents one equally spaced period. The
implementation uses zero risk-free rate, simple adjacent equity returns, sample
standard deviation, and annualizes with `sqrt(N)`. Irregular snapshot cadence
must therefore not be annualized without an explicit resampling policy.

For zero closed trades, win rate, profit factor, averages and payoff ratio are
`None`. When there are gains but no losses, profit factor and payoff ratio are
positive infinity; when only losses exist, payoff ratio is `0.0`. Sharpe is
`None` without an explicit convention, with fewer than two returns, or with
zero return variance. Drawdown is zero for a non-declining equity curve.

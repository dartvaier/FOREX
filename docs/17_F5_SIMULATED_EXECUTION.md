# F5.6 — SimulatedExecution

## Scope

`SimulatedExecution` receives an `OrderIntent` and a validated
`HistoricalBarFeed`. It selects the first actual bar open at or after the order
timestamp, delegates price terms to `CostModel`, and produces a `Fill` inside
an explicit `ExecutionResult`.

It has no dependency on Strategy, Risk, Portfolio or MetaTrader 5 and performs
no Portfolio mutation.

## Baseline timing

Signals are created on a completed bar's close. The order timestamp therefore
matches the next contiguous bar's opening timestamp, which is eligible for
execution. The executor uses timestamps, not row adjacency: if a bar is
missing, it fills at the next bar that exists; it never fabricates a gap bar.

If no later/equal bar open exists, `ExecutionStatus.UNFILLED` is returned with
no Fill. A symbol mismatch is an explicit `REJECTED` result. `Fill` ids are
derived deterministically from `order_id`, preserving traceability.

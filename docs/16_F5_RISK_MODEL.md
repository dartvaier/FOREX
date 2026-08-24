# F5.5 — Risk Model

## Scope

`RiskModel` is the boundary between a Strategy's `Signal` and an executable
`OrderIntent`. It owns approval and final order quantity; Strategy never does.
It neither creates a Fill nor executes an order, calculates a CostModel, or
mutates a Portfolio.

## Baseline decision

`FixedSizeRiskModel` operates under `RiskLimits` for one configured symbol,
one open position, no pyramiding and no hedge. It accepts an optional immutable
`Position` snapshot rather than the Portfolio itself.

- `ENTER_LONG` → BUY with `fixed_quantity` when flat.
- `ENTER_SHORT` → SELL with `fixed_quantity` when flat.
- `HOLD` → rejected decision and no order.
- `EXIT` → the opposite side, using the currently open position's exact size.

The order id is derived deterministically from `signal_id`. This enables
repeatable backtests; a future order ledger will enforce cross-event uniqueness.

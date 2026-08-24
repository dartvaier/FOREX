# F5.1 — Trading Domain Models

## Status

```text
IMPLEMENTED — PENDING LOCAL TEST EXECUTION / REVIEW
```

This milestone starts the implementation of F5 — Backtest Engine.

The objective is to make the main trading state transitions explicit before implementing the simulation loop.

## Implemented contracts

### Signal

Produced by a Strategy.

Baseline actions:

```text
ENTER_LONG
ENTER_SHORT
EXIT
HOLD
```

A `Signal` represents strategy intent only. It is not an executable broker order.

Core fields:

```text
signal_id
strategy_id
symbol
timestamp
action
reason
metadata
```

### OrderIntent

Represents an order candidate after the future Risk Engine gate.

Baseline:

```text
side: BUY / SELL
order_type: MARKET
```

Core fields:

```text
order_id
signal_id
symbol
side
quantity
order_type
created_at
stop_loss
take_profit
metadata
```

The Strategy does not own final financial sizing. `quantity` belongs to the order intent created after risk evaluation.

### Fill

Represents the result of simulated or broker execution.

Core fields:

```text
fill_id
order_id
fill_time
reference_price
execution_price
quantity
spread_impact
slippage
commission
```

`reference_price` and `execution_price` are deliberately separate so execution costs can be modeled without pretending OHLC is a guaranteed executable Bid/Ask price.

## Architectural flow

```text
Strategy
   ↓
Signal
   ↓
Risk Engine
   ↓
OrderIntent
   ↓
Execution
   ↓
Fill
   ↓
Portfolio
```

Invariant:

```text
Signal != OrderIntent != Fill
```

## Validation rules introduced

- trading timestamps must be timezone-aware and UTC;
- identifiers and symbols cannot be empty;
- order/fill quantities must be positive;
- reference and execution prices must be positive;
- stop loss and take profit, when present, must be positive;
- spread impact and commission cannot be negative.

Slippage is intentionally allowed to be signed because future execution models may represent favorable or unfavorable slippage.

## Tests

Unit tests were added in:

```text
tests/test_domain_models.py
```

They cover the initial UTC and numeric invariants and the relationships between the domain models.

The repository currently has no GitHub Actions workflow, so these tests must be run locally before merge:

```powershell
.venv\Scripts\activate
pytest tests/test_domain_models.py -v
pytest -v
```

## Next milestone

```text
F5.2 — BacktestContext
```

The next component should define the information boundary exposed to a Strategy at simulation time, preserving the no-look-ahead invariant:

```text
max(data_available_to_strategy.close_time)
<=
simulation_time
```

# F5.4 — CostModel

## Scope

`CostModel` deterministically maps a reference price, order side and quantity
to execution terms. It returns `CostEstimate`; it does not create `Fill`, send
orders, inspect a Portfolio, or depend on Strategy or Risk.

## Baseline models

- `ZeroCostModel`: explicit engineering diagnostic with no price or monetary
  cost.
- `FixedCostModel`: full Bid/Ask spread, adverse slippage in price units and
  commission per executed unit.

## Accounting decision

The reference price is a mid price. A configured spread is the full Bid/Ask
distance, so each fill uses exactly half: BUY adds it and SELL subtracts it.
Consequently a same-reference BUY/SELL round trip pays one full spread, not two.
Slippage is non-negative and always worsens the execution price. Commission is
non-negative and is passed through for the future Execution layer to record in
the resulting `Fill`.

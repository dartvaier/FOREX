# F5.3 — Portfolio

## Scope

The baseline Portfolio accounts for one configured symbol and at most one open
position. It consumes `Fill` objects and owns cash, equity, realized and
unrealized PnL, commissions already charged in fills, and immutable snapshots.

It does not evaluate Strategy logic, Risk rules, sizing, or a CostModel.

## Decisions

- F5.1 `Fill` intentionally does not carry side or symbol. The Portfolio is
  constructed for one symbol and receives `PositionSide` only when opening;
  a later order/execution layer will supply that provenance.
- Entry commission reduces cash immediately. Unrealized PnL is gross market
  PnL; therefore `equity = cash + unrealized_pnl` at every snapshot.
- On close, realized PnL is the trade's net PnL, including entry and exit
  commission. Partial closes, reversal, multiple symbols and multiple open
  positions are explicitly rejected.
- Snapshots are immutable and are emitted after an opening fill, closing fill,
  or mark-to-market event.

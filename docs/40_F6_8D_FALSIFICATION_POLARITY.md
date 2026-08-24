# F6.8d — Falsification Polarity & Evaluation Semantics

Each `FalsificationCriterion` is a failure predicate. `evaluate(value)` returns
`true` only when `metric operator threshold` is true, which falsifies the
hypothesis. The criterion therefore encodes failure polarity, not a target.

For a hypothesis requiring Sharpe above 1.2, use `sharpe_ratio LTE 1.2` at
`EXPERIMENT`; for drawdown no greater than 20%, use
`maximum_drawdown_percent GT 20` at `GATE`. This meaning is supplied to both
providers in the declarative context. It does not execute or authorize
research.

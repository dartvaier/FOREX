# F6.8 — Research Context & Quality Policy

F6.7c validated the local provider and factual assessment boundary, but the
first accepted proposal was a generic EMA crossover with unsupported parameter
choices. F6.8 therefore improves proposal quality before any expansion of
autonomy.

`proposal_context()` supplies only declarative Registry facts, the single
allowed strategy and a versioned quality policy. It never supplies code, a
filesystem, shell, MT5, a runner, gate access or holdout data. The policy
requires a testable thesis, a market mechanism, parameter rationale, a
quantitative falsification threshold with a valid unit and evaluation horizon,
and novelty against the Registry context. It also prohibits unregistered
indicators, filters and conditions: only the declared EMA crossover may define
the hypothesis.

`HypothesisProposal` now carries `parameter_rationale`; the deterministic
validator requires it and a quantitative falsification criterion. This remains
a proposal boundary: an accepted proposal does not start research, alter the
Registry, run a gate or use holdout data.

Until a corresponding declarative plugin is registered, the validator also
rejects proposals that depend on ATR, RSI, MACD or Bollinger indicators. This
is a fail-closed bridge to F6.9, not an expansion of the strategy catalog.

The context remains within the existing 4096-token baseline. Context tuning is
deferred until a real Registry demonstrates truncation.

The first local qwen3:14b re-run used an unregistered ATR condition despite the
textual policy. It was not allowed to progress: the deterministic validator now
returns `UNSUPPORTED_STRATEGY` for that dependency. A fresh proposal-only
canary must satisfy this boundary and the human quality review before any loop,
assessment repetition or autonomy decision.

When a proposal is `ACCEPTED`, the proposal-only canary writes
`human_review.json` beside the proposal and validation artifacts. It records
the proposal fingerprint, Registry-context version and fingerprint, validation,
parameter rationale and falsification criteria, with
`research_authorization=NOT_AUTHORIZED`. No freeze, experiment or controlled
loop is permitted until explicit human approval.

# F6 — Audit Status and GitHub Record

This document is the versioned GitHub record for the F6 AI Research Layer as
of 2026-08-24. It complements the non-sensitive local canary artifacts under
`outputs/agent_canary/`, which remain ignored by Git.

## Integrated implementation

| Scope | Pull request | Result |
| --- | --- | --- |
| F6.7b local Ollama provider | #26 | Merged |
| F6.7c audited proposal-only canary | #27 | Merged |
| F6.7c frozen assessment-only canary | #28 | Merged |
| F6.8 research context and quality policy | #29 | Merged |
| F6.8 accepted-proposal human review package | #30 | Merged |
| F6.8 EURUSD factual context | #31 | Merged |
| F6.8b executable semantics and metric allowlist | #32 | Merged |
| F6.8c typed falsification contract | #33 | Merged |
| F6.8d falsification polarity | #34 | Merged |
| F6.8e catalog closure validation | #35 | Merged |

Every listed pull request passed the Python 3.12/3.13/3.14 CI matrix before
merge. Local suites were also run for Python 3.12 and 3.14.

## Provider and canary record

`qwen3:14b` was validated for bounded proposal-only and assessment-only calls.
The provider uses a fail-closed deadline; a first short deadline failed with
`TIMEOUT`, while the canonical 120-second proposal-only call succeeded. The
assessment-only canary preserved frozen facts and GateStatus.

The most recent F6.8e proposal-only canary is recorded locally as
`CONNECTION_REFUSED` / `ollama unavailable`. It did not produce a proposal,
run the validator, create a review package, or start research.

## Human-review decisions

| Proposal fingerprint | Decision | Reason(s) |
| --- | --- | --- |
| `9c648c12688692f76a1948c9cdad57bdc4a02150a6dd226f98a13fd147349f30` | REJECTED | `FACTUAL_UNIT_ERROR`; `DATASET_ASSUMPTION_CONTRADICTION` |
| `3eb7ad819a68fceda6076f03b3dc028701421a33c5b2580f723e09eefe6e8cc3` | BLOCKED | `AMBIGUOUS_FALSIFICATION_POLARITY` |
| `c1f9597e66c1f0a9b518482a36c7a06f57617a6eeb7ce5cdd50114033f165f58` | REJECTED_BY_HUMAN_REVIEW | `UNREGISTERED_INDICATOR_DEPENDENCY`; `UNSUPPORTED_DYNAMIC_PARAMETER_SEMANTICS` |

All three remain intact. Their research and freeze authorization are
`NOT_AUTHORIZED`.

## Active architectural boundary

Only declarative fixed-parameter `EMA_CROSSOVER` EURUSD/H1 is registered.
`fast_period` and `slow_period` are positive integers fixed by StrategySpec
and Experiment. ATR, RSI, MACD, Bollinger, dynamic/adaptive periods,
countertrend/reversal semantics, non-typed falsification and unsupported
metrics fail closed.

No freeze, Experiment, Sensitivity, Walk-Forward, Strategy Gate,
ControlledResearchLoop, execution, MT5 access, or autonomous research is
authorized. F6.9 remains pending a separately approved catalog expansion.

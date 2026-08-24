# F6.8c — Typed Falsification Contract

Falsification is no longer free text. Every criterion names a typed metric,
operator, finite numeric threshold and scientific scope. The only supported
metrics are the versioned `F6_METRICS_V1` outputs with their actual
availability in `EXPERIMENT`, `WALK_FORWARD` or `GATE`.

The validator rejects unknown metrics/operators, non-finite thresholds and
metric/scope mismatches deterministically. Providers request the same typed
schema through Structured Outputs. Semantic strategy checks remain separate
from human economic review; no research action is introduced.

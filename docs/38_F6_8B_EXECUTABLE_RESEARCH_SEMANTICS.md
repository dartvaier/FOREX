# F6.8b — Executable Research Semantics

F6.8b supplies the proposal agent with the registered EMA crossover semantics:
crossing above enters long, crossing below enters short, on a closed H1 bar.
This is a directional trend-following strategy, not a countertrend or reversal
strategy.

The context also contains a versioned allowlist of metrics deterministically
produced by Performance, Walk-Forward and Strategy Gate. The validator rejects
countertrend/reversal semantics and falsification criteria based on p-values,
statistical significance, event studies, correlation, probability, pips or any
metric outside that allowlist. It does not assess economic plausibility.

This remains proposal-only. No proposal can authorize freeze, Experiment,
Sensitivity, Walk-Forward, Strategy Gate or ControlledResearchLoop.

The first `qwen3:14b` F6.8b canary was rejected as `UNSUPPORTED_METRIC`: one
criterion used Sharpe ratio, but another supplied only an evaluation horizon
and no measurable falsification metric. No human-review package or research
action was created.

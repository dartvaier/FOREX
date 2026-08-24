# F6.7c — Local Provider Validation Results

## Proposal-only baseline: qwen3:14b

On 2026-08-24, the manual `proposal-only` canary was run against local Ollama
with `qwen3:14b`, 4096 context and temperature zero. A first 25-second
wall-clock run failed closed with `TIMEOUT`; it did not create a proposal or
start research. The repeated canonical 120-second run completed in about 13
seconds and passed.

| Check | Result |
| --- | --- |
| Provider | `SUCCESS` |
| Schema validation | Valid |
| ProposalValidator | `ACCEPTED` |
| Research run / AgentRun | Not created |
| Gate or holdout | Not used |
| Capability boundary | Preserved |

The passing non-sensitive local artifacts are retained under
`outputs/agent_canary/proposal-qwen3-14b-20260824-120s/` and are intentionally
ignored by Git. They contain `summary.json`, `proposal.json` and
`validation.json`. The shorter timeout artifact is retained separately for
latency evidence.

The accepted proposal is technically valid but scientifically weak: it is a
generic EMA 12/26 crossover, gives no justification for those parameters, and
uses falsification criteria without pre-specified operational thresholds. It is
not evidence of novelty or strategy quality.

## Assessment-only baseline: qwen3:14b

The assessment canary used frozen synthetic facts with a known `PASS` gate,
Sharpe 1.25, net return 14%, maximum drawdown -8% and 120 trades. It completed
successfully, retained an identical facts fingerprint and preserved `PASS`.
The interpretation repeated those values accurately and did not introduce or
alter a quantitative fact. Its artifacts are retained under
`outputs/agent_canary/assessment-qwen3-14b-20260824/`.

## Decision

The local provider and both bounded canaries are technically validated. Do not
run a controlled loop or autonomous policy yet: the proposal review does not
meet the required scientific-quality bar. F6.8 should therefore focus on
Research Context & Prompt Quality (including parameter rationale,
operational falsification and registry novelty context), while retaining the
4096 context baseline. The 8B/14B comparison remains pending and should reuse
the improved, identical task after that quality work is in place.

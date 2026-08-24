# F6.7c — Local Provider Validation Results

## Proposal-only baseline: qwen3:14b

On 2026-08-24, the manual `proposal-only` canary was run against local Ollama
with `qwen3:14b`, 4096 context and temperature zero. The run used a 25-second
wall-clock deadline to make the result observable in the local validation
environment.

| Check | Result |
| --- | --- |
| Provider | `FAILED` — `TIMEOUT` |
| Schema validation | Not reached |
| ProposalValidator | Not reached |
| Research run / AgentRun | Not created |
| Gate or holdout | Not used |
| Capability boundary | Preserved |

The non-sensitive local artifacts are retained under
`outputs/agent_canary/proposal-qwen3-14b-20260824/` and are intentionally
ignored by Git. They contain `summary.json` and `error.json`; no proposal or
validation artifact exists because the provider did not return one.

## Decision

This is a provider-latency failure, not a negative quality assessment of the
model. Do not run assessment-only, a controlled loop, the 8B comparison, or
F6.8 based on this result. Re-run the same proposal-only task after diagnosing
the local Ollama latency, preserving the 4096 context baseline unless evidence
of context truncation appears.

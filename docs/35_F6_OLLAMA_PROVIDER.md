# F6.7b — Local Ollama Provider

`OllamaProvider` uses the local native `/api/chat` endpoint with JSON Schema `format`, zero temperature and configurable `OLLAMA_HOST`/`OLLAMA_MODEL`. The default baseline is `qwen3:8b`. The deterministic canary also sets `think=false`; this avoids unbounded reasoning output and does not change the 4096-token context baseline. Connection, timeout, missing-model, provider and invalid-output failures are structured and fail closed. The real HTTP request has a wall-clock deadline and is terminated if it exceeds the configured timeout. It can be passed to the existing manual proposal/assessment canaries; CI uses only mocked transport and requires no Ollama installation.

## F6.7c manual proposal-only canary

Use the larger local model first, without starting research, a gate, a holdout, or a loop:

```powershell
$env:OLLAMA_HOST = "http://localhost:11434"
$env:OLLAMA_MODEL = "qwen3:14b"
python -m research.canary --canary-id proposal-qwen3-14b-YYYYMMDD
```

The command is opt-in and stores non-sensitive review artifacts under
`outputs/agent_canary/<canary-id>/`: `summary.json`, `proposal.json`, and
`validation.json` on a successful proposal; an `error.json` is written on a
structured provider failure. The summary records the provider result, schema
check, validator execution and the bounded scope. A proposal-only canary has no
`AgentRun`, because it deliberately never creates a research run.

Review the artifacts before running assessment-only. A provider timeout or other
failure is fail-closed: the command exits non-zero and no research is started.

Assessment-only needs an explicitly frozen JSON object supplied by the trusted
operator; the LLM receives its values but never a file capability. It snapshots
and fingerprints the facts before the provider call, then requires the same
snapshot and `gate_status` afterwards:

```powershell
python -m research.canary assessment-only `
  --canary-id assessment-qwen3-14b-YYYYMMDD `
  --facts-file docs/fixtures/f6_7c_assessment_facts.json
```

The output includes `facts.json` and `assessment.json`. The latter is an
interpretation alongside the immutable fact snapshot; it is not an authority to
rewrite any metric or GateStatus.

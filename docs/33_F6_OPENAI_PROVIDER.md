# F6.7 — Real LLM Provider Integration

`OpenAIProvider` is an optional thin Responses API adapter using strict JSON-schema Structured Outputs. `OPENAI_API_KEY` is read only from the environment and never stored in telemetry or audits. Fail-closed structured errors cover auth, rate, timeout, provider and invalid-output conditions. Real tests use `llm_integration` and remain disabled by default; CI uses mocks only.

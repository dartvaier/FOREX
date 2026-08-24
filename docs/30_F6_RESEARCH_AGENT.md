# F6.4 — Research Agent / LLM Adapter

The agent has an explicit allowlist: registry query, proposal submission, research-run start/query and evidence analysis. `LLMProvider` is vendor-independent and may only return a proposal object or interpretation text. Schema validation remains authoritative; assessment facts are immutable and cannot modify computed metrics, gate status or holdout controls. No autonomous loops, MT5, shell, filesystem or direct quantitative-runner access exists.

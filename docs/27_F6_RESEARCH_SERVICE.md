# F6.1 — Research Service / Agent Tool Layer

`ResearchService` is a typed, deterministic local façade for registry queries and F5 Experiment, Sensitivity, Walk-Forward and Gate runners. It accepts only declarative `StrategySpec` for registered EMA Crossover H1, returns structured tool statuses, preserves fingerprints and caches identical requests for idempotence. It imports no OpenAI, LLM, MCP or MT5 integration and has no broker/order capability.

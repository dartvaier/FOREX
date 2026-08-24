# F6.7b — Local Ollama Provider

`OllamaProvider` uses the local native `/api/chat` endpoint with JSON Schema `format`, zero temperature and configurable `OLLAMA_HOST`/`OLLAMA_MODEL`. The default baseline is `qwen3:8b`. Connection, timeout, missing-model, provider and invalid-output failures are structured and fail closed. It can be passed to the existing manual proposal/assessment canaries; CI uses only mocked transport and requires no Ollama installation.

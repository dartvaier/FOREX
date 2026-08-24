# F6.8e — Catalog Closure Validation

The current catalog contains only a fixed-parameter `EMA_CROSSOVER` for
EURUSD/H1. `fast_period` and `slow_period` are positive integers fixed by the
StrategySpec and Experiment; adaptive, dynamic, volatility-adjusted and
regime-dependent periods are unsupported.

Validation scans every scientific text field: title, thesis, expected
mechanism, parameter rationale, assumptions and tags. ATR, RSI, MACD,
Bollinger and dynamic-period dependencies fail closed wherever they appear.
This closes the catalog; it does not add indicators or runtime parameter logic.

# F5.13 — Final Holdout / Strategy Gate

F5.13a freezes Strategy, Risk, costs, dataset, final window and acceptance criteria in `StrategyGateSpec`; it has no holdout dataframe. F5.13b executes that frozen spec once, records a fingerprinted audit result, and cannot be rerun by the same runner. Insufficient closed trades return INCONCLUSIVE. The gate evaluates return, PF, Sharpe, drawdown, trade count and degradation against walk-forward. No parameter change is permitted after the result.

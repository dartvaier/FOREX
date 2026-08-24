# F5.7 — BacktestEngine

The engine is a bar-by-bar temporal orchestrator. At each open it executes an
approved pending order; at close it marks an open position, builds the safe
context, calls Strategy and asks Risk for a decision. Approved orders are held
for the next actual opening. `BacktestResult` retains signals, decisions,
orders, executions, fills, snapshots and contexts. HOLD, rejection and
UNFILLED are normal recorded outcomes; metrics remain out of scope.

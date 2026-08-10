# AGENTS.md

## Purpose

This repository is the **FOREX Algorithmic Trading Research Platform**.

Agents working here must prioritize:

1. correctness;
2. temporal integrity;
3. reproducibility;
4. explicit costs and risk;
5. test coverage;
6. research discipline;
7. only then performance or optimization.

The goal is not to make a backtest look profitable. The goal is to build a system capable of detecting whether an edge survives realistic constraints without fooling itself.

---

## Read Before Changing Code

At the beginning of a task, determine the real repository state before making assumptions.

Check, when available:

```powershell
git status --short --branch
git branch --show-current
git log -5 --oneline
```

Then read the files relevant to the task.

Important project references include:

```text
CHANGELOG.md
DECISIONS.md
docs/10_BACKTEST_DESIGN.md
docs/11_ROADMAP.md
docs/12_STRATEGY_RESEARCH.md
docs/13_RESEARCH_RUNNER.md
docs/14_RISK_MANAGEMENT.md
```

Do not assume `README.md`, an old branch, or an old roadmap section reflects the current implementation.

When documentation and implementation appear inconsistent, investigate using this order:

```text
1. current automated tests
2. current code
3. DECISIONS.md
4. current phase documentation
5. CHANGELOG.md
6. README.md
```

Do not silently override an architectural decision just because another implementation is easier.

---

## Environment

Primary environment:

```text
OS: Windows
Shell: PowerShell
Python: 3.14.x
Tests: pytest
Broker/Data Source: MetaTrader 5
Storage: Parquet
Internal timezone: UTC
```

Tests that require a live MetaTrader 5 connection use the `integration` pytest marker.

Engineering tests for backtest, strategy, performance, and risk should remain independent of a live broker connection whenever possible.

---

## Architecture Boundaries

Respect the existing separation of responsibilities.

### Strategy

A Strategy may:

- interpret market data;
- generate a `Signal`;
- provide rationale/metadata;
- provide technical stop/target information when appropriate.

A Strategy must not:

- call MetaTrader 5 order execution;
- create fills directly;
- control the Portfolio;
- calculate execution costs;
- choose final financial exposure outside the Risk layer;
- access future data.

### Risk

Risk is responsible for:

- approving or rejecting new exposure;
- position sizing;
- exposure limits;
- loss limits;
- future portfolio-level protections.

### Execution

Execution is responsible for converting approved orders into simulated fills according to the configured execution model.

### Cost Model

Execution costs belong outside Strategy.

Cost components include, as applicable:

- spread;
- slippage;
- commission;
- future financing/swap models.

### Portfolio

Portfolio owns:

- open position state;
- cash;
- realized/unrealized PnL;
- equity.

### Performance

Performance code owns metrics, drawdown, trade statistics, and result aggregation.

### Research

The `research/` layer owns experiment orchestration, reproducibility, reports, comparisons, and research configuration.

Before creating a new abstraction, verify that the concept does not already exist in `backtest/`, `backtest/models/`, `strategy/`, `research/`, or the ledgers.

---

## Critical Temporal Invariants

These rules must not be weakened to improve a result.

### UTC

All internal timestamps must remain timezone-aware UTC.

Session-specific timezone conversions should occur only when a strategy explicitly needs them.

### Closed Bars Only

Strategies must only receive data considered available at the simulated time.

Do not deliberately expose a still-forming candle as a closed candle.

### No Look-Ahead

Future information is forbidden.

A Strategy must never use data from `t+1` or later when deciding at `t`.

This also applies to:

- future OHLC;
- higher timeframes that have not closed yet;
- labels created using future returns;
- precomputed features whose values would not yet be known.

### Multi-Timeframe Causality

M15 may be used as the base execution clock.

H1/H4 data become available only after their own candle close time.

Never synchronize multi-timeframe data merely with equal integer indexes such as:

```python
M15.iloc[i]
H1.iloc[i]
H4.iloc[i]
```

Synchronize using timestamps and causal availability.

### Gaps

Do not manufacture missing candles.

Do not use `ffill()` or similar logic simply to hide missing market periods.

The engine should use the next real available bar.

### Incomplete Derived Bars

Processed H1/H4 bars marked incomplete must not generate normal strategy signals by default.

---

## Baseline Execution Semantics

Preserve the current baseline unless an explicit architectural decision changes it:

```text
Clock: bar-by-bar
Signal: after candle close
Execution: next available bar open
Orders: market baseline
Position: one at a time
Pyramiding: disabled
Automatic reversal: disabled
Incomplete bars: excluded by default
Missing bars: preserved
Ambiguous SL/TP: worst case
Costs: explicit component
Look-ahead: prohibited
```

A signal based on candle `t` must not receive guaranteed execution at the same closing price used to create the signal.

### Signal != Order != Fill

Preserve the conceptual flow:

```text
Strategy
  -> Signal
  -> RiskGate
  -> RiskDecision
  -> Order
  -> Execution
  -> Fill
  -> Portfolio
  -> Trade
```

A valid market signal may still be rejected by Risk.

That is expected behavior.

---

## Costs and Trading Friction

Do not evaluate a strategy only with zero trading costs.

The current research baseline commonly uses explicit values similar to:

```text
spread_pips = 2.0
slippage_pips = 0.5
commission_per_lot_per_side = 3.50
```

Treat these as research parameters, not universal market constants.

Zero-cost runs are useful for diagnosing gross signal quality and engineering behavior.

A strategy intended for promotion must also be tested with explicit costs and, when relevant, cost stress such as:

```text
baseline
1.5x baseline
2.0x baseline
```

Never improve a backtest by hiding spread, slippage, commission, gap behavior, or intrabar ambiguity.

---

## Research Discipline

Do not mine parameters until a profitable historical combination appears.

Before testing a new hypothesis, define:

```text
HYPOTHESIS
RATIONALE
FEATURES
ENTRY RULES
EXIT RULES
WARM-UP
PREDEFINED PARAMETERS
TIMEFRAME
COST MODEL
RISK MODEL
ACCEPTANCE CRITERIA
REJECTION CRITERIA
```

Then run the experiment.

Do not define acceptance criteria after seeing the result.

### Preferred Validation Order

```text
Hypothesis
  -> synthetic/unit tests
  -> zero-cost backtest
  -> explicit-cost backtest
  -> trade/result analysis
  -> predefined local sensitivity
  -> cost stress
  -> validation period
  -> out-of-sample
```

Out-of-sample data must behave like a lockbox. Do not optimize on it.

### Previously Tested Families

The branch already contains research implementations for strategies including:

- EMA Trend Following;
- Volatility Breakout;
- Time-Series Momentum;
- Mean Reversion;
- Asian Range Breakout;
- Carry baseline;
- Regime Detection;
- Multi-Timeframe Momentum.

Do not repeatedly sweep these same primary specifications until one becomes profitable.

A rejected family should only be reopened with a materially new structural hypothesis and a defensible rationale.

### Turnover Matters

Always inspect whether a small gross edge is being consumed by trading friction.

Important diagnostics include:

```text
trade count
average gross edge per trade
cost per round trip
net expectancy
holding period
profit factor
drawdown
```

Do not optimize win rate in isolation.

---

## Research Runner

Prefer the existing reproducible runner over isolated ad-hoc backtest scripts.

Examples:

```powershell
python -m research.runner --strategy ema_trend
python -m research.runner --strategy time_series_momentum --cost explicit
python -m research.runner --strategy ema_trend --date-from 2015-01-01 --date-to 2020-12-31
python -m research.runner --strategy time_series_momentum --param lookback=192
python -m research.summarize
```

When adding a Strategy:

1. implement it in `strategy/` using the existing Strategy contract;
2. add deterministic unit tests;
3. add it to the research registry if appropriate;
4. run relevant tests;
5. run zero-cost research;
6. run explicit-cost research;
7. record and interpret the result.

Do not build a custom engine around a Strategy.

---

## Risk Management

Current risk infrastructure includes concepts such as:

```text
RiskGate
RiskDecision
VolumeRules
FixedSizeRiskGate
StopBasedRiskGate
ExposureLimitRiskGate
DailyLossRiskGate
```

Preserve the compositional RiskGate design.

Risk limits that block new exposure must not accidentally block `EXIT` behavior that reduces exposure.

As of the current branch, F7 Risk Management is in progress. Re-read `docs/14_RISK_MANAGEMENT.md` and the current roadmap before choosing the next risk task.

The next documented block at the time this file was created is the **Drawdown Guard**.

Before implementing it, inspect at least:

```text
backtest/risk.py
backtest/drawdown.py
backtest/equity_ledger.py
backtest/equity_recorder.py
relevant risk tests
docs/14_RISK_MANAGEMENT.md
```

Do not create a parallel drawdown subsystem if the current components can be extended cleanly.

Risk management must not be used to retroactively manufacture edge from an unprofitable Strategy.

Evaluate signal edge and risk transformation separately.

---

## Tests

Prefer small deterministic synthetic datasets for financial logic.

If a behavior can be proven with 3, 5, or 10 bars, do not depend on hundreds of thousands of historical rows to validate it.

Separate:

```text
rule correctness
engine integration
historical research outcome
```

### Bug-Fix Workflow

For well-defined bugs:

```text
1. reproduce with a failing test
2. confirm the test fails for the expected reason
3. make the smallest correct change
4. run the focused test
5. run related tests
6. run regression tests
```

Do not change a correct test merely to make incorrect code pass.

### Test Execution

Typical progression:

```text
focused test
-> related test module
-> non-integration suite
-> full suite when the environment supports it
```

Example non-integration run:

```powershell
pytest -m "not integration" -q
```

Do not claim a test passed unless it was actually executed.

A MetaTrader 5 connection failure is not automatically a BacktestEngine logic failure.

---

## Regression and Reproducibility

Treat regression tests as contracts.

If a code change alters a previously stable backtest result, determine whether it is:

- a real bug fix;
- a regression;
- an intentional execution/model change.

Intentional semantic changes may require updates to:

```text
tests
DECISIONS.md
CHANGELOG.md
relevant docs
```

A reproducible experiment should allow reconstruction of:

```text
dataset
dataset hash
period
symbol
timeframe
strategy
strategy parameters
cost model
risk model
engine policies
initial capital
result
```

Record the Git commit when the research tooling supports it.

Same code + same data + same configuration should produce the same result.

---

## Suspiciously Good Results

An unusually strong backtest should trigger more auditing, not less.

Check for:

```text
look-ahead
data leakage
same-close execution
future H1/H4 availability
missing costs
wrong gap handling
optimistic SL/TP ambiguity
position sizing errors
duplicate PnL
spread double-counting or omission
small sample size
PnL concentration
```

Do not promote a strategy until these failure modes are ruled out.

---

## Git Workflow

Do not work directly on `master` by default.

Use the active feature/fix branch appropriate to the task.

Before changing code, inspect branch and status.

Prefer small, auditable commits.

Examples:

```text
feat(risk): add equity drawdown guard
test(risk): cover drawdown lock behavior
feat(strategy): add volatility regime filter
fix(backtest): preserve next-open execution after gap
docs: document drawdown risk policy
```

Before committing, inspect:

```powershell
git status
git diff --check
git diff --stat
git diff
```

Do not commit secrets, broker credentials, API keys, tokens, large unintended datasets, or temporary research output.

Do not automatically execute destructive or history-rewriting Git operations such as:

```text
git reset --hard
git clean -fd
force push
destructive rebase
branch deletion
history rewrite
merge into master
```

without explicit authorization.

Do not push or merge merely because tests are green unless the user explicitly requested it.

---

## Trading Safety

The repository is currently a research/backtest/risk platform, not an authorization to trade live funds.

Do not introduce real order execution merely to test a Strategy.

Do not call `mt5.order_send()` or silently enable live trading unless the execution/demo phase has explicitly been authorized and designed.

Preserve read-only behavior where the current project state requires it.

The intended progression is:

```text
backtest
-> validation
-> out-of-sample
-> risk validation
-> demo
-> monitoring
-> only then consider later execution stages
```

---

## Completion Report

When finishing a code task, report:

```text
Implemented
Files changed
Tests executed
Test results
Architectural impact
Git/branch state
Recommended next step
```

When finishing a research experiment, report:

```text
Hypothesis
Strategy
Dataset
Period
Parameters
Costs
Trades
Net Profit
Expectancy
Profit Factor
Drawdown
Win Rate
Average Trade
Robustness evidence
Limitations
Decision
```

Useful research decisions include:

```text
REJECTED
INSUFFICIENT EVIDENCE
INTERESTING
PROMISING - VALIDATE
OOS CANDIDATE
VALIDATED FOR DEMO
```

Do not jump directly from a profitable backtest to production.

---

## Final Principle

When multiple choices exist, prefer:

```text
correctness over speed
causality over convenience
explicit assumptions over hidden behavior
simple hypotheses over parameter-heavy rules
reproducibility over one-off results
robustness over peak historical profit
```

The central question for every strategy is:

> Does the apparent advantage survive causal data access, explicit costs, realistic execution assumptions, risk controls, validation, and data that was not used to create the hypothesis?

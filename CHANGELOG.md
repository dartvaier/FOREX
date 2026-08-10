# Changelog

Todas as mudanças relevantes da plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

serão registradas neste arquivo.

O formato segue, de maneira simplificada, os princípios de:

```text
Keep a Changelog
Semantic Versioning
```

As versões representam marcos técnicos do projeto e não necessariamente releases de um sistema pronto para trading real.

---

# [Unreleased]

Próxima fase planejada:

```text
FOREX v0.3.0
Strategy Research
```

## Planned

- Fixtures e relatórios para pesquisa de estratégia.
- Validação out-of-sample inicial.
- Comparação com custos explícitos.

## Added

- Simple EMA Trend Following baseline.
- Strategy Research documentation.
- Unit tests for warm-up, EMA cross above, EMA cross below and no-cross scenarios.
- BacktestEngine integration tests for EMA strategy with zero-cost and explicit-cost configurations.
- Causal closed-bar context windowing for stateful strategies.
- Initial historical EMA baseline result for EURUSD M15.
- Local sensitivity results for EMA 10/30, 20/50 and 50/200.
- Volatility Breakout baseline strategy, tests and initial EURUSD M15 result.
- Time-Series Momentum baseline strategy, tests and initial EURUSD M15 result.
- Simple Mean Reversion baseline strategy, tests and initial EURUSD M15 result.
- Reproducible research runner and report summaries (research/).
- Asian Range Breakout baseline strategy, tests and initial EURUSD M15 result.
- Simple Carry baseline strategy, tests and initial EURUSD M15 result.
- Simple Regime Detection baseline strategy, tests and initial EURUSD M15 result.
- Multi-Timeframe Momentum baseline strategy, tests, causal H1/H4 context support and initial EURUSD M15 result.
- RiskGate protocol, volume-step validation and StopBasedRiskGate sizing from entry/stop metadata.
- ExposureLimitRiskGate wrapper with max quantity and max notional checks.
- DailyLossRiskGate wrapper with absolute and percentage daily loss limits.
- DrawdownRiskGate wrapper with absolute and percentage all-time-high drawdown locks.
- KillSwitchRiskGate wrapper with latch kill/reset and SOFT/HARD modes (ADR-045).
- Cost stress support in the research runner (--cost-multiplier 1.0/1.5/2.0) with
  auditable base params + multiplier in reports (F8 first block).
- Structured local sensitivity and subperiod harness (research/sweep.py):
  one-parameter sweeps (--range/--values) and standard F8 subperiods
  (--subperiods), each run an auditable runner report, with comparison CSV.
- Formal Development/Validation/OOS period definitions (research/periods.py):
  pre-registered roles (dev 2015-20, val 2021-23, oos lockbox 2024-26),
  mechanical OOS guard (--period oos requires --allow-oos), and structured
  stability analysis (--stability: dev vs val deltas + signal consistency).
- F8 COMPLETE: robustness results documented in docs/15_ROBUSTNESS.md
  (sweep grids, subperiods, dev/val stability, cost stress 1.5x/2.0x for
  TSM/EMA/MR; OOS lockbox untouched). All three baseline strategies are
  consistently negative under explicit costs; no parameter islands.
- OOS lockbox consulted once at baseline close (2026-08-10, explicit
  --allow-oos): TSM -1.71%, EMA -2.48%, MR -4.23% explicit; TSM +0.42%
  zero-cost. Out-of-sample confirms dev/val: no baseline strategy passes
  under explicit costs. Event logged in docs/15_ROBUSTNESS.md.
- F9 (Demo Execution) IN PROGRESS, engineering core without activation:
  execution/ package (ExecutionInterface, BrokerState, Order/Fill
  validation, Position Reconciliation) with 28 tests; no MT5 dependency,
  TRADING_ENABLED=false unchanged (docs/16_EXECUTION_LAYER.md).
- F9 MT5Execution adapter (execution/mt5_execution.py): implements
  ExecutionInterface via MT5 API with lazy import, order validation before
  send, retcode translation and fill validation; trading_enabled=False
  guard blocks submit/cancel (read-only monitoring allowed). 16 tests with
  a fake MT5 module; no real broker call. 943 tests total.
- F9 Logs, Monitoring and Broker/Demo validation (execution/audit_log.py,
  monitoring.py, broker_validation.py): JSONL audit trail, immutable demo
  metrics (latency, slippage, rejection rate) and roadmap 84 preconditions
  (demo trade mode, server allowlist, TRADING_ENABLED, kill switch).
  BrokerAccountState.trade_mode added; MT5Execution.validate_environment()
  gates Demo activation. +20 tests; 963 total.
- F9 Execution comparison (execution/comparison.py): expected vs observed
  (roadmap 86-87) with pips/latency tolerances, WITHIN/OUTSIDE verdicts and
  comparison_summary for the Demo validation period. F9 engineering is now
  COMPLETE; only explicit Demo activation remains. +12 tests; 975 total.
- F10 Live Readiness IN PROGRESS (readiness/ package + docs/17):
  programmatic readiness review (module availability as evidence), risk
  limits (risk per trade, daily loss, drawdown, leverage, exposure),
  safety helpers (duplicate orders, connection breach) and operational
  procedures documented. Real-state review shows only demo_validation and
  trading_flag pending (both require explicit activation). +20 tests; 995.
- F10 readiness CLI (readiness/__main__.py, python -m readiness): renders
  the review with live module evidence + operator flags, optional risk
  limits check; exit 0/1 for scripting. Demo activation procedure
  documented in docs/17 (section 9). +15 tests; 1010 total.
- Demo activation test (authorized, 2026-08-10): first live market
  round-trip on the demo account (EURUSD 0.01, SL 20 pips). FILLED with
  233ms latency and 0.0 pips slippage; total virtual cost 0.01 USD.
  Adapter fixes from real-broker findings: symbol-derived filling mode
  (retcode 10030), close_position() by ticket for hedging accounts, and
  positions_get() without symbol=None. 1012 tests.

---

# [0.2.0] - 2026-08-10

## Backtesting Infrastructure

- BacktestEngine bar-by-bar.
- Simulation Clock.
- BacktestConfig.
- InstrumentSpecification.
- Signal model.
- Order model.
- Fill model.
- Position model.
- Trade model.
- Portfolio.
- Fixed Size Risk baseline.
- CostModel.
- Spread model configurável.
- Slippage configurável.
- Commission configurável.
- Stop Loss.
- Take Profit.
- Worst-case ambiguous bar policy.
- Gap-through-stop handling.
- Trade Ledger.
- Order Ledger.
- Fill Ledger.
- Equity Curve.
- Performance metrics básicas.
- Regression tests do BacktestEngine.
- Fixtures artificiais determinísticas.
- Proteção explícita contra look-ahead.
- Next-open execution.
- Tratamento de posições abertas no final do backtest.
- Resultado consolidado em `BacktestResult`.
- Estratégias podem informar `stop_loss` e `take_profit` via metadata do Signal.

## Baseline Decisions

O BacktestEngine inicial segue:

```text
Clock:
bar-by-bar

Signal:
after candle close

Execution:
next available bar open

Orders:
market

Position:
one at a time

Pyramiding:
disabled

Automatic reversal:
disabled

Incomplete bars:
excluded

Missing bars:
preserved

Ambiguous Stop/TP:
worst case

Costs:
explicit CostModel

Look-ahead:
prohibited
```

# [0.1.1] - 2026-08-08

## Documentation Completion

Patch release destinado a completar a documentação do marco:

```text
FOREX v0.1
Data & Infrastructure Foundation
```

---

# [0.1.0] - 2026-08-08

## Data & Infrastructure Foundation

Primeiro marco técnico formal da plataforma.

Esta versão estabelece a infraestrutura de dados, integração com MetaTrader 5, transformação temporal, testes e documentação necessários antes do desenvolvimento do BacktestEngine.

Esta versão:

```text
NÃO
```

representa um bot de trading operacional.

Não existem ainda:

```text
BacktestEngine

Strategy Engine

Risk Engine completo

Execution Engine

ordens automáticas

Live Trading
```

---

## Added — Development Environment

Adicionado ambiente de desenvolvimento baseado em:

```text
Windows

Python 3.14.5

Virtual Environment (.venv)
```

Dependências principais:

```text
MetaTrader5

pandas

numpy

python-dotenv

matplotlib

pytest

pyarrow
```

Versões validadas incluem:

```text
MetaTrader5 5.0.6090

pytest 9.1.1
```

---

## Added — Project Structure

Criada estrutura modular inicial:

```text
broker/

data/

strategy/

risk/

execution/

backtest/

monitoring/

config/

tests/

docs/
```

A arquitetura foi projetada para manter separação entre:

```text
Broker

Data

Strategy

Risk

Execution

Backtest
```

---

## Added — MetaTrader 5 Integration

Adicionado:

```text
broker/mt5_client.py
```

com classe:

```text
MT5Client
```

Funcionalidades atuais:

```text
connect

disconnect

account_info

symbol_info

current_tick

current_bar

rates

rates_range
```

---

## Added — MT5 Connection Lifecycle

Implementado ciclo:

```text
initialize
    ↓
operações
    ↓
shutdown
```

Também adicionado suporte a:

```python
with MT5Client() as client:
    ...
```

para gerenciamento automático da conexão.

---

## Added — Demo Environment

A integração foi validada utilizando:

```text
MetaTrader 5

MetaQuotes-Demo

Conta Demo
```

O projeto permanece:

```text
READ ONLY
```

---

## Security

Adicionada configuração:

```env
TRADING_ENABLED=false
```

Nenhuma chamada de:

```python
mt5.order_send()
```

faz parte do fluxo atual.

---

## Added — EURUSD Instrument Support

O primeiro instrumento utilizado é:

```text
EURUSD
```

Especificações observadas:

```text
Digits:          5

Point:           0.00001

Pip:             0.00010

Points per Pip:  10

Contract Size:   100000

Volume Min:      0.01

Volume Step:     0.01
```

Esses valores são consultados através do broker e não devem ser tratados como universais.

---

## Added — Market Data Layer

Adicionado:

```text
data/market_data.py
```

com classe:

```text
MarketData
```

Funcionalidades:

```text
current quote

Bid

Ask

Point

Pip Size

spread atual

closed bars
```

---

## Added — Closed Candle Protection

Definida regra:

```text
bar 0
=
barra mais recente
```

Dados destinados à aplicação utilizam:

```text
start_pos = 1
```

para excluir deliberadamente a barra corrente.

Essa regra também possui teste automatizado.

---

## Added — UTC Standard

Definido:

```text
UTC
```

como timezone interno oficial do projeto.

Todos os timestamps persistidos devem ser:

```text
timezone-aware
```

Conversões para sessões futuras deverão utilizar timezones reais como:

```text
Europe/London

America/New_York
```

---

## Added — Historical Data Layer

Adicionado:

```text
data/historical_data.py
```

com classe:

```text
HistoricalData
```

Responsabilidades:

```text
historical download

chunk processing

UTC normalization

sorting

deduplication

validation

Parquet persistence
```

---

## Fixed — MT5 Historical Range Handling

Durante o desenvolvimento, uma requisição extensa de histórico apresentou:

```text
Terminal: Invalid params
```

Foram realizados testes com intervalos menores.

Como solução, foi adotada coleta histórica em blocos.

---

## Added — Historical Chunking

Configuração atual:

```text
chunk_days = 90
```

Fluxo:

```text
period
  ↓
90-day chunks
  ↓
concat
  ↓
sort
  ↓
deduplicate
  ↓
validate
```

---

## Added — Explicit Timestamp Conversion

Datas timezone-aware são convertidas para:

```text
Unix timestamp inteiro
```

antes de serem passadas ao:

```text
copy_rates_range()
```

---

## Added — Requested Range Validation

Adicionada proteção para garantir que candles retornados pertençam à janela efetivamente solicitada.

Conceitualmente:

```python
current_from <= time < current_to
```

Isso protege a coleta contra respostas inesperadas da fonte.

---

## Added — Historical Dataset

Criado dataset:

```text
data/raw/EURUSD/M15.parquet
```

Fonte:

```text
MetaQuotes-Demo
```

Timeframe:

```text
M15
```

Timezone:

```text
UTC
```

---

## Data Snapshot

Cobertura atual:

```text
First:
2015-01-02 09:00:00 UTC

Last:
2026-08-07 23:45:00 UTC
```

Quantidade:

```text
288223 candles
```

---

## Added — Parquet Storage

Escolhido:

```text
Apache Parquet
```

como formato principal de séries históricas.

Motivos incluem:

```text
preservação de tipos

timezone

compressão

integração com pandas

eficiência
```

---

## Added — Historical Metadata

Criado:

```text
data/metadata/EURUSD_M15.json
```

através de:

```text
generate_metadata.py
```

A metadata registra características e limitações conhecidas do dataset.

---

## Added — Historical Analysis

Criado:

```text
analyze_history.py
```

para auditoria de:

```text
coverage

duplicates

null values

OHLC

annual candle count

gaps

spread

tick volume

real volume
```

---

## Data Quality — Structural Integrity

Resultado atual:

```text
Duplicates:
0

Null Values:
0

Invalid OHLC:
0
```

---

## Data Quality — Annual Coverage

Candles M15 por ano:

```text
2015    24776

2016    24898

2017    24804

2018    24812

2019    24784

2020    24901

2021    24914

2022    24912

2023    24824

2024    24897

2025    24757

2026    14944
```

O ano de 2026 representa período parcial.

---

## Added — Gap Detection

Foram identificados:

```text
659 gaps
```

Classificação inicial:

```text
605
cross-weekend

54
intraweek
```

---

## Decision — No Artificial Gap Filling

Definida política:

```text
NÃO utilizar forward-fill
para fabricar candles ausentes.
```

Não serão criadas barras artificiais através de:

```python
ffill()
```

sobre preços.

---

## Data Quality — Historical Spread

Estatísticas gerais observadas:

```text
count:
288223

mean:
3.636688 points

median:
2 points

min:
0 points

max:
129 points
```

---

## Data Quality — Zero Spread

Percentual aproximado:

```text
32.54%
```

de candles com:

```text
spread = 0
```

---

## Decision — Historical Spread

Definido que:

```text
MT5 candle spread
!=
official Backtest CostModel
```

O campo continuará preservado para:

```text
audit

research

comparison
```

---

## Data Quality — Tick Volume

Estatísticas observadas:

```text
mean:
~926

median:
680

min:
1

max:
21483
```

---

## Decision — Tick Volume

O campo:

```text
tick_volume
```

poderá ser utilizado como:

```text
relative feed activity
```

mas não deverá ser interpretado como:

```text
global traded Forex volume
```

---

## Data Quality — Real Volume

Foi identificada forte inconsistência estrutural.

Percentual aproximado de candles com:

```text
real_volume > 0
```

por período:

```text
2015    ~44%

2016   ~100%

2017    ~43%

2018+     0%
```

---

## Decision — Real Volume

Definido:

```text
real_volume
```

não será utilizado atualmente como:

```text
feature

signal

filter

regime input
```

O campo permanece no dataset raw apenas para rastreabilidade.

---

## Added — Timeframe Builder

Adicionado:

```text
data/timeframe_builder.py
```

com:

```text
TimeframeBuilder
```

Responsável por:

```text
M15 → H1

M15 → H4
```

---

## Added — Timeframe Build Script

Criado:

```text
build_timeframes.py
```

Saídas:

```text
data/processed/EURUSD/H1.parquet

data/processed/EURUSD/H4.parquet
```

---

## Added — OHLC Aggregation

Timeframes superiores utilizam:

```text
Open
=
first Open

High
=
maximum High

Low
=
minimum Low

Close
=
last Close
```

---

## Added — Tick Volume Aggregation

Para candles derivados:

```text
tick_volume
=
sum(source tick_volume)
```

---

## Decision — Spread Not Aggregated

O campo:

```text
spread
```

não é agregado para H1/H4.

Motivos:

```text
semântica de agregação ambígua

qualidade histórica inconsistente

CostModel futuro independente
```

---

## Decision — Real Volume Not Aggregated

O campo:

```text
real_volume
```

não é agregado em H1/H4 devido à inconsistência histórica observada.

---

## Added — Source Bar Tracking

Candles processados registram:

```text
source_bar_count

expected_bar_count

complete
```

---

## Added — H1 Completeness

Regra:

```text
H1 completo
=
4 candles M15
```

---

## Added — H4 Completeness

Regra:

```text
H4 completo
=
16 candles M15
```

---

## Decision — Preserve Incomplete Aggregated Bars

Buckets parcialmente preenchidos não são apagados.

Eles permanecem como:

```text
complete=False
```

para:

```text
audit

diagnostics

data quality
```

---

## Decision — Empty Buckets Are Removed

Buckets com:

```text
source_bar_count = 0
```

não são persistidos.

Isso evita criar candles artificiais durante períodos sem negociação.

---

## Added — H1 Dataset

Arquivo:

```text
data/processed/EURUSD/H1.parquet
```

Resultado:

```text
Candles:
72080

Complete:
72018

Incomplete:
62
```

Cobertura:

```text
2015-01-02 09:00 UTC
→
2026-08-07 23:00 UTC
```

---

## Added — H4 Dataset

Arquivo:

```text
data/processed/EURUSD/H4.parquet
```

Resultado:

```text
Candles:
18046

Complete:
17929

Incomplete:
117
```

Cobertura:

```text
2015-01-02 08:00 UTC
→
2026-08-07 20:00 UTC
```

---

## Added — H4 UTC Alignment

Fronteiras H4 atuais:

```text
00:00

04:00

08:00

12:00

16:00

20:00
```

em:

```text
UTC
```

---

## Decision — Daily Timeframe Deferred

D1 não será construído ainda.

Antes deve ser definida explicitamente a convenção de:

```text
daily boundary

timezone

broker/session close
```

Não será assumido automaticamente:

```text
00:00 UTC
```

como fronteira diária universal.

---

## Added — Automated Testing

Configurado:

```text
pytest
```

Arquivo:

```text
pytest.ini
```

com marker:

```text
integration
```

para testes que dependem do MetaTrader 5.

---

## Added — MarketData Tests

Foram implementados testes para:

```text
current quote

closed bar count

sorting

duplicate timestamps

UTC

OHLC

positive prices

tick volume

current candle exclusion
```

Total:

```text
9 tests
```

---

## Added — HistoricalData Tests

Testes para:

```text
file existence

non-empty dataset

unique timestamps

sorted timestamps

UTC

null values

OHLC

positive prices
```

Total:

```text
8 tests
```

---

## Added — TimeframeBuilder Tests

Testes para:

```text
H1 creation

H4 creation

H1 = 4 M15

H4 = 16 M15

H1 alignment

H4 alignment

UTC

OHLC integrity
```

Total:

```text
8 tests
```

---

## Test Result

Estado oficial do marco:

```text
25 collected

25 passed

0 failed
```

Ambiente observado:

```text
Python 3.14.5

pytest 9.1.1
```

Tempo observado:

```text
0.84s
```

Esse tempo não constitui requisito de performance.

---

## Added — Testing Philosophy

Definida estratégia para:

```text
Unit Tests

Integration Tests

Regression Tests futuros
```

Princípios:

```text
critical bugs create regression tests

time must be tested

costs must be tested

PnL must be manually verifiable

look-ahead prevention must be tested
```

---

## Added — Backtest Design

Criado:

```text
docs/10_BACKTEST_DESIGN.md
```

O BacktestEngine ainda não foi implementado.

O design foi documentado antecipadamente.

---

## Decision — Backtest Clock

O futuro BacktestEngine controlará:

```text
simulation_time
```

e funcionará inicialmente:

```text
bar-by-bar
```

---

## Decision — Signal Timing

Baseline:

```text
Signal on Close
```

---

## Decision — Execution Timing

Baseline:

```text
Execution on Next Available Open
```

Isso evita utilizar o mesmo fechamento simultaneamente como:

```text
dados para decisão
```

e:

```text
preço garantido de execução.
```

---

## Decision — No Look-Ahead

Strategy poderá utilizar apenas dados cujo:

```text
bar_close_time
<=
simulation_time
```

---

## Decision — Strategy Does Not Execute

Fluxo planejado:

```text
Strategy
   ↓
Signal
   ↓
Risk
   ↓
Order
   ↓
Execution
```

Não será permitido:

```text
Strategy
→
order_send()
```

---

## Decision — Signal / Order / Fill Separation

Conceitos independentes:

```text
Signal

Order

Fill
```

Isso prepara o sistema para futura execução Demo e possíveis rejeições/slippage.

---

## Decision — Single Position Baseline

Primeira versão do BacktestEngine utilizará:

```text
uma posição por vez
```

Estados:

```text
FLAT

LONG

SHORT
```

---

## Decision — No Pyramiding Baseline

Não serão suportados inicialmente:

```text
scale-in

pyramiding

multiple simultaneous entries
```

---

## Decision — No Automatic Reversal

Um sinal contrário não fará automaticamente:

```text
LONG → SHORT
```

A posição deverá ser encerrada antes de uma nova entrada oposta.

---

## Decision — Intrabar Ambiguity

Quando Stop e Take Profit forem ambos tocados dentro do mesmo candle e a sequência não puder ser determinada:

```text
WORST_CASE
```

será utilizado por padrão.

---

## Decision — Gap Through Stop

Se o preço abrir além do Stop em condição desfavorável:

```text
não assumir fill garantido no Stop.
```

A abertura pior será usada como referência antes da aplicação dos custos apropriados.

---

## Decision — Explicit Costs

O futuro BacktestEngine deverá utilizar:

```text
CostModel
```

separado da Strategy.

Custos planejados:

```text
spread

slippage

commission

swap
```

---

## Decision — Zero-Cost Backtest Classification

Configuração:

```text
spread = 0
slippage = 0
commission = 0
swap = 0
```

será permitida para testes de engenharia.

Resultados deverão ser classificados como:

```text
ZERO COST / IDEALIZED
```

---

## Decision — Dataset Raw Remains Immutable During Backtests

O futuro BacktestEngine não deverá modificar:

```text
data/raw/
```

durante experimentos.

---

## Added — Architecture Documentation

Criados:

```text
docs/01_PROJECT_OVERVIEW.md

docs/02_ARCHITECTURE.md

docs/03_ENVIRONMENT_SETUP.md

docs/04_MT5_INTEGRATION.md

docs/05_MARKET_DATA.md

docs/06_HISTORICAL_DATA.md

docs/07_DATA_QUALITY.md

docs/08_TESTING.md

docs/09_DATA_TRANSFORMATION.md

docs/10_BACKTEST_DESIGN.md

docs/11_ROADMAP.md
```

---

## Added — Project README

Criado/atualizado:

```text
README.md
```

contendo visão geral do projeto, arquitetura, status, dados, testes e roadmap.

---

## Added — Architecture Decision Records

Criado:

```text
DECISIONS.md
```

contendo decisões arquiteturais documentadas no formato ADR simplificado.

---

## Added — Project Roadmap

Criado:

```text
docs/11_ROADMAP.md
```

Fases definidas:

```text
F0 Research & Methodology

F1 Environment

F2 Market Data

F3 Historical Data

F4 Data Transformation

F5 Backtest Engine

F6 Strategy Research

F7 Risk Management

F8 Robustness & Validation

F9 Demo Execution

F10 Live Readiness
```

---

## Completed Phases

No marco:

```text
v0.1.0
```

estão concluídas:

```text
F0 ✅ Research & Methodology

F1 ✅ Environment

F2 ✅ Market Data

F3 ✅ Historical Data

F4 ✅ Data Transformation
```

---

## Next Phase

Próxima fase:

```text
F5 — Backtest Engine
```

Marco planejado:

```text
v0.2.0
```

---

# Known Limitations — v0.1.0

A versão atual possui limitações conhecidas.

## Data

```text
MetaQuotes-Demo é a fonte atual.

Spread histórico não é considerado custo definitivo.

Real Volume não é confiável como feature.

Existem gaps intraweek.

Não existe D1 padronizado.

Não existe dataset Bid/Ask persistente oficial.
```

---

## Backtesting

```text
BacktestEngine ainda não existe.

Não existem trades simulados oficiais.

Não existem métricas de Strategy.

Não existe CostModel implementado.
```

---

## Strategy

```text
Nenhuma Strategy está implementada
como componente oficial.
```

---

## Risk

```text
Risk Engine ainda não implementado.
```

---

## Execution

```text
Nenhum order_send.

Nenhuma execução Demo automatizada.

Nenhuma execução Live.
```

---

## Storage

```text
Parquet implementado.

SQLite ainda não implementado.

Dataset version/hash ainda não implementado.
```

---

## Reproducibility

Ainda faltam:

```text
dataset SHA256

formal dataset version

experiment manifest

git commit tracking por experimento
```

---

# Security Status — v0.1.0

Estado:

```text
READ ONLY
```

Configuração:

```env
TRADING_ENABLED=false
```

Ambiente:

```text
Demo
```

Execução externa:

```text
DISABLED / NOT IMPLEMENTED
```

---

# Quality Gate — v0.1.0

Antes de avançar para:

```text
F5
```

o projeto deve manter:

```powershell
pytest -v
```

com resultado:

```text
25 passed
0 failed
```

---

# Documentation Gate — v0.1.0

Documentação do marco:

```text
README.md                           ✅

docs/01_PROJECT_OVERVIEW.md         ✅
docs/02_ARCHITECTURE.md             ✅
docs/03_ENVIRONMENT_SETUP.md        ✅
docs/04_MT5_INTEGRATION.md          ✅
docs/05_MARKET_DATA.md              ✅
docs/06_HISTORICAL_DATA.md          ✅
docs/07_DATA_QUALITY.md             ✅
docs/08_TESTING.md                  ✅
docs/09_DATA_TRANSFORMATION.md      ✅
docs/10_BACKTEST_DESIGN.md          ✅
docs/11_ROADMAP.md                  ✅

DECISIONS.md                        ✅
CHANGELOG.md                        ✅
```

---

# v0.1.0 Definition of Done

```text
[x] Development Environment

[x] Virtual Environment

[x] MT5 Integration

[x] Demo Account Integration

[x] EURUSD Support

[x] MarketData

[x] Closed Candle Protection

[x] UTC

[x] HistoricalData

[x] Chunked Download

[x] M15 Historical Dataset

[x] Parquet

[x] Metadata

[x] Data Quality Analysis

[x] Gap Analysis

[x] Spread Analysis

[x] Tick Volume Analysis

[x] Real Volume Analysis

[x] TimeframeBuilder

[x] H1

[x] H4

[x] Incomplete Bar Detection

[x] Automated Tests

[x] 25 / 25 Tests Passing

[x] Architecture Documentation

[x] Backtest Design

[x] Roadmap

[x] Architecture Decisions

[x] Changelog
```

---

# Release Classification

```text
Version:
0.1.0

Codename:
Data & Infrastructure Foundation

Status:
DEVELOPMENT / RESEARCH

Trading Ready:
NO

Backtest Ready:
INFRASTRUCTURE READY,
ENGINE NOT IMPLEMENTED

Demo Execution Ready:
NO

Live Ready:
NO
```

---

# Next Release Target

```text
0.2.0
```

Codename:

```text
Backtesting Infrastructure
```

Primary objective:

> Implementar e validar um BacktestEngine determinístico, temporalmente correto e auditável antes de iniciar estratégias quantitativas reais.

---

# Changelog Policy

Mudanças futuras deverão ser registradas nas categorias:

```text
Added

Changed

Fixed

Deprecated

Removed

Security
```

quando apropriado.

---

# Versioning Policy

Estrutura:

```text
MAJOR.MINOR.PATCH
```

Exemplo:

```text
0.2.3
```

Durante o estágio inicial:

```text
0.x.x
```

indica que a arquitetura ainda está evoluindo rapidamente.

---

# Minor Version

Exemplo:

```text
0.1 → 0.2
```

representa novo marco relevante.

Exemplo:

```text
v0.2
=
Backtesting Infrastructure
```

---

# Patch Version

Exemplo:

```text
0.2.0 → 0.2.1
```

poderá representar:

```text
bug fix

teste adicional

correção documental

pequena melhoria
```

sem mudança conceitual significativa no marco.

---

# Breaking Changes

Durante o estágio:

```text
0.x
```

mudanças incompatíveis ainda podem ocorrer.

Mesmo assim, mudanças que alterem resultados históricos deverão ser claramente registradas.

Exemplos:

```text
mudança no execution timing

mudança no CostModel

mudança no PnL

mudança na política de Stop

mudança no resample
```

---

# Backtest Reproducibility Warning

Quando o BacktestEngine existir, qualquer mudança em:

```text
Engine

Strategy

Risk

Costs

Dataset

TimeframeBuilder
```

poderá alterar resultados.

Por isso o Changelog deverá registrar mudanças que afetem:

```text
comparabilidade entre experimentos.
```

---

# Current Snapshot

```text
FOREX v0.1.0
│
├── Research                  ✅
│
├── Environment               ✅
│
├── MT5                       ✅
│
├── Market Data               ✅
│
├── Historical Data           ✅
│
├── Data Quality              ✅
│
├── M15                       ✅
│
├── H1                        ✅
│
├── H4                        ✅
│
├── Testing                   ✅ 25/25
│
├── Documentation             ✅
│
├── Backtest Engine           ⬜
│
├── Strategies                ⬜
│
├── Risk Engine               ⬜
│
├── Execution                 ⬜
│
└── Demo Validation           ⬜
```

---

# Next

```text
FOREX v0.2.0

Backtesting Infrastructure
```

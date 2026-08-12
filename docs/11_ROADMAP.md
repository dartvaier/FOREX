# Roadmap

## 1. Objetivo

Este documento define o roadmap oficial da plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

O objetivo é organizar a evolução do projeto em fases claras, com:

- escopo;
- dependências;
- critérios de conclusão;
- entregáveis;
- riscos;
- ordem de implementação.

O projeto deve evoluir de forma incremental.

O princípio principal é:

> Nenhuma camada deve ser construída sobre uma base que ainda não foi suficientemente validada.

---

# 2. Visão Geral

O roadmap atual é:

```text
F0  Research & Methodology
          ↓
F1  Environment
          ↓
F2  Market Data
          ↓
F3  Historical Data
          ↓
F4  Data Transformation
          ↓
F5  Backtest Engine
          ↓
F6  Strategy Research
          ↓
F7  Risk Management
          ↓
F8  Robustness & Validation
          ↓
F9  Demo Execution
          ↓
F10 Live Readiness
```

---

# 3. Estado Atual

Status atual:

```text
F0  Research & Methodology      ✅ COMPLETE

F1  Environment                 ✅ COMPLETE

F2  Market Data                 ✅ COMPLETE

F3  Historical Data             ✅ COMPLETE

F4  Data Transformation         ✅ COMPLETE

F5  Backtest Engine             ✅ COMPLETE

F6  Strategy Research           ✅ COMPLETE BASELINE

F7  Risk Management             ✅ COMPLETE

F8  Robustness & Validation     ✅ COMPLETE

F9  Demo Execution              ✅ COMPLETE

F10 Live Readiness              🟡 INFRA READY / OPERATOR DECISION

---

# 4. Marco Atual

O projeto encontra-se no marco lógico:

```text
FOREX v0.5
```

Descrição:

```text
Robustness & Validation
```

Esse marco representa:

```text
ambiente configurado

MetaTrader 5 integrado

dados correntes funcionando

histórico coletado

dados auditados

M15 persistido

H1/H4 derivados

testes automatizados

documentação da base

BacktestEngine baseline

performance metrics básicas

strategy research baseline inicial

risk gate baseline

stop-based sizing inicial

regression tests F5
```

Não representa:

```text
trading bot completo

Strategy validada

Risk Engine pronto

execução de ordens
```

---

# 5. F0 — Research & Methodology

Status:

```text
COMPLETE
```

Objetivo:

> Definir como estratégias quantitativas serão pesquisadas e validadas antes da implementação.

---

# 6. Escopo F0

Foram estudadas famílias como:

```text
Trend Following

Time-Series Momentum

Volatility Breakout

Mean Reversion

Carry

Session-Based Strategies

Regime Detection

Multi-Timeframe Momentum
```

---

# 7. Princípios Definidos

A metodologia estabeleceu:

```text
hipótese antes do backtest

evidência separada de heurística

controle de look-ahead

controle de data snooping

custos explícitos

out-of-sample

robustez

demo antes de execução real
```

---

# 8. Classificação de Afirmações

A pesquisa utiliza as categorias:

```text
DEFINIÇÃO

EVIDÊNCIA

HEURÍSTICA

HIPÓTESE
```

Isso evita transformar regras experimentais em fatos.

---

# 9. Ordem Inicial de Estratégias

A ordem planejada para pesquisa é:

```text
1. Simple EMA Trend Following

2. Simple Volatility Breakout

3. Time-Series Momentum

4. Simple Mean Reversion

5. Asian Range Breakout

6. Carry

7. Regime Detection

8. Multi-Timeframe / modelos avançados
```

Essa ordem representa prioridade de engenharia.

Não representa expectativa de lucro.

---

# 10. Definition of Done — F0

```text
[x] metodologia de pesquisa definida

[x] riscos de overfitting documentados

[x] look-ahead documentado

[x] custos considerados parte obrigatória

[x] validação OOS definida

[x] famílias de estratégia priorizadas
```

---

# 11. F1 — Environment

Status:

```text
COMPLETE
```

Objetivo:

> Criar ambiente reproduzível para desenvolvimento da plataforma.

---

# 12. Ambiente Atual

Validado com:

```text
Windows

Python 3.14.5

MetaTrader5 5.0.6090

pytest 9.1.1
```

Ambiente virtual:

```text
.venv
```

---

# 13. Dependências Principais

```text
MetaTrader5

pandas

numpy

python-dotenv

matplotlib

pytest

pyarrow
```

---

# 14. Definition of Done — F1

```text
[x] Python configurado

[x] .venv funcionando

[x] dependências instaladas

[x] VS Code usando .venv

[x] MetaTrader 5 instalado

[x] conta Demo conectada

[x] pytest configurado

[x] .env criado

[x] .gitignore definido
```

---

# 15. F2 — Market Data

Status:

```text
COMPLETE
```

Objetivo:

> Criar uma camada segura entre o projeto e os dados correntes do MetaTrader 5.

---

# 16. Componentes F2

Implementados:

```text
broker/mt5_client.py

data/market_data.py
```

---

# 17. Funcionalidades

```text
MT5 initialize

shutdown

account info

symbol info

current tick

Bid

Ask

Point

Pip Size

current bar

closed bars
```

---

# 18. Regra Crítica

Dados destinados à Strategy:

```text
não incluem deliberadamente
o candle corrente.
```

A regra é protegida por teste automatizado.

---

# 19. Definition of Done — F2

```text
[x] conexão MT5

[x] EURUSD disponível

[x] Bid/Ask válidos

[x] Point validado

[x] Pip Size definido

[x] candles disponíveis

[x] candle corrente excluído

[x] timestamps UTC

[x] testes de integração
```

---

# 20. F3 — Historical Data

Status:

```text
COMPLETE
```

Objetivo:

> Criar uma base histórica persistente e auditável.

---

# 21. Dataset Atual

```text
EURUSD

M15

MetaQuotes-Demo
```

Cobertura:

```text
2015-01-02 09:00 UTC
→
2026-08-07 23:45 UTC
```

Quantidade:

```text
288223 candles
```

---

# 22. Persistência

Arquivo:

```text
data/raw/EURUSD/M15.parquet
```

Formato:

```text
Parquet
```

---

# 23. Coleta

O histórico é coletado em:

```text
chunks de 90 dias
```

Isso reduz problemas com requisições muito extensas.

---

# 24. Data Quality

Resultado estrutural:

```text
Duplicados:       0

Nulls:            0

OHLC inválidos:   0
```

---

# 25. Gaps

Identificados:

```text
659 gaps
```

Classificação:

```text
605 weekend

54 intraweek
```

Gaps não são preenchidos artificialmente.

---

# 26. Campos Auxiliares

Decisões:

```text
tick_volume
→ disponível com ressalvas

spread histórico
→ não utilizar como CostModel oficial

real_volume
→ não utilizar como feature
```

---

# 27. Definition of Done — F3

```text
[x] coleta histórica

[x] coleta em chunks

[x] UTC

[x] Parquet

[x] validação estrutural

[x] análise anual

[x] análise de gaps

[x] análise de spread

[x] análise de tick volume

[x] análise de real volume

[x] metadata
```

---

# 28. F4 — Data Transformation

Status:

```text
COMPLETE
```

Objetivo:

> Construir timeframes superiores de forma controlada a partir da fonte M15.

---

# 29. Timeframes

Pipeline:

```text
M15
 ├── H1
 └── H4
```

---

# 30. H1 Atual

```text
Total:
72080

Completos:
72018

Incompletos:
62
```

---

# 31. H4 Atual

```text
Total:
18046

Completos:
17929

Incompletos:
117
```

---

# 32. Completude

H1:

```text
4 M15
```

H4:

```text
16 M15
```

Campos:

```text
source_bar_count

expected_bar_count

complete
```

---

# 33. Regra Crítica

Candles incompletos:

```text
são preservados
```

mas:

```text
não serão utilizados
pela Strategy por padrão.
```

---

# 34. Definition of Done — F4

```text
[x] TimeframeBuilder

[x] H1

[x] H4

[x] OHLC aggregation

[x] tick_volume aggregation

[x] alinhamento UTC

[x] source_bar_count

[x] expected_bar_count

[x] complete

[x] preservação de incompletos

[x] testes automatizados
```

---

# 35. Quality Gate Atual

Antes de iniciar F5:

```text
pytest -v
```

Resultado esperado:

```text
25 passed
```

Estado atual:

```text
25 / 25 PASS
```

---

# 36. F5 — Backtest Engine

Status:

```text
COMPLETE
```

Próximo grande marco do projeto.

Versão lógica planejada:

```text
FOREX v0.2
```

---

# 37. Objetivo F5

> Criar um motor de backtesting determinístico, auditável e temporalmente correto antes de implementar estratégias reais.

---

# 38. Primeiro Princípio do Backtester

```text
No Look-Ahead
```

A Strategy só poderá utilizar informações disponíveis naquele instante histórico.

---

# 39. Modelo Baseline

Definido em:

```text
docs/10_BACKTEST_DESIGN.md
```

Baseline:

```text
bar-by-bar

Signal on Close

Execution on Next Open

Market Orders

uma posição por vez

sem pyramiding

sem reversal automático

custos explícitos

gaps preservados

candles incompletos excluídos

worst-case intrabar
```

---

# 40. Subfases F5

A implementação deverá ocorrer em etapas.

```text
F5.1 Core Models             ✅ COMPLETE

F5.2 Simulation Clock        ✅ COMPLETE

F5.3 Signal / Order / Fill   ✅ COMPLETE

F5.4 Position / Portfolio    ✅ COMPLETE

F5.5 CostModel               ✅ COMPLETE

F5.6 Stops / Targets         ✅ COMPLETE

F5.7 Trade Ledger            ✅ COMPLETE

F5.8 Performance             ✅ COMPLETE

F5.9 Regression Tests        ✅ COMPLETE
```

---

# 41. F5.1 — Core Models


Status:

```text
COMPLETE

```

---

# 42. F5.2 — Simulation Clock


Status:

```text
COMPLETE
```
---

# 43. F5.3 — Signal / Order / Fill

Status:

```text
COMPLETE

Fluxo:

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
   ↓
Fill
```

---

# 44. F5.4 — Portfolio

Implementar:

```text
cash

equity

position

realized PnL

unrealized PnL
```

---

# 45. F5.5 — CostModel

Baseline deverá possuir:

```text
spread

slippage

commission
```

Swap poderá entrar em etapa posterior caso não esteja pronto no primeiro baseline.

---

# 46. F5.6 — Stops e Targets

Implementar:

```text
Stop Loss

Take Profit

gap through stop

intrabar ambiguity
```

Policy baseline:

```text
WORST_CASE
```

---

# 47. F5.7 — Ledgers

Implementar:

```text
Signal Ledger

Order Ledger

Fill Ledger

Trade Ledger

Equity Curve
```

---

# 48. F5.8 — Performance

Primeiras métricas:

```text
Net Profit

Total Return

Maximum Drawdown

Trade Count

Win Rate

Average Win

Average Loss

Profit Factor

Expectancy
```

Depois:

```text
Sharpe

Sortino

CAGR

Recovery Factor
```

---

# 49. F5.9 — Regression Tests

Criar datasets artificiais pequenos.

Exemplo:

```text
10 candles conhecidos

sinais em horários fixos

entradas conhecidas

saídas conhecidas

PnL calculável manualmente
```

---

# 50. Testes Obrigatórios F5

No mínimo:

```text
no future access

signal time

order time

fill time

next-open execution

long PnL

short PnL

spread

commission

slippage

stop

take profit

ambiguous candle

gap through stop

cash

equity

final forced close
```

---

# 51. Definition of Done — F5

```text
[x] Clock implementado

[x] No look-ahead protegido

[x] Signal implementado

[x] Order implementado

[x] Fill implementado

[x] Position implementado

[x] Portfolio implementado

[x] CostModel implementado

[x] Stop Loss implementado

[x] Take Profit implementado

[x] Worst-case intrabar implementado

[x] Trade Ledger implementado

[x] Equity Curve implementada

[x] Métricas básicas implementadas

[x] Regression tests

[x] Resultado determinístico

[x] Documentação atualizada
```

---

# 52. F6 — Strategy Research

Status:

```text
IN PROGRESS
```

Iniciada após o fechamento da F5 baseline.

---

# 53. Objetivo F6

> Implementar hipóteses quantitativas de forma controlada sobre um BacktestEngine já validado.

---

# 54. Primeira Strategy

```text
Simple EMA Trend Following
```

Status:

```text
IMPLEMENTED BASELINE
```

Objetivo:

```text
engineering baseline
```

e não:

```text
estratégia final.
```

---

# 55. Motivo da EMA Strategy

É uma Strategy:

```text
simples

auditável

causal

fácil de testar

fácil de explicar
```

Isso a torna adequada para validar o ciclo completo.

---

# 56. Pipeline de Estratégia

Cada Strategy seguirá:

```text
Hypothesis
   ↓
Primary Specification
   ↓
Implementation
   ↓
Unit Tests
   ↓
Backtest
   ↓
Cost Stress
   ↓
Robustness
   ↓
Validation
```

---

# 57. Strategy Interface

A interface futura deverá ser comum.

Conceitualmente:

```python
strategy.on_bar(context)
```

retornando:

```text
Signal
```

---

# 58. Strategy Não Faz

```text
order_send

position sizing global

equity accounting

broker access direto

cost calculation
```

---

# 59. Ordem de Pesquisa

Após EMA baseline:

```text
Volatility Breakout      ✅ BASELINE TESTED

Time-Series Momentum     ✅ BASELINE TESTED

Mean Reversion           ✅ BASELINE TESTED

Asian Range Breakout     ✅ BASELINE TESTED

Carry                    ✅ BASELINE TESTED

Regime Detection         ✅ BASELINE TESTED

Multi-Timeframe          ✅ BASELINE TESTED
```

---

# 60. Definition of Done — F6 Inicial

Para cada Strategy:

```text
[x] hipótese registrada

[x] racional registrado

[x] parâmetros primários definidos

[x] código implementado

[x] unit tests

[x] backtest base

[x] custos

[x] trade log analisável

[x] sem look-ahead

[x] resultado histórico analisado

[x] resultado reproduzível
```

---

# 61. F7 — Risk Management

Status:

```text
COMPLETE
```

---

# 62. Objetivo F7

> Separar decisão de mercado da decisão de exposição financeira.

---

# 63. Risk Engine

Fluxo:

```text
Signal
  ↓
Risk Engine
  ↓
Approved / Rejected
  ↓
Order
```

---

# 64. Componentes Planejados

```text
Fixed Position Size

Risk Per Trade

Stop-Based Position Sizing

Max Exposure

Daily Loss Limit

Maximum Drawdown Protection

Volume Min/Max/Step

Kill Switch
```

---

# 65. Position Sizing

Modelo futuro:

```text
capital

risk %

stop distance

instrument specification
```

produzem:

```text
position size
```

Implementado no primeiro bloco F7:

```text
[x] implementation of RiskGate protocol

[x] VolumeRules

[x] FixedSizeRiskGate com validação de volume_step

[x] StopBasedRiskGate

[x] ExposureLimitRiskGate

[x] DailyLossRiskGate

[x] DrawdownRiskGate

[x] KillSwitchRiskGate

[x] entry_price + stop_loss metadata

risk_fraction

max_quantity opcional

max_notional opcional

max_daily_loss opcional

max_daily_loss_fraction opcional

[x] max_drawdown opcional

[x] max_drawdown_pct opcional

[x] kill()/reset() latch
```

---

# 66. Risk Invariants

Exemplos:

```text
lot nunca abaixo de volume_min

lot nunca acima de volume_max

lot respeita volume_step

risk nunca excede limite configurado

daily loss pode bloquear novas entradas

kill switch bloqueia execução
```

---

# 67. Definition of Done — F7

```text
[x] Risk Engine separado

[x] Fixed Size

[x] Risk %

[x] Stop-Based Sizing

[x] volume constraints

[x] exposure limits

[x] daily loss

[x] drawdown protection

[x] kill switch

[x] testes automatizados
```

---

# 68. F8 — Robustness & Validation

Status:

```text
COMPLETE
```

Essa fase é quantitativa, não apenas de engenharia.

Blocos implementados:

```text
cost stress no research runner
(--cost-multiplier 1.5 / 2.0)

sensibilidade local estruturada
(research/sweep.py --range/--values, um parametro por vez)

subperiod analysis padrao
(research/sweep.py --subperiods, 2015-17/2018-20/2021-23/2024-26)

periodos formais Dev/Val/OOS pre-registrados
(research/periods.py; dev 2015-20, val 2021-23, oos lockbox 2024-26)

lockbox guard mecanico
(--period oos exige --allow-oos explicito, roadmap 74)

stability analysis dev vs val
(--stability: deltas + consistencia de sinal)

resultados documentados
(docs/15_ROBUSTNESS.md: sweep + subperiods + stability + cost stress)
```

---

# 69. Objetivo F8

> Determinar se o resultado observado parece robusto ou apenas consequência do período/parâmetro escolhido.

---

# 70. Componentes

```text
Development Set

Validation Set

Out-of-Sample Lockbox

Sensitivity Tests

Cost Stress

Subperiod Analysis

Regime Analysis

Walk-Forward

Monte Carlo

Data-Snooping Controls
```

---

# 71. Parameter Sensitivity

Não buscar apenas:

```text
melhor parâmetro
```

Procurar:

```text
região estável
```

Exemplo:

```text
EMA 48
EMA 49
EMA 50
EMA 51
EMA 52
```

Se apenas:

```text
EMA 50
```

funcionar, há sinal de fragilidade.

---

# 72. Cost Stress

Obrigatório testar:

```text
base cost

1.5 × cost

2.0 × cost
```

---

# 73. Subperiod Analysis

Analisar períodos como:

```text
2015–2017

2018–2020

2021–2023

2024–2026
```

de acordo com o experimento.

O objetivo é verificar estabilidade temporal.

---

# 74. Out-of-Sample

O período OOS final deve funcionar como:

```text
lockbox
```

Ele não deve ser consultado repetidamente durante desenvolvimento.

---

# 75. Walk-Forward

Futuramente:

```text
train
 ↓
validate
 ↓
advance window
 ↓
repeat
```

Status:

```text
DONE — hipotese WF-01 testada e rejeitada (docs/18):
nenhum edge transferivel no tempo sob custos explicitos;
lockbox OOS permanece selado (nada passou no criterio).
```

---

# 76. Monte Carlo

Pode ser utilizado para estudar:

```text
trade sequence risk

drawdown distribution

path dependency
```

Não deve ser confundido com prova contra data snooping.

---

# 77. Advanced Robustness

Possíveis métodos futuros:

```text
Deflated Sharpe Ratio

PBO

CSCV
```

Somente após a infraestrutura básica estar estabilizada.

---

# 78. Definition of Done — F8

```text
[x] development period definido

[x] validation period definido

[x] OOS protegido

[x] sensitivity tests

[x] cost stress

[x] subperiod analysis

[x] stability analysis

[x] resultados documentados
```

---

# 79. F9 — Demo Execution

Status:

```text
COMPLETE
```

Blocos implementados:

```text
Execution Interface (execution/interface.py)
MT5Execution (execution/mt5_execution.py, ativado e validado em demo)
Order/Fill Validation | Broker State | Reconciliation
Logs (audit_log.py) | Monitoring (monitoring.py)
Broker/Demo Validation (broker_validation.py)
Execution Comparison (comparison.py)

Ativacao demo: 2026-08-10 (autorizacao explicita)
periodo de validacao: 5/5 round-trips, 100% within tolerance,
latencia media 231 ms, slippage 0.00 pips, 0 rejeicoes
```

---

# 80. Objetivo F9

> Validar o comportamento do sistema em tempo real sem utilizar capital real.

---

# 81. Ambiente

```text
MetaTrader 5

Demo Account
```

O sistema permanecerá:

```text
TRADING_ENABLED=false
```

até a Execution Layer estar pronta e explicitamente habilitada para Demo.

---

# 82. Execution Architecture

Fluxo:

```text
MarketData
    ↓
Strategy
    ↓
Risk
    ↓
MT5Execution
    ↓
MetaTrader 5 Demo
```

---

# 83. Componentes Necessários

Antes de Demo:

```text
Execution Interface      IMPLEMENTED
MT5Execution             IMPLEMENTED (adapter, nao ativado)
Order Validation         IMPLEMENTED
Fill Validation          IMPLEMENTED
Position Reconciliation  IMPLEMENTED
Broker State             IMPLEMENTED
Logs                     IMPLEMENTED
Monitoring               IMPLEMENTED
Broker/Demo Validation   IMPLEMENTED (engineering)
Kill Switch              IMPLEMENTED (F7)
```

---

# 84. Segurança

Antes de qualquer `order_send()`:

```text
validar conta Demo

validar servidor

validar símbolo

validar trade mode

validar quantity

validar Risk Engine

validar TRADING_ENABLED

validar kill switch
```

---

# 85. Demo ≠ Backtest

Durante Demo surgirão fatores como:

```text
spread real do momento

latência

requotes

slippage

connection errors

order rejection

broker constraints
```

Esses fatores não existem da mesma forma no backtest.

---

# 86. Objetivo da Demo

Comparar:

```text
expected execution
```

com:

```text
observed execution
```

---

# 87. Metrics da Demo

Registrar:

```text
signal_time

order_time

fill_time

expected_price

actual_price

spread

slippage

commission

latency

rejection
```

---

# 88. Definition of Done — F9

```text
[x] Execution Layer

[x] Demo-only validation

[x] trading flag

[x] kill switch

[x] broker validation

[x] order validation

[x] reconciliation

[x] monitoring

[x] logs

[x] execution comparison

[x] período de validação Demo concluído
```

---

# 89. F10 — Live Readiness

Status:

```text
IN PROGRESS
```

Blocos implementados:

```text
readiness review programatica (readiness/review.py)
risk limits (readiness/risk_limits.py)
safety helpers (readiness/safety.py)
operational procedures documentadas (docs/17_LIVE_READINESS.md)

demo validation concluida; trading flag permanece decisao explicita
do operador
```

Essa fase não significa automaticamente:

```text
começar a operar capital real.
```

Significa apenas avaliar se a infraestrutura está pronta para essa decisão.

---

# 90. Pré-Requisitos

Nenhuma execução real deve ser considerada antes de:

```text
Backtest robusto

OOS

Cost Stress

Risk Engine

Demo Validation

Execution Validation

Monitoring

Kill Switch

Operational Procedures
```

---

# 91. Live Readiness Review

Antes de qualquer capital real deve existir revisão específica de:

```text
risco por trade

risco diário

drawdown máximo

alavancagem

exposição

falhas de conexão

ordens duplicadas

broker downtime

dados incorretos

recovery procedures
```

---

# 92. Capital Inicial

Qualquer futura alocação real deve ser definida separadamente.

O saldo virtual atual da conta Demo:

```text
não define
```

o risco ou tamanho da futura operação real.

---

# 93. Live não é Objetivo Automático

É permitido que o projeto permaneça indefinidamente como:

```text
research platform

backtesting platform

demo platform
```

caso nenhuma Strategy atenda aos critérios necessários.

---

# 94. Princípio de Descarte

Uma Strategy pode ser descartada em qualquer fase.

Fluxo válido:

```text
Hypothesis
   ↓
Backtest
   ↓
FAILED
   ↓
DISCARD
```

Isso é um resultado científico válido.

---

# 95. Não Forçar Resultado

Não fazer:

```text
Strategy falha
   ↓
otimizar centenas de parâmetros
   ↓
encontrar uma combinação lucrativa
   ↓
declarar sucesso
```

O objetivo é testar hipóteses, não fabricar equity curves.

---

# 96. Milestones Lógicos

Planejamento atual:

```text
v0.1
Data & Infrastructure Foundation

v0.2
Backtesting Infrastructure

v0.3
Strategy Research Baseline

v0.4
Risk Management

v0.5
Robustness & OOS

v0.6
Demo Execution
```

Esses números podem evoluir conforme o projeto.

---

# 97. v0.1

Escopo:

```text
Environment

MT5 Integration

Market Data

Historical Data

Data Quality

Timeframe Builder

Testing

Documentation
```

---

# 98. v0.2

Escopo planejado:

```text
BacktestEngine

Clock

Signal

Order

Fill

Position

Portfolio

CostModel

Trade Ledger

Performance básico
```

---

# 99. v0.3

Escopo planejado:

```text
Strategy Interface

EMA Baseline

Volatility Breakout

TSM

initial research framework
```

---

# 100. v0.4

Escopo:

```text
Risk Engine

position sizing

risk limits

kill switch
```

---

# 101. v0.5

Escopo:

```text
Validation

OOS

Walk-Forward

Cost Stress

Robustness
```

---

# 102. v0.6

Escopo:

```text
MT5Execution

Demo Trading

Monitoring

Reconciliation
```

---

# 103. D1 Future

Daily candles ainda não fazem parte da pipeline atual.

Antes de implementar D1 é necessário definir:

```text
daily boundary

timezone

broker convention
```

---

# 104. Multiple Symbols

Após EURUSD estar estabilizado:

```text
GBPUSD   [x] 288k M15 + H1/H4 + backtest
USDJPY   [x] coleta ok; conversao de moeda RESOLVIDA (docs/22)
USDCHF   [x] coleta ok + backtest
AUDUSD   [x] coleta ok + backtest
USDCAD   [x] coleta ok + backtest
NZDUSD   [x] coleta ok + backtest
crosses  [ ] fase posterior
```

Status: dados completos; primeira leitura dev (docs/21): TODOS os
19 backtests (6 pares x 3 estrategias + USDJPY) negativos — nenhum
par tem edge com custos; sem motivacao para val/OOS multi-par por
enquanto. Conversao de moeda quote→USD implementada (docs/22).

---

# 105. Multi-Asset Não é Prioridade Atual

Antes:

```text
single symbol correto
```

Depois:

```text
multi-symbol.
```

---

# 106. Multi-Timeframe Runtime

DONE — auditoria 2026-08-10 (docs/20): a sincronizacao runtime
M15/H1/H4 ja esta implementada no BacktestEngine
(BacktestContextBuilder, por timestamp apos fechamento, nunca por
indice). Evidencia: tests/test_backtest_multitimeframe.py + as
strategies MULTI-TIMEFRAME-MOMENTUM e o filtro RF-01 (H4) que a
usam em producao. Nenhuma mudanca necessaria.

---

# 107. Feature Engineering

Uma futura camada poderá organizar:

```text
returns

EMA

ATR

RSI

ADX

volatility

session features
```

Essa camada ainda não existe formalmente.

---

# 108. Machine Learning

Machine Learning não é prioridade.

Só deverá ser investigado depois de:

```text
backtester confiável

baseline simples

controle OOS

controle de overfitting

feature pipeline confiável
```

---

# 109. HMM / Advanced Regime Models

Modelos como:

```text
HMM
```

podem ser investigados futuramente.

Mas primeiro devem existir baselines simples de regime.

---

# 110. Banco de Dados

A arquitetura futura prevê:

```text
SQLite
```

principalmente para:

```text
experiments

trades

execution logs

metadata

runtime state
```

Séries históricas permanecem em:

```text
Parquet
```

por enquanto.

---

# 111. Parquet vs SQLite

Política conceitual:

```text
Parquet
→ grandes séries históricas

SQLite
→ dados relacionais / operacionais
```

---

# 112. Experiment Tracking

Futuramente cada backtest deverá produzir:

```text
experiment_id

dataset

strategy

parameters

costs

risk

metrics

git commit
```

---

# 113. Dataset Versioning

Planejado:

```text
SHA256

dataset_version

collection_timestamp
```

Isso aumentará a reprodutibilidade.

---

# 114. CI/CD

Futuro:

```text
GitHub Actions
```

para:

```text
unit tests

linting

regression tests
```

Testes MT5 poderão exigir runner Windows específico.

---

# 115. Logging

Migrar gradualmente de:

```text
print()
```

para:

```text
logging
```

nos componentes permanentes.

---

# 116. Monitoring

Na fase Demo:

```text
connection state

strategy state

position state

PnL

risk limits

execution errors
```

deverão ser monitorados.

---

# 117. Kill Switch

O Kill Switch é requisito obrigatório antes da execução.

Deve existir independentemente da Strategy.

---

# 118. Documentation Policy

Cada fase deverá atualizar:

```text
README

docs/

DECISIONS.md

CHANGELOG.md
```

quando necessário.

---

# 119. Decision Records

Mudanças arquiteturais importantes devem ser registradas em:

```text
DECISIONS.md
```

Exemplos:

```text
UTC

Parquet

Next Open execution

Worst-case ambiguous candle

No artificial gap filling
```

---

# 120. Changelog

Toda mudança relevante de marco deve ser registrada em:

```text
CHANGELOG.md
```

---

# 121. Definition of Done Global

Uma funcionalidade crítica não é considerada concluída apenas porque:

```text
"funcionou uma vez"
```

Critério:

```text
implementada

testada

documentada

reproduzível

integrada sem quebrar testes existentes
```

---

# 122. Test Gate Global

Antes de avançar de fase:

```powershell
pytest -v
```

deve permanecer verde.

Regressões precisam ser investigadas antes de adicionar novas funcionalidades.

---

# 123. Current Test Gate

Estado atual:

```text
1065 tests

1065 passed

0 failed
```

---

# 124. Data Gate Global

Nenhuma Strategy deverá receber:

```text
dados não validados

timestamps desconhecidos

candle aberto

candles agregados incompletos
```

por padrão.

---

# 125. Execution Gate Global

Nenhuma ordem externa deverá ser possível antes de:

```text
Execution Layer implementada

Risk Engine implementado

Demo validation

trading flag

kill switch
```

---

# 126. Pesquisa e Engenharia

O roadmap mantém duas linhas paralelas:

```text
Research
```

e:

```text
Engineering
```

A pesquisa pergunta:

```text
há edge?
```

A engenharia pergunta:

```text
o teste do edge é confiável?
```

As duas são necessárias.

---

# 127. Ordem de Prioridade

A ordem atual é:

```text
Correctness

Reproducibility

Auditability

Risk

Robustness

Performance

Complexity
```

Velocidade de execução não deve ser priorizada sobre correção.

---

# 128. Roadmap Resumido

```text
        RESEARCH
           ✅
            │
            ▼
       ENVIRONMENT
           ✅
            │
            ▼
       MARKET DATA
           ✅
            │
            ▼
      HISTORICAL DATA
           ✅
            │
            ▼
   DATA TRANSFORMATION
           ✅
            │
            ▼
      BACKTEST ENGINE
           ✅
            │
            ▼
       STRATEGIES
           ✅
            │
            ▼
       RISK ENGINE
           ✅
            │
            ▼
 ROBUSTNESS / OOS
           ✅
            │
            ▼
      DEMO EXECUTION
           ✅
            │
            ▼
     LIVE READINESS
           🟡
```

---

# 129. Próxima Ação Técnica

Estado tecnico atual:

```text
F0-F9 completos.
F10 com infraestrutura pronta.
Busca de edge encerrada nas hipoteses atuais.
```

A proxima acao tecnica deve ser escolhida explicitamente entre:

```text
CI/CD
dataset versioning
experiment tracking
nova hipotese pre-registrada
melhoria operacional de demo
nenhuma acao, manter research/demo
```

---

# 130. Próxima Ação de Documentação

Qualquer nova hipotese ou evolucao estrutural deve atualizar:

```text
README.md

docs/12_STRATEGY_RESEARCH.md ou documento dedicado

docs/11_ROADMAP.md

CHANGELOG.md
```

---

# 131. Estado do Roadmap

Marco atual:

```text
FOREX v0.6

MT5Execution / Demo Trading / Monitoring / Reconciliation
```

Status:

```text
F0  ✅  F1  ✅  F2  ✅  F3  ✅
F4  ✅  F5  ✅  F6  ✅  F7  ✅
F8  ✅  F9  ✅  F10 🟡 INFRA READY
```

Pendencias F10 (nao bloqueiam pesquisa; decisao de capital real e
separada, secao 92):

```text
Live Readiness Review formal (secao 91) — DONE, docs/17 secao 10
Decisao de capital real — operador, nunca automatica
```

Itens futuros:

```text
Walk-Forward (75) — DONE (docs/18): 3 baselines REJECT
Multiple Symbols (104) — dados 6 majors + 19 backtests (docs/21)
Multi-Timeframe Runtime (106) — DONE (docs/20)
Conversao de moeda quote->USD — DONE (docs/22)
Busca de edge — ENCERRADA (docs/24, roadmap §93: research/demo)
Monte Carlo (76) | DSR/PBO/CSCV (77) | D1 (103)
Feature Engineering (107) | ML (108) | HMM (109)
Banco de Dados (110) | Experiment Tracking (112)
Dataset Versioning (113) | CI/CD (114)
```

Conversao de moeda quote->USD —
   DONE (docs/22 + hardening MC-01..05, docs/25)
Hardening pos-auditoria (docs/25) — DONE 2026-08-12:
   v0.6.1 Execution Safety (ES-01..05)
   v0.6.2 Risk Composition (RC-01..02)
   v0.6.3 Multi-Currency Financial Integrity (MC-01..05)
   v0.6.4 Readiness & Audit (RA-01..07)
CI (RA-07) — GitHub Actions pytest non-integration
Novo programa de pesquisa ABERTO (docs/26, 2026-08-12):
   hipoteses H01-H07 registradas
H03 (volatility surprise) — ESTAGIO 1 REJECTED (docs/26 §11):
   retorno condicional nulo nas janelas 40/60/80; slot 00:00
   (~1.98 pips brutos) abaixo do custo round-trip 3.7 pips
H05/H06 (choques eficientes/ineficientes) — ESTAGIO 1 REJECTED
   (docs/26 §13): DE nao adiciona poder vs controles; H05 ~0 com 3
   inversoes de sinal por ano; H06 negativo (oposto da hipotese)
H01 (falso rompimento da faixa asiatica) — ESTAGIO 1 REJECTED
   (docs/26 §15): signed ~0 em h1-8 e buffers 0.10/0.15/0.20; h8
   levemente positivo (continuacao, nao reversao); sinal inverte 4x
   por ano; midpoint sempre tocado em 8 barras (nao discrimina)
H02 (handoff Asia-Londres condicionado ao formato) — ESTAGIO 1
   REJECTED (docs/26 §17): continuation_up negativo em todos os
   cenarios de fronteira e 10/12 anos (OPOSTO da hipotese); demais
   grupos instaveis entre horizontes e anos; amostras 5-31/ano
Proxima hipotese ativa: H04 (compressao + atividade, docs/26 §4
   prioridade 3) — pre-registro obrigatorio antes de qualquer
   backtest
Decisao de capital real (§92) permanece separada, sob o operador.
---

# 132. Regra Final

> O projeto só avança quando a fase anterior possui base suficiente para que os resultados da próxima sejam interpretáveis e reproduzíveis.

O próximo arquivo é:

```text
DECISIONS.md
```

Nele serão registradas as decisões arquiteturais que devem sobreviver ao contexto de uma única sessão de desenvolvimento.

# FOREX Algorithmic Trading Research Platform

Plataforma de pesquisa e desenvolvimento de estratégias algorítmicas para Forex, construída em Python e integrada ao MetaTrader 5.

O projeto prioriza integridade de dados, reprodutibilidade, controle temporal e prevenção de erros como look-ahead bias, uso de candles ainda em formação e modelagem incorreta de custos de execução.

> Status atual: F7 - Risk Management em andamento após oito hipóteses baseline testadas na F6.

---

## Status Do Projeto

| Fase | Descrição | Status |
|---|---|---|
| F0 | Pesquisa e metodologia | Concluída |
| F1 | Ambiente de desenvolvimento | Concluída |
| F2 | Market Data Layer | Concluída |
| F3 | Historical Data Layer | Concluída |
| F4 | Data Transformation | Concluída |
| F5 | Backtest Engine | Concluída |
| F6 | Strategy Research | Concluída no baseline inicial |
| F7 | Risk Engine | Em andamento |
| F8 | Robustness & Validation | Não iniciada |
| F9 | Demo Execution | Não iniciada |

---

## O Que Já Existe

- Integração read-only com MetaTrader 5.
- Coleta e persistência de histórico em Parquet.
- Dataset principal `EURUSD M15` auditado.
- Construção de timeframes derivados `H1` e `H4`.
- BacktestEngine determinístico, bar-by-bar e sem look-ahead.
- Modelos de `Signal`, `Order`, `Fill`, `Position` e `Trade`.
- Ledgers de sinais, ordens, fills, trades e equity.
- CostModel explícito com spread, slippage e comissão.
- RiskGate com fixed size, validação de volume, sizing baseado em stop, limites de exposição e daily loss guard.
- Stop Loss, Take Profit, gap-through-stop e política worst-case intrabar.
- Métricas básicas de performance.
- Primeira estratégia baseline: `SimpleEmaTrendStrategy`.
- Segunda hipótese simples: `VolatilityBreakoutStrategy`.
- Terceira hipótese simples: `TimeSeriesMomentumStrategy`.
- Quarta hipótese simples: `SimpleMeanReversionStrategy`.
- Quinta hipótese simples: `AsianRangeBreakoutStrategy`.
- Sexta hipótese simples: `SimpleCarryStrategy`.
- Sétima hipótese simples: `SimpleRegimeDetectionStrategy`.
- Oitava hipótese simples: `MultiTimeframeMomentumStrategy`.

---

## Stack

- Windows
- Python 3.14.5
- MetaTrader 5
- MetaTrader5 Python API
- pandas
- NumPy
- PyArrow
- python-dotenv
- matplotlib
- pytest
- Git

Versão validada do pacote MetaTrader5:

```text
MetaTrader5 5.0.6090
```

---

## Mercado Inicial

O primeiro mercado utilizado no desenvolvimento é:

| Item | Valor |
|---|---|
| Mercado | Forex |
| Símbolo | EURUSD |
| Fonte | MetaQuotes-Demo |
| Digits | 5 |
| Point | 0.00001 |
| Pip | 0.00010 |
| Points / Pip | 10 |
| Contract Size | 100000 |
| Volume mínimo | 0.01 |
| Volume step | 0.01 |

Esses valores são obtidos dinamicamente através do MetaTrader 5 e não devem ser tratados como universais para todos os símbolos.

---

## Arquitetura

```text
MetaTrader 5
    |
    v
MT5Client
    |
    +--> MarketData
    |
    +--> HistoricalData --> Parquet
                             |
                             v
                       TimeframeBuilder
                             |
                             +--> H1
                             +--> H4

Validated Historical Data
    |
    v
BacktestEngine
    |
    +--> Strategy
    +--> Risk Gate
    +--> CostModel
    +--> Execution
    +--> Portfolio
    +--> Ledgers
    +--> Performance
```

---

## Estrutura Principal

```text
FOREX/
├── backtest/
├── broker/
├── config/
├── data/
│   ├── raw/EURUSD/M15.parquet
│   ├── processed/EURUSD/H1.parquet
│   ├── processed/EURUSD/H4.parquet
│   └── metadata/
├── docs/
├── execution/
├── monitoring/
├── research/
├── risk/
├── strategy/
├── tests/
├── CHANGELOG.md
├── DECISIONS.md
├── README.md
├── requirements.txt
└── pytest.ini
```

---

## Regras Temporais

Todo o sistema utiliza UTC como timezone interno.

Isso inclui:

- candles;
- ticks;
- histórico;
- datasets processados;
- timestamps utilizados pelo backtester.

Estratégias recebem apenas dados historicamente disponíveis no momento da decisão.

No MetaTrader 5:

```text
posição 0 = barra mais recente/corrente
posição 1 = barra anterior
```

A camada `MarketData` usa somente candles fechados para dados destinados às estratégias.

---

## Dataset Histórico Principal

Dataset bruto atual:

| Item | Valor |
|---|---|
| Símbolo | EURUSD |
| Timeframe | M15 |
| Fonte | MetaQuotes-Demo |
| Formato | Parquet |
| Timezone | UTC |
| Primeiro candle | 2015-01-02 09:00:00 UTC |
| Último candle | 2026-08-07 23:45:00 UTC |
| Quantidade | 288223 candles |
| Arquivo | `data/raw/EURUSD/M15.parquet` |

Qualidade do dataset M15:

| Checagem | Resultado |
|---|---:|
| Duplicados | 0 |
| Valores nulos | 0 |
| OHLC inválidos | 0 |
| Gaps totais | 659 |
| Weekend gaps | 605 |
| Intraweek gaps | 54 |

Gaps não são preenchidos artificialmente. A descontinuidade original dos dados é preservada.

---

## Timeframes Derivados

Os timeframes superiores são construídos a partir do M15.

```text
M15
├── H1
└── H4
```

Resumo atual:

| Timeframe | Arquivo | Candles | Completos | Incompletos |
|---|---|---:|---:|---:|
| H1 | `data/processed/EURUSD/H1.parquet` | 72080 | 72018 | 62 |
| H4 | `data/processed/EURUSD/H4.parquet` | 18046 | 17929 | 117 |

Candles incompletos são preservados para rastreabilidade, mas estratégias e backtests devem usar apenas candles completos salvo quando houver motivo explícito para outra política.

---

## Backtesting

O BacktestEngine baseline implementa:

- simulação bar-by-bar;
- signal on close;
- execution on next open;
- market orders;
- uma posição por vez;
- sem pyramiding;
- sem reversal automático;
- custos explícitos;
- gaps preservados;
- stops e targets protetivos;
- worst-case intrabar;
- fechamento forçado no fim do backtest;
- resultado consolidado em `BacktestResult`.

Métricas básicas:

- net profit;
- total return;
- max drawdown;
- trade count;
- win rate;
- average win;
- average loss;
- profit factor;
- expectancy.

---

## Strategy Research

A F6 começou com:

```text
Simple EMA Trend Following
```

Regra inicial:

- EMA rápida cruza acima da EMA lenta: `ENTER_LONG`;
- EMA rápida cruza abaixo da EMA lenta: `EXIT`;
- sem cruzamento ou warm-up: `HOLD`.

Parâmetros baseline:

```text
fast_period = 20
slow_period = 50
symbol = EURUSD
```

Resultado histórico inicial em `EURUSD M15`:

| Configuração | Trades | Net Profit | Max Drawdown | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|
| Zero-cost | 2715 | -81.94 | 232.05 | 0.976041 | 9918.06 |
| Custos explícitos | 2715 | -1086.49 | 1115.19 | 0.738059 | 8913.51 |

Esse resultado não descarta trend following como família. Ele apenas indica que esta especificação simples, nesses parâmetros e nesse dataset, não mostrou edge suficiente.

Segunda hipótese testada:

```text
Volatility Breakout
```

Resultado histórico inicial em `EURUSD M15`:

| Configuração | Trades | Net Profit | Max Drawdown | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|
| Zero-cost | 4336 | -541.31 | 594.00 | 0.873042 | 9458.69 |
| Custos explícitos | 4336 | -2145.63 | 2159.55 | 0.599219 | 7854.37 |

Essa especificação primária também não mostrou edge.

Terceira hipótese testada:

```text
Time-Series Momentum
```

Resultado histórico inicial em `EURUSD M15`:

| Configuração | Trades | Net Profit | Max Drawdown | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|
| Zero-cost | 2674 | 175.01 | 183.73 | 1.063166 | 10175.01 |
| Custos explícitos | 2674 | -814.37 | 845.84 | 0.765704 | 9185.63 |

Essa hipótese mostrou sinal bruto em zero-cost, mas ainda não sobreviveu aos custos explícitos baseline.

Quarta hipótese testada:

```text
Simple Mean Reversion
```

Resultado histórico inicial em `EURUSD M15`:

| Configuração | Trades | Net Profit | Max Drawdown | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|
| Zero-cost | 6568 | 128.39 | 131.39 | 1.027958 | 10128.39 |
| Custos explícitos | 6568 | -2301.77 | 2306.19 | 0.590060 | 7698.23 |

Essa hipótese também mostrou sinal bruto em zero-cost, mas o número alto de trades tornou o resultado muito sensível aos custos.

Quinta hipótese testada:

```text
Asian Range Breakout
```

Resultado histórico inicial em `EURUSD M15`:

| Configuração | Trades | Net Profit | Max Drawdown | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|
| Zero-cost | 2972 | -259.80 | 382.75 | 0.949656 | 9740.20 |
| Custos explícitos | 2972 | -1359.44 | 1446.21 | 0.762751 | 8640.56 |

Essa configuração baseline não mostrou edge bruto suficiente nem em zero-cost. Com custos explícitos, a perda aumentou de forma relevante.

Sexta hipótese testada:

```text
Simple Carry
```

Resultado histórico inicial em `EURUSD M15`:

| Configuração | Trades | Net Profit | Max Drawdown | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|
| Zero-cost | 1 | 48.38 | 251.03 | inf | 10048.38 |
| Custos explícitos | 1 | 48.01 | 251.03 | inf | 10048.01 |

Esse teste usa apenas um proxy direcional estático de carry. Ele não inclui accrual de swap ou curva histórica de juros, então ainda não representa uma estratégia de carry completa.

Sétima hipótese testada:

```text
Simple Regime Detection
```

Resultado histórico inicial em `EURUSD M15`:

| Configuração | Trades | Net Profit | Max Drawdown | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|
| Zero-cost | 2681 | -100.64 | 126.20 | 0.967062 | 9899.36 |
| Custos explícitos | 2681 | -1092.61 | 1096.87 | 0.704169 | 8907.39 |

Esse filtro simples de regime ficou próximo do zero sem custos, mas não sobreviveu aos custos explícitos.

Oitava hipótese testada:

```text
Multi-Timeframe Momentum
```

Resultado histórico inicial em `EURUSD M15` com contexto `H1/H4`:

| Configuração | Trades | Net Profit | Max Drawdown | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|
| Zero-cost | 6838 | -289.52 | 422.58 | 0.935529 | 9710.48 |
| Custos explícitos | 6838 | -2819.58 | 2847.70 | 0.554227 | 7180.42 |

Esse baseline validou a infraestrutura multi-timeframe sem look-ahead, mas a regra inicial operou demais e não mostrou edge.

---

## Testes

Suíte atual:

```text
830 passed
```

Comando:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Áreas cobertas:

- market data;
- historical data;
- timeframe builder;
- backtest models;
- clock e context;
- signal/order/fill pipeline;
- portfolio e custos;
- protective exits;
- ledgers;
- performance;
- regression tests;
- strategy research baselines;
- multi-timeframe context availability;
- risk gate and stop-based sizing.
- exposure limit risk gate.
- daily loss risk gate.

---

## Ambiente

Criar ambiente virtual:

```powershell
python -m venv .venv
```

Ativar no PowerShell:

```powershell
.\.venv\Scripts\activate
```

Instalar dependências:

```powershell
pip install -r requirements.txt
```

---

## Segurança

O projeto ainda não executa ordens reais.

Nesta fase:

```text
TRADING_ENABLED=false
```

Antes de qualquer execução futura deverão existir:

- validação em backtest;
- validação out-of-sample;
- testes de custos;
- gerenciamento de risco;
- limites de perda;
- kill switch;
- validação em conta demo.

---

## Documentação

Documentos principais:

- `docs/01_PROJECT_OVERVIEW.md`
- `docs/02_ARCHITECTURE.md`
- `docs/03_ENVIRONMENT_SETUP.md`
- `docs/04_MT5_INTEGRATION.md`
- `docs/05_MARKET_DATA.md`
- `docs/06_HISTORICAL_DATA.md`
- `docs/07_DATA_QUALITY.md`
- `docs/08_TESTING.md`
- `docs/09_DATA_TRANSFORMATION.md`
- `docs/10_BACKTEST_DESIGN.md`
- `docs/11_ROADMAP.md`
- `docs/12_STRATEGY_RESEARCH.md`
- `docs/13_RESEARCH_RUNNER.md`
- `docs/14_RISK_MANAGEMENT.md`
- `DECISIONS.md`
- `CHANGELOG.md`

---

## Próximos Passos

1. Implementar drawdown guard.
2. Definir kill switch do backtest/demo.
3. Preparar portfolio-level risk.
4. Manter todos os backtests reproduzíveis antes de qualquer Demo.

# Strategy Research

## 1. Objetivo

Este documento registra a fase:

```text
F6 - Strategy Research
```

O objetivo da F6 e implementar hipoteses quantitativas de forma controlada sobre o BacktestEngine baseline.

Uma strategy aparentemente lucrativa nao prova edge.

Uma strategy ruim tambem nao invalida a infraestrutura.

Cada strategy deve separar:

```text
hipotese

racional

regra primaria

implementacao

testes

custos

resultado
```

---

## 2. Strategy Baseline Atual

```text
Simple EMA Trend Following
```

Status:

```text
IMPLEMENTED BASELINE
```

Arquivo:

```text
strategy/ema_trend.py
```

Testes:

```text
tests/test_strategy_ema_trend.py
```

---

## 3. Hipotese

Classificacao:

```text
HIPOTESE
```

Hipotese primaria:

```text
Quando a EMA rapida cruza acima da EMA lenta, o mercado pode estar entrando em regime de alta suficiente para justificar uma posicao long.
```

Hipotese de saida:

```text
Quando a EMA rapida cruza abaixo da EMA lenta, a condicao primaria de tendencia long deixa de existir.
```

Esta hipotese ainda nao representa evidencia de lucratividade.

---

## 4. Racional

A Simple EMA Trend Following foi escolhida como primeira strategy porque e:

```text
simples

auditavel

causal

facil de testar

adequada para validar o ciclo completo da plataforma
```

O objetivo inicial e engineering baseline.

Nao e uma strategy final.

---

## 5. Regra Primaria

Parametros baseline:

```text
fast_period = 20

slow_period = 50

symbol = EURUSD
```

Regras:

```text
fast EMA cruza acima da slow EMA
-> ENTER_LONG

fast EMA cruza abaixo da slow EMA
-> EXIT

sem cruzamento
-> HOLD
```

Warm-up:

```text
len(closed_bars) < slow_period + 1
-> HOLD
```

---

## 6. Regras de Engenharia

A Strategy:

```text
usa apenas BacktestContext

usa apenas closed_bars

nao acessa DataFrame

nao acessa broker

nao cria ordens

nao calcula custos

nao calcula tamanho de posicao

nao controla equity
```

O BacktestEngine continua responsavel por:

```text
order creation

risk gate

execution

portfolio

ledgers

performance
```

---

## 7. Testes Implementados

Cobertura inicial:

```text
parameter validation

warm-up

cross above

cross below

no cross

signal timestamp

strategy identity

BacktestEngine zero-cost

BacktestEngine explicit-cost
```

Os testes utilizam series artificiais pequenas para validar a regra antes de qualquer interpretacao de resultado historico real.

---

## 8. Proximo Passo

Rodar analises de robustez e sensibilidade local sobre a Simple EMA Trend Following.

---

## 9. Backtest Historico Inicial

Dataset:

```text
EURUSD M15

2015-01-02 09:00:00 UTC
ate
2026-08-07 23:45:00 UTC

288223 candles
```

Parametros:

```text
fast_period = 20

slow_period = 50

fixed_quantity = 0.01 lot

initial_capital = 10000.00
```

Resultado zero-cost:

```text
trades:              2715
net_profit:          -81.94
total_return_pct:    -0.8194
max_drawdown:        232.05
max_drawdown_pct:    2.2996
win_rate:            29.2449
profit_factor:       0.976041
average_trade:       -0.0302
final_equity:        9918.06
```

Resultado com custos explicitos:

```text
spread_pips:                  2.0
slippage_pips:                0.5
commission_per_lot_per_side:  3.50

trades:              2715
net_profit:          -1086.49
total_return_pct:    -10.8649
max_drawdown:        1115.19
max_drawdown_pct:    11.1316
win_rate:            26.0037
profit_factor:       0.738059
average_trade:       -0.4002
final_equity:        8913.51
```

Observacao inicial:

```text
A EMA baseline nao apresentou edge no primeiro backtest historico.

O resultado zero-cost ja ficou levemente negativo.

Com custos explicitos, a deterioracao foi material.
```

Interpretacao:

```text
Este resultado nao descarta trend following como familia.

Ele apenas indica que esta especificacao primaria simples, nestes parametros e neste dataset, nao e candidata suficiente sem novas evidencias.
```

---

## 10. Proximo Passo Detalhado

Rodar a Simple EMA Trend Following com pequenas variacoes controladas:

```text
EMA 10 / 30

EMA 20 / 50

EMA 50 / 200
```

Depois disso, registrar:

```text
periodo testado

parametros

custos

trade count

net profit

drawdown

win rate

profit factor

observacoes
```

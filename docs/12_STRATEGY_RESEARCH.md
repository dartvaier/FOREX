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

## 8. Sensibilidade Local Inicial

Objetivo:

```text
Verificar se a conclusao inicial da EMA 20/50 muda em janelas simples predefinidas.
```

Importante:

```text
Isto nao e otimizacao.

As combinacoes foram escolhidas antes da leitura dos resultados.
```

Dataset:

```text
EURUSD M15

2015-01-02 09:00:00 UTC
ate
2026-08-07 23:45:00 UTC

288223 candles
```

Parametros comuns:

```text
fixed_quantity = 0.01 lot

initial_capital = 10000.00
```

Resultado zero-cost:

| EMA fast/slow | Trades | Net Profit | Return % | Max DD | Max DD % | Win Rate % | Profit Factor | Avg Trade | Final Equity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 / 30 | 5182 | -284.67 | -2.8467 | 410.11 | 4.0789 | 27.1903 | 0.938190 | -0.0549 | 9715.33 |
| 20 / 50 | 2715 | -81.94 | -0.8194 | 232.05 | 2.2996 | 29.2449 | 0.976041 | -0.0302 | 9918.06 |
| 50 / 200 | 822 | -18.09 | -0.1809 | 226.25 | 2.2325 | 31.3869 | 0.989912 | -0.0220 | 9981.91 |

Resultado com custos explicitos:

```text
spread_pips = 2.0
slippage_pips = 0.5
commission_per_lot_per_side = 3.50
```

| EMA fast/slow | Trades | Net Profit | Return % | Max DD | Max DD % | Win Rate % | Profit Factor | Avg Trade | Final Equity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 / 30 | 5182 | -2202.01 | -22.0201 | 2212.09 | 22.1209 | 23.0992 | 0.635470 | -0.4249 | 7797.99 |
| 20 / 50 | 2715 | -1086.49 | -10.8649 | 1115.19 | 11.1316 | 26.0037 | 0.738059 | -0.4002 | 8913.51 |
| 50 / 200 | 822 | -322.23 | -3.2223 | 376.94 | 3.7612 | 30.0487 | 0.839207 | -0.3920 | 9677.77 |

Leitura:

```text
Nenhuma janela testada apresentou edge.

A reducao de frequencia em EMA 50/200 diminuiu a perda e o impacto dos custos,
mas ainda nao produziu expectativa positiva.

O custo deteriorou todas as combinacoes de forma material.
```

Decisao:

```text
Manter Simple EMA Trend Following como benchmark de engenharia.

Nao tratar esta especificacao como candidata promissora.
```

---

## 9. Proximo Passo

Avancar para a proxima hipotese:

```text
Volatility Breakout
```

---

## 10. Backtest Historico Inicial

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

## 11. Proximo Passo Detalhado

Hipotese primaria testada:

```text
Volatility Breakout

entry_lookback = 20

exit_lookback = 10

min_range_pips = 10

fixed_quantity = 0.01 lot
```

Regra:

```text
close atual rompe acima da maxima dos 20 candles anteriores

e

range dos 20 candles anteriores >= 10 pips

-> ENTER_LONG

close atual rompe abaixo da minima dos 10 candles anteriores

-> EXIT

caso contrario

-> HOLD
```

Resultado zero-cost:

```text
trades:              4336
net_profit:          -541.31
total_return_pct:    -5.4131
max_drawdown:        594.00
max_drawdown_pct:    5.9260
win_rate:            35.2629
profit_factor:       0.873042
average_trade:       -0.1248
final_equity:        9458.69
```

Resultado com custos explicitos:

```text
spread_pips:                  2.0
slippage_pips:                0.5
commission_per_lot_per_side:  3.50

trades:              4336
net_profit:          -2145.63
total_return_pct:    -21.4563
max_drawdown:        2159.55
max_drawdown_pct:    21.5950
win_rate:            29.0129
profit_factor:       0.599219
average_trade:       -0.4948
final_equity:        7854.37
```

Leitura:

```text
A especificacao primaria simples de Volatility Breakout nao apresentou edge.

O resultado zero-cost ja foi negativo.

Com custos explicitos, a deterioracao foi severa.
```

Decisao:

```text
Nao promover esta especificacao para validacao OOS.

Manter Volatility Breakout como familia possivel apenas se uma nova regra primaria for definida com racional melhor.
```

---

## 12. Proximo Passo

Avancar para a proxima hipotese simples:

```text
Time-Series Momentum
```

Objetivo:

```text
testar se retornos acumulados recentes possuem continuacao positiva apos custos
```

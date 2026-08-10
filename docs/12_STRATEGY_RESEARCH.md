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

Hipotese primaria testada:

```text
Time-Series Momentum

lookback = 96 candles M15

entry_threshold = 0.0010

exit_threshold = 0.0

fixed_quantity = 0.01 lot
```

Regra:

```text
retorno acumulado dos ultimos 96 candles > 0.10%

-> ENTER_LONG

retorno acumulado dos ultimos 96 candles < 0.00%

-> EXIT

caso contrario

-> HOLD
```

Resultado zero-cost:

```text
trades:              2674
net_profit:          175.01
total_return_pct:    1.7501
max_drawdown:        183.73
max_drawdown_pct:    1.8013
win_rate:            32.2737
profit_factor:       1.063166
average_trade:       0.0654
final_equity:        10175.01
```

Resultado com custos explicitos:

```text
spread_pips:                  2.0
slippage_pips:                0.5
commission_per_lot_per_side:  3.50

trades:              2674
net_profit:          -814.37
total_return_pct:    -8.1437
max_drawdown:        845.84
max_drawdown_pct:    8.4321
win_rate:            25.5423
profit_factor:       0.765704
average_trade:       -0.3046
final_equity:        9185.63
```

Leitura:

```text
A Time-Series Momentum baseline apresentou sinal bruto positivo em zero-cost.

O resultado nao sobreviveu aos custos explicitos baseline.

Isso sugere que a hipotese pode conter informacao direcional,
mas a especificacao atual opera com friccao demais ou edge insuficiente.
```

Decisao:

```text
Nao promover para OOS ainda.

Marcar como mais interessante que EMA e Volatility Breakout,
mas ainda nao aprovada apos custos.
```

---

## 13. Proximo Passo

Hipotese primaria testada:

```text
Simple Mean Reversion

lookback = 16 candles M15

entry_threshold = -0.0010

exit_threshold = 0.0

fixed_quantity = 0.01 lot
```

Regra:

```text
retorno acumulado dos ultimos 16 candles < -0.10%

-> ENTER_LONG

retorno acumulado dos ultimos 16 candles >= 0.00%

-> EXIT

caso contrario

-> HOLD
```

Resultado zero-cost:

```text
trades:              6568
net_profit:          128.39
total_return_pct:    1.2839
max_drawdown:        131.39
max_drawdown_pct:    1.3139
win_rate:            64.8904
profit_factor:       1.027958
average_trade:       0.0195
final_equity:        10128.39
```

Resultado com custos explicitos:

```text
spread_pips:                  2.0
slippage_pips:                0.5
commission_per_lot_per_side:  3.50

trades:              6568
net_profit:          -2301.77
total_return_pct:    -23.0177
max_drawdown:        2306.19
max_drawdown_pct:    23.0619
win_rate:            50.2132
profit_factor:       0.590060
average_trade:       -0.3505
final_equity:        7698.23
```

Leitura:

```text
A Mean Reversion baseline apresentou sinal bruto positivo em zero-cost.

O alto numero de trades tornou a estrategia muito sensivel a custos.

Com custos explicitos, a deterioracao foi severa.
```

Decisao:

```text
Nao promover para OOS.

Registrar como evidencia de que estrategias intraday de alta frequencia operacional
precisam de edge bruto muito maior para sobreviver a custos.
```

---

## 14. Asian Range Breakout

Hipotese primaria testada:

```text
Asian Range Breakout

range_start_hour_utc = 0

range_end_hour_utc = 6

trade_end_hour_utc = 20

min_range_pips = 5.0

fixed_quantity = 0.01 lot
```

Regra:

```text
Construir a maxima e a minima da faixa entre 00:00 UTC e 06:00 UTC.

Apos o fechamento da faixa:

close > range_high

-> ENTER_LONG

close < range_low

-> ENTER_SHORT

Permitir apenas um rompimento por data UTC.

A partir de 20:00 UTC:

-> EXIT

caso contrario

-> HOLD
```

Resultado zero-cost:

```text
trades:              2972
net_profit:          -259.80
total_return_pct:    -2.5980
max_drawdown:        382.75
max_drawdown_pct:    3.7904
win_rate:            50.5047
profit_factor:       0.949656
average_trade:       -0.0874
final_equity:        9740.20
```

Resultado com custos explicitos:

```text
spread_pips:                  2.0
slippage_pips:                0.5
commission_per_lot_per_side:  3.50

trades:              2972
net_profit:          -1359.44
total_return_pct:    -13.5944
max_drawdown:        1446.21
max_drawdown_pct:    14.3501
win_rate:            45.6258
profit_factor:       0.762751
average_trade:       -0.4574
final_equity:        8640.56
```

Leitura:

```text
A Asian Range Breakout baseline nao apresentou sinal bruto positivo em zero-cost.

Com custos explicitos, a deterioracao foi relevante.

A configuracao atual nao justifica promocao para OOS.
```

Decisao:

```text
Nao promover para OOS.

Registrar como evidencia negativa para esta especificacao primaria.
```

---

## 15. Simple Carry

Hipotese primaria testada:

```text
Simple Carry

carry_score = -1.0

entry_threshold = 0.5

exit_threshold = 0.0

fixed_quantity = 0.01 lot
```

Regra:

```text
carry_score >= entry_threshold

-> ENTER_LONG

carry_score <= -entry_threshold

-> ENTER_SHORT

abs(carry_score) <= exit_threshold

-> EXIT

caso contrario

-> HOLD
```

Observacao:

```text
Este baseline usa apenas um proxy direcional estatico.

Ele nao modela accrual diario de swap, curva historica de juros,
mudanca temporal do diferencial de taxas ou custos de financiamento.

Portanto, o resultado abaixo deve ser lido como exposicao direcional
associada a uma hipotese de carry, nao como carry completo.
```

Resultado zero-cost:

```text
trades:              1
net_profit:          48.38
total_return_pct:    0.4838
max_drawdown:        251.03
max_drawdown_pct:    2.4490
win_rate:            100.0000
profit_factor:       inf
average_trade:       48.3800
final_equity:        10048.38
```

Resultado com custos explicitos:

```text
spread_pips:                  2.0
slippage_pips:                0.5
commission_per_lot_per_side:  3.50

trades:              1
net_profit:          48.01
total_return_pct:    0.4801
max_drawdown:        251.03
max_drawdown_pct:    2.4491
win_rate:            100.0000
profit_factor:       inf
average_trade:       48.0100
final_equity:        10048.01
```

Leitura:

```text
O proxy estatico de carry teve resultado positivo no periodo completo.

Como houve apenas um trade, o profit factor infinito nao deve ser interpretado
como robustez estatistica.

O resultado tambem nao inclui receita ou custo de swap.
```

Decisao:

```text
Nao promover para OOS como carry completo.

Registrar como evidencia de que a proxima evolucao de Carry precisa
de dados historicos de taxas/swap ou de uma camada de financiamento.
```

---

## 16. Simple Regime Detection

Hipotese primaria testada:

```text
Simple Regime Detection

trend_lookback = 96 candles M15

volatility_lookback = 96 candles M15

entry_threshold = 0.0025

exit_threshold = 0.0005

max_volatility = 0.00055

fixed_quantity = 0.01 lot
```

Regra:

```text
Calcular o retorno dos ultimos 96 candles.

Calcular a volatilidade realizada dos retornos close-to-close
dos ultimos 96 candles.

realized_volatility > max_volatility

-> EXIT

trend_return >= entry_threshold
e realized_volatility <= max_volatility

-> ENTER_LONG

trend_return <= -entry_threshold
e realized_volatility <= max_volatility

-> ENTER_SHORT

abs(trend_return) <= exit_threshold

-> EXIT

caso contrario

-> HOLD
```

Resultado zero-cost:

```text
trades:              2681
net_profit:          -100.64
total_return_pct:    -1.0064
max_drawdown:        126.20
max_drawdown_pct:    1.2620
win_rate:            38.4900
profit_factor:       0.967062
average_trade:       -0.0375
final_equity:        9899.36
```

Resultado com custos explicitos:

```text
spread_pips:                  2.0
slippage_pips:                0.5
commission_per_lot_per_side:  3.50

trades:              2681
net_profit:          -1092.61
total_return_pct:    -10.9261
max_drawdown:        1096.87
max_drawdown_pct:    10.9687
win_rate:            33.0800
profit_factor:       0.704169
average_trade:       -0.4075
final_equity:        8907.39
```

Leitura:

```text
O filtro simples de regime reduziu o drawdown em zero-cost,
mas nao apresentou edge bruto positivo.

Com custos explicitos, o resultado deteriorou de forma relevante.

A configuracao atual ainda opera demais para um sinal fraco.
```

Decisao:

```text
Nao promover para OOS.

Registrar como baseline negativa para esta especificacao simples
de trend + volatilidade.
```

---

## 17. Variacoes Exploratorias Pre-Registradas (Asian Range Breakout)

Objetivo:

```text
Verificar se a conclusao da especificacao primaria muda com
ajustes simples de parametros, mantendo a mesma regra.

As combinacoes foram definidas ANTES da leitura dos resultados.
Isso nao e otimizacao: e uma grade exploratoria de sensibilidade.
```

Dataset e parametros comuns:

```text
EURUSD M15
2015-01-02 09:00:00 UTC ate 2026-08-08 00:00:00 UTC
fixed_quantity = 0.01 lot
initial_capital = 10000.00
```

Grade (uma variacao por execucao):

| Tag | Parametros |
|---|---|
| V1 | min_range_pips = 10 |
| V2 | min_range_pips = 15 |
| V3 | trade_end_hour_utc = 16 |
| V4 | trade_end_hour_utc = 12 |
| V5 | range_end_hour_utc = 8 |
| V6 | min_range_pips = 10 + trade_end_hour_utc = 16 |

Criterio de leitura:

```text
Uma variacao so seria interessante se:
- zero-cost positivo E
- custos explicitos ainda positivos (ou proximo de zero)

Senao, o resultado reforca a decisao de descartar a
especificacao primaria atual.
```

---

## 18. Resultado da Grade Exploratoria (Asian Range Breakout)

Resultado zero-cost:

| Variacao | Trades | Net Profit | Return % | Win Rate % | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|---:|
| Base (5 pips, 0-6h, exit 20h) | 2972 | -259.80 | -2.5980 | 50.50 | 0.949656 | 9740.20 |
| V1 (min_range 10) | 2850 | -277.15 | -2.7715 | 50.91 | 0.944840 | 9722.85 |
| V2 (min_range 15) | 2320 | -252.18 | -2.5218 | 51.55 | 0.940238 | 9747.82 |
| V3 (exit 16h) | 2929 | -186.58 | -1.8658 | 50.80 | 0.952915 | 9813.42 |
| V4 (exit 12h) | 2735 | -127.52 | -1.2752 | 52.03 | 0.945172 | 9872.48 |
| V5 (range 0-8h) | 2964 | -18.00 | -0.1800 | 50.81 | 0.996299 | 9982.00 |
| V6 (min_range 10 + exit 16h) | 2807 | -192.67 | -1.9267 | 50.84 | 0.950072 | 9807.33 |

Resultado com custos explicitos:

```text
spread_pips:                  2.0
slippage_pips:                0.5
commission_per_lot_per_side:  3.50
```

| Variacao | Trades | Net Profit | Return % | Win Rate % | Profit Factor | Final Equity |
|---|---:|---:|---:|---:|---:|---:|
| Base | 2972 | -1359.44 | -13.5944 | 45.63 | 0.762751 | 8640.56 |
| V1 | 2850 | -1331.65 | -13.3165 | 45.68 | 0.760931 | 8668.35 |
| V2 | 2320 | -1110.58 | -11.1058 | 46.90 | 0.761652 | 8889.42 |
| V3 | 2929 | -1270.31 | -12.7031 | 43.63 | 0.720420 | 8729.69 |
| V4 | 2735 | -1139.47 | -11.3947 | 41.02 | 0.606028 | 8860.53 |
| V5 | 2964 | -1114.68 | -11.1468 | 46.12 | 0.794499 | 8885.32 |
| V6 | 2807 | -1231.26 | -12.3126 | 44.28 | 0.721157 | 8768.74 |

Leitura:

```text
Nenhuma variacao atendeu ao criterio pre-registrado
(zero-cost positivo E resultado positivo apos custos).

Todas as variacoes ficaram negativas em zero-cost.

V5 (range 0-8h) foi a menos pior em zero-cost
(PF 0.9963, -18.00), mas continuou claramente negativa
apos custos (PF 0.7945).

V4 (exit 12h) mostrou a maior sensibilidade a custos
(PF explicito 0.6060), consistente com holding mais curto.

Nenhum ajuste simples de parametro revelou edge.
```

Decisao:

```text
Descartar a especificacao primaria atual de Asian Range
Breakout e suas variacoes simples.

Reabrir a familia apenas com uma regra primaria nova
e racional melhor (ex.: filtros de sessao/volume,
assimetria direcional, saida com stop/target).
```

---

## 19. Proximo Passo

Avancar para:

```text
Multi-Timeframe
```

Objetivo:

```text
testar se sinais em M15 melhoram quando filtrados por contexto H1/H4
sem quebrar causalidade ou alinhamento temporal
```

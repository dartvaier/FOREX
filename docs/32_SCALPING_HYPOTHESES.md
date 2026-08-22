# 32 — Scalping Hypotheses

Este documento registra hipoteses de scalping separadas do pipeline
M15 atual. Nenhuma hipotese aqui representa sinal de producao ou
autorizacao para trading real.

## Status Atual

- datasets M15/H1/H4 continuam no fluxo principal;
- scalping deve usar pasta separada:

```text
data/scalping/raw/<SYMBOL>/M1.parquet
data/scalping/processed/<SYMBOL>/M5.parquet
```

- importador JForex M1 preparado:

```powershell
python import_jforex_scalping.py --input-dir data/import/JForex --symbol USDJPY
```

Se os CSVs estiverem na pasta do Desktop:

```powershell
python import_jforex_scalping.py --input-dir C:\Users\Gabriel\Desktop\FOREX\data\import\JForex --symbol USDJPY
```

## Dados Necessarios no JForex

Exportar Bid e Ask em M1 para USDJPY:

```text
USDJPY_1 Min_Bid_2015.01.01_2026.08.22.csv
USDJPY_1 Min_Ask_2015.01.01_2026.08.22.csv
```

Formato esperado:

```text
Time (EET),Open,High,Low,Close,Volume
```

O importador converte EET/EEST para UTC, combina Bid/Ask em preco
medio, calcula `spread` em pontos, grava M1 raw e gera M5 por resample
sem preencher gaps.

## SC-01 — USDJPY Micro Pullback em Regime Favoravel

Status:

```text
PROPOSED
```

Hipotese:

> Em USDJPY, quando o regime M15 esta direcional e o spread esta
> comprimido, pequenos pullbacks contra a direcao do regime em M1/M5
> tendem a reverter para continuacao curta, com alvo pequeno e timeout
> rapido.

Racional:

- USDJPY foi o primeiro par com edge positivo apos custo calibrado;
- o melhor resultado veio de `ensemble_regime_cost`, nao de alpha
  isolado;
- scalping exige operar pouco, em janela liquida, com spread baixo e
  contexto direcional favoravel.

Especificacao candidata:

```text
Simbolo: USDJPY
Base micro: M1
Decision view: M5
Filtro superior: M15 ensemble_regime_cost
Sessoes: Londres + NY overlap
Spread: abaixo do p50 ou p60 historico do mesmo slot horario
```

Entrada long candidata:

```text
1. M15 ensemble_regime_cost bullish
2. M1/M5 faz pullback curto contra a direcao
3. candle fecha retomando a direcao do regime
4. spread atual <= limiar do slot horario
```

Entrada short: regra espelhada.

Saida candidata:

```text
Stop: ultimo micro swing ou 2x spread
Alvo: 1.0R a 1.5R, ou 3-6 pips
Timeout: 5-12 candles M1, ou 2-4 candles M5
```

Primeiro experimento:

1. medir spreads M1/M5 por horario;
2. marcar periodos em que o M15 `ensemble_regime_cost` esta direcional;
3. estudar retornos condicionais apos pullbacks em M5;
4. somente depois criar uma Strategy operacional.

Critério inicial de rejeicao:

- edge liquido <= 0 apos custo calibrado;
- resultado depender de uma unica janela temporal;
- turnover alto destruir expectancy;
- ganho concentrado em poucos eventos extremos.

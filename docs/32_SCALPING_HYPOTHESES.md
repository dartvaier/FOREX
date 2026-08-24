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

## Perfil de Spread

Depois de importar M1/M5, medir o custo micro por horario:

```powershell
python -m research.scalping_spread_profile --symbol USDJPY --timeframe M1
python -m research.scalping_spread_profile --symbol USDJPY --timeframe M5
```

Saidas:

```text
research/reports/scalping/scalping_spread_profile_USDJPY_M1.json
research/reports/scalping/scalping_spread_profile_USDJPY_M1.csv
research/reports/scalping/scalping_spread_profile_USDJPY_M5.json
research/reports/scalping/scalping_spread_profile_USDJPY_M5.csv
```

Primeira medicao com JForex USDJPY M1/M5 2015-01-01 -> 2026-08-21:

```text
M1: mediana 0.40 pips, p90 0.90, p95 1.20
M5: mediana 0.40 pips, p90 0.86, p95 1.16
```

Por sessao:

| Timeframe | Sessao | Spread med | Spread p90 | Spread p95 |
|---|---|---:|---:|---:|
| M1 | london_ny_overlap | 0.30 | 0.70 | 0.80 |
| M1 | london_morning | 0.40 | 0.70 | 0.80 |
| M1 | new_york | 0.40 | 0.80 | 1.00 |
| M1 | off_session | 0.50 | 1.20 | 2.30 |
| M5 | london_ny_overlap | 0.34 | 0.68 | 0.78 |
| M5 | london_morning | 0.36 | 0.66 | 0.76 |
| M5 | new_york | 0.40 | 0.78 | 0.94 |
| M5 | off_session | 0.46 | 1.18 | 2.34 |

Leitura inicial: para SC-01, a janela operacional candidata deve
comecar por Londres/NY overlap, especialmente UTC 14-16. Fora de
sessao o p90/p95 de spread cresce o bastante para tornar scalping
menos atraente.

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

1. marcar periodos em que o M15 `ensemble_regime_cost` esta direcional;
2. estudar retornos condicionais apos pullbacks em M5 durante UTC 14-16;
3. comparar contra Londres manha e fora de sessao como controles;
4. somente depois criar uma Strategy operacional.

Implementacao do estudo:

```powershell
python -m research.scalping_pullback_study --symbol USDJPY
```

Saidas:

```text
research/reports/scalping/scalping_pullback_study_USDJPY.json
research/reports/scalping/scalping_pullback_study_USDJPY.csv
```

Primeira medicao com USDJPY M5 2015-01-01 -> 2026-08-21,
pullback de 3 candles M5, minimo 2.0 pips, horizonte de 6 candles
M5 e custo adicional de 1.7 pips alem do spread de entrada:

| Sessao | Eventos | Gross medio | Hit rate | Net medio |
|---|---:|---:|---:|---:|
| all | 15,676 | 0.16 | 50.62% | -2.11 |
| london_morning | 3,295 | 0.28 | 52.14% | -1.81 |
| london_ny_overlap | 3,125 | 0.18 | 51.20% | -1.92 |
| new_york | 3,050 | -0.01 | 49.90% | -2.14 |
| off_session | 6,206 | 0.16 | 49.87% | -2.36 |

Leitura: a forma pura da hipotese SC-01 nao passa no criterio de
custo. Existe uma leve inclinacao bruta em Londres manha e overlap,
mas pequena demais para vencer spread + slippage/commission estimados.
O proximo passo nao deve ser criar uma estrategia operacional ainda;
deve ser adicionar filtros de qualidade do setup: spread por slot,
forca do regime M15, distancia do pullback, volatilidade intradiaria e
separacao long/short.

Sweep de filtros de qualidade:

```powershell
python -m research.scalping_pullback_filter_sweep --symbol USDJPY
```

Saidas:

```text
research/reports/scalping/scalping_pullback_filter_sweep_USDJPY.json
research/reports/scalping/scalping_pullback_filter_sweep_USDJPY.csv
```

O sweep combina:

- sessao: all, liquid, london_morning, london_ny_overlap;
- lado: all, long, short;
- horizonte: 3 e 6 candles M5;
- spread: percentil causal por slot UTC <= p50/p60;
- forca do regime M15: abs(blended_value) >= 0.35/0.50/0.65;
- pullback minimo: 2/3/4 pips.

Melhor recorte com pelo menos 250 eventos:

| Sessao | Lado | H | Spread slot | Regime | Pullback | Eventos | Gross medio | Hit rate | Net medio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| london_ny_overlap | short | 6 | p50 | 0.65 | 4.0 | 308 | 1.64 | 52.92% | -0.40 |
| london_ny_overlap | short | 6 | p60 | 0.65 | 4.0 | 356 | 1.30 | 51.69% | -0.74 |
| liquid | short | 6 | p50 | 0.65 | 4.0 | 575 | 1.13 | 52.00% | -0.91 |

Leitura: os filtros melhoram muito a hipotese bruta, principalmente
short no overlap Londres/NY com regime forte, pullback maior e spread
abaixo do p50 do slot. Mesmo assim, nenhuma combinacao ficou positiva
apos custo estimado. SC-01 continua como pesquisa; ainda nao deve virar
Strategy.

Critério inicial de rejeicao:

- edge liquido <= 0 apos custo calibrado;
- resultado depender de uma unica janela temporal;
- turnover alto destruir expectancy;
- ganho concentrado em poucos eventos extremos.

## SC-02 — USDJPY Micro Breakout em Regime Favoravel

Status:

```text
RESEARCHED / NOT PROMOTED
```

Hipotese:

> Em USDJPY, quando o regime M15 esta direcional e o spread esta
> comprimido, rompimentos M5 na direcao do regime podem carregar
> continuacao curta por alguns candles.

Regra do primeiro estudo:

```text
Filtro superior: M15 ensemble_regime_cost
Base micro: M5
Canal: maxima/minima dos 6 candles M5 anteriores
Entrada long: close rompe a maxima anterior na direcao de regime long
Entrada short: close rompe a minima anterior na direcao de regime short
Min breakout: 0.5 pip
Min corpo: 0.5 pip na direcao do regime
Horizontes: 1/2/3/6 candles M5
Custo: spread de entrada + 1.7 pips
```

Implementacao do estudo:

```powershell
python -m research.scalping_breakout_study --symbol USDJPY
```

Saidas:

```text
research/reports/scalping/scalping_breakout_study_USDJPY.json
research/reports/scalping/scalping_breakout_study_USDJPY.csv
```

Primeira medicao com USDJPY M5 2015-01-01 -> 2026-08-21,
horizonte de 6 candles M5:

| Sessao | Eventos | Gross medio | Hit rate | Net medio |
|---|---:|---:|---:|---:|
| all | 22,951 | -0.04 | 47.56% | -2.21 |
| london_morning | 4,747 | 0.13 | 48.35% | -1.96 |
| london_ny_overlap | 4,518 | 0.03 | 49.67% | -2.05 |
| new_york | 4,573 | -0.28 | 46.23% | -2.40 |
| off_session | 9,113 | -0.03 | 46.78% | -2.32 |

Recortes por lado no horizonte de 6 candles M5:

| Sessao | Lado | Eventos | Gross medio | Hit rate | Net medio |
|---|---|---:|---:|---:|---:|
| london_morning | long | 2,836 | 0.31 | 49.68% | -1.79 |
| london_ny_overlap | short | 1,843 | 0.28 | 48.56% | -1.79 |
| new_york | short | 1,776 | -0.28 | 44.99% | -2.38 |
| off_session | short | 3,788 | 0.10 | 47.36% | -2.19 |

Sweep de filtros de qualidade:

```powershell
python -m research.scalping_breakout_filter_sweep --symbol USDJPY
```

Saidas:

```text
research/reports/scalping/scalping_breakout_filter_sweep_USDJPY.json
research/reports/scalping/scalping_breakout_filter_sweep_USDJPY.csv
```

O sweep combina:

- sessao: all, liquid, london_morning, london_ny_overlap;
- lado: all, long, short;
- horizonte: 3 e 6 candles M5;
- spread: percentil causal por slot UTC <= p50/p60;
- forca do regime M15: abs(blended_value) >= 0.35/0.50/0.65;
- breakout minimo: 0.5/1.0/2.0 pips;
- corpo minimo: 0.5/1.0 pip.

Melhor recorte com pelo menos 250 eventos:

| Sessao | Lado | H | Spread slot | Regime | Breakout | Corpo | Eventos | Gross medio | Hit rate | Net medio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| london_ny_overlap | short | 6 | p50 | 0.65 | 2.0 | 0.5 | 446 | 1.24 | 48.88% | -0.78 |
| london_ny_overlap | short | 6 | p60 | 0.65 | 2.0 | 0.5 | 557 | 1.06 | 49.73% | -0.96 |
| liquid | short | 6 | p50 | 0.65 | 2.0 | 0.5 | 833 | 0.89 | 48.98% | -1.13 |

Leitura: SC-02 tambem nao passa no criterio de custo. O mesmo padrao
aparece de novo: short no overlap Londres/NY com regime forte e spread
comprimido e a melhor regiao, mas o edge bruto medio ainda nao paga a
barreira de spread + slippage/commission. Isso sugere que continuar
apertando filtros direcionais simples tende a virar parameter mining.

Proximo caminho de pesquisa:

1. testar micro mean reversion apos excesso intrabar, em vez de
   continuacao direcional simples;
2. adicionar filtro de volatilidade intradiaria antes de novas regras;
3. avaliar M1 apenas como timing de entrada, mantendo M5/M15 como
   contexto;
4. pausar promocao de qualquer scalper ate haver edge liquido positivo
   em estudo simples e reproduzivel.

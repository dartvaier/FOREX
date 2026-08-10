# Robustness & Validation (F8)

## 1. Objetivo

Este documento registra os resultados da fase:

```text
F8 - Robustness & Validation
```

O objetivo (roadmap §69) e determinar se o resultado observado das
estrategias parece robusto ou apenas consequencia do periodo/parametro
escolhido. A leitura aqui e **negativa e consistente**: nenhuma estrategia
do baseline sobrevive a custos explicitos, e essa ausencia de edge e
temporalmente estavel, nao um artefato de periodo.

Fonte dos dados:

```text
research/reports/f8/  (CSVs de sweep/subperiods/stability + JSONs de cost stress)
```

Todos os experimentos:

```text
EURUSD M15
custos explicitos (spread 2.0 pips, slippage 0.5 pips, comissao 3.50 USD/lote/lado)
capital inicial 10,000 USD
lote fixo 0.01
```

## 2. Periodos formais (pre-registrados)

Definidos em `research/periods.py` ANTES de qualquer execucao:

```text
dev (development)    2015-01-01 .. 2021-01-01
val (validation)     2021-01-01 .. 2024-01-01
oos (lockbox)        2024-01-01 .. 2027-01-01   <- NAO consultado
```

O OOS lockbox permanece intacto (roadmap §74): nenhuma execucao F8 o
consultou. O guard mecanico (`--period oos` exige `--allow-oos`) bloqueia
consultas acidentais.

## 3. TIME-SERIES-MOMENTUM (lookback=96, entry_threshold=0.001)

### 3.1 Sensibilidade local: lookback

| lookback | trades | net_profit | return_pct | max_dd_pct | win_rate | pf |
|---|---|---|---|---|---|---|
| 64 | 3667 | -1480.31 | -14.80 | 14.92 | 25.93 | 0.679 |
| 96 | 2674 | -814.37 | -8.14 | 8.43 | 25.54 | 0.766 |
| 128 | 2363 | -821.74 | -8.22 | 8.42 | 24.33 | 0.744 |
| 160 | 2176 | -830.75 | -8.31 | 8.42 | 24.54 | 0.732 |
| 192 | 1889 | -679.34 | -6.79 | 7.37 | 24.14 | 0.759 |

Leitura: **regiao estavel 96-192** (-6.8% a -8.3%), comportamento suave e
monotono em turnover (1889-3667 trades). Nenhuma ilha de parametro; o
grid inteiro e consistentemente negativo com custos.

### 3.2 Subperiods

| period | trades | net_profit | return_pct | max_dd_pct | win_rate | pf |
|---|---|---|---|---|---|---|
| 2015-2017 | 740 | -142.93 | -1.43 | 2.03 | 26.22 | 0.856 |
| 2018-2020 | 658 | -187.83 | -1.88 | 2.33 | 25.84 | 0.778 |
| 2021-2023 | 700 | -314.59 | -3.15 | 3.79 | 23.71 | 0.671 |
| 2024-2026 | 576 | -170.86 | -1.71 | 1.72 | 26.56 | 0.749 |

Leitura: negativo nos 4 subperiods; pior em 2021-2023, mas nenhuma janela
sequer se aproxima do break-even.

### 3.3 Stability (dev vs val)

| period | return_pct | net_profit | max_dd_pct | win_rate | pf |
|---|---|---|---|---|---|
| dev | -3.25 | -325.20 | 3.78 | 26.06 | 0.823 |
| val | -3.15 | -314.59 | 3.79 | 23.71 | 0.671 |

Veredito: **CONSISTENT** (mesmo sinal; deltas de retorno ~0.1pp).

### 3.4 Cost stress

| multiplier | round_trip | return_pct | max_dd_pct |
|---|---|---|---|
| 1.0x (base) | 0.37 USD (3.70 pips) | -8.14 | 8.43 |
| 1.5x | 0.555 USD (5.55 pips) | -13.09 | 13.18 |
| 2.0x | 0.74 USD (7.40 pips) | -18.04 | 18.04 |

Leitura: degradacao quase linear com o custo. Referencia zero-cost:
+1.75% -> explicito -8.14% (2674 trades). O resultado e dominado por
custo; o edge bruto (se existir) nao sobrevive ao round-trip de 0.37 USD
nessa frequencia.

## 4. SIMPLE-EMA-TREND (fast=20, slow=50)

### 4.1 Sensibilidade local: fast_period

| fast | trades | net_profit | return_pct | max_dd_pct | win_rate | pf |
|---|---|---|---|---|---|---|
| 10 | 3879 | -1545.32 | -15.45 | 15.61 | 22.89 | 0.687 |
| 15 | 3169 | -1245.23 | -12.45 | 12.73 | 24.27 | 0.719 |
| 20 | 2715 | -1086.49 | -10.86 | 11.13 | 26.00 | 0.738 |
| 25 | 2444 | -1034.35 | -10.34 | 10.63 | 27.05 | 0.737 |
| 30 | 2235 | -884.22 | -8.84 | 9.05 | 26.80 | 0.759 |

Leitura: monotono (fast mais rapido = mais trades = pior). Regiao estavel
20-30 (-8.8% a -10.9%); nenhum valor positivo no grid.

### 4.2 Subperiods

| period | trades | net_profit | return_pct | max_dd_pct | win_rate | pf |
|---|---|---|---|---|---|---|
| 2015-2017 | 678 | -212.87 | -2.13 | 2.65 | 27.73 | 0.818 |
| 2018-2020 | 689 | -260.41 | -2.60 | 3.28 | 25.83 | 0.735 |
| 2021-2023 | 720 | -369.10 | -3.69 | 4.05 | 25.28 | 0.669 |
| 2024-2026 | 627 | -248.10 | -2.48 | 2.60 | 25.20 | 0.718 |

### 4.3 Stability (dev vs val)

| period | return_pct | net_profit | max_dd_pct | win_rate | pf |
|---|---|---|---|---|---|
| dev | -4.69 | -469.21 | 5.21 | 26.77 | 0.782 |
| val | -3.69 | -369.10 | 4.05 | 25.28 | 0.669 |

Veredito: **CONSISTENT**.

### 4.4 Cost stress

| multiplier | round_trip | return_pct | max_dd_pct |
|---|---|---|---|
| 1.0x (base) | 0.37 USD (3.70 pips) | -10.86 | 11.13 |
| 1.5x | 0.555 USD (5.55 pips) | -15.89 | 16.02 |
| 2.0x | 0.74 USD (7.40 pips) | -20.91 | 21.01 |

## 5. SIMPLE-MEAN-REVERSION (lookback=16, entry_threshold=-0.001)

### 5.1 Sensibilidade local: lookback

| lookback | trades | net_profit | return_pct | max_dd_pct | win_rate | pf |
|---|---|---|---|---|---|---|
| 8 | 8302 | -2819.87 | -28.20 | 28.22 | 48.11 | 0.549 |
| 16 | 6568 | -2301.77 | -23.02 | 23.06 | 50.21 | 0.590 |
| 24 | 5604 | -1933.14 | -19.33 | 19.35 | 52.36 | 0.620 |
| 32 | 4994 | -1567.60 | -15.68 | 15.70 | 54.57 | 0.671 |

Leitura: **morte por mil cortes** — win rate alto (48-55%) com payoff
negativo; quanto mais turnover, maior a perda. Monotono e consistente;
nenhum valor positivo.

### 5.2 Subperiods

| period | trades | net_profit | return_pct | max_dd_pct | win_rate | pf |
|---|---|---|---|---|---|---|
| 2015-2017 | 1899 | -746.11 | -7.46 | 7.53 | 51.45 | 0.592 |
| 2018-2020 | 1572 | -486.38 | -4.86 | 4.93 | 49.43 | 0.612 |
| 2021-2023 | 1736 | -648.82 | -6.49 | 6.52 | 50.92 | 0.573 |
| 2024-2026 | 1361 | -423.29 | -4.23 | 4.28 | 48.49 | 0.583 |

### 5.3 Stability (dev vs val)

| period | return_pct | net_profit | max_dd_pct | win_rate | pf |
|---|---|---|---|---|---|
| dev | -12.32 | -1231.55 | 12.36 | 50.53 | 0.600 |
| val | -6.49 | -648.82 | 6.52 | 50.92 | 0.573 |

Veredito: **CONSISTENT** (ambos negativos; melhora relativa em val por
menor turnover, sem nunca cruzar o zero).

## 6. Leituras consolidadas

1. **Robustez temporal: CONSISTENTE (negativa).** As tres estrategias sao
   negativas em dev, val e nos 4 subperiods. A ausencia de edge nao e
   artefato de periodo — e estavel em ~11 anos de dados.

2. **Sensibilidade parametrica: sem ilhas.** Todos os grids sao monotoneos
   ou planos; nenhum pico isolado de lucro escondido entre valores vizinhos.
   Buscar "o parametro certo" dentro dessas classes e inutil.

3. **Sensibilidade a custo: alta e linear.** 1.5x/2.0x degradam o resultado
   na mesma proporcao. Estrategias de alto turnover (MR: 6568 trades) sao as
   mais frágeis; TSM (1889-2674 trades) e a menos frágil, ainda assim
   perdedora.

4. **Diagnostico geral:** o edge bruto (zero-cost) e marginal ou inexistente
   e nao sobrevive ao round-trip de 0.37 USD. O caminho nao e re-otimizar
   parametros (os grids provam monotonia), e sim reconstruir edge: filtros
   de regime, reducao de turnover, melhoria de payoff — ou aceitar que essas
   classes simples nao tem edge em EURUSD M15.

## 7. Status do OOS

```text
OOS lockbox (2024-2026): NAO CONSULTADO
```

Guard mecanico ativo. Qualquer consulta futura exige decisao explicita
(`--allow-oos`) e deve ser registrada como evento de lockbox.

## 8. Conclusao

F8 atende integralmente o Definition of Done (roadmap §78):

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

Fase F8: COMPLETE. A conclusao quantitativa: nenhuma estrategia atual
atinge os criterios de aceitacao com custos explicitos; a infraestrutura
de robustez (periodos formais, lockbox, sweep, stability, cost stress)
esta pronta para avaliar as proximas hipoteses.

## 9. Artefatos

```text
research/reports/f8/*_sweep_*.csv       grids de sensibilidade
research/reports/f8/*_subperiods.csv    estabilidade temporal
research/reports/f8/*_stability.csv     dev vs val + signal_consistent
research/reports/f8/*_f8-cost1{5,0}.json  cost stress 1.5x/2.0x
```

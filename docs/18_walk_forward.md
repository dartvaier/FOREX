# 18 — Walk-Forward Validation (roadmap §75)

Status: **CONCLUÍDO** — hipótese WF-01 testada e rejeitada para os três
baselines. Nenhuma estratégia possui edge transferível no tempo sob
custos explícitos.

---

## 1. Hipótese pré-registrada (WF-01)

> Se o edge de uma estratégia baseline for real e transferível no tempo,
> então a seleção de parâmetros em janelas de treino rolantes (2 anos)
> pela métrica **expectancy** máxima, aplicada na janela de validação
> subsequente (1 ano), produz net profit positivo na MAIORIA das janelas
> sob custos explícitos.

Critérios de aceite (decididos ANTES de ver resultados):

```text
>= 5/7 janelas val com net_profit > 0
E expectancy média val > 0
E mesmo sinal de retorno em >= 5/7 janelas
```

Métrica de seleção: expectancy (maior), tiebreak profit_factor.

## 2. Design (pré-registrado)

- Janelas: train 2y / val 1y / step 1y, 2015-01-01 → 2024-01-01 (7 janelas).
- Grids: reutilizam os grids F8 (docs/15) verbatim, sem valores novos:
  - TSM: lookback ∈ {64, 96, 128, 160, 192} (entry_threshold=0.001)
  - EMA: fast_period ∈ {10, 15, 20, 25, 30} (slow_period=50)
  - MR: lookback ∈ {8, 16, 24, 32} (entry_threshold=-0.001)
- Custos: explícitos baseline (spread 2.0 / slippage 0.5 / comm 3.5),
  multiplier 1.0, tamanho fixo 0.01 lote, EURUSD M15.
- Lockbox: as janelas terminam exatamente em 2024-01-01; o OOS
  (2024-2027) não é tocado (guarda mecânica em `research/walkforward.py`).

## 3. Resultados (custo explícito)

### TIME-SERIES-MOMENTUM

| janela | train→val | sel | train_exp | trades | net_profit | return_pct | expectancy | pf |
|---|---|---|---|---|---|---|---|---|
| WF-01 | 2015→2017 | 96 | -0.3033 | 213 | 15.22 | 0.1522 | 0.0715 | 1.0616 |
| WF-02 | 2016→2018 | 96 | -0.2196 | 226 | -91.38 | -0.9138 | -0.4043 | 0.7106 |
| WF-03 | 2017→2019 | 96 | -0.1612 | 195 | -91.56 | -0.9156 | -0.4695 | 0.6047 |
| WF-04 | 2018→2020 | 192 | -0.2950 | 151 | 58.61 | 0.5861 | 0.3881 | 1.2968 |
| WF-05 | 2019→2021 | 192 | 0.1136 | 144 | -109.94 | -1.0994 | -0.7635 | 0.4495 |
| WF-06 | 2020→2022 | 160 | -0.1511 | 238 | -96.67 | -0.9667 | -0.4062 | 0.7232 |
| WF-07 | 2021→2023 | 160 | -0.5662 | 182 | -55.76 | -0.5576 | -0.3064 | 0.7652 |

**2/7 positivas (29%)** · avg return −0.53% · avg expectancy −0.27 →
**REJECT**

Caso notável WF-05: a única janela com train expectancy positiva
(lookback=192, +0.11) produziu val de −1.10% — exemplo direto de
não-transferibilidade temporal.

### SIMPLE-EMA-TREND

| janela | train→val | sel | train_exp | trades | net_profit | return_pct | expectancy | pf |
|---|---|---|---|---|---|---|---|---|
| WF-01 | 2015→2017 | 10 | -0.5025 | 545 | -87.13 | -0.8713 | -0.1599 | 0.8654 |
| WF-02 | 2016→2018 | 30 | -0.2891 | 172 | 32.57 | 0.3257 | 0.1894 | 1.1145 |
| WF-03 | 2017→2019 | 30 | -0.0168 | 187 | -100.19 | -1.0019 | -0.5358 | 0.6021 |
| WF-04 | 2018→2020 | 30 | -0.3980 | 186 | -17.22 | -0.1722 | -0.0926 | 0.9446 |
| WF-05 | 2019→2021 | 30 | -0.3191 | 209 | -129.06 | -1.2906 | -0.6175 | 0.5405 |
| WF-06 | 2020→2022 | 30 | -0.3750 | 202 | -173.79 | -1.7379 | -0.8603 | 0.6047 |
| WF-07 | 2021→2023 | 10 | -0.6142 | 341 | -88.68 | -0.8868 | -0.2601 | 0.7712 |

**1/7 positivas (14%)** · avg return −0.89% · avg expectancy −0.39 →
**REJECT**

### SIMPLE-MEAN-REVERSION

| janela | train→val | sel | train_exp | trades | net_profit | return_pct | expectancy | pf |
|---|---|---|---|---|---|---|---|---|
| WF-01 | 2015→2017 | 8 | -0.4091 | 743 | -121.78 | -1.2178 | -0.1639 | 0.7759 |
| WF-02 | 2016→2018 | 8 | -0.4203 | 676 | -109.35 | -1.0935 | -0.1618 | 0.7888 |
| WF-03 | 2017→2019 | 8 | -0.2787 | 458 | -137.32 | -1.3732 | -0.2998 | 0.5118 |
| WF-04 | 2018→2020 | 8 | -0.3263 | 748 | -201.81 | -2.0181 | -0.2698 | 0.6376 |
| WF-05 | 2019→2021 | 32 | -0.2347 | 373 | -157.15 | -1.5715 | -0.4213 | 0.5333 |
| WF-06 | 2020→2022 | 16 | -0.2811 | 719 | -236.34 | -2.3634 | -0.3287 | 0.6439 |
| WF-07 | 2021→2023 | 16 | -0.3556 | 548 | -224.50 | -2.2450 | -0.4097 | 0.5218 |

**0/7 positivas (0%)** · avg return −1.82% · avg expectancy −0.33 →
**REJECT**

## 4. Conclusões

1. **Hipótese WF-01 rejeitada** para os três baselines: o edge não é
   transferível no tempo — 0–2 janelas positivas de 7, expectancy média
   negativa em todos.
2. **Consistente com F8**: os grids eram monotônicos e negativos; o
   walk-forward confirma que "o melhor do grid" por janela continua
   negativo (a maioria das train expectancies selecionadas é negativa —
   não existe ilha lucrativa para encontrar).
3. **Parâmetros selecionados oscilam** (TSM 96↔192, EMA 10↔30, MR
   8↔32), típico de overfitting a ruído por janela.
4. **Lockbox OOS permanece SELADO**: nenhuma estratégia passou no
   critério de aceite, portanto não há o que validar fora da amostra.
   (Uma consulta futura exigiria `--allow-oos` + evento logado,
   conforme docs/15 §7.)
5. Direção de pesquisa (consistente com docs/15): reconstrução de edge
   (filtros de regime, redução de turnover, melhora de payoff), não
   mais varredura de parâmetros.

## 5. Artefatos

- Harness: `research/walkforward.py` (CLI `python -m research.walkforward`)
- Testes: `tests/test_research_walkforward.py` (17 testes sintéticos)
- CSVs: `research/reports/{TIME_SERIES_MOMENTUM,EMA_TREND,MEAN_REVERSION}_walkforward.csv`
- Relatórios auditáveis completos (JSON + trades.csv) em
  `research/reports/` (tags `wf-WF-XX-val` e `sweep-*`)

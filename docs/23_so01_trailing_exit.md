# 23 — SO-01: Trailing ATR Exit no TSM (gestão de saída/payoff)

Status: **CONCLUÍDO — hipótese SO-01 rejeitada**. O trailing ATR em
M15 piora os resultados (aumenta turnover e expectancy negativa).
Achado secundário importante: o TSM tem edge bruto zero-cost marginal
que é totalmente destruído pelos custos de turnover.

Hipótese pré-registrada: `.cluster/payoff-exit/plan.md`.

---

## 1. Hipótese (pré-registrada)

Substituir o exit por momentum do TSM por um **trailing stop ATR**
(2× ATR, lookback 14, M15 fechado) deve deixar o lucro correr em
tendências, melhorar o payoff e a expectancy sob custos. Entradas
inalteradas; no modo trailing o exit por momentum é desligado.

Critérios de aceite (pré-registrados):

```text
net(trailing) > net(baseline)  E  expectancy > 0  E  trades >= 100
```

## 2. Implementação

- `strategy/time_series_momentum.py`: `exit_mode` ("momentum" default
  preserva o baseline; "trailing_atr" novo), `trail_atr_lookback=14`,
  `trail_atr_mult=2.0`; estado ratchet (`highest_close`), saída quando
  `close < highest_close - mult*ATR`; `reset()` limpa estado (engine
  chama por run). 8 testes sintéticos novos.

## 3. Resultados (EURUSD M15)

### Dev (2015-2021)

| run | cost | trades | net | ret% | wr% | pf | exp | dd% |
|---|---|---|---|---|---|---|---|---|
| baseline | zero | 1397 | +191.69 | +1.92 | 31.71 | 1.131 | +0.137 | 1.09 |
| trailing | zero | 3672 | +132.84 | +1.33 | 36.82 | 1.044 | +0.036 | 1.02 |
| baseline | explicit | 1397 | -325.20 | -3.25 | 26.06 | 0.823 | -0.233 | 3.78 |
| trailing | explicit | 3672 | -1225.80 | -12.26 | 30.01 | 0.688 | -0.334 | 12.30 |
| trail mult 1.5 | explicit | 5082 | -1880.88 | -18.81 | 28.12 | 0.604 | -0.370 | 18.81 |
| trail mult 3.0 | explicit | 2276 | -695.50 | -6.96 | 32.38 | 0.775 | -0.306 | 7.06 |
| trail lookback 10 | explicit | 3691 | -1272.71 | -12.73 | 29.40 | 0.679 | -0.345 | 12.80 |
| trail lookback 20 | explicit | 3682 | -1338.14 | -13.38 | 29.68 | 0.664 | -0.363 | 13.41 |

### Val (2021-2024)

| run | trades | net | ret% | exp |
|---|---|---|---|---|
| baseline | 700 | -314.59 | -3.15 | -0.449 |
| trailing | 1896 | -784.78 | -7.85 | -0.414 |

## 4. Análise

1. **O trailing ATR em M15 AUMENTA o turnover** (1397 → 3672 trades):
   a folga de 2× ATR é pequena na escala M15 → saídas prematuras +
   reentradas frequentes (o trailing não bloqueia reentrada). Cada
   ciclo extra paga 3.7 pips.
2. **Nenhuma configuração vence o baseline** (mult 1.5/2.0/3.0,
   lookback 10/14/20): o melhor trailing (mult 3.0, -695) ainda é
   pior que baseline (-325).
3. **Achado secundário (importante)**: zero-cost dev é POSITIVO no
   baseline (+191.69, expectancy +0.137). O edge bruto existe, é
   pequeno e é **destruído pelos custos de turnover**: 1397 trades ×
   ~0.37 USD de round-trip ≈ 517 USD de custo > 191 USD de lucro
   bruto. O TSM M15 não é viável sob custos por construção (frequência
   alta × edge pequeno).
4. **Veredito: REJECT** (critério falha: trailing pior que baseline e
   expectancy negativa). Lockbox OOS não consultado.

## 5. Conclusão do eixo "gestão de saída"

Entradas (RF-01) e saídas (SO-01) testadas: nenhuma modificação
resolve. A alavanca real é **turnover**: a próxima hipótese natural é
o mesmo TSM em **H1/H4** (menos trades, custo relativo menor por
movimento) — mesma lógica, escala maior. Alternativa: encerrar a
busca de edge e manter research/demo (roadmap §93).

## 6. Artefatos

- Código: `strategy/time_series_momentum.py` (commit `cc41714`)
- Testes: `tests/test_strategy_tsm_trailing.py` (8)
- Relatórios: `research/reports/TIME-SERIES-MOMENTUM_M15_*_so01-*.json`
- Plano pré-registrado: `.cluster/payoff-exit/plan.md`

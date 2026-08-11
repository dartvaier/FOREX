# 24 — TF-01: TSM em H1/H4 + Encerramento da Busca de Edge

Status: **CONCLUÍDO — TF-01 rejeitado; busca de edge encerrada**
(roadmap §93: a plataforma permanece research/demo).

Hipótese pré-registrada: `.cluster/tf-timeframe/plan.md`.

---

## 1. Hipótese (pré-registrada)

O TSM M15 tem edge bruto positivo (+1.9% dev zero-cost) destruído por
custos de turnover. Operar o mesmo TSM em H1/H4 reduz a frequência e
pode preservar o edge sob custos explícitos.

Critérios de aceite (pré-registrados): dev explicit `expectancy > 0`
E `net_profit > 0` E `trades >= 100`.

## 2. Resultados (EURUSD, custos 2.0/0.5/3.5)

| tf | período | cost | trades | net | ret% | exp | dd% |
|---|---|---|---|---|---|---|---|
| M15 | dev | zero | 1397 | +191.69 | +1.92 | +0.137 | 1.09 |
| M15 | dev | explicit | 1397 | -325.20 | -3.25 | -0.233 | 3.78 |
| M15 | val | explicit | 700 | -314.59 | -3.15 | -0.449 | 3.79 |
| H1 | dev | zero | 444 | +100.52 | +1.01 | +0.226 | 1.06 |
| H1 | dev | explicit | 444 | -63.76 | -0.64 | -0.144 | 1.67 |
| H1 | val | explicit | 251 | -207.02 | -2.07 | -0.825 | 2.51 |
| H4 | dev | zero | 178 | -95.83 | -0.96 | -0.538 | 2.06 |
| H4 | dev | explicit | 178 | -161.69 | -1.62 | -0.908 | 2.55 |
| H4 | val | explicit | 72 | -48.01 | -0.48 | -0.667 | 1.71 |

## 3. Análise

1. **H1 reduz o prejuízo 5× em dev** (M15 -325 → H1 -64): o turnover
   caiu (1397 → 444 trades). A direção esperada se confirma.
2. **Mas a expectancy permanece negativa** (dev -0.144, val -0.825):
   o edge bruto H1 (+100, exp +0.226 ≈ 2.3 pips/trade) é MENOR que o
   do M15 e ainda é consumido pelo custo residual (~164 USD de custo
   vs +100 USD de lucro bruto).
3. **H4 não tem edge bruto** (zero-cost -95): o sinal de momentum com
   lookback de 16 dias não captura movimento suficiente.
4. **Padrão estrutural**: o TSM ganha ~1.4–2.3 pips por trade bruto,
   sempre ABAIXO do custo de round-trip de 3.7 pips. Nenhuma
   modificação de entrada/saída/timeframe muda essa aritmética.

## 4. Encerramento da busca de edge (decisão registrada)

Evidência acumulada (F8 → docs/24):

```text
F8    grids monótonos negativos; sem ilhas de parâmetro
OOS   lockbox consultado 1x: todos negativos (sem --allow-oos depois)
WF    walk-forward: 0-2/7 janelas positivas; parâmetros oscilam
RF-01 filtro de regime: reduz perdas, não cria edge
SO-01 trailing ATR: aumenta turnover, piora
TF-01 H1/H4: reduz custo, edge bruto insuficiente (H1) ou ausente (H4)
MS    multi-par: 19/19 backtests negativos em dev
```

**Decisão (roadmap §93)**: nenhuma hipótese testada sobrevive à
validação sob custos explícitos. A busca de edge com as estratégias
baseline está ENCERRADA. A plataforma permanece como **research/demo
platform** (F0-F9 completos, execução demo validada, infra pronta
para capital real se o operador decidir — §92).

A fronteira seguinte (ML/HMM, §108-109) é um projeto de pesquisa
diferente, não uma continuação incremental — e só deve ser iniciada
com expectativa de longo prazo, sem promessa de edge.

## 5. Artefatos

- Relatórios: `research/reports/TIME-SERIES-MOMENTUM_*_tf01-*.json`
- Plano pré-registrado: `.cluster/tf-timeframe/plan.md`
- DECISIONS.md: entrada TF-01 + encerramento da busca

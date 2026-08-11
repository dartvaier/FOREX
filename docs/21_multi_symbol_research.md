# 21 — Pesquisa Multi-Symbol (roadmap §104): primeira leitura dev

Status: coleta completa dos 6 majors; backtests baseline em dev
(explicit). **Nenhum par apresenta edge com custos.** USDJPY expõe a
limitação multi-moeda do modelo de custo — valores monetários de
pares com quote ≠ USD são INVALIDOS até existir conversão de moeda.

---

## 1. Dados

Todos os 6 majors coletados (M15 2015-01-01 → 2026-08-10, ~288k
candles por par) + H1/H4 construídos:

```text
EURUSD (pré-existente) | GBPUSD | USDJPY | USDCHF | AUDUSD | USDCAD | NZDUSD
```

## 2. Resultados (dev 2015-2021, custos explícitos 2.0/0.5/3.5)

### Pares USD-quote (valores monetários VÁLIDOS em USD)

| par | estratégia | trades | net | ret% | wr% | pf | exp |
|---|---|---|---|---|---|---|---|
| EURUSD | TSM | 1397 | -325.20 | -3.25 | 26.06 | 0.823 | -0.233 |
| EURUSD | EMA | (F8) | - | - | - | - | - |
| EURUSD | MR | (F8) | - | - | - | - | - |
| GBPUSD | TSM | 1471 | -334.17 | -3.34 | 28.08 | 0.866 | -0.227 |
| USDCHF | TSM | 1543 | -798.66 | -7.99 | 24.37 | 0.613 | -0.518 |
| AUDUSD | TSM | 1640 | -657.40 | -6.57 | 23.90 | 0.646 | -0.401 |
| USDCAD | TSM | 1510 | -657.48 | -6.57 | 23.58 | 0.720 | -0.435 |
| NZDUSD | TSM | 1671 | -615.68 | -6.16 | 23.34 | 0.669 | -0.369 |
| USDCHF | EMA | 1493 | -912.47 | -9.12 | 25.32 | 0.590 | -0.611 |
| AUDUSD | EMA | 1444 | -613.57 | -6.14 | 25.00 | 0.683 | -0.425 |
| USDCAD | EMA | 1437 | -583.97 | -5.84 | 26.51 | 0.764 | -0.406 |
| NZDUSD | EMA | 1428 | -548.81 | -5.49 | 25.91 | 0.714 | -0.384 |
| USDCHF | MR | 3635 | -942.33 | -9.42 | 51.03 | 0.642 | -0.259 |
| AUDUSD | MR | 4345 | -1406.75 | -14.07 | 50.08 | 0.535 | -0.324 |
| USDCAD | MR | 3564 | -875.00 | -8.75 | 56.06 | 0.727 | -0.246 |
| NZDUSD | MR | 4588 | -1514.44 | -15.14 | 49.00 | 0.514 | -0.330 |

**Leitura**: todos os 16 backtests válidos são NEGATIVOS. Nenhum par
escapa do padrão do EURUSD; expectancies negativas em toda a matriz.

### USDJPY (corrigido pela conversão de moeda — docs/22)

| par | estratégia | trades | net | ret% | max_dd |
|---|---|---|---|---|---|
| USDJPY | TSM | 1401 | -401.21 | -4.01 | 4.04% |
| USDJPY | EMA | 1394 | -440.36 | -4.40 | 4.42% |
| USDJPY | MR | 3410 | -1291.99 | -12.92 | 12.99% |

Com a conversão quote→USD (docs/22), o USDJPY se alinha aos demais
pares: **todos negativos** — a conclusão desta seção permanece
com a matriz monetária íntegra. Round-trip em pips: 3.78
(comissão mais cara em pares de pip barato).

## 3. Conclusões

1. **Nenhum par com edge sob custos explícitos** — o resultado do
   EURUSD (F8 + WF + RF-01) generaliza para os 5 pares USD-quote.
2. **USDJPY fica fora da comparação monetária** até a conversão de
   moeda (extensão futura). O invariante em PIPS permanece válido.
3. Não há motivação para val/OOS multi-par enquanto dev for
   uniformemente negativo — a direção continua sendo reconstrução de
   edge (payoff/gestão de saída).

## 4. Artefatos

- Dados: `data/raw/{GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,NZDUSD}/M15.parquet`
  + `data/processed/*/{H1,H4}.parquet` (gitignored)
- Relatórios: `research/reports/*_M15_explicit_ms-*-dev.json` (15)
  + PoC GBPUSD
- Scripts: `.cluster/multi-symbol-mtf/{run_baselines,summarize_pairs}.py`

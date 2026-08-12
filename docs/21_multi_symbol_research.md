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

### Pares USD-quote (valores monetários em USD, rate 1.0)

| par | estratégia | trades | net | ret% | wr% | pf | exp |
|---|---|---|---|---|---|---|---|
| EURUSD | TSM | 1397 | -325.20 | -3.25 | 26.06 | 0.823 | -0.233 |
| EURUSD | EMA | (F8) | - | - | - | - | - |
| EURUSD | MR | (F8) | - | - | - | - | - |
| GBPUSD | TSM | 1471 | -334.17 | -3.34 | 28.08 | 0.866 | -0.227 |
| AUDUSD | TSM | 1640 | -657.40 | -6.57 | 23.90 | 0.646 | -0.401 |
| NZDUSD | TSM | 1671 | -615.68 | -6.16 | 23.34 | 0.669 | -0.369 |
| AUDUSD | EMA | 1444 | -613.57 | -6.14 | 25.00 | 0.683 | -0.425 |
| NZDUSD | EMA | 1428 | -548.81 | -5.49 | 25.91 | 0.714 | -0.384 |
| AUDUSD | MR | 4345 | -1406.75 | -14.07 | 50.08 | 0.535 | -0.324 |
| NZDUSD | MR | 4588 | -1514.44 | -15.14 | 49.00 | 0.514 | -0.330 |

**Leitura**: todos os 13 backtests USD-quote são NEGATIVOS.

### Pares USD-base (conversão completa — docs/22 + hardening MC-01..05)

Reexecutado em 2026-08-12 (docs/25 MC-05) no período dev formal
(2015-01-01..2021-01-01, custos explícitos). Trades IDÊNTICOS aos
da primeira leitura; os valores monetários de USDCHF/USDCAD agora
são convertidos para account currency (USD) — antes estavam em
moeda quote (CHF/CAD). USDJPY já estava convertido desde docs/22.

| par | estratégia | trades | net | ret% | pf | exp | max_dd |
|---|---|---|---|---|---|---|---|
| USDJPY | TSM | 1401 | -401.21 | -4.01 | 0.76 | -0.286 | 4.04% |
| USDCHF | TSM | 1543 | -860.80 | -8.61 | 0.60 | -0.558 | 8.69% |
| USDCAD | TSM | 1510 | -534.24 | -5.34 | 0.70 | -0.354 | 5.70% |
| USDJPY | EMA | 1394 | -440.36 | -4.40 | 0.76 | -0.316 | 4.42% |
| USDCHF | EMA | 1493 | -974.40 | -9.74 | 0.58 | -0.653 | 9.82% |
| USDCAD | EMA | 1437 | -473.58 | -4.74 | 0.75 | -0.330 | 5.16% |
| USDJPY | MR | 3410 | -1291.99 | -12.92 | 0.55 | -0.379 | 12.99% |
| USDCHF | MR | 3635 | -959.42 | -9.59 | 0.65 | -0.264 | 11.13% |
| USDCAD | MR | 3564 | -731.24 | -7.31 | 0.70 | -0.205 | 7.71% |

**Leitura**: com a matriz monetária íntegra (19/19 pares/estratégias
em USD), TODOS os backtests dev são NEGATIVOS. A conversão não
inverte nenhuma conclusão: nenhum par apresenta edge sob custos
explícitos. Round-trip em pips: 3.7 nos USD-quote; 3.63–4.05 nos
USD-base conforme o preço (comissão USD fixa = pips diferentes).

## 3. Conclusões

1. **Nenhum par com edge sob custos explícitos** — o resultado do
   EURUSD (F8 + WF + RF-01) generaliza para os 7 majors: 19/19
   backtests dev (3 estratégias x 7 pares, USD íntegro) NEGATIVOS.
2. **Matriz monetária íntegra desde o hardening MC-01..05**
   (docs/25): conversão quote→USD também em StopBasedRiskGate,
   ExposureLimitRiskGate e TradeFactory; USDCHF/USDCAD reclassificados
   como USD-base. O invariante em PIPS permanece válido.
3. Não há motivação para val/OOS multi-par enquanto dev for
   uniformemente negativo — a direção continua sendo reconstrução de
   edge (payoff/gestão de saída).

## 4. Artefatos

- Dados: `data/raw/{GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,NZDUSD}/M15.parquet`
  + `data/processed/*/{H1,H4}.parquet` (gitignored)
- Relatórios: `research/reports/*_M15_explicit_ms-*-dev.json` (15)
  + PoC GBPUSD
- Scripts: `.cluster/multi-symbol-mtf/{run_baselines,summarize_pairs}.py`

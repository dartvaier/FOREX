# 19 — RF-01: Filtro de Regime no TSM (reconstrução de edge)

Status: **CONCLUÍDO — hipótese RF-01 rejeitada** (filtro reduz perdas,
mas não cria edge; expectancy permanece negativa).

Hipótese pré-registrada: `.cluster/regime-filter/plan.md`.

---

## 1. Hipótese (pré-registrada)

O momentum time-series (TSM) lucra predominantemente em regimes de
ALTA volatilidade. Filtrar ENTRADAS para ocorrerem apenas quando a
volatilidade H4 recente está ACIMA da mediana histórica deve reduzir
turnover, melhorar a expectancy e produzir net profit > 0 em dev sob
custos explícitos.

Critérios de aceite (pré-registrados, decididos ANTES de ver
resultados):

```text
net_profit(regime on) > net_profit(baseline)  E
expectancy > 0                                 E
trades >= 100 (amostra mínima)
```

## 2. Implementação

- `strategy/time_series_momentum.py`: novo parâmetro
  `regime_filter="h4_vol_high"` (default `"none"` preserva o baseline
  exatamente — contrato de regressão intacto, 1043 testes verdes).
- Regime: `vol_recente = std(retornos log dos últimos 48 H4 fechados)`;
  `mediana = mediana(|retorno| dos últimos 250 H4 fechados)`;
  favorável quando `vol_recente > mediana`.
- Filtro de ENTRADA apenas: EXIT/HOLD do TSM inalterados.
- Causalidade garantida pelo engine (só H4 fechados via
  `BacktestContext.timeframe_bars`).
- 14 testes sintéticos novos (`tests/test_strategy_tsm_regime.py`).

## 3. Resultados (EURUSD M15, custos explícitos 2.0/0.5/3.5)

### Dev (2015-2021)

| run | trades | net_profit | return | win_rate | pf | expectancy | max_dd |
|---|---|---|---|---|---|---|---|
| baseline | 1397 | -325.20 | -3.2520% | 26.06 | 0.8229 | -0.2328 | 3.775% |
| regime24 | 1336 | -269.99 | -2.6999% | 26.20 | 0.8452 | -0.2021 | 3.691% |
| regime48 | 1341 | -273.68 | -2.7368% | 26.17 | 0.8438 | -0.2041 | 3.756% |
| regime96 | 1341 | -273.68 | -2.7368% | 26.17 | 0.8438 | -0.2041 | 3.756% |

### Val (2021-2024)

| run | trades | net_profit | return | win_rate | pf | expectancy | max_dd |
|---|---|---|---|---|---|---|---|
| baseline | 700 | -314.59 | -3.1459% | 23.71 | 0.6707 | -0.4494 | 3.792% |
| regime48 | 668 | -296.67 | -2.9667% | 23.20 | 0.6757 | -0.4441 | 3.593% |

## 4. Análise

1. **O filtro funciona na direção esperada**: reduz turnover (dev
   1397→1341, val 700→668) e corta entradas ruins — net melhora em dev
   (-325→-270, +17%) e val (-315→-297, +6%).
2. **Mas não cria edge**: a expectancy permanece negativa em todas as
   configurações (dev ≈ -0.20, val ≈ -0.44). O critério `expectancy > 0`
   FALHA → **RF-01 REJEITADA**.
3. **Sensibilidade estável, sem ilha**: regime_lookback 24/48/96 →
   net -270/-274/-274; comportamento suave e monotônico.
4. **Lockbox OOS permanece SELADO**: nada passou no critério; nenhuma
   consulta ao período 2024-2027.
5. Leitura: a seleção de entrada é apenas parte do problema — o custo
   round-trip (3.7 pips) combinado com win rate ~26% exige um payoff
   que o TSM não produz. Direção futura: payoff/gestão de saída, não
   mais seleção de entrada.

## 5. Artefatos

- Código: `strategy/time_series_momentum.py` (commit `22dfa82`)
- Testes: `tests/test_strategy_tsm_regime.py` (14)
- Relatórios auditáveis: `research/reports/TIME-SERIES-MOMENTUM_M15_explicit_rf01-*.json`
- Plano pré-registrado: `.cluster/regime-filter/plan.md`

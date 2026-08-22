# 31 — Alpha Ensemble Experiments

Este documento registra o fluxo operacional para testar a nova camada
de alpha ensemble adicionada a partir do roadmap `docs/30`.

Status atual:

- contratos core de alpha: implementados;
- TSMOM alpha e EMA alpha: implementados;
- ensemble, ledger, diagnostics: implementados;
- regime gating, hysteresis e cost-aware gating: implementados;
- configuracao declarativa YAML: implementada;
- helper multi-symbol: implementado;
- importador JForex/Dukascopy: implementado;
- primeira execucao historica local: concluida com datasets M15 dos 7 majors.

## 1. Configuracoes Disponiveis

Single-symbol:

```text
config/strategies/ensemble_low_turnover_v1.yaml
```

Multi-symbol:

```text
config/strategies/ensemble_low_turnover_multi_symbol_v1.yaml
```

A configuracao multi-symbol declara os 7 majors:

```text
AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY
```

Ela usa `pip_size: auto`, resolvido pelo registry central em
`backtest/instruments.py`. Isso evita usar `0.00010` por engano em
USDJPY, cujo pip size e `0.01`.

## 2. Preparar Dados

O runner precisa do M15 raw:

```text
data/raw/<SYMBOL>/M15.parquet
```

Quando os dados vierem do MT5, para cada simbolo:

```powershell
python collect_history.py --symbol EURUSD
python build_timeframes.py --symbol EURUSD
```

Repetir para:

```text
AUDUSD
EURUSD
GBPUSD
NZDUSD
USDCAD
USDCHF
USDJPY
```

Quando os dados vierem do JForex/Dukascopy, exporte Bid e Ask em M15
e importe todos os arquivos de uma vez:

```powershell
python import_jforex.py --input-dir data/import/JForex
```

Se a pasta estiver fora do repositorio local, informe o caminho completo:

```powershell
python import_jforex.py --input-dir C:\Users\Gabriel\Desktop\FOREX\data\import\JForex
```

O importador combina Bid/Ask em preco medio, calcula `spread` em pontos
compativeis com o campo do MT5, arredonda o volume combinado para
`tick_volume` inteiro e grava:

```text
data/raw/<SYMBOL>/M15.parquet
data/processed/<SYMBOL>/H1.parquet
data/processed/<SYMBOL>/H4.parquet
```

Por padrao ele corrige inconsistencias pequenas de extremos OHLC comuns
em exportacoes arredondadas do JForex, garantindo apenas que `high`
contenha `open/close` e que `low` contenha `open/close`. Para auditoria
estrita:

```powershell
python import_jforex.py --input-dir data/import/JForex --strict-ohlc
```

## 3. Preflight Multi-Symbol

O helper `research.multi_symbol` checa os datasets antes de executar.
Se faltar algum M15, ele falha cedo e lista todos os caminhos ausentes.

Execucao padrao:

```powershell
python -m research.multi_symbol --cost explicit --tag dev
```

Executar apenas simbolos com dataset disponivel:

```powershell
python -m research.multi_symbol --cost explicit --tag dev --skip-missing
```

Limitar manualmente pares:

```powershell
python -m research.multi_symbol --symbols EURUSD,USDJPY --cost explicit --tag dev
```

Rodar zero-cost e explicit-cost:

```powershell
python -m research.multi_symbol --cost both --tag dev
```

## 4. Saidas

Cada execucao por par continua usando `research.runner` e gera os
relatorios normais em:

```text
research/reports/
```

O helper tambem grava um resumo agregado:

```text
research/reports/multi_symbol_<strategy>_<timeframe>_<cost>_<tag>.json
research/reports/multi_symbol_<strategy>_<timeframe>_<cost>_<tag>.csv
```

Os reports ficam gitignored por design.

## 5. Criterios de Leitura

Para cada simbolo, comparar:

- trades;
- net profit;
- return pct;
- max drawdown pct;
- win rate;
- profit factor;
- expectancy;
- round-trip cost em pips.

Leitura minima esperada:

1. zero-cost mostra se existe edge bruto;
2. explicit-cost mostra se o edge cobre friccao;
3. reducao de turnover so importa se preservar ou melhorar expectancy;
4. multi-symbol so avanca para portfolio agregado se houver resultado
   positivo e estavel por simbolo.

## 6. Primeira Execucao Real

Fonte:

```text
JForex/Dukascopy Bid+Ask M15, 2015-01-01 -> 2026-08-21
```

Comando:

```powershell
python -m research.multi_symbol --cost both --tag alpha-ensemble-dev
```

Resumo agregado:

```text
research/reports/multi_symbol_declarative_ensemble_M15_both_alpha-ensemble-dev.csv
```

| Symbol | Cost | Trades | Net PnL | Return % | Max DD % | PF | Expectancy | Cost pips |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AUDUSD | explicit | 2068 | -1192.76 | -11.93 | 12.11 | 0.722 | -0.5768 | 3.70 |
| AUDUSD | zero | 2068 | -427.61 | -4.28 | 4.49 | 0.887 | -0.2068 | 0.00 |
| EURUSD | explicit | 1957 | -670.17 | -6.70 | 7.86 | 0.852 | -0.3424 | 3.70 |
| EURUSD | zero | 1957 | 53.92 | 0.54 | 2.48 | 1.013 | 0.0276 | 0.00 |
| GBPUSD | explicit | 2354 | -886.65 | -8.87 | 9.59 | 0.866 | -0.3767 | 3.70 |
| GBPUSD | zero | 2354 | -15.66 | -0.16 | 4.53 | 0.997 | -0.0067 | 0.00 |
| NZDUSD | explicit | 1987 | -855.53 | -8.56 | 8.86 | 0.782 | -0.4306 | 3.70 |
| NZDUSD | zero | 1987 | -120.34 | -1.20 | 2.67 | 0.965 | -0.0606 | 0.00 |
| USDCAD | explicit | 2065 | -816.20 | -8.16 | 8.82 | 0.795 | -0.3953 | 3.93 |
| USDCAD | zero | 2065 | -202.68 | -2.03 | 4.14 | 0.943 | -0.0982 | 0.00 |
| USDCHF | explicit | 1804 | -834.95 | -8.35 | 8.55 | 0.804 | -0.4628 | 3.65 |
| USDCHF | zero | 1804 | -124.71 | -1.25 | 2.58 | 0.967 | -0.0691 | 0.00 |
| USDJPY | explicit | 2617 | -307.95 | -3.08 | 4.15 | 0.942 | -0.1177 | 3.88 |
| USDJPY | zero | 2617 | 510.47 | 5.10 | 1.82 | 1.106 | 0.1951 | 0.00 |

Leitura:

- o ensemble atual ainda nao possui edge bruto robusto nos 7 majors;
- EURUSD fica praticamente flat em zero-cost e negativo com custo;
- USDJPY e o unico par com edge bruto mais claro, mas ainda nao cobre
  friccao explicita;
- o proximo trabalho deve focar diagnostico por alpha, por regime e por
  custo medido antes de qualquer portfolio agregado.

## 7. Medicao de Spreads JForex

Comando:

```powershell
python -m research.cost_measurement --out research/reports/cost_measurement_jforex_all.json
```

| Symbol | Spread med | Spread p90 | RT overall med | RT weekly med |
|---|---:|---:|---:|---:|
| AUDUSD | 1.00 | 1.40 | 2.70 | 2.70 |
| EURUSD | 0.30 | 0.60 | 2.00 | 2.10 |
| GBPUSD | 0.90 | 1.60 | 2.60 | 2.70 |
| NZDUSD | 1.10 | 1.70 | 2.80 | 2.80 |
| USDCAD | 1.20 | 1.80 | 2.90 | 3.00 |
| USDCHF | 1.00 | 1.90 | 2.70 | 2.80 |
| USDJPY | 0.40 | 0.90 | 2.10 | 2.20 |

Leitura: os spreads medianos importados do JForex sao menores que o
baseline fixo de 2.0 pips usado nos backtests `explicit`, mas ainda
ha slippage e comissao no round-trip. O proximo passo deve comparar
`explicit` fixo contra custo calibrado por simbolo, sem mudar a regra
de entrada ainda.

## 8. Execucao Com Spread Calibrado

Comando:

```powershell
python -m research.multi_symbol --cost both --tag alpha-ensemble-calibrated --calibrated-spread --calibration-path research/reports/cost_measurement_jforex_all.json
```

Resumo agregado:

```text
research/reports/multi_symbol_declarative_ensemble_M15_both_alpha-ensemble-calibrated.csv
```

| Symbol | Cost | Trades | Net PnL | Return % | Max DD % | PF | Expectancy | Cost pips |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AUDUSD | explicit | 2068 | -985.96 | -9.86 | 10.05 | 0.763 | -0.4768 | 2.70 |
| AUDUSD | zero | 2068 | -427.61 | -4.28 | 4.49 | 0.887 | -0.2068 | 0.00 |
| EURUSD | explicit | 1957 | -337.48 | -3.37 | 4.84 | 0.922 | -0.1724 | 2.00 |
| EURUSD | zero | 1957 | 53.92 | 0.54 | 2.48 | 1.013 | 0.0276 | 0.00 |
| GBPUSD | explicit | 2354 | -627.71 | -6.28 | 7.43 | 0.903 | -0.2667 | 2.60 |
| GBPUSD | zero | 2354 | -15.66 | -0.16 | 4.53 | 0.997 | -0.0067 | 0.00 |
| NZDUSD | explicit | 1987 | -676.71 | -6.77 | 7.17 | 0.822 | -0.3406 | 2.80 |
| NZDUSD | zero | 1987 | -120.34 | -1.20 | 2.67 | 0.965 | -0.0606 | 0.00 |
| USDCAD | explicit | 2065 | -691.15 | -6.91 | 7.82 | 0.823 | -0.3347 | 3.13 |
| USDCAD | zero | 2065 | -202.68 | -2.03 | 4.14 | 0.943 | -0.0982 | 0.00 |
| USDCHF | explicit | 1804 | -640.30 | -6.40 | 6.68 | 0.845 | -0.3549 | 2.65 |
| USDCHF | zero | 1804 | -124.71 | -1.25 | 2.58 | 0.967 | -0.0691 | 0.00 |
| USDJPY | explicit | 2617 | 30.84 | 0.31 | 2.25 | 1.006 | 0.0118 | 2.28 |
| USDJPY | zero | 2617 | 510.47 | 5.10 | 1.82 | 1.106 | 0.1951 | 0.00 |

Leitura:

- custo calibrado melhora todos os pares frente ao `explicit` fixo;
- USDJPY passa de negativo para levemente positivo apos custo;
- o edge ainda e fraco: profit factor 1.006 e expectancy 0.0118;
- antes de qualquer portfolio, USDJPY precisa de analise temporal,
  diagnostico por alpha e stress de custo.

## 9. Diagnostico por Alpha — USDJPY

Comando:

```powershell
python -m research.alpha_diagnostic_matrix --symbol USDJPY --cost both --calibrated-spread --calibration-path research/reports/cost_measurement_jforex_all.json
```

Resumo agregado:

```text
research/reports/alpha_diagnostics/alpha_diagnostic_matrix_USDJPY_both.csv
```

| Variant | Cost | Trades | Net PnL | Return % | Max DD % | PF | Expectancy | Cost pips |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ema_only | explicit | 8078 | -921.26 | -9.21 | 9.69 | 0.887 | -0.1140 | 2.27 |
| ema_only | zero | 8078 | 568.23 | 5.68 | 1.21 | 1.080 | 0.0703 | 0.00 |
| ensemble_cost_gate | explicit | 2617 | 30.84 | 0.31 | 2.25 | 1.006 | 0.0118 | 2.28 |
| ensemble_cost_gate | zero | 2617 | 510.47 | 5.10 | 1.82 | 1.106 | 0.1951 | 0.00 |
| ensemble_raw | explicit | 4973 | -281.85 | -2.82 | 4.01 | 0.956 | -0.0567 | 2.27 |
| ensemble_raw | zero | 4973 | 635.78 | 6.36 | 1.41 | 1.109 | 0.1278 | 0.00 |
| ensemble_regime | explicit | 1617 | 74.82 | 0.75 | 2.03 | 1.023 | 0.0463 | 2.27 |
| ensemble_regime | zero | 1617 | 374.52 | 3.75 | 1.77 | 1.120 | 0.2316 | 0.00 |
| ensemble_regime_cost | explicit | 1104 | 253.14 | 2.53 | 2.00 | 1.090 | 0.2293 | 2.27 |
| ensemble_regime_cost | zero | 1104 | 457.25 | 4.57 | 1.69 | 1.170 | 0.4142 | 0.00 |
| tsmom_only | explicit | 2201 | -94.59 | -0.95 | 2.73 | 0.975 | -0.0430 | 2.28 |
| tsmom_only | zero | 2201 | 308.46 | 3.08 | 2.26 | 1.086 | 0.1401 | 0.00 |

Leitura:

- TSMOM e EMA possuem edge bruto em zero-cost, mas nao cobrem custo
  calibrado sozinhos;
- EMA tem turnover muito alto, o que destrói o resultado apos custo;
- ensemble bruto melhora edge bruto, mas ainda perde apos custo;
- cost gate atual torna o ensemble levemente positivo;
- regime gate melhora profit factor e reduz trades;
- regime + cost gate e a melhor variante ate aqui: 1104 trades,
  `+2.53%`, PF 1.090, expectancy 0.2293 apos custo calibrado.

Conclusao provisoria: para USDJPY, o sinal promissor nao e um alpha
isolado. Ele aparece quando o ensemble e filtrado por regime e custo.
O proximo passo deve testar se isso e estavel por janelas temporais e
sob stress de custo antes de promover a variante.

## 10. Proximos Passos

1. Avaliar USDJPY `ensemble_regime_cost` por janelas temporais e stress
   de custo.
2. Calibrar tambem o `cost_gate.cost_estimate_pips` declarativo por
   simbolo, em vez de manter 3.7 pips fixo para todos.
3. Rodar o mesmo diagnostico nos outros pares para confirmar se USDJPY
   e caso isolado ou padrao repetivel.
4. Ajustar filtros de turnover/conviccao apenas com hipoteses
   predefinidas.
5. Se houver edge robusto apos custo, planejar portfolio multi-symbol agregado,
   exposicao por moeda e limites de risco consolidados.

Enquanto isso nao acontecer, o projeto permanece em modo research/demo.

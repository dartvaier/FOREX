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
- execucao historica local: pendente de datasets M15 em `data/raw`.

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

Para cada simbolo:

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

## 6. Proximos Passos

1. Restaurar/coletar M15 para os 7 majors.
2. Rodar `python -m research.multi_symbol --cost both --tag alpha-ensemble-dev`.
3. Abrir o CSV agregado e comparar resultados por par.
4. Atualizar este documento com a tabela real.
5. Se houver edge robusto, planejar portfolio multi-symbol agregado,
   exposicao por moeda e limites de risco consolidados.

Enquanto isso nao acontecer, o projeto permanece em modo research/demo.

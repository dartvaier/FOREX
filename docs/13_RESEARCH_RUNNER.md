# Research Runner

Ferramenta reproduzível para rodar backtests de pesquisa sobre o
`BacktestEngine` e gravar um pacote de auditoria em `research/reports/`.

O runner é uma camada fina de orquestração. Toda a semântica de simulação
(bar-by-bar, sem look-ahead, candles fechados, UTC, custos explícitos,
worst-case intrabar) pertence ao `BacktestEngine` e seus componentes.

## Arquivos

| Arquivo | Função |
|---|---|
| `research/runner.py` | Roda um backtest de pesquisa e grava JSON + trades CSV |
| `research/summarize.py` | Lê os relatórios e imprime tabela comparativa |
| `research/reports/` | Saída dos backtests (JSON + CSV por execução) |

## Como rodar

Do diretório raiz do projeto, com o venv ativo:

```powershell
.\.venv\Scripts\python.exe -m research.runner --strategy ema_trend
```

O padrão roda os dois modelos de custo (zero e explícito) no período
completo do dataset. Exemplos:

```powershell
# Uma estratégia, só custo explícito
python -m research.runner --strategy asian_range_breakout --cost explicit

# Alterando parâmetros da estratégia
python -m research.runner --strategy time_series_momentum --param lookback=192 --param entry_threshold=0.002

# Restringindo o período (janela de treino / OOS)
python -m research.runner --strategy ema_trend --date-from 2015-01-01 --date-to 2020-12-31

# Timeframe derivado (H1 / H4)
python -m research.runner --strategy ema_trend --timeframe H1

# Gravando também a curva de equity completa
python -m research.runner --strategy mean_reversion --equity-csv

# Cost stress (F8): baseline, 1.5x e 2.0x dos custos explícitos
python -m research.runner --strategy time_series_momentum --cost explicit --cost-multiplier 1.5 --tag cost1x5
python -m research.runner --strategy time_series_momentum --cost explicit --cost-multiplier 2.0 --tag cost2x
```

### Opções principais

| Opção | Padrão | Descrição |
|---|---|---|
| `--strategy` | obrigatório | Chave no registro: `ema_trend`, `volatility_breakout`, `time_series_momentum`, `mean_reversion`, `asian_range_breakout`, `carry`, `regime_detection`, `multi_timeframe_momentum` |
| `--symbol` | `EURUSD` | Instrumento (registro em `research/runner.py`) |
| `--timeframe` | `M15` | `M15` (raw) ou `H1`/`H4` (processed) |
| `--date-from` / `--date-to` | período completo | Janela UTC (`YYYY-MM-DD` ou ISO-8601); `date_to` é exclusivo |
| `--initial-capital` | `10000.0` | Capital inicial |
| `--fixed-quantity` | `0.01` | Tamanho de posição em lotes |
| `--cost` | `both` | `zero`, `explicit` ou `both` |
| `--spread-pips` | `2.0` | Spread (pips) do `FixedCostModel` |
| `--slippage-pips` | `0.5` | Slippage por lado (pips) |
| `--commission` | `3.50` | Comissão por lote por lado (USD) |
| `--cost-multiplier` | `1.0` | Multiplicador de stress aplicado a spread, slippage e comissão (F8; ignorado em `zero`) |
| `--param KEY=VALUE` | — | Sobrescreve parâmetro da estratégia (repetível) |
| `--tag` | vazio | Sufixo nos nomes dos relatórios para distinguir variações da mesma estratégia (ex.: `--tag V1`) |
| `--equity-csv` | off | Grava também a curva de equity |

## Cost Stress (F8)

O `--cost-multiplier` escala os três parâmetros de custo explícito pelo mesmo
fator, preservando a estrutura relativa do `FixedCostModel`:

```text
multiplier 1.0  -> custo baseline
multiplier 1.5  -> stress moderado
multiplier 2.0  -> stress forte
```

O relatório JSON registra de forma auditável:

```text
config.cost_params          -> parâmetros BASE (não escalados)
config.cost_multiplier      -> fator de stress aplicado
cost_analysis.round_trip_*  -> custo efetivo (já escalado)
```

Isso permite comparar a fragilidade de uma estratégia ao custo: se 1.5x ou 2.0x
destroem o resultado, o edge é frágil (repo §17). O `research.summarize` exibe
a coluna `cost_multiplier` para comparar execuções lado a lado.

## Sensibilidade Local e Subperiodos (F8)

O `research/sweep.py` orquestra execuções do runner com disciplina de
sensibilidade local (repo §15-16): **um parâmetro por vez**, grid declarado
antes de rodar, comparação por regiões de estabilidade — nunca seleção do
máximo.

```powershell
# Sensibilidade local: lookback 96→192 com passo 32 (fim inclusivo)
python -m research.sweep --strategy time_series_momentum --range lookback=96:192:32 --cost explicit

# Lista explícita de valores
python -m research.sweep --strategy mean_reversion --values lookback=32,48,64

# Parâmetros fixos permanecem fixos durante o sweep
python -m research.sweep --strategy time_series_momentum --range lookback=96:192:32 --param entry_threshold=0.002

# Subperiods padrão F8 (roadmap §73): 2015-17, 2018-20, 2021-23, 2024-26
python -m research.sweep --strategy ema_trend --subperiods --cost explicit
```

Cada execução produz um relatório auditável completo via `run_single`
(com tag `sweep-<key>=<value>` ou `sub-<period>`). O resumo comparativo sai
em `<out>/<STRATEGY>_sweep_<key>.csv` (ou `_subperiods.csv`) com:

```text
param_value | period | trades | net_profit | return_pct | max_dd_pct
win_rate | profit_factor | expectancy | cost | cost_multiplier
```

Regras:

- `--range key=start:end:step` e `--values key=v1,v2,v3` são mutuamente
  exclusivos com `--subperiods`.
- O parâmetro varrido é validado contra os campos do dataclass da estratégia.
- Em `--subperiods`, as janelas são fixas (pré-definidas antes de ver resultados).

## Saída

Para cada execução, em `research/reports/`:

- `<STRATEGY>_<TF>_<cost>.json` — relatório consolidado:
  - metadados do dataset (caminho, linhas, sha256 do Parquet);
  - configuração completa (parâmetros, custos, políticas do engine);
  - performance (`PerformanceSummary` completo: trades, win rate,
    profit factor, net profit, expectativa, drawdown);
  - breakdown por lado (long/short) e por motivo de saída;
  - análise de custo (custo de round-trip em USD e pips).
- `<STRATEGY>_<TF>_<cost>.trades.csv` — um trade por linha, com custos
  discriminados (spread, slippage, comissão) e `exit_reason`.

A tabela comparativa:

```powershell
python -m research.summarize
python -m research.summarize --csv
```

## Adicionando uma estratégia nova

1. Implemente a estratégia em `strategy/` seguindo o contrato
   (`on_bar(context) -> Signal`, `closed_bar_limit`, `reset`).
2. Adicione a chave no `STRATEGY_REGISTRY` em `research/runner.py`:
   `"nome": "strategy.meu_modulo"`.
3. Rode `python -m research.runner --strategy nome`.

O runner descobre automaticamente a classe da estratégia no módulo e
valida `--param` contra os campos do dataclass.

Estratégias multi-timeframe podem declarar:

```text
higher_timeframes
```

Quando isso existir, o runner carrega automaticamente os datasets
processados necessários (`H1`/`H4`) e entrega ao `BacktestEngine`.

## Reproducibilidade

Cada relatório registra:

- versão do schema do relatório e data de geração;
- sha256 do Parquet de origem;
- parâmetros exatos (estratégia, custos, engine, janela);
- políticas do engine (`ambiguous_bar_policy`, `end_of_backtest_policy`,
  `allow_incomplete_bars`).

Qualquer mudança que altere resultados de backtests antigos deve ser
registrada em `DECISIONS.md` e `CHANGELOG.md`, conforme a regra do
projeto, para que relatórios de versões diferentes não sejam comparados
diretamente.

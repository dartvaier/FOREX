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
```

### Opções principais

| Opção | Padrão | Descrição |
|---|---|---|
| `--strategy` | obrigatório | Chave no registro: `ema_trend`, `volatility_breakout`, `time_series_momentum`, `mean_reversion`, `asian_range_breakout`, `carry`, `regime_detection` |
| `--symbol` | `EURUSD` | Instrumento (registro em `research/runner.py`) |
| `--timeframe` | `M15` | `M15` (raw) ou `H1`/`H4` (processed) |
| `--date-from` / `--date-to` | período completo | Janela UTC (`YYYY-MM-DD` ou ISO-8601); `date_to` é exclusivo |
| `--initial-capital` | `10000.0` | Capital inicial |
| `--fixed-quantity` | `0.01` | Tamanho de posição em lotes |
| `--cost` | `both` | `zero`, `explicit` ou `both` |
| `--spread-pips` | `2.0` | Spread (pips) do `FixedCostModel` |
| `--slippage-pips` | `0.5` | Slippage por lado (pips) |
| `--commission` | `3.50` | Comissão por lote por lado (USD) |
| `--param KEY=VALUE` | — | Sobrescreve parâmetro da estratégia (repetível) |
| `--tag` | vazio | Sufixo nos nomes dos relatórios para distinguir variações da mesma estratégia (ex.: `--tag V1`) |
| `--equity-csv` | off | Grava também a curva de equity |

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

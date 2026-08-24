# F5.9 — First Strategy: EMA Crossover

`EmaCrossoverStrategy` é a primeira Strategy de engenharia do projeto. O
baseline é EURUSD H1, com `fast_period` e `slow_period` configuráveis e a
restrição `fast_period < slow_period`. Não há pesquisa ou otimização de
parâmetros nesta fase.

A Strategy recebe apenas `BacktestContext`. Em `BAR_CLOSE`, ela calcula EMAs
causais a partir de `closed_bars`: cada EMA é inicializada pela SMA da sua
primeira janela e atualizada apenas com fechamentos já disponíveis. O warm-up é
explícito: são necessários `slow_period + 1` candles fechados para comparar a
EMA atual à anterior. Antes disso, e na ausência de cruzamento, o resultado é
`HOLD`.

```text
fast anterior <= slow anterior e fast atual > slow atual -> ENTER_LONG
fast anterior >= slow anterior e fast atual < slow atual -> ENTER_SHORT
caso contrário                                      -> HOLD
```

Os sinais são direcionais, não ordens. Com o baseline de F5.5, uma entrada
contrária enquanto há posição aberta é uma rejeição normal do RiskModel: a
Strategy não consulta nem tenta controlar a posição, e não existe reversal
automático. O fechamento explícito de posições será definido por uma regra de
saída posterior, sem acoplar esta Strategy ao Portfolio.

## Runner mínimo

O runner carrega um Parquet real H1 de EURUSD, constrói feed, Strategy, risco,
custos, execução e Portfolio, e retorna/escreve um `PerformanceReport`:

```powershell
python -m experiments.run_ema_crossover data/processed/EURUSD/H1.parquet `
  --fast-period 20 --slow-period 50 --quantity 1 `
  --output outputs/ema_h1_report.json
```

Custos podem ser declarados por `--spread`, `--slippage` e
`--commission-per-unit`. Sharpe continua indisponível até que
`--periods-per-year` seja informado explicitamente, conforme F5.8.

O runner solicita ao Engine somente os últimos `slow_period + 1` candles no
Context. A EMA mantém seu estado causal enquanto as barras avançam, portanto
essa limitação reduz memória sem alterar sinais nem tornar dados futuros
visíveis à Strategy.

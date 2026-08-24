# Checkpoint de arquitetura — F5.1 a F5.8

Antes da primeira Strategy, o backtester possui uma separação explícita de
responsabilidades:

```text
Strategy -> Signal -> RiskModel -> OrderIntent -> SimulatedExecution -> Fill
                                                                    -> Portfolio
BacktestResult ----------------------------------------------------> PerformanceAnalytics
```

| Fase | Responsabilidade concluída | Não pertence à camada |
|---|---|---|
| F5.1 | `Signal`, `OrderIntent`, `Fill` imutáveis | execução, risco e PnL |
| F5.2 | relógio, feed e `BacktestContext` sem futuro | decisão de mercado |
| F5.3 | `Position`, `Portfolio` e snapshots | Strategy e custos |
| F5.4 | estimativa determinística de spread, slippage e comissão | criação de Fill ou Portfolio |
| F5.5 | aprovação e tamanho final de ordens | preços, execução e PnL |
| F5.6 | Fill na próxima abertura disponível | Strategy, Risk, Portfolio ou MT5 |
| F5.7 | orquestração temporal e histórico bruto | regras de cada componente |
| F5.8 | relatório analítico somente leitura | mutação do backtest ou contabilidade |

Invariantes preservados: timestamps UTC, barras imutáveis, Signal on Close /
Next Available Open, gaps preservados, uma posição por símbolo, sem pyramiding,
sem hedge, sem reversal automático e resultados determinísticos. Uma Strategy
não recebe feed, Portfolio, RiskModel, CostModel, executor ou MT5; sua fronteira
de informação é somente `BacktestContext`.

F5.9 adiciona uma Strategy dentro dessa fronteira. Ela não altera contratos nem
redistribui responsabilidades já estabelecidas.

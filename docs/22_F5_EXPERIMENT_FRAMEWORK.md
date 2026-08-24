# F5.10 — Experiment Framework e validação out-of-sample

`ExperimentSpec` e `TemporalSplit` são imutáveis e registram dataset, símbolo,
timeframe, intervalos, parâmetros de Strategy/Risk/Cost e capital inicial. O
fingerprint SHA-256 é calculado da representação JSON canônica dessa
configuração; não existe busca, grade ou otimização automática nesta fase.

O split exige `train_start < train_end <= test_start < test_end`. O
`ExperimentRunner` instancia Strategy, RiskModel, CostModel, Portfolio e
BacktestEngine separadamente para in-sample e out-of-sample, produzindo um
`PerformanceReport` independente em cada janela.

Warm-up usa apenas as últimas barras anteriores ao começo da janela. A Strategy
as observa para inicializar indicadores, mas o Engine bloqueia decisão de risco,
ordens, fills, snapshots, trades e PnL até a primeira barra da janela avaliada.
Não há shuffle, preenchimento de gaps ou reaproveitamento de Portfolio entre
janelas. Assim, o out-of-sample não herda posição, caixa ou estado de execução
do in-sample.

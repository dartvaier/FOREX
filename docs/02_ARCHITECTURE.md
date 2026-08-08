Esse documento registrará como reproduzir o ambiente de desenvolvimento utilizado atualmente.
# Architecture

## 1. Objetivo

Este documento define a arquitetura da plataforma **FOREX Algorithmic Trading Research Platform**.

Seu objetivo é estabelecer:

- responsabilidades de cada módulo;
- limites entre componentes;
- fluxo de dados;
- dependências permitidas;
- componentes implementados;
- componentes planejados;
- regras de comunicação entre camadas;
- invariantes arquiteturais;
- princípios para evolução futura do projeto.

A arquitetura deve impedir que o sistema evolua para um conjunto de scripts fortemente acoplados.

O princípio central é:

```text
Cada componente deve possuir
uma responsabilidade claramente definida.
```

---

# 2. Estado Atual

No marco atual do projeto estão implementadas as seguintes camadas:

```text
Broker Integration
       ↓
Market Data
       ↓
Historical Data
       ↓
Data Quality
       ↓
Timeframe Transformation
```

Componentes implementados:

```text
MT5Client
MarketData
HistoricalData
TimeframeBuilder
Parquet Storage
Metadata Generation
Data Quality Analysis
Automated Tests
```

Componentes ainda planejados:

```text
BacktestEngine
Strategy Engine
Signal Model
CostModel
Risk Engine
Portfolio
Execution Engine
Performance Analytics
Experiment Manager
Monitoring
Demo Trading
```

É importante manter essa distinção.

Um componente documentado como planejado não deve ser considerado funcional até possuir implementação e testes.

---

# 3. Visão Geral da Arquitetura

A arquitetura completa pretendida é:

```text
                         ┌─────────────────────┐
                         │    MetaTrader 5     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      MT5Client      │
                         │      broker/        │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
           ┌─────────────────┐             ┌─────────────────┐
           │   MarketData    │             │ HistoricalData  │
           │      data/      │             │      data/      │
           └────────┬────────┘             └────────┬────────┘
                    │                               │
                    │                               ▼
                    │                        ┌──────────────┐
                    │                        │   Parquet    │
                    │                        └──────┬───────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ TimeframeBuilder    │
                         │       data/         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Validated Datasets  │
                         │   M15 / H1 / H4     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                     ┌───────────────────────────┐
                     │      BacktestEngine       │
                     │         backtest/         │
                     └────────────┬──────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
     ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
     │  Strategy   │       │    Risk     │       │  CostModel  │
     │ strategy/   │       │   risk/     │       │ backtest/   │
     └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  ▼
                         ┌─────────────────────┐
                         │      Portfolio      │
                         │ Positions / Equity  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Performance      │
                         │ Metrics / Trades    │
                         └─────────────────────┘
```

Na execução futura em conta Demo, parte do fluxo será compartilhada, mas o `BacktestEngine` será substituído por uma camada de execução em tempo real.

---

# 4. Estrutura de Diretórios

Estrutura arquitetural principal:

```text
FOREX/
│
├── broker/
│   ├── __init__.py
│   └── mt5_client.py
│
├── data/
│   ├── __init__.py
│   ├── market_data.py
│   ├── historical_data.py
│   ├── timeframe_builder.py
│   │
│   ├── raw/
│   ├── processed/
│   └── metadata/
│
├── strategy/
│
├── risk/
│
├── execution/
│
├── backtest/
│
├── monitoring/
│
├── config/
│
├── tests/
│
└── docs/
```

Cada diretório representa uma responsabilidade diferente.

---

# 5. Broker Layer

Diretório:

```text
broker/
```

Responsabilidade:

> Encapsular comunicação com APIs ou plataformas externas de mercado.

Implementação atual:

```text
broker/mt5_client.py
```

Classe principal:

```text
MT5Client
```

O `MT5Client` é responsável apenas por comunicação com o MetaTrader 5.

Exemplos de responsabilidades válidas:

```text
initialize()
shutdown()
account_info()
symbol_info()
symbol_info_tick()
copy_rates_from_pos()
copy_rates_range()
```

Exemplos de responsabilidades que não pertencem ao `MT5Client`:

```text
calcular EMA
gerar sinal
calcular risco
calcular Sharpe
resample H1
decidir entrada
realizar backtest
```

O broker adapter deve funcionar como uma fronteira entre:

```text
Aplicação
   ↕
Broker externo
```

---

# 6. Regra de Isolamento do Broker

Outros componentes não devem chamar diretamente:

```python
MetaTrader5
```

quando existir uma abstração equivalente no `MT5Client`.

Exemplo preferido:

```python
client.current_tick("EURUSD")
```

em vez de:

```python
mt5.symbol_info_tick("EURUSD")
```

espalhado pelo projeto.

Isso reduz acoplamento com o MetaTrader 5.

No futuro, uma arquitetura semelhante poderá permitir:

```text
MT5Client
DukascopyClient
BrokerXClient
HistoricalProviderClient
```

sem exigir reescrever toda a plataforma.

---

# 7. Market Data Layer

Arquivo:

```text
data/market_data.py
```

Classe:

```text
MarketData
```

Responsabilidade:

> Transformar dados de mercado obtidos através do broker em estruturas consistentes para consumo pelo restante do sistema.

Responsabilidades atuais:

```text
obter candles fechados
normalizar timestamps
manter UTC
obter Bid
obter Ask
calcular spread atual
determinar point
determinar pip size
```

`MarketData` conhece:

```text
MT5Client
```

mas não deve conhecer:

```text
Strategy
BacktestEngine
Risk
Execution
```

---

# 8. Regra de Candle Fechado

A camada `MarketData` possui uma das invariantes mais importantes do sistema:

```text
Dados destinados à estratégia
não devem incluir deliberadamente
a barra corrente ainda em formação.
```

No MetaTrader 5:

```text
bar 0 = barra mais recente
```

Para séries utilizadas pela estratégia:

```text
start_pos = 1
```

é atualmente utilizado para excluir a barra corrente.

Existe um teste automatizado específico para essa propriedade.

---

# 9. Historical Data Layer

Arquivo:

```text
data/historical_data.py
```

Classe:

```text
HistoricalData
```

Responsabilidade:

> Coletar, validar e persistir séries históricas.

Fluxo:

```text
HistoricalData
      │
      ▼
MT5Client.rates_range()
      │
      ▼
download em chunks
      │
      ▼
normalização
      │
      ▼
validação
      │
      ▼
Parquet
```

A coleta histórica é realizada em blocos em vez de uma única requisição muito grande.

Configuração utilizada atualmente:

```text
chunk_days = 90
```

---

# 10. Responsabilidades do HistoricalData

A camada deve garantir, no mínimo:

```text
timezone UTC
ordem cronológica
timestamps únicos
OHLC válido
preços positivos
dataset não vazio
```

Ela também deve impedir que respostas anômalas do broker sejam aceitas silenciosamente.

Quando o broker retorna candles fora da janela solicitada, os registros devem ser filtrados pela janela efetivamente requisitada.

---

# 11. Raw Data

Diretório:

```text
data/raw/
```

Representa dados obtidos da fonte com o mínimo de transformação necessário para normalização e integridade.

Dataset atual:

```text
data/raw/EURUSD/M15.parquet
```

Características:

```text
Símbolo: EURUSD
Timeframe: M15
Timezone: UTC
Fonte: MetaQuotes-Demo
```

O objetivo do `raw/` é preservar a fonte base utilizada para derivar outros datasets.

---

# 12. Processed Data

Diretório:

```text
data/processed/
```

Contém datasets derivados da fonte base.

Atualmente:

```text
data/processed/EURUSD/H1.parquet
data/processed/EURUSD/H4.parquet
```

Esses arquivos são construídos a partir de:

```text
M15
```

e não coletados como fontes independentes nesta fase.

---

# 13. Metadata Layer

Diretório:

```text
data/metadata/
```

Responsabilidade:

> Registrar informações sobre origem, cobertura e limitações dos datasets.

Exemplo atual:

```text
EURUSD_M15.json
```

A metadata deve permitir responder:

```text
qual é a fonte?
qual símbolo?
qual timeframe?
qual período?
quantas barras?
qual timezone?
há limitações conhecidas?
spread é confiável?
real_volume é confiável?
```

No futuro a metadata deverá ser expandida para datasets processados e experimentos.

---

# 14. Timeframe Transformation Layer

Arquivo:

```text
data/timeframe_builder.py
```

Classe:

```text
TimeframeBuilder
```

Responsabilidade:

> Construir timeframes superiores de maneira determinística a partir do timeframe base.

Fluxo atual:

```text
M15
 ├── H1
 └── H4
```

Agregação OHLC:

```text
Open  = primeiro Open
High  = maior High
Low   = menor Low
Close = último Close
```

Tick volume:

```text
tick_volume = soma dos candles fonte
```

---

# 15. Integridade de Timeframes Derivados

Cada timeframe possui uma quantidade esperada de candles fonte.

H1:

```text
4 × M15
```

H4:

```text
16 × M15
```

Cada candle derivado possui:

```text
source_bar_count
expected_bar_count
complete
```

Exemplo:

```text
source_bar_count   = 15
expected_bar_count = 16
complete           = False
```

Isso impede que agregações incompletas sejam tratadas silenciosamente como candles normais.

---

# 16. Política para Candles Incompletos

Candles incompletos são preservados.

Eles não devem ser:

```text
apagados silenciosamente
preenchidos artificialmente
considerados válidos por padrão
```

A regra planejada para estratégias e backtests é:

```python
df[df["complete"]]
```

ou comportamento equivalente.

Isso mantém:

```text
dataset de auditoria
        ↓
completos + incompletos
```

separado de:

```text
dataset de estratégia
        ↓
somente candles válidos
```

---

# 17. Strategy Layer

Diretório futuro:

```text
strategy/
```

Status:

```text
PLANEJADO
```

Responsabilidade:

> Transformar informações disponíveis do mercado em intenção de operação.

A Strategy não deverá enviar ordens.

Entrada conceitual:

```text
Market State
```

Saída conceitual:

```text
Signal
```

Exemplo:

```text
Market Data
    ↓
Strategy
    ↓
LONG
```

ou:

```text
SHORT
FLAT
EXIT
```

---

# 18. Estratégia Não Controla Execução

Arquitetura incorreta:

```text
Strategy
   ↓
order_send()
```

Arquitetura pretendida:

```text
Strategy
   ↓
Signal
   ↓
Risk
   ↓
Order Intent
   ↓
Execution
```

Isso permite testar a mesma estratégia em:

```text
Backtest
Demo
Live futuro
```

sem alterar sua lógica central.

---

# 19. Signal Model

Status:

```text
PLANEJADO
```

Um sinal deverá futuramente possuir informações explícitas.

Exemplo conceitual:

```text
symbol
timestamp
side
strategy_id
reason
metadata
```

Possíveis lados:

```text
LONG
SHORT
EXIT
FLAT
```

A especificação definitiva será feita durante o design do Backtest Engine.

---

# 20. Risk Layer

Diretório futuro:

```text
risk/
```

Status:

```text
PLANEJADO
```

Responsabilidade:

> Determinar se uma intenção de operação pode ser executada e com qual tamanho.

A camada de risco deverá responder perguntas como:

```text
A operação é permitida?
Qual o tamanho máximo?
Qual o risco monetário?
O limite diário foi atingido?
Existe posição conflitante?
O drawdown excedeu o limite?
```

A Strategy não deve calcular diretamente o lote final.

---

# 21. Fluxo Strategy → Risk

Fluxo esperado:

```text
Strategy
   │
   ▼
Signal
   │
   ▼
Risk Engine
   │
   ├── REJECT
   │
   └── APPROVE
          │
          ▼
      Order Intent
```

Uma estratégia pode gerar um sinal válido e ainda assim o Risk Engine rejeitar sua execução.

---

# 22. Cost Model

Status:

```text
PLANEJADO
```

Responsabilidade:

> Modelar custos associados à execução simulada.

O CostModel deverá ser independente da Strategy.

Custos possíveis:

```text
spread
commission
slippage
swap
```

Arquitetura pretendida:

```text
Order
  ↓
CostModel
  ↓
Execution Price + Costs
```

---

# 23. Razão para CostModel Independente

O histórico atual mostrou que:

```text
spread do candle MT5
```

não é suficientemente consistente para ser tratado automaticamente como custo real.

Separar o CostModel permite:

```text
FixedSpreadModel
ConservativeSpreadModel
TickBidAskModel
BrokerHistoricalCostModel
```

e testes de estresse:

```text
cost × 1.0
cost × 1.5
cost × 2.0
```

sem modificar a Strategy.

---

# 24. Backtest Layer

Diretório:

```text
backtest/
```

Status:

```text
PLANEJADO
```

Componente principal futuro:

```text
BacktestEngine
```

Responsabilidade:

> Simular cronologicamente a interação entre estratégia, risco, execução, posições e custos.

O BacktestEngine deverá controlar o relógio da simulação.

---

# 25. Controle Temporal do Backtest

Princípio central:

```text
O BacktestEngine controla o tempo.
```

A Strategy não deve poder consultar livremente dados futuros.

Fluxo conceitual:

```text
bar t disponível
      ↓
Strategy recebe somente dados disponíveis
      ↓
gera Signal
      ↓
Risk avalia
      ↓
ordem é criada
      ↓
execução ocorre segundo regras definidas
      ↓
Portfolio é atualizado
      ↓
avança para t+1
```

---

# 26. Event Ordering

A ordem dos eventos dentro do BacktestEngine será explicitamente documentada antes da implementação.

Exemplo conceitual:

```text
1. abrir nova barra
2. processar ordens pendentes
3. atualizar stops / exits
4. atualizar posição
5. disponibilizar candle fechado
6. calcular estratégia
7. gerar novos sinais
8. aplicar risco
9. registrar novas ordens
```

Essa sequência é apenas ilustrativa neste documento.

A ordem definitiva será especificada em:

```text
docs/10_BACKTEST_DESIGN.md
```

antes da implementação.

---

# 27. Execution Layer

Diretório:

```text
execution/
```

Status:

```text
PLANEJADO
```

Sua responsabilidade futura será executar ordens aprovadas.

Durante backtest:

```text
SimulatedExecution
```

Durante Demo:

```text
MT5Execution
```

Possível arquitetura futura:

```text
ExecutionInterface
       │
       ├── SimulatedExecution
       └── MT5Execution
```

Isso permite que Strategy e Risk permaneçam independentes do ambiente de execução.

---

# 28. Order Model

Status:

```text
PLANEJADO
```

Uma ordem futura poderá possuir informações como:

```text
symbol
side
quantity
order_type
requested_price
stop_loss
take_profit
timestamp
strategy_id
```

O modelo definitivo será definido durante a implementação do Backtest Engine e Execution Engine.

---

# 29. Fill Model

Uma ordem e uma execução são conceitos diferentes.

```text
Order
  ↓
Execution
  ↓
Fill
```

Um `Fill` representa a execução efetiva.

Informações conceituais:

```text
fill_price
fill_time
quantity
slippage
commission
```

Essa separação será especialmente importante quando o sistema evoluir para simulações mais realistas.

---

# 30. Portfolio Layer

Status:

```text
PLANEJADO
```

Responsabilidade:

> Manter o estado financeiro da simulação.

Possíveis responsabilidades:

```text
cash
equity
positions
realized PnL
unrealized PnL
exposure
margin
trade history
```

A Strategy não deve calcular diretamente o equity da conta.

---

# 31. Position Model

Uma posição futura deverá representar o estado de exposição em um instrumento.

Exemplo conceitual:

```text
symbol
side
quantity
entry_price
entry_time
unrealized_pnl
stop_loss
take_profit
```

A especificação final será definida junto ao Portfolio e BacktestEngine.

---

# 32. Performance Layer

Status:

```text
PLANEJADO
```

Responsabilidade:

> Transformar trades e curva de capital em métricas quantitativas.

Possíveis métricas:

```text
Net Profit
CAGR
Maximum Drawdown
Sharpe Ratio
Sortino Ratio
Profit Factor
Win Rate
Average Win
Average Loss
Payoff
Expectancy
Exposure
Trade Count
```

Performance não deve alterar decisões de execução durante o backtest.

É uma camada de análise.

---

# 33. Monitoring Layer

Diretório:

```text
monitoring/
```

Status:

```text
PLANEJADO
```

Responsabilidades futuras:

```text
logs
health checks
erros de conexão
estado do broker
estado da estratégia
posição atual
PnL
risk limits
kill switch
```

Essa camada terá importância maior durante execução Demo e futura execução real.

---

# 34. Configuration Layer

Diretório:

```text
config/
```

Responsabilidade futura:

> Centralizar configurações do sistema.

Configurações não devem ficar espalhadas por diversos arquivos Python.

Exemplos futuros:

```text
symbol
timeframe
dataset
risk limits
broker settings
cost model
strategy parameters
logging
```

Credenciais não devem ser versionadas.

---

# 35. Environment Variables

Arquivo local:

```text
.env
```

Exemplo atual:

```env
TRADING_ENABLED=false
MT5_SYMBOL=EURUSD
MT5_TIMEFRAME=M15
```

Credenciais futuras, se necessárias, deverão permanecer fora do Git.

O arquivo:

```text
.env
```

deve estar no:

```text
.gitignore
```

---

# 36. Dependency Direction

Uma das regras arquiteturais mais importantes é a direção das dependências.

Preferido:

```text
Broker
  ↑
Data
  ↑
Backtest
  ↑
Application
```

Com componentes especializados conectados ao Backtest:

```text
Strategy
Risk
CostModel
Portfolio
```

Dependências circulares devem ser evitadas.

Exemplo indesejado:

```text
Strategy imports BacktestEngine
BacktestEngine imports Strategy
```

---

# 37. Regras de Dependência

Regras pretendidas:

```text
broker/
    não depende de strategy/
    não depende de backtest/
    não depende de risk/

data/
    pode depender de broker/
    não depende de strategy/
    não depende de backtest/

strategy/
    não depende de broker diretamente
    não envia ordens
    não conhece MetaTrader5

risk/
    não depende de MetaTrader5 diretamente

backtest/
    pode orquestrar strategy, risk, cost e portfolio

execution/
    pode depender de broker/
    não deve conter lógica de estratégia
```

Essas regras reduzem acoplamento.

---

# 38. Arquitetura de Execução Futura

Backtest:

```text
Historical Dataset
       ↓
BacktestEngine
       ↓
Strategy
       ↓
Risk
       ↓
SimulatedExecution
       ↓
Portfolio
```

Demo futura:

```text
MetaTrader 5
      ↓
MarketData
      ↓
Strategy
      ↓
Risk
      ↓
MT5Execution
      ↓
Broker
```

A lógica da Strategy deve permanecer essencialmente a mesma entre os dois ambientes.

---

# 39. Separação entre Signal e Order

Uma regra fundamental será:

```text
Signal != Order
```

Exemplo:

```text
Strategy:
"Quero ficar LONG."

             ↓

Signal

             ↓

Risk:
"Permitido, tamanho 0.10."

             ↓

Order Intent

             ↓

Execution:
"Executado a X."
```

Isso impede que decisões de risco sejam acopladas às estratégias.

---

# 40. Separação entre Order e Fill

Outra distinção importante:

```text
Order != Fill
```

Uma ordem pode:

```text
ser executada
ser rejeitada
ser parcialmente executada
sofrer slippage
```

Mesmo que o primeiro Backtest Engine utilize um modelo simplificado, a arquitetura deve permitir evolução posterior.

---

# 41. Data Invariants

As seguintes propriedades são consideradas invariantes da camada de dados.

## Timezone

```text
UTC timezone-aware
```

## Ordem

```text
timestamps crescentes
```

## Duplicação

```text
timestamp único por símbolo/timeframe
```

## OHLC

```text
High >= Open
High >= Close
High >= Low

Low <= Open
Low <= Close
```

## Preços

```text
preço > 0
```

## Candle corrente

```text
não utilizado como candle fechado
```

Essas propriedades devem possuir testes automatizados.

---

# 42. Backtest Invariants

Quando o BacktestEngine for desenvolvido, novas invariantes deverão existir.

Exemplos planejados:

```text
nenhum dado futuro acessível
nenhum fill antes da ordem
nenhuma saída antes da entrada
PnL consistente com posição
custos sempre aplicados conforme CostModel
equity consistente com cash + posições
```

Essas regras deverão ser testadas automaticamente.

---

# 43. Risk Invariants

Exemplos futuros:

```text
posição nunca excede limite configurado
risco por trade respeita limite
trading disabled impede execução
daily loss limit bloqueia novas operações
kill switch bloqueia execução
```

Essas invariantes são especialmente importantes antes da fase Demo.

---

# 44. Read-Only Boundary Atual

O estado atual do projeto possui uma fronteira de segurança explícita:

```text
READ ONLY
```

A integração atual consulta:

```text
conta
símbolo
ticks
candles
histórico
```

mas não implementa execução de ordens.

Não existe atualmente fluxo:

```text
Signal → order_send()
```

---

# 45. Trading Flag

Configuração prevista:

```env
TRADING_ENABLED=false
```

Quando a execução for implementada, essa flag não deverá ser a única proteção.

Ela será apenas uma entre várias barreiras de segurança.

---

# 46. Test Architecture

Diretório:

```text
tests/
```

Atualmente existem testes para:

```text
MarketData
HistoricalData
TimeframeBuilder
```

Estado:

```text
25 tests
25 passed
```

A estratégia de testes deve crescer junto com a arquitetura.

---

# 47. Tipos de Testes

## Unit Tests

Testam componentes isolados.

Exemplo futuro:

```text
CostModel
Position sizing
PnL calculation
EMA strategy
```

Não devem depender de MT5 sempre que possível.

## Integration Tests

Validam interação com sistemas externos.

Exemplo atual:

```text
MT5 connection
current quote
current bar
closed bars
```

Esses testes podem exigir o terminal MetaTrader 5 aberto.

## Regression Tests

Serão utilizados futuramente para garantir que resultados conhecidos não mudaram devido a alterações inesperadas.

Exemplo:

```text
dataset pequeno
strategy fixa
resultado esperado fixo
```

---

# 48. Determinismo

Backtests devem ser determinísticos sempre que possível.

Isto significa:

```text
mesmo código
mesmo dataset
mesmos parâmetros
mesmo CostModel

        ↓

mesmo resultado
```

Caso exista aleatoriedade, por exemplo em Monte Carlo, deverá existir:

```text
random_seed
```

registrado.

---

# 49. Experiment Reproducibility

Um experimento futuro deverá registrar:

```text
experiment_id
strategy_version
dataset
symbol
timeframe
date_from
date_to
parameters
cost_model
risk_config
code_version
metrics
```

Isso permitirá reproduzir resultados posteriormente.

---

# 50. Logging

Logging será preferível a `print()` em componentes permanentes.

Os scripts atuais utilizam prints para diagnóstico e desenvolvimento.

No futuro:

```text
logging/
```

ou configuração equivalente deverá registrar:

```text
timestamp
level
component
event
context
```

Exemplos:

```text
INFO
WARNING
ERROR
CRITICAL
```

---

# 51. Error Handling

Erros externos não devem ser silenciosamente ignorados.

Exemplo:

```text
MT5 retorna None
```

deve resultar em:

```text
erro explícito
+
last_error()
```

Em coleta histórica, determinadas falhas podem ser tratadas por chunk, mas devem ser registradas.

---

# 52. Fail Fast

Quando uma invariável essencial for violada, o sistema deve preferir falhar explicitamente.

Exemplo:

```text
OHLC inválido
timezone ausente
dataset vazio
timestamp duplicado
```

é preferível:

```text
raise ValueError(...)
```

a tentar corrigir silenciosamente o dado.

---

# 53. Evitar Correções Silenciosas

Exemplos indesejados:

```python
df = df.ffill()
```

sem justificativa.

```python
df = df.drop_duplicates()
```

sem registrar que duplicados existiram.

```python
price = abs(price)
```

para corrigir valor inválido.

Transformações devem ser explícitas e justificadas.

---

# 54. Data Lineage

A origem dos datasets deve ser rastreável.

Atualmente:

```text
MetaQuotes-Demo
      ↓
EURUSD M15 raw
      ↓
TimeframeBuilder
      ├── H1
      └── H4
```

No futuro, datasets deverão possuir metadata suficiente para registrar essa linhagem.

---

# 55. Source of Truth

Para a etapa atual:

```text
M15 raw
```

é a fonte primária para os timeframes intraday derivados.

H1 e H4 são produtos derivados.

Isso significa:

```text
M15 → source of truth intraday atual
```

para essa pipeline.

---

# 56. Daily Timeframe

Daily ainda não faz parte da transformação atual.

Ele deverá ser tratado separadamente.

Motivo:

```text
Daily candle boundary
```

pode depender do timezone e horário de fechamento utilizado pela fonte/broker.

Não devemos simplesmente assumir que:

```text
00:00 UTC
```

é universalmente a fronteira correta para D1.

---

# 57. Session-Based Strategies

Estratégias futuras relacionadas a sessões deverão utilizar timezones reais.

Exemplos:

```text
Europe/London
America/New_York
```

Não utilizar:

```text
GMT fixo
```

para representar Londres ao longo de todo o ano.

A conversão deve considerar DST.

---

# 58. Architecture Principle: Simple First

O sistema deve implementar primeiro versões simples e verificáveis.

Exemplo:

```text
Simple BacktestEngine
        ↓
testes
        ↓
custos básicos
        ↓
testes
        ↓
features avançadas
```

Não devemos começar diretamente com:

```text
event bus complexo
distributed processing
machine learning pipeline
microservices
```

sem necessidade.

---

# 59. Architecture Principle: Auditability

Resultados importantes devem ser auditáveis.

Deve ser possível responder:

```text
por que esse trade ocorreu?
qual candle gerou o sinal?
qual preço foi usado?
qual custo foi aplicado?
qual posição existia?
qual regra de risco aprovou?
```

Isso será especialmente importante durante análise de backtests.

---

# 60. Architecture Principle: Replaceability

Componentes externos devem ser substituíveis.

Exemplo:

```text
MT5Client
```

não deve determinar toda a arquitetura.

No futuro deve ser possível adicionar outra fonte sem reescrever:

```text
Strategy
Risk
Performance
Backtest
```

---

# 61. Architecture Principle: No Hidden State

Evitar estado global oculto.

Exemplo indesejado:

```python
CURRENT_POSITION = ...
GLOBAL_BALANCE = ...
```

espalhado pelo projeto.

Estado relevante deve pertencer a objetos explícitos:

```text
Portfolio
Position
BacktestState
BrokerState
```

---

# 62. Architecture Principle: Explicit Time

O tempo deve ser explícito.

Evitar componentes que consultem:

```python
datetime.now()
```

durante backtests para determinar o relógio da simulação.

O BacktestEngine deverá fornecer o tempo corrente simulado.

Isso ajuda a impedir vazamento entre:

```text
tempo real
```

e:

```text
tempo histórico simulado
```

---

# 63. Architecture Principle: Explicit Costs

Custos nunca devem estar escondidos dentro de uma estratégia.

Exemplo incorreto:

```python
if signal:
    price += 0.0001
```

dentro da Strategy.

Preferido:

```text
Signal
  ↓
Execution
  ↓
CostModel
```

---

# 64. Architecture Principle: Explicit Risk

Da mesma forma:

```text
Strategy
```

não deve possuir regras globais de risco da conta.

A estratégia pode eventualmente definir características como:

```text
stop técnico
```

mas:

```text
capital risk
position sizing
daily loss
portfolio exposure
```

pertencem à camada de risco.

---

# 65. Evolução Prevista

A evolução arquitetural pretendida é:

```text
v0.1
Data Infrastructure

        ↓

v0.2
Backtesting Infrastructure

        ↓

v0.3
Initial Strategies

        ↓

v0.4
Risk Management

        ↓

v0.5
Robustness / OOS

        ↓

v0.6
Demo Execution

        ↓

versões futuras
```

Esses números representam roadmap lógico e podem ser ajustados no `CHANGELOG`.

---

# 66. Arquitetura Atual Resumida

```text
IMPLEMENTADO

MetaTrader 5
     ↓
MT5Client
     ↓
MarketData
     ↓
HistoricalData
     ↓
Parquet
     ↓
TimeframeBuilder
     ↓
M15 / H1 / H4
     ↓
Validation
     ↓
25 Automated Tests
```

---

# 67. Arquitetura Futura Resumida

```text
Validated Data
     ↓
BacktestEngine
     ↓
Strategy
     ↓
Signal
     ↓
Risk
     ↓
Order
     ↓
Execution
     ↓
Fill
     ↓
Portfolio
     ↓
Performance
```

---

# 68. Regra Arquitetural Principal

A regra central para futuras implementações é:

> Uma Strategy expressa intenção.  
> O Risk Engine decide se essa intenção pode se transformar em ordem.  
> A Execution Layer determina como a ordem é executada.  
> O Portfolio registra o resultado financeiro.  
> O BacktestEngine controla o tempo e orquestra o processo.

Nenhum desses componentes deve assumir silenciosamente as responsabilidades dos demais.

---

# 69. Estado do Documento

Arquitetura documentada no marco:

```text
FOREX v0.1
```

Componentes implementados:

```text
Broker Integration       COMPLETE
Market Data              COMPLETE
Historical Data          COMPLETE
Data Transformation      COMPLETE
Automated Tests          25 / 25
```

Próximo documento:

```text
docs/03_ENVIRONMENT_SETUP.md
```

Esse documento registrará como reproduzir o ambiente de desenvolvimento utilizado atualmente.
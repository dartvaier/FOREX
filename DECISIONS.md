# Architecture & Engineering Decisions

## RF-01 (2026-08-10): Filtro de regime — reduz perda, nao cria edge

- **Decisao**: hipotese RF-01 REJEITADA (expectancy permanece
  negativa em dev e val apesar da melhora de net profit).
- **Racional**: filtro de entrada por vol H4 (h4_vol_high) corta
  trades ruins e melhora net (-17% dev, -6% val), mas o problema
  central e payoff/custos: win rate ~26% com round-trip de 3.7 pips
  nao produz expectancy positiva.
- **Consequencia**: proxima direcao de pesquisa e gestao de SAIDA
  (payoff/trailing/exits), nao mais selecao de entrada. Lockbox OOS
  permanece selado. Implementacao do filtro mantida no codigo
  (default none, sem impacto em regressao) como ferramenta para
  combinacoes futuras.

## WF-01 (2026-08-10): Walk-Forward — nenhum edge transferivel

- **Decisao**: hipotese WF-01 REJEITADA para os tres baselines
  (TSM 2/7, EMA 1/7, MR 0/7 janelas positivas sob custos explicitos).
- **Racional**: selecao por expectancy em train rolando nao produz
  val positivo na maioria das janelas; parametros selecionados oscilam
  (overfitting a ruido por janela); consistente com F8 (grids
  monotonos negativos).
- **Consequencia**: lockbox OOS permanece selado; proxima direcao e
  reconstrucao de edge (regime/turnover/payoff), nao varredura de
  parametros.

## 1. Objetivo

Este documento registra decisões arquiteturais e de engenharia importantes da plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

O objetivo é preservar o contexto das decisões para que, no futuro, seja possível responder perguntas como:

```text
Por que usamos UTC?

Por que H1/H4 são derivados do M15?

Por que gaps não são preenchidos?

Por que o spread histórico do MT5 não é usado diretamente?

Por que o sinal não executa no mesmo Close?

Por que Stop e Take Profit ambíguos usam worst-case?
```

O formato é inspirado em:

```text
Architecture Decision Records
ADR
```

---

# 2. Status Possíveis

Cada decisão utiliza um dos seguintes estados:

```text
ACCEPTED
```

Decisão adotada como regra atual do projeto.

```text
PROPOSED
```

Decisão ainda em análise.

```text
SUPERSEDED
```

Decisão substituída por outra posterior.

```text
DEPRECATED
```

Não deve mais ser utilizada.

Além disso, este documento diferencia:

```text
IMPLEMENTED
```

de:

```text
IMPLEMENTATION PENDING
```

Uma decisão pode já estar aceita arquiteturalmente mesmo que o código correspondente ainda pertença a uma fase futura.

---

# ADR-001 — UTC como Timezone Interno

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

Dados financeiros podem ser fornecidos em:

```text
horário do broker
horário local
UTC
horário de sessão
```

Utilizar vários fusos internamente aumentaria o risco de:

```text
desalinhamento de candles
erro de sessão
erro de DST
look-ahead
comparações temporais incorretas
```

## Decisão

Todo timestamp interno do projeto deve utilizar:

```text
UTC
```

e ser:

```text
timezone-aware
```

## Consequências

Dados de:

```text
M15
H1
H4
ticks
backtests
experimentos
```

devem permanecer em UTC.

Conversões para sessões específicas devem acontecer apenas quando necessário.

Exemplos:

```text
Europe/London

America/New_York
```

Offsets fixos não devem substituir timezones reais quando houver DST.

---

# ADR-002 — Candle Corrente Não é Candle Fechado

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

No MetaTrader 5:

```text
bar 0
```

representa a barra mais recente.

Durante mercado ativo ela normalmente ainda está em formação.

Utilizar seu OHLC final aparente como dado fechado pode gerar:

```text
repainting
look-ahead
sinais inconsistentes
```

## Decisão

Dados destinados a estratégias devem utilizar apenas candles já considerados fechados.

Na integração corrente:

```python
start_pos = 1
```

é utilizado pela `MarketData` para excluir deliberadamente a barra mais recente.

## Proteção

Existe teste automatizado:

```text
test_closed_bars_do_not_include_current_bar
```

## Consequências

A futura Strategy Layer não deverá acessar diretamente:

```text
bar 0
```

como candle fechado.

---

# ADR-003 — M15 como Fonte Intraday Canônica Atual

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

O projeto necessita inicialmente de:

```text
M15
H1
H4
```

Coletar cada timeframe independentemente poderia criar diferenças de:

```text
fronteira temporal
gaps
fonte
alinhamento
```

## Decisão

O dataset:

```text
EURUSD M15
```

é a fonte canônica intraday atual.

H1 e H4 são derivados de M15.

Fluxo:

```text
M15 Raw
   ↓
TimeframeBuilder
   ├── H1
   └── H4
```

## Consequências

H1/H4 são:

```text
processed data
```

e podem ser regenerados.

O M15 possui prioridade de preservação.

---

# ADR-004 — Gaps Não São Preenchidos Artificialmente

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

O histórico possui descontinuidades temporais causadas por:

```text
fim de semana
feriados
feed
manutenção
outras causas
```

Preencher automaticamente esses períodos com:

```python
ffill()
```

criaria candles que não existiram na fonte.

## Decisão

Não criar candles artificiais para preencher gaps.

## Consequências

Uma série como:

```text
10:00
10:15
10:30
11:00
```

permanece sem:

```text
10:45
```

Indicadores e estratégias deverão lidar com a série realmente observada.

---

# ADR-005 — Candles Agregados Incompletos São Preservados

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

O pandas consegue construir um H1 ou H4 mesmo que parte dos M15 esperados esteja ausente.

O OHLC resultante pode parecer estruturalmente válido.

## Decisão

Cada candle processado registra:

```text
source_bar_count
expected_bar_count
complete
```

## Regra

H1:

```text
expected_bar_count = 4
```

H4:

```text
expected_bar_count = 16
```

Completude:

```text
complete =
source_bar_count == expected_bar_count
```

## Consequências

Candles parciais permanecem disponíveis para:

```text
auditoria
diagnóstico
data quality
```

em vez de serem silenciosamente apagados.

---

# ADR-006 — Estratégias Devem Utilizar Apenas Candles Completos por Padrão

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING NO BACKTEST
```

## Contexto

Um candle H4 com:

```text
15 M15
```

não representa quatro horas completas, mesmo que tenha OHLC válido.

## Decisão

A política padrão da futura Strategy/Backtest Layer será utilizar:

```text
complete == True
```

## Consequências

Candles:

```text
complete=False
```

não devem gerar sinais por padrão.

Exceções precisarão ser explicitamente justificadas e documentadas.

---

# ADR-007 — Parquet como Formato Principal das Séries Históricas

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

As séries históricas precisam preservar:

```text
tipos
timezone
estrutura
```

e permitir leitura eficiente.

## Decisão

Utilizar:

```text
Apache Parquet
```

como formato principal.

## Implementação Atual

```text
data/raw/EURUSD/M15.parquet

data/processed/EURUSD/H1.parquet

data/processed/EURUSD/H4.parquet
```

## Consequências

CSV não é utilizado como armazenamento principal da pipeline histórica.

Pode continuar sendo usado para exportações específicas.

---

# ADR-008 — Spread Histórico do MT5 Não é o CostModel Oficial

## Status

```text
ACCEPTED
IMPLEMENTED AS DATA POLICY
```

## Contexto

O campo:

```text
spread
```

dos candles históricos apresentou:

```text
muitos valores zero
mudanças importantes entre anos
distribuição inconsistente
```

Foi observado aproximadamente:

```text
32.54%
```

de candles com spread igual a zero no dataset atual.

## Decisão

Preservar o campo para:

```text
auditoria
pesquisa
comparação
```

mas não utilizá-lo automaticamente como custo oficial de execução.

## Consequências

O BacktestEngine deverá possuir:

```text
CostModel
```

separado.

---

# ADR-009 — CostModel Deve Ser Independente

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

Custos são parte do modelo de execução, não da lógica de mercado da estratégia.

Misturá-los dentro da Strategy dificultaria:

```text
stress tests
comparações
substituição de fonte
auditoria
```

## Decisão

Criar futuramente um componente independente:

```text
CostModel
```

Responsável por:

```text
spread
slippage
commission
swap
```

## Possíveis Implementações

```text
FixedSpreadModel

ConservativeSpreadModel

TickBidAskModel

BrokerHistoricalCostModel
```

## Consequências

Uma mesma Strategy poderá ser testada com múltiplos cenários de custos sem alterar sua lógica.

---

# ADR-010 — Real Volume Não Será Utilizado Como Feature

## Status

```text
ACCEPTED
IMPLEMENTED AS DATA POLICY
```

## Contexto

O campo:

```text
real_volume
```

apresentou forte quebra estrutural.

Aproximadamente:

```text
2015  ~44%
2016 ~100%
2017  ~43%
2018+   0%
```

dos candles possuíam valor maior que zero.

## Decisão

`real_volume` não será utilizado atualmente como:

```text
feature
signal
filter
regime
position sizing input
```

## Consequências

O campo continua preservado no:

```text
M15 raw
```

para rastreabilidade.

---

# ADR-011 — Tick Volume Representa Atividade Relativa

## Status

```text
ACCEPTED
IMPLEMENTED AS DATA POLICY
```

## Contexto

O mercado Forex spot é descentralizado.

O:

```text
tick_volume
```

do feed não representa o volume global negociado de EURUSD.

## Decisão

O campo poderá ser utilizado futuramente como:

```text
medida relativa de atividade do feed
```

mas não será descrito como:

```text
volume global do mercado Forex
```

## Consequências

Qualquer estratégia baseada em tick volume deverá tratar sua utilidade como hipótese a ser testada.

---

# ADR-012 — Sistema Permanece Read-Only Antes da Camada de Execução

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

As primeiras fases do projeto tratam de:

```text
dados
engenharia
backtest
pesquisa
```

Não existe necessidade de permitir execução de ordens enquanto essas camadas ainda estão sendo construídas.

## Decisão

O estado atual é:

```text
READ ONLY
```

com:

```env
TRADING_ENABLED=false
```

Nenhum fluxo atual deverá chamar:

```python
mt5.order_send()
```

## Consequências

Execução só será introduzida em fase futura, inicialmente em conta Demo.

---

# ADR-013 — Strategy Não Envia Ordens Diretamente

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Acoplar uma Strategy diretamente ao broker produziria uma arquitetura como:

```text
Strategy
   ↓
MetaTrader5
   ↓
order_send()
```

Isso misturaria:

```text
sinal
risco
execução
broker
```

## Decisão

A Strategy deverá apenas expressar intenção.

Fluxo:

```text
Strategy
   ↓
Signal
   ↓
Risk
   ↓
Order
   ↓
Execution
```

## Consequências

A mesma Strategy poderá futuramente ser utilizada em:

```text
Backtest

Demo

Live futuro
```

sem conhecer o ambiente de execução.

---

# ADR-014 — Signal Não é Order

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

Um sinal de mercado pode ser válido, mas a operação ainda pode ser rejeitada por:

```text
risco
posição atual
limite diário
tamanho mínimo
kill switch
```

## Decisão

Manter conceitos distintos:

```text
Signal
```

e:

```text
Order
```

## Fluxo

```text
Signal
   ↓
Risk Gate
   ↓
Approved Order
```

## Consequências

Risk Engine pode rejeitar um sinal sem alterar a Strategy.

A implementação atual usa um contrato:

```text
RiskGate
```

com decisões auditáveis:

```text
RiskDecision
```

O `FixedSizeRiskGate` mantém o baseline histórico. O
`StopBasedRiskGate` permite calcular quantidade a partir de:

```text
entry_price
stop_loss
account_equity
risk_fraction
instrument contract_size
```

A quantidade final respeita:

```text
volume_min
volume_max
volume_step
```

`ExposureLimitRiskGate` pode envolver outro RiskGate para rejeitar entradas
que excedam limites de:

```text
max_quantity
max_notional
```

Quando `max_notional` e usado, o Signal precisa informar `entry_price`
em metadata para que a exposicao nocional seja calculada de forma
auditavel.

`DailyLossRiskGate` tambem pode envolver outro RiskGate. Ele observa
`EquityPoint` gerados pelo BacktestEngine e bloqueia novas entradas quando
a perda do dia UTC atinge:

```text
max_daily_loss
max_daily_loss_fraction
```

Sinais `HOLD` e `EXIT` continuam permitidos mesmo com o limite diario
atingido, porque nao aumentam exposicao financeira.

---

# ADR-015 — Order Não é Fill

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Uma ordem representa intenção de execução.

Um Fill representa execução efetiva.

No mundo real uma ordem pode:

```text
ser rejeitada
sofrer slippage
executar parcialmente
não executar
```

## Decisão

Modelar separadamente:

```text
Order
```

e:

```text
Fill
```

mesmo que o primeiro backtester use execução simplificada.

## Consequências

A arquitetura poderá evoluir sem precisar redefinir o conceito de trade posteriormente.

---

# ADR-016 — Backtest Baseline: Signal on Close / Execution on Next Open

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Se uma Strategy utiliza:

```text
Close de t
```

para produzir um sinal, o preço final do candle só é conhecido após seu fechamento.

Assumir execução garantida nesse mesmo `Close` pode gerar viés otimista.

## Decisão

Modelo baseline:

```text
Candle t fecha
      ↓
Strategy gera Signal
      ↓
Order criada
      ↓
Fill na abertura
da próxima barra disponível
```

## Regra

```text
signal_time < fill_time
```

para market orders baseline.

## Consequências

O primeiro BacktestEngine deverá usar:

```text
NEXT OPEN EXECUTION
```

como comportamento padrão.

---

# ADR-017 — A Próxima Barra Disponível é Usada Após um Gap

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Pode não existir a barra cronologicamente esperada após um sinal.

Exemplo:

```text
sexta-feira
      ↓
signal
      ↓
fim de semana
      ↓
segunda-feira
```

## Decisão

Não criar uma barra artificial.

A market order baseline é executada na:

```text
próxima barra realmente disponível
```

## Consequências

Gaps de preço permanecem no modelo.

---

# ADR-018 — Worst-Case para Ambiguidade Intrabar

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Com dados OHLC não conhecemos a sequência exata de preços dentro do candle.

Exemplo LONG:

```text
Entry = 100
Stop  = 95
TP    = 105

High = 110
Low  = 90
```

Sabemos que ambos foram tocados.

Não sabemos qual ocorreu primeiro.

## Decisão

Default:

```text
AMBIGUOUS_BAR_POLICY =
WORST_CASE
```

## Consequências

Quando Stop e Take Profit forem atingidos na mesma barra e não houver informação temporal adicional:

```text
assumir o resultado desfavorável.
```

Isso reduz viés otimista.

---

# ADR-019 — Gap Through Stop Não Garante Fill no Stop

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Exemplo LONG:

```text
Stop = 1.1000
```

Próxima abertura:

```text
1.0950
```

O mercado já abriu abaixo do stop.

## Decisão

Não assumir execução impossível em:

```text
1.1000
```

O preço de abertura pior deverá ser utilizado como referência de execução, com custos adicionais aplicados conforme o modelo.

## Consequências

Stops não funcionam como garantias artificiais de preço.

---

# ADR-020 — Baseline Permite Uma Posição por Vez

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

O objetivo inicial do BacktestEngine é validar:

```text
tempo
execução
PnL
custos
estado
```

antes de introduzir gerenciamento complexo de múltiplas posições.

## Decisão

Baseline:

```text
FLAT
LONG
SHORT
```

com:

```text
uma posição aberta por vez
```

## Não Permitido Inicialmente

```text
pyramiding

scale-in

scale-out

múltiplas posições simultâneas
```

## Consequências

A contabilidade inicial fica mais simples e auditável.

---

# ADR-021 — Sem Reversão Automática no Baseline

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Caso exista:

```text
LONG
```

e a Strategy gere:

```text
ENTER_SHORT
```

é possível interpretar isso de várias maneiras.

## Decisão

O baseline não fará:

```text
LONG → SHORT
```

automaticamente.

A posição deve primeiro ser encerrada explicitamente.

## Consequências

Reversal futuro deverá ser modelado como:

```text
Close
+
new Entry
```

com custos e fills separados.

---

# ADR-022 — BacktestEngine Controla o Relógio

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Se Strategy ou outros componentes controlarem livremente o tempo, podem surgir:

```text
look-ahead
sincronização incorreta
mistura entre tempo real e simulado
```

## Decisão

O:

```text
BacktestEngine
```

será a única fonte oficial do:

```text
simulation_time
```

## Consequências

Durante backtest não utilizar:

```python
datetime.now()
```

para decisões de mercado.

---

# ADR-023 — Bar Timestamp Representa o Início do Intervalo

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Contexto

Os datasets atuais utilizam timestamp semelhante ao MetaTrader.

## Decisão

```text
time
```

representa:

```text
bar_start_time
```

Exemplo:

```text
M15 10:00
```

representa:

```text
10:00 → 10:15
```

## Consequências

A disponibilidade completa desse candle ocorre apenas em:

```text
10:15
```

O BacktestEngine deverá derivar:

```text
bar_close_time
```

a partir do timeframe.

---

# ADR-024 — Sincronização Multi-Timeframe Será Temporal

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Em estratégias:

```text
M15
H1
H4
```

os índices dos DataFrames não representam o mesmo instante.

## Decisão

Não sincronizar timeframes através de:

```python
df_m15.iloc[i]
df_h1.iloc[i]
df_h4.iloc[i]
```

## Regra

Sincronização deverá utilizar:

```text
timestamp
+
bar close time
+
availability time
```

A implementação atual disponibiliza candles superiores via:

```text
BacktestContext.timeframe_bars
```

com:

```text
Timeframe.H1
Timeframe.H4
```

O `BacktestEngine` mantém o relógio base em M15 e só entrega candles
H1/H4 cujo fechamento seja menor ou igual ao `current_time`.

## Consequências

Um:

```text
H4 08:00
```

não poderá ser usado como fechado antes de:

```text
12:00
```

Estratégias multi-timeframe devem declarar os timeframes superiores
necessários e, quando possível, os limites de janela para evitar carregar
histórico superior completo em cada passo.

---

# ADR-025 — H4 Atual é Alinhado em UTC

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Decisão

Buckets H4 atuais utilizam as fronteiras:

```text
00:00
04:00
08:00
12:00
16:00
20:00
```

em:

```text
UTC
```

## Contexto

Esse alinhamento fornece construção determinística dos timeframes processados.

## Consequências

Uma Strategy H4 precisa conhecer essa semântica.

Ela não deve assumir automaticamente horário do broker ou sessão de Nova York.

---

# ADR-026 — D1 Não Será Criado Antes de Definir a Fronteira Diária

## Status

```text
ACCEPTED
IMPLEMENTATION DEFERRED
```

## Contexto

Candles diários variam conforme:

```text
timezone
broker
session close
```

Utilizar:

```text
00:00 UTC
```

sem decisão explícita poderia produzir um D1 diferente daquele usado pela estratégia ou literatura estudada.

## Decisão

Não criar D1 nesta fase.

Antes será necessário definir:

```text
daily boundary
timezone
trading session convention
```

## Consequências

Atualmente os timeframes processados oficialmente são:

```text
H1
H4
```

---

# ADR-027 — Dados Raw Não Recebem Features de Estratégia

## Status

```text
ACCEPTED
IMPLEMENTED AS POLICY
```

## Contexto

Adicionar:

```text
EMA
RSI
ATR
signals
labels
```

ao dataset raw misturaria:

```text
fonte
```

com:

```text
experimento
```

## Decisão

O dataset raw permanece livre de features de Strategy.

## Consequências

Features deverão pertencer a uma futura:

```text
Feature Layer
```

ou pipeline de experimento.

---

# ADR-028 — Dados Raw Não São Modificados pelo Backtest

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Decisão

O BacktestEngine deverá consumir:

```text
dados read-only
```

Ele não deverá:

```text
editar

corrigir

sobrescrever

regravar
```

o M15 raw.

## Consequências

Experimentos não alteram silenciosamente sua própria fonte histórica.

---

# ADR-029 — Falhas Estruturais Devem Falhar Explicitamente

## Status

```text
ACCEPTED
IMPLEMENTED PARCIALMENTE
```

## Contexto

Correções silenciosas podem esconder bugs.

Exemplos:

```text
OHLC inválido

dataset vazio

timezone ausente

timestamp duplicado
```

## Decisão

Preferir:

```text
fail fast
```

para violações estruturais.

## Consequências

Usar:

```python
raise ValueError(...)
```

ou:

```python
raise RuntimeError(...)
```

em vez de inventar correções.

---

# ADR-030 — Data Quality Problem Não É Automaticamente Data Error

## Status

```text
ACCEPTED
IMPLEMENTED AS POLICY
```

## Contexto

Nem toda característica estranha deve destruir o dataset.

Exemplo:

```text
High < Low
```

é estruturalmente impossível.

Mas:

```text
gap de feriado
```

pode ser perfeitamente legítimo.

## Decisão

Separar:

```text
HARD FAIL
```

de:

```text
WARNING / METADATA
```

## Hard Fail

```text
OHLC impossível

timestamp inválido

preço não positivo

timezone incorreto
```

## Warning / Metadata

```text
gap

spread zero

real_volume inconsistente
```

---

# ADR-031 — Resultados Devem Ser Reproduzíveis

## Status

```text
ACCEPTED
IMPLEMENTATION PARCIAL
```

## Decisão

O princípio é:

```text
mesmo dataset
+
mesmo código
+
mesma configuração
=
mesmo resultado
```

## Futuro

Backtests deverão registrar:

```text
dataset
dataset hash
strategy version
parameters
cost model
risk model
engine version
git commit
```

---

# ADR-032 — Dataset Hash Será Introduzido Antes da Validação Quantitativa Final

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Um nome como:

```text
EURUSD_M15.parquet
```

não garante que o conteúdo do arquivo permaneceu igual.

## Decisão

Adicionar futuramente:

```text
SHA256
```

ou identificador criptográfico equivalente ao manifesto do dataset.

## Consequências

Será possível provar qual versão do histórico foi utilizada em determinado experimento.

---

# ADR-033 — Parquet para Séries, SQLite para Dados Operacionais Futuros

## Status

```text
ACCEPTED AS ARCHITECTURAL DIRECTION
IMPLEMENTATION PARTIAL
```

## Decisão

Utilizar:

```text
Parquet
```

para:

```text
historical time series
```

e futuramente:

```text
SQLite
```

para dados relacionais como:

```text
experiments

trades

execution logs

metadata operacional

runtime state
```

## Consequências

Não transformar SQLite em armazenamento principal de milhões de barras apenas por conveniência.

---

# ADR-034 — Estratégias Simples Antes de Modelos Avançados

## Status

```text
ACCEPTED
```

## Contexto

Começar diretamente com:

```text
Machine Learning

HMM

modelos complexos
```

tornaria mais difícil separar:

```text
edge real
```

de:

```text
bug de infraestrutura
```

## Decisão

Ordem inicial:

```text
Simple EMA Trend Following

Volatility Breakout

Time-Series Momentum

Mean Reversion

Session Strategies

Carry

Regime Models

Advanced / ML
```

## Consequências

A primeira Strategy será usada também como baseline de engenharia.

---

# ADR-035 — Pesquisa e Engenharia Permanecem Separadas

## Status

```text
ACCEPTED
```

## Contexto

A pergunta:

```text
"A estratégia possui edge?"
```

é diferente de:

```text
"O backtest está correto?"
```

## Decisão

Manter separação conceitual entre:

```text
Quantitative Research
```

e:

```text
Software / Data Engineering
```

## Consequências

Uma boa infraestrutura não prova rentabilidade.

Uma Strategy aparentemente lucrativa não prova que a infraestrutura está correta.

As duas áreas precisam ser validadas independentemente.

---

# ADR-036 — Zero-Cost Backtests Só Serão Usados para Engenharia

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Testes matemáticos do BacktestEngine precisam conseguir eliminar custos para facilitar validação manual.

Porém estratégias reais em Forex possuem custos.

## Decisão

Permitir:

```text
spread = 0

slippage = 0

commission = 0

swap = 0
```

somente como configuração explícita.

## Consequências

Resultados desse tipo deverão ser identificados como:

```text
ZERO COST
IDEALIZED
```

e não como resultado realista.

---

# ADR-037 — Costs Devem Ser Auditáveis Separadamente

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Mesmo quando o spread estiver incorporado no preço de execução, é útil saber quanto ele afetou o resultado.

## Decisão

Registrar separadamente quando possível:

```text
spread impact

slippage impact

commission

swap
```

## Consequências

Será possível responder:

```text
quanto a Strategy ganhou antes dos custos?

quanto perdeu em spread?

quanto perdeu em slippage?
```

---

# ADR-038 — Não Contar Spread Duas Vezes

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Se o spread alterar diretamente:

```text
execution_price
```

e depois também for subtraído novamente do PnL, o custo será duplicado.

## Decisão

O CostModel deverá possuir uma convenção única.

Se:

```text
spread está incorporado ao preço
```

não deve ser novamente descontado como custo monetário separado.

## Consequências

O ledger pode registrar o impacto do spread para auditoria sem alterar novamente o Net PnL.

---

# ADR-039 — Primeiro Backtester Será Bar-by-Bar

## Status

```text
ACCEPTED
IMPLEMENTATION PENDING
```

## Contexto

Backtesting totalmente vetorizado pode ser eficiente, mas dificulta modelar corretamente:

```text
estado
ordens
fills
stops
gaps
risk
```

## Decisão

O baseline será:

```text
bar-by-bar
```

com comportamento próximo a:

```text
event-driven
```

## Consequências

Features podem ser pré-calculadas de forma causal, mas execução e estado permanecem cronológicos.

---

# ADR-040 — Correção Tem Prioridade sobre Performance

## Status

```text
ACCEPTED
```

## Decisão

A prioridade de engenharia é:

```text
1. Correctness

2. Reproducibility

3. Auditability

4. Risk

5. Robustness

6. Performance

7. Complexity
```

## Consequências

Não otimizar prematuramente o BacktestEngine antes de possuir resultados validados por testes simples.

---

# ADR-041 — Bugs Críticos Devem Produzir Regression Tests

## Status

```text
ACCEPTED
```

## Decisão

Quando um bug importante for identificado:

```text
1. reproduzir em teste

2. verificar que o teste falha

3. corrigir

4. verificar que passa
```

## Consequências

O mesmo bug não deve depender apenas da memória do desenvolvedor para não retornar.

---

# ADR-042 — Nenhuma Estratégia Será Aprovada Apenas por um Backtest Lucrativo

## Status

```text
ACCEPTED
```

## Contexto

Uma curva histórica positiva pode resultar de:

```text
overfitting

data snooping

custos inadequados

período favorável

look-ahead

acaso
```

## Decisão

A progressão será:

```text
Hypothesis
   ↓
Backtest
   ↓
Cost Stress
   ↓
Robustness
   ↓
Validation
   ↓
OOS
   ↓
Demo
```

## Consequências

Backtest lucrativo é apenas uma etapa do processo.

---

# ADR-043 — OOS Final Será Tratado como Lockbox

## Status

```text
ACCEPTED
IMPLEMENTATION FUTURE
```

## Contexto

Consultar repetidamente o OOS transforma-o, na prática, em parte do desenvolvimento.

## Decisão

O período final Out-of-Sample deverá ser usado de maneira restrita.

## Consequências

Parâmetros não devem ser ajustados continuamente em resposta ao resultado do lockbox.

---

# ADR-044 — Conta Demo Antes de Qualquer Execução Real

## Status

```text
ACCEPTED
```

## Decisão

Sequência mínima:

```text
Backtest

Robustness

OOS

Risk

Demo

Live Readiness
```

## Consequências

Não existe transição direta de:

```text
Backtest
```

para:

```text
capital real
```

---

# ADR-045 — Kill Switch Será Obrigatório Antes de Execução

## Status

```text
ACCEPTED
IMPLEMENTED
```

## Decisão

Antes da Execution Layer poder enviar ordens externas deverá existir:

```text
Kill Switch
```

independente da Strategy.

## Implementação

`KillSwitchRiskGate` em `backtest/risk.py`: wrapper composicional com latch
`kill()`/`reset()`, modos SOFT (bloqueia entradas, permite exits) e HARD
(`block_exits=True`, bloqueia entradas e exits). HOLD sempre passa.

## Consequências

Mesmo uma Strategy funcionando normalmente poderá ter sua execução bloqueada pelo mecanismo de segurança.

---

# ADR-046 — TRADING_ENABLED Não Será a Única Proteção

## Status

```text
ACCEPTED
IMPLEMENTATION FUTURE
```

## Contexto

Uma única variável de ambiente não é suficiente para proteger execução financeira.

## Decisão

Além de:

```env
TRADING_ENABLED=false
```

serão necessários controles como:

```text
demo account validation

risk limits

volume validation

duplicate-order protection

kill switch

broker state validation
```

---

# ADR-047 — Estado Atual do Projeto é Desenvolvimento e Pesquisa

## Status

```text
ACCEPTED
```

## Classificação

```text
Development

Research

Demo Broker Integration
```

Não existe atualmente:

```text
Production Trading

Live Trading
```

## Consequências

Resultados atuais não devem ser interpretados como sistema pronto para operar capital real.

---

# ADR-048 — v0.1 Representa Fundação de Dados, Não Bot Completo

## Status

```text
ACCEPTED
```

## Contexto

O marco atual possui:

```text
Environment

MT5 Integration

Market Data

Historical Data

Data Quality

Data Transformation

Testing

Documentation
```

Mas ainda não possui:

```text
BacktestEngine

Strategy Engine

Risk Engine

Execution Engine
```

## Decisão

O marco lógico:

```text
FOREX v0.1
```

será denominado:

```text
Data & Infrastructure Foundation
```

## Consequências

`v0.1` não deve ser interpretado como uma primeira versão operacional de trading.

---

# 3. Resumo das Decisões

| ADR | Decisão | Status |
|---|---|---|
| 001 | UTC interno | ✅ Implementado |
| 002 | Candle corrente excluído | ✅ Implementado |
| 003 | M15 como fonte intraday | ✅ Implementado |
| 004 | Sem preenchimento artificial de gaps | ✅ Implementado |
| 005 | Preservar candles incompletos | ✅ Implementado |
| 006 | Strategy usa completos por padrão | 🟡 Código futuro |
| 007 | Parquet para séries históricas | ✅ Implementado |
| 008 | Spread MT5 não é CostModel | ✅ Aceito |
| 009 | CostModel independente | 🟡 Código futuro |
| 010 | Real Volume fora das features | ✅ Aceito |
| 011 | Tick Volume = atividade relativa | ✅ Aceito |
| 012 | Read-only atual | ✅ Implementado |
| 013 | Strategy não envia ordens | 🟡 Código futuro |
| 014 | Signal != Order | 🟡 Código futuro |
| 015 | Order != Fill | 🟡 Código futuro |
| 016 | Signal Close → Next Open | 🟡 Backtest futuro |
| 017 | Gap → próxima barra disponível | 🟡 Backtest futuro |
| 018 | Intrabar ambiguity = worst-case | 🟡 Backtest futuro |
| 019 | Gap through stop usa preço pior | 🟡 Backtest futuro |
| 020 | Uma posição por vez | 🟡 Baseline futuro |
| 021 | Sem reversão automática | 🟡 Baseline futuro |
| 022 | Engine controla simulation time | 🟡 Backtest futuro |
| 023 | Timestamp = início da barra | ✅ Implementado |
| 024 | Multi-TF por tempo/disponibilidade | 🟡 Futuro |
| 025 | H4 alinhado em UTC | ✅ Implementado |
| 026 | D1 adiado | ✅ Decisão aceita |
| 027 | Raw sem features | ✅ Política atual |
| 028 | Backtest não modifica Raw | 🟡 Futuro |
| 029 | Fail Fast estrutural | ✅ Parcial |
| 030 | Hard Fail != Warning | ✅ Política atual |
| 031 | Reprodutibilidade obrigatória | 🟡 Parcial |
| 032 | Dataset hash futuro | 🟡 Futuro |
| 033 | Parquet + SQLite futuro | 🟡 Parcial |
| 034 | Estratégias simples primeiro | ✅ Aceito |
| 035 | Pesquisa ≠ Engenharia | ✅ Aceito |
| 036 | Zero-cost só para engenharia | 🟡 Futuro |
| 037 | Custos auditáveis | 🟡 Futuro |
| 038 | Não duplicar spread | 🟡 Futuro |
| 039 | Backtester bar-by-bar | 🟡 Futuro |
| 040 | Correção antes de performance | ✅ Aceito |
| 041 | Bug crítico → regression test | ✅ Aceito |
| 042 | Backtest lucrativo não basta | ✅ Aceito |
| 043 | OOS como lockbox | 🟡 Futuro |
| 044 | Demo antes de Live | ✅ Aceito |
| 045 | Kill Switch obrigatório | ✅ Implementado |
| 046 | Trading flag não basta | 🟡 Futuro |
| 047 | Estado = Research/Development | ✅ Atual |
| 048 | v0.1 = Data Foundation | ✅ Atual |

---

# 4. Alteração de Decisões

Nenhuma decisão deste documento deve ser considerada permanentemente imutável.

Entretanto, alterações importantes devem ser explícitas.

Exemplo:

```text
ADR-016
Next Open Execution
```

caso futuramente seja substituído por:

```text
Bid/Ask Tick Execution
```

não deve simplesmente desaparecer.

O correto será registrar:

```text
ADR-016
SUPERSEDED BY ADR-XXX
```

---

# 5. Regra de Atualização

Ao alterar uma decisão arquitetural:

```text
1. documentar a nova decisão

2. explicar o motivo

3. marcar a anterior como SUPERSEDED
   quando aplicável

4. alterar o código

5. alterar/adicionar testes

6. atualizar CHANGELOG.md
```

---

# 6. Decisões e Experimentos

Mudanças em decisões que afetam execução podem tornar backtests antigos não diretamente comparáveis.

Exemplos:

```text
Next Open → Same Close

Fixed Spread → Bid/Ask

Worst Case → Lower Timeframe Resolution

One Position → Pyramiding
```

Por isso resultados futuros deverão registrar a versão/configuração do Engine.

---

# 7. Invariantes Mais Importantes

Entre todas as decisões atuais, algumas formam o núcleo do projeto:

```text
UTC

No Look-Ahead

Closed Candles

No Artificial Gap Filling

Explicit Costs

Signal != Order

Order != Fill

Strategy != Execution

Reproducibility

Risk Before Execution
```

Qualquer alteração nessas áreas exige atenção especial.

---

# 8. Estado do Documento

Marco:

```text
FOREX v0.1
```

Descrição:

```text
Data & Infrastructure Foundation
```

Última revisão inicial:

```text
2026-08-08
```

Próximo arquivo:

```text
CHANGELOG.md
```

O `CHANGELOG.md` fechará formalmente o marco `v0.1` e registrará tudo que foi construído até o momento antes de começarmos a implementação do `BacktestEngine`.

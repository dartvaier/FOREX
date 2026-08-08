# Market Data

## 1. Objetivo

Este documento define o contrato oficial dos dados de mercado utilizados pela plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

O objetivo é estabelecer regras claras para:

- candles;
- ticks;
- Bid e Ask;
- timestamps;
- timezone;
- Point;
- Pip;
- spread;
- volume;
- candles fechados;
- schemas de DataFrame;
- integridade dos dados;
- disponibilidade temporal;
- consumo futuro por Strategy e BacktestEngine.

O princípio central é:

```text
Um dado só pode ser utilizado
se sua definição, origem e momento
de disponibilidade forem conhecidos.
```

---

# 2. Fonte Atual

A fonte de mercado utilizada no estado atual é:

```text
MetaTrader 5
MetaQuotes-Demo
```

Símbolo inicial:

```text
EURUSD
```

Timeframe base:

```text
M15
```

Timeframes derivados:

```text
H1
H4
```

---

# 3. Responsabilidade da Market Data Layer

A camada responsável pelos dados correntes está localizada em:

```text
data/market_data.py
```

Classe principal:

```text
MarketData
```

Sua responsabilidade é transformar informações obtidas pelo broker em estruturas consistentes para o restante da aplicação.

Fluxo:

```text
MetaTrader 5
      ↓
MT5Client
      ↓
MarketData
      ↓
dados normalizados
```

---

# 4. Responsabilidades Atuais

A camada `MarketData` é responsável por:

```text
obter candles fechados
obter cotação atual
normalizar timestamps
preservar UTC
obter Bid
obter Ask
calcular spread instantâneo
obter Point
determinar Pip Size
```

Ela não é responsável por:

```text
gerar sinais
calcular indicadores de estratégia
executar ordens
calcular position sizing
realizar backtests
calcular métricas
```

---

# 5. Timezone Oficial

Todo dado temporal interno utiliza:

```text
UTC
```

Os timestamps devem ser:

```text
timezone-aware
```

e não:

```text
timezone-naive
```

Exemplo válido:

```text
2026-08-07 23:45:00+00:00
```

O sufixo:

```text
+00:00
```

indica UTC.

---

# 6. Conversão de Timestamp

Os timestamps recebidos do MetaTrader 5 são convertidos através de:

```python
pd.to_datetime(
    df["time"],
    unit="s",
    utc=True,
)
```

Resultado:

```text
Unix timestamp
      ↓
pandas Timestamp
      ↓
UTC timezone-aware
```

---

# 7. Regra de Timezone

Nenhum componente deve assumir que timestamps sem timezone representam UTC.

Exemplo indesejado:

```python
pd.to_datetime(df["time"], unit="s")
```

quando o resultado será utilizado como referência temporal crítica.

Preferido:

```python
pd.to_datetime(
    df["time"],
    unit="s",
    utc=True,
)
```

---

# 8. Sessões de Mercado

O dataset bruto permanece em UTC.

Conversões para sessões específicas só devem ocorrer quando necessário.

Exemplos:

```text
Europe/London
America/New_York
```

Fluxo:

```text
UTC raw data
    ↓
timezone conversion
    ↓
session-specific logic
```

A fonte bruta não deve ser armazenada permanentemente em horário local de sessão.

---

# 9. DST

Sessões futuras não devem utilizar offsets fixos durante todo o ano.

Exemplo incorreto:

```text
London = UTC+0 sempre
```

Londres possui mudanças de horário relacionadas a DST.

Deve ser utilizada:

```text
Europe/London
```

e não uma regra manual fixa.

---

# 10. Candle

Um candle representa a agregação de informações de preço em determinado intervalo.

Schema conceitual:

```text
time
open
high
low
close
tick_volume
spread
real_volume
```

Para datasets derivados podem existir também:

```text
source_bar_count
expected_bar_count
complete
```

---

# 11. Open

```text
open
```

representa o primeiro preço registrado no intervalo do candle segundo a fonte utilizada.

Para candles derivados:

```text
Open = primeiro Open
```

dos candles fonte pertencentes ao intervalo.

---

# 12. High

```text
high
```

representa o maior preço observado no intervalo.

Invariante:

```text
High >= Open
High >= Close
High >= Low
```

---

# 13. Low

```text
low
```

representa o menor preço observado no intervalo.

Invariante:

```text
Low <= Open
Low <= Close
Low <= High
```

---

# 14. Close

```text
close
```

representa o último preço conhecido do intervalo segundo o candle fornecido pela fonte.

Para um candle ainda em formação:

```text
close
```

não representa necessariamente o fechamento definitivo.

Esse ponto é fundamental.

---

# 15. OHLC Integrity

Todo candle aceito deve satisfazer:

```text
High >= Open
High >= Close
High >= Low

Low <= Open
Low <= Close
```

Além disso:

```text
Open  > 0
High  > 0
Low   > 0
Close > 0
```

Essas propriedades possuem testes automatizados.

---

# 16. Candle Corrente

No MetaTrader 5:

```text
bar 0
```

representa a barra mais recente.

Durante mercado ativo essa barra normalmente está em formação.

Exemplo:

```text
Timeframe M15

23:45 ───────────── 00:00
        bar 0
```

Às:

```text
23:52
```

o candle ainda não terminou.

---

# 17. Candle Fechado

No fluxo atual de `MarketData`, candles destinados à aplicação são obtidos com:

```python
start_pos=1
```

Isso exclui a barra mais recente.

Exemplo:

```text
bar 0 → mais recente
bar 1 → anterior
bar 2 → anterior
```

O método:

```text
get_closed_bars()
```

não deve retornar deliberadamente a barra corrente.

---

# 18. Regra de Disponibilidade Temporal

A regra oficial é:

> Um candle só pode ser utilizado como fechado quando todas as informações necessárias daquele candle já estavam disponíveis no momento da decisão.

Fluxo correto:

```text
Candle t termina
     ↓
OHLC final de t torna-se conhecido
     ↓
Strategy pode processar t
     ↓
ação futura pode ocorrer
```

---

# 19. Look-Ahead

Exemplo incorreto:

```text
candle t ainda aberto
      ↓
utiliza Close final de t
      ↓
gera decisão dentro de t
```

Isso utiliza informação futura.

É considerado:

```text
look-ahead bias
```

e invalida o experimento.

---

# 20. Regra para Estratégias

A futura Strategy Layer não deverá receber livremente a fonte bruta do broker.

Preferencialmente deverá receber:

```text
validated closed bars
```

ou outra estrutura controlada pelo BacktestEngine.

Isso evita acesso acidental a:

```text
candle corrente
dados futuros
campos não validados
```

---

# 21. Current Quote

A cotação corrente é obtida através de:

```text
MarketData.get_current_quote()
```

A resposta conceitual possui:

```text
symbol
bid
ask
point
pip_size
spread_points
spread_pips
```

---

# 22. Bid

```text
Bid
```

representa o preço do lado comprador exibido pelo feed.

Conceitualmente, para uma posição vendida ou fechamento de compra, Bid pode ser relevante para execução.

A modelagem definitiva de execução pertence ao futuro `Execution` / `CostModel`.

---

# 23. Ask

```text
Ask
```

representa o preço do lado vendedor exibido pelo feed.

Conceitualmente, para uma entrada comprada ou fechamento de venda, Ask pode ser relevante.

Novamente, a regra exata pertence ao modelo de execução.

---

# 24. Invariante Bid / Ask

A cotação deve satisfazer:

```text
Bid > 0
Ask > 0
Ask >= Bid
```

Se:

```text
Ask < Bid
```

o dado deve ser considerado inválido.

Existe teste automatizado para essa propriedade.

---

# 25. Spread Instantâneo

O spread corrente é calculado como:

```text
Spread = Ask - Bid
```

Em código:

```python
spread_price = tick.ask - tick.bid
```

---

# 26. Spread em Points

```python
spread_points = (
    spread_price / point
)
```

Para EURUSD observado:

```text
Point = 0.00001
```

Exemplo:

```text
Bid = 1.15571
Ask = 1.15573
```

Então:

```text
Spread Price  = 0.00002
Spread Points = 2
```

---

# 27. Point

`Point` é uma propriedade do símbolo obtida diretamente do broker.

Para o EURUSD atual:

```text
Point = 0.00001
```

Esse valor não deve ser hardcoded globalmente.

Outros instrumentos podem possuir especificações diferentes.

---

# 28. Digits

O EURUSD observado possui:

```text
Digits = 5
```

Isso significa que o preço é exibido com cinco casas decimais.

Exemplo:

```text
1.15571
```

---

# 29. Pip Size

Para pares Forex típicos com:

```text
3 ou 5 digits
```

a implementação atual considera:

```text
pip_size = point × 10
```

Para EURUSD:

```text
Point    = 0.00001
Pip Size = 0.00010
```

Logo:

```text
10 points = 1 pip
```

---

# 30. Regra de Pip

A fórmula atual é:

```python
if info.digits in (3, 5):
    pip_size = info.point * 10
else:
    pip_size = info.point
```

Essa regra atende ao instrumento atual, mas não deve ser considerada uma especificação universal para todos os ativos futuros.

Uma camada de `InstrumentSpecification` poderá ser criada futuramente.

---

# 31. Contract Size

Para o EURUSD observado:

```text
Contract Size = 100000
```

Esse valor é obtido através das especificações do símbolo.

Ele será importante futuramente para:

```text
position sizing
PnL
margin
risk
```

mas não deve ser hardcoded.

---

# 32. Volume Mínimo

O ambiente atual reportou:

```text
Volume mínimo = 0.01
```

Esse valor também pertence às especificações do instrumento.

---

# 33. Volume Step

O ambiente atual reportou:

```text
Volume step = 0.01
```

Futuramente o Risk Engine deverá garantir que qualquer tamanho de posição respeite:

```text
volume_min
volume_max
volume_step
```

---

# 34. Tick

Um tick representa uma atualização da cotação fornecida pelo broker.

Campos observados incluem:

```text
time
time_msc
bid
ask
```

A presença de:

```text
time_msc
```

permite granularidade em milissegundos.

---

# 35. Tick Timestamp

Ticks históricos podem ser convertidos com:

```python
pd.to_datetime(
    ticks_df["time_msc"],
    unit="ms",
    utc=True,
)
```

Isso preserva maior resolução temporal que o campo em segundos.

---

# 36. Historical Tick Spread

Ticks históricos permitem calcular:

```text
Ask - Bid
```

em cada atualização.

Isso poderá ser utilizado futuramente em modelos de custo mais realistas.

Entretanto, a qualidade do feed deverá ser avaliada antes.

---

# 37. Limitação dos Ticks MetaQuotes-Demo

Durante testes foram observados muitos ticks com:

```text
Bid == Ask
```

Logo:

```text
Spread = 0
```

Isso significa que o histórico de ticks do MetaQuotes-Demo também não deve ser automaticamente assumido como reprodução perfeita da execução real.

---

# 38. Candle Spread Field

Candles MT5 possuem um campo:

```text
spread
```

No dataset atual esse campo é preservado.

Entretanto, ele apresentou comportamento inconsistente ao longo dos anos.

---

# 39. Spread Histórico Observado

No dataset M15 atual:

```text
Candles: 288223
```

O percentual de:

```text
spread = 0
```

foi aproximadamente:

```text
32.54%
```

Também foram observadas diferenças relevantes entre anos.

---

# 40. Spread por Ano

A distribuição do campo histórico variou significativamente.

Exemplos observados:

```text
2015
mediana ~7 points

2021
mediana 0 points

2025
mediana ~4 points

2026
mediana 0 points
```

Esse comportamento indica que a origem ou interpretação do campo não é completamente estável ao longo do histórico.

---

# 41. Decisão sobre Spread Histórico

O campo:

```text
spread
```

será preservado para:

```text
auditoria
análise
pesquisa
```

mas:

```text
não será utilizado automaticamente
como custo oficial do backtest.
```

O futuro `CostModel` será responsável por custos.

---

# 42. Market Data != Cost Model

Essa distinção é arquitetural:

```text
Market Data
    ↓
descreve dados observados

Cost Model
    ↓
descreve custo assumido de execução
```

O BacktestEngine não deverá misturar esses conceitos.

---

# 43. Tick Volume

O campo:

```text
tick_volume
```

representa a quantidade de atualizações/ticks associadas ao candle conforme o feed.

Ele é preservado.

---

# 44. Interpretação do Tick Volume

O `tick_volume` pode futuramente ser utilizado para estudar:

```text
atividade relativa
expansão de atividade
confirmação de breakout
regimes
```

Mas não deve ser chamado de:

```text
volume total negociado no mercado Forex
```

porque o mercado spot FX é descentralizado.

---

# 45. Tick Volume Atual

No histórico M15 atual, o campo apresentou valores coerentes e não negativos.

Foi observado:

```text
mínimo > 0
```

no dataset histórico analisado.

Existe também teste garantindo:

```text
tick_volume >= 0
```

para dados correntes.

---

# 46. Real Volume

O campo:

```text
real_volume
```

também existe nos candles da fonte.

Entretanto, sua disponibilidade é inconsistente.

---

# 47. Comportamento do Real Volume

Foi observada a seguinte proporção de candles com:

```text
real_volume > 0
```

aproximadamente:

```text
2015   44%
2016  100%
2017   43%
2018    0%
2019    0%
2020    0%
2021    0%
2022    0%
2023    0%
2024    0%
2025    0%
2026    0%
```

---

# 48. Decisão sobre Real Volume

O campo:

```text
real_volume
```

não será utilizado como:

```text
feature
filtro
sinal
input de estratégia
```

na configuração atual.

Ele permanece no dataset bruto por rastreabilidade.

---

# 49. Schema M15 Raw

O dataset bruto atual possui colunas equivalentes a:

```text
time
open
high
low
close
tick_volume
spread
real_volume
```

Arquivo:

```text
data/raw/EURUSD/M15.parquet
```

---

# 50. Tipos Conceituais

Schema conceitual:

```text
time           datetime64[ns, UTC]

open           numeric
high           numeric
low            numeric
close          numeric

tick_volume    integer-like
spread         integer-like
real_volume    integer-like
```

Os tipos exatos podem depender de pandas/Parquet, mas essas categorias conceituais devem ser preservadas.

---

# 51. Schema H1 / H4

Os datasets processados possuem:

```text
time
open
high
low
close
tick_volume
source_bar_count
expected_bar_count
complete
```

Campos como:

```text
spread
real_volume
```

não são agregados no `TimeframeBuilder` atual.

---

# 52. source_bar_count

Representa quantas barras fonte M15 foram encontradas no intervalo.

Exemplo H1:

```text
source_bar_count = 4
```

significa que os quatro candles M15 esperados estavam disponíveis.

---

# 53. expected_bar_count

Número de candles esperados para construir o timeframe.

H1:

```text
expected_bar_count = 4
```

H4:

```text
expected_bar_count = 16
```

---

# 54. complete

É calculado como:

```text
source_bar_count == expected_bar_count
```

Exemplo:

```text
H4
source_bar_count   = 15
expected_bar_count = 16

complete = False
```

---

# 55. Regra para Estratégias

A regra padrão futura será utilizar:

```text
complete == True
```

para datasets derivados.

Candles incompletos permanecem armazenados, mas não serão aceitos por padrão na Strategy Layer.

---

# 56. Por que Preservar Candles Incompletos

Apagar silenciosamente candles incompletos faria a auditoria perder informação sobre:

```text
gaps
falhas do feed
feriados
fragmentação do histórico
```

Por isso:

```text
processed dataset
```

preserva:

```text
complete=False
```

quando necessário.

---

# 57. Data Order

Todos os datasets devem estar ordenados por:

```text
time
```

em ordem crescente.

Invariante:

```python
df["time"].is_monotonic_increasing
```

deve ser:

```text
True
```

---

# 58. Duplicados

Um dataset de:

```text
symbol + timeframe
```

não deve possuir dois candles com o mesmo timestamp.

Invariante:

```text
duplicated(time) = 0
```

---

# 59. Null Values

Campos essenciais não devem possuir valores nulos.

Para o dataset atual:

```text
time
open
high
low
close
tick_volume
spread
real_volume
```

foram encontrados:

```text
0 nulls
```

---

# 60. Missing Candles

Um timestamp ausente não é automaticamente um valor nulo.

Exemplo:

```text
10:00
10:15
10:30
11:00
```

O candle:

```text
10:45
```

não existe.

Isso representa:

```text
gap temporal
```

e não:

```text
NaN
```

---

# 61. Política de Gaps

Gaps não são preenchidos automaticamente.

Não utilizar:

```python
df.ffill()
```

para fabricar preços ausentes.

Não criar artificialmente:

```text
OHLC do candle inexistente
```

---

# 62. Motivo

Forward-fill de preços em um candle ausente poderia criar:

```text
dados que nunca foram observados
```

e posteriormente gerar:

```text
indicadores
sinais
entradas
```

sobre uma barra artificial.

Isso não é aceitável por padrão.

---

# 63. Gap Detection

Para M15:

```text
intervalo esperado = 15 minutos
```

Então:

```python
delta = df["time"].diff()
```

e:

```text
delta > 15 minutos
```

representa uma descontinuidade temporal.

---

# 64. Gap != Error

Forex possui interrupções normais.

Exemplo:

```text
sexta-feira
    ↓
fim de semana
    ↓
domingo/segunda
```

Portanto:

```text
gap
```

não significa automaticamente:

```text
dataset corrompido
```

---

# 65. Estado Atual dos Gaps

No dataset M15:

```text
Gaps totais: 659
```

Classificação inicial:

```text
Atravessam fim de semana: 605
Inteiramente em dias úteis: 54
```

---

# 66. Gaps Intraweek

Entre os 54 gaps intraweek existem:

```text
Natal
Ano Novo
feriados
outros intervalos não classificados
```

Os intervalos não classificados continuam preservados.

Não são corrigidos manualmente sem evidência.

---

# 67. Market Data Availability

Além do valor do dado, o sistema deve considerar:

```text
quando esse dado se tornou conhecido
```

Isso será fundamental no BacktestEngine.

Exemplo:

```text
H1 candle timestamp = 10:00

intervalo:
10:00 → 11:00
```

O OHLC definitivo desse candle só é conhecido após o final do intervalo.

---

# 68. Candle Timestamp Semantics

Nos datasets atuais, o campo:

```text
time
```

representa o início do intervalo.

Exemplo M15:

```text
23:45
```

representa:

```text
23:45 → 00:00
```

---

# 69. H1 Timestamp Semantics

Exemplo:

```text
10:00
```

representa aproximadamente:

```text
10:00 → 11:00
```

quando completo.

---

# 70. H4 Timestamp Semantics

Os H4 atuais são alinhados em UTC nas fronteiras:

```text
00:00
04:00
08:00
12:00
16:00
20:00
```

Exemplo:

```text
08:00
```

representa o grupo:

```text
08:00 → 12:00
```

---

# 71. Primeiro H4 do Dataset

O primeiro M15 disponível é:

```text
2015-01-02 09:00 UTC
```

O primeiro grupo H4 correspondente começa em:

```text
08:00 UTC
```

Como os M15 de:

```text
08:00
08:15
08:30
08:45
```

não existem no dataset, esse H4 é incompleto.

Ele deve ser marcado:

```text
complete = False
```

---

# 72. Dados Processados Não Substituem Raw

`H1.parquet` e `H4.parquet` são derivados.

Fonte atual de verdade intraday:

```text
M15 raw
```

Fluxo:

```text
M15 raw
   ↓
TimeframeBuilder
   ├── H1
   └── H4
```

---

# 73. Raw Data

Arquivo atual:

```text
data/raw/EURUSD/M15.parquet
```

Representa o dataset base utilizado nesta etapa.

Transformações destrutivas não devem ser realizadas diretamente nesse arquivo sem necessidade.

---

# 74. Processed Data

Arquivos:

```text
data/processed/EURUSD/H1.parquet
data/processed/EURUSD/H4.parquet
```

Esses arquivos podem ser regenerados a partir do M15.

Isso é uma propriedade importante de reprodutibilidade.

---

# 75. Dataset M15 Atual

Estado validado:

```text
Candles:
288223
```

Período:

```text
2015-01-02 09:00 UTC
→
2026-08-07 23:45 UTC
```

---

# 76. Dataset H1 Atual

Estado:

```text
Candles totais: 72080

Completos:      72018
Incompletos:       62
```

Período:

```text
2015-01-02 09:00 UTC
→
2026-08-07 23:00 UTC
```

---

# 77. Dataset H4 Atual

Estado:

```text
Candles totais: 18046

Completos:      17929
Incompletos:      117
```

Período:

```text
2015-01-02 08:00 UTC
→
2026-08-07 20:00 UTC
```

---

# 78. DataFrame Contract para Estratégias

Ainda não existe uma Strategy implementada.

Entretanto, o contrato pretendido é que estratégias recebam somente informações necessárias e válidas.

Exemplo conceitual:

```text
time
open
high
low
close
tick_volume
```

e eventualmente features derivadas.

Campos de infraestrutura como:

```text
spread histórico inconsistente
real_volume
```

não devem ser introduzidos automaticamente.

---

# 79. Strategy Data Filtering

Para H1/H4 o consumo padrão será equivalente a:

```python
strategy_data = df[
    df["complete"]
].copy()
```

Esse filtro deverá ser centralizado futuramente, evitando que cada Strategy implemente sua própria versão de limpeza.

---

# 80. Market Data e Indicators

Indicadores futuros deverão ser calculados sobre dados validados.

Fluxo:

```text
Validated Market Data
        ↓
Feature / Indicator Layer
        ↓
Strategy
```

Não:

```text
Raw Broker Response
        ↓
Strategy diretamente
```

---

# 81. Indicadores Não Alteram Dados Originais

Exemplo futuro:

```python
df["ema_20"] = ...
```

deve ocorrer em uma cópia ou pipeline apropriada.

O dataset raw deve permanecer rastreável.

---

# 82. Dados Futuros

Indicadores com janelas devem utilizar somente:

```text
presente + passado disponível
```

Nunca:

```text
future bars
```

Exemplo de erro:

```text
swing high confirmado usando i+3
```

e tratado como conhecido no candle `i`.

Nesse caso, a confirmação só pode ser considerada disponível após as barras futuras necessárias.

---

# 83. Data Leakage

Data leakage pode ocorrer mesmo sem acessar diretamente o preço futuro.

Exemplos:

```text
normalização usando média de todo dataset

seleção de parâmetros usando OOS

feature calculada com futuro

labels futuros usados como signals

preenchimento baseado em valores posteriores
```

O Market Data Contract deve ser respeitado também pelas futuras Feature e Strategy Layers.

---

# 84. Dados de Treino e Teste

A divisão:

```text
research
validation
lockbox OOS
```

será responsabilidade da infraestrutura de experimentos futura.

A camada de Market Data não deve decidir quais períodos pertencem a treino ou teste.

Ela apenas fornece séries temporalmente válidas.

---

# 85. Data Quality Boundary

A camada de dados deve rejeitar ou marcar problemas estruturais.

Exemplos:

```text
OHLC inválido          → erro
timezone ausente       → erro
duplicados             → erro ou tratamento explícito
candle incompleto      → marcado
gap                    → preservado
spread inconsistente   → metadata / ressalva
real_volume instável   → metadata / ressalva
```

Nem todo problema exige remoção.

---

# 86. Fail Fast

Quando uma invariante fundamental for violada, o comportamento esperado é:

```text
falhar explicitamente
```

em vez de corrigir silenciosamente.

Exemplo:

```python
if df.empty:
    raise ValueError(...)
```

---

# 87. Data Provenance

Todo dataset importante deve permitir identificar:

```text
fonte
símbolo
timeframe
período
timezone
quantidade
transformação aplicada
limitações conhecidas
```

A infraestrutura atual já possui:

```text
data/metadata/
```

para iniciar esse processo.

---

# 88. Metadata Atual

Arquivo:

```text
data/metadata/EURUSD_M15.json
```

Registra informações como:

```text
symbol
timeframe
source
timezone
first_bar
last_bar
bars
duplicates
missing_values
spread reliability
real_volume reliability
usage
notes
```

---

# 89. Uso do Dataset Atual

Classificação atual:

```text
development_and_research
```

O dataset pode ser utilizado para:

```text
desenvolvimento
testes
backtest inicial
pesquisa estrutural
engenharia
```

Ele não deve ser automaticamente considerado:

```text
dataset final de execução real
```

---

# 90. Data Source Future

Antes de validações finais poderão ser utilizadas fontes adicionais.

Possíveis objetivos:

```text
Bid/Ask histórico mais confiável
ticks de maior qualidade
custos do broker escolhido
histórico independente
```

A arquitetura deve permitir substituir ou comparar fontes.

---

# 91. Symbol Naming

Atualmente:

```text
EURUSD
```

é utilizado diretamente.

No futuro brokers podem utilizar nomes como:

```text
EURUSD.a
EURUSDm
EURUSD.pro
```

Portanto poderá ser necessário separar:

```text
canonical_symbol
```

de:

```text
broker_symbol
```

Essa camada ainda não foi implementada.

---

# 92. Instrument Specification Future

Uma futura abstração poderá possuir:

```text
symbol
digits
point
pip_size
contract_size
volume_min
volume_max
volume_step
tick_size
tick_value
currency_base
currency_profit
currency_margin
```

Isso evitará regras específicas espalhadas pelo código.

---

# 93. Campos MT5 Ainda Relevantes

Campos do símbolo que deverão ser considerados antes da Execution Layer incluem:

```text
trade_tick_size
trade_tick_value
trade_tick_value_profit
trade_tick_value_loss

currency_base
currency_profit
currency_margin

trade_stops_level
trade_freeze_level

filling_mode
trade_mode

swap_long
swap_short
swap_rollover3days
```

Esses campos ainda não fazem parte do contrato completo atual.

---

# 94. Daily Data

D1 ainda não foi derivado a partir do M15.

Isso é deliberado.

A fronteira de um candle diário pode depender do modelo de sessão/broker.

Antes de construir D1 deve ser definido:

```text
qual horário marca a fronteira diária?
```

Não assumir automaticamente:

```text
00:00 UTC
```

como regra universal.

---

# 95. Multi-Timeframe Future

Estratégias futuras poderão utilizar mais de um timeframe.

Exemplo:

```text
H4 → regime

H1 → signal

M15 → execution
```

O BacktestEngine deverá garantir que cada timeframe seja disponibilizado respeitando seu fechamento real.

---

# 96. Multi-Timeframe Look-Ahead

Exemplo perigoso:

Às:

```text
10:30
```

usar um candle H1 de:

```text
10:00 → 11:00
```

como se já estivesse fechado.

Isso seria look-ahead.

O mecanismo futuro deverá disponibilizar H1 somente após seu fechamento.

---

# 97. Event Time Future

O projeto deverá distinguir futuramente:

```text
bar_start_time
bar_close_time
signal_time
order_time
fill_time
```

O campo atual:

```text
time
```

representa apenas o início da barra.

Esses conceitos adicionais serão importantes no BacktestEngine.

---

# 98. Exemplo Temporal

Para M15:

```text
bar_start_time:
10:00

bar interval:
10:00 → 10:15

bar data fully available:
10:15
```

Então um sinal baseado no fechamento de 10:00 deve ser tratado como disponível após:

```text
10:15
```

e não às:

```text
10:00
```

---

# 99. Execution Price Future

O `Close` do candle de sinal não deverá ser automaticamente assumido como preço de execução.

É necessário distinguir:

```text
signal price
execution price
```

Exemplo:

```text
signal calculado após fechamento de t
        ↓
execução em abertura de t+1
```

ou outro modelo explicitamente definido.

Essa regra pertence a:

```text
Backtest Design
```

---

# 100. Market Data Invariants

As invariantes oficiais atuais são:

```text
timestamp timezone-aware

timezone = UTC

timestamps ordenados

timestamps únicos por símbolo/timeframe

Open > 0
High > 0
Low > 0
Close > 0

High >= Open
High >= Close
High >= Low

Low <= Open
Low <= Close

Bid > 0
Ask > 0

Ask >= Bid

spread instantâneo >= 0

tick_volume >= 0

candle corrente não é tratado
como candle fechado

candles derivados incompletos
são explicitamente marcados
```

---

# 101. Testes Relacionados

Existem atualmente testes para:

```text
current quote

closed bars

bar count

timestamp ordering

duplicates

UTC

OHLC integrity

positive prices

tick_volume

current bar exclusion

H1 creation

H4 creation

source bar count

H1 alignment

H4 alignment

derived OHLC integrity
```

---

# 102. Estado dos Testes

No marco atual:

```text
25 passed
0 failed
```

Esses testes formam parte do contrato executável da camada de dados.

---

# 103. Regra Principal do Market Data Contract

A principal regra desta camada é:

> Dados de mercado devem representar apenas informações que realmente existiam e estavam disponíveis no instante simulado.

Qualquer transformação futura deve preservar essa propriedade.

---

# 104. Estado Atual

Market Data no marco:

```text
FOREX v0.1
```

Status:

```text
Current Quote             COMPLETE
Bid / Ask                 COMPLETE
Point                      COMPLETE
Pip Size                   COMPLETE
Closed Bars                COMPLETE
UTC                        COMPLETE
OHLC Validation            COMPLETE
Historical M15             COMPLETE
H1 Transformation          COMPLETE
H4 Transformation          COMPLETE
Incomplete Bar Tracking    COMPLETE
Automated Tests            COMPLETE

Cost Model                 NOT IMPLEMENTED
Strategy Features          NOT IMPLEMENTED
Daily Dataset              NOT IMPLEMENTED
Multi-Timeframe Engine     NOT IMPLEMENTED
Execution Price Model      NOT IMPLEMENTED
```

---

# 105. Próximo Documento

O próximo documento é:

```text
docs/06_HISTORICAL_DATA.md
```

Ele documentará em detalhes:

```text
coleta histórica
chunks
Parquet
cobertura temporal
dataset M15
metadata
raw / processed
reprodutibilidade
atualização futura
limitações da fonte
```
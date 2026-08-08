# Backtest Design

## 1. Objetivo

Este documento define o design do futuro:

```text
BacktestEngine
```

da plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

O BacktestEngine ainda não está implementado.

Este documento existe antes da implementação para estabelecer o comportamento esperado do sistema e impedir que decisões importantes sejam tomadas implicitamente durante a programação.

O princípio central é:

> O BacktestEngine deve reproduzir somente decisões e execuções que seriam possíveis utilizando as informações disponíveis naquele instante histórico.

---

# 2. Status

Estado atual:

```text
DESIGN
```

Implementação:

```text
NOT STARTED
```

Este documento define o contrato inicial da fase:

```text
F5 — Backtest Engine
```

---

# 3. Objetivos do Backtester

O BacktestEngine deverá ser capaz de:

```text
percorrer dados cronologicamente

controlar o relógio da simulação

disponibilizar somente dados conhecidos

receber sinais de Strategy

converter sinais em ordens

aplicar regras de risco

simular execução

aplicar custos

controlar posições

calcular PnL

controlar cash e equity

registrar trades

produzir resultados reproduzíveis
```

---

# 4. O Backtester Não Deve

O BacktestEngine não deverá:

```text
otimizar estratégias automaticamente

acessar dados futuros

inventar candles ausentes

assumir custos zero silenciosamente

alterar o dataset raw

permitir Strategy enviar ordens diretamente

esconder ambiguidades de execução

alterar parâmetros durante o experimento
sem registro
```

---

# 5. Arquitetura Conceitual

Fluxo pretendido:

```text
Validated Historical Data
          ↓
     BacktestEngine
          ↓
       Strategy
          ↓
        Signal
          ↓
      Risk Engine
          ↓
     Order Intent
          ↓
 Simulated Execution
          ↓
         Fill
          ↓
       Portfolio
          ↓
    Trade / Equity
          ↓
      Performance
```

---

# 6. Princípio Temporal

O princípio mais importante é:

```text
O BacktestEngine controla o tempo.
```

A Strategy nunca controla o relógio da simulação.

Ela recebe apenas informações que o Engine decidiu que já estão disponíveis.

---

# 7. Relógio da Simulação

O BacktestEngine será:

```text
bar-by-bar
```

na primeira implementação.

Isso significa que a simulação avança cronologicamente de candle em candle.

Exemplo M15:

```text
10:00
 ↓
10:15
 ↓
10:30
 ↓
10:45
 ↓
11:00
```

---

# 8. Timestamp do Candle

Nos datasets atuais:

```text
time
```

representa o início da barra.

Exemplo:

```text
M15 time = 10:00
```

representa:

```text
10:00 → 10:15
```

---

# 9. Bar Close Time

O BacktestEngine deverá derivar conceitualmente:

```text
bar_close_time
```

através do timeframe.

Exemplo M15:

```text
bar_start = 10:00
bar_close = 10:15
```

H1:

```text
bar_start = 10:00
bar_close = 11:00
```

H4:

```text
bar_start = 08:00
bar_close = 12:00
```

---

# 10. Disponibilidade do OHLC

O OHLC definitivo de uma barra somente é considerado disponível após:

```text
bar_close_time
```

Logo:

```text
H1 10:00
```

não pode ser utilizado como candle fechado às:

```text
10:30
```

---

# 11. Modelo Temporal Inicial

A primeira versão utilizará:

```text
Signal on Close
Execution on Next Bar Open
```

Fluxo:

```text
Candle t fecha
     ↓
Strategy recebe candle t
     ↓
Strategy gera Signal
     ↓
Order Intent é criada
     ↓
próxima barra disponível abre
     ↓
ordem é executada
```

---

# 12. Exemplo

Candle:

```text
10:00 → 10:15
```

fecha às:

```text
10:15
```

A Strategy calcula um sinal usando esse candle.

Entrada:

```text
Open do candle 10:15
```

e não:

```text
Close do candle 10:00
```

---

# 13. Motivo

Utilizar o fechamento de `t` simultaneamente como:

```text
informação para gerar o sinal
```

e:

```text
preço garantido de execução
```

poderia criar execução impossível.

O modelo inicial evita essa ambiguidade.

---

# 14. Regra Principal de Execução

Para market signals:

```text
signal_time = fechamento de t

order_time >= signal_time

fill_time = abertura da próxima barra disponível
```

Portanto:

```text
fill_time >= signal_time
```

A igualdade de timestamps é permitida porque o fechamento da barra `t`
e a abertura da barra `t+1` podem compartilhar a mesma fronteira temporal.

Nesse caso, a proteção contra look-ahead depende da ordem dos eventos:

```text
BAR t CLOSE
    ↓
Signal
    ↓
Order
    ↓
BAR t+1 OPEN
    ↓
Fill

na implementação baseline.

---

# 15. Último Candle do Dataset

Se a Strategy gerar sinal no último candle disponível:

```text
não existe próxima barra
```

Logo:

```text
a ordem não pode ser executada.
```

Ela deverá ser registrada como:

```text
UNFILLED
```

ou cancelada no encerramento do backtest com motivo explícito.

---

# 16. Informação Disponível para Strategy

No instante simulado `T`, a Strategy poderá acessar somente candles cujo:

```text
bar_close_time <= T
```

Nunca candles com:

```text
bar_close_time > T
```

---

# 17. No Look-Ahead

A seguinte condição deverá ser uma invariante:

```text
max(data_available_to_strategy.close_time)
<=
simulation_time
```

Qualquer violação invalida o backtest.

---

# 18. Dados Futuros

A Strategy nunca deverá receber:

```text
df completo
```

sem uma barreira temporal.

Arquitetura perigosa:

```python
strategy.generate_signal(full_dataframe, i)
```

se a Strategy puder acessar livremente:

```python
full_dataframe.iloc[i + 1:]
```

---

# 19. Interface Preferida

A interface futura deverá restringir a informação disponível.

Exemplo conceitual:

```python
strategy.on_bar(context)
```

onde:

```text
context
```

contém apenas informações permitidas naquele instante.

---

# 20. Context

Um futuro objeto:

```text
BacktestContext
```

poderá conter:

```text
current_time

current_bar

historical_bars

position

equity

strategy_state
```

sem expor dados futuros.

---

# 21. Escopo Inicial

A primeira versão do BacktestEngine será intencionalmente simples.

Baseline:

```text
um símbolo por execução

uma Strategy

uma posição aberta por vez

market orders

bar-by-bar

Signal on Close

Next Open execution
```

---

# 22. O Que Não Faz Parte do Baseline

Não será obrigatório inicialmente suportar:

```text
multi-asset portfolio

partial fills

order book

latency modeling

multiple simultaneous positions

pyramiding

complex pending orders

tick-by-tick simulation

market impact
```

Esses recursos podem ser adicionados depois.

---

# 23. Símbolo Inicial

O primeiro instrumento será:

```text
EURUSD
```

Isso permite validar o Engine antes de generalizar para múltiplos símbolos.

---

# 24. Timeframes Iniciais

O Engine deverá funcionar inicialmente com:

```text
M15
H1
H4
```

desde que o dataset utilizado esteja validado.

---

# 25. Candles Incompletos

Nos datasets processados existem:

```text
complete
```

com:

```text
True
False
```

A política padrão será:

```text
complete == True
```

para Strategy e Backtest.

---

# 26. Incompletos Não Geram Sinais

Por padrão:

```text
complete=False
```

não deverá ser enviado à Strategy como candle normal.

Isso vale especialmente para:

```text
H1
H4
```

---

# 27. Gaps

Candles ausentes não são fabricados.

Exemplo:

```text
10:00
10:15
10:30
11:00
```

O Engine não cria:

```text
10:45
```

---

# 28. Próxima Barra Disponível

Caso exista um gap:

```text
Signal
   ↓
gap
   ↓
próxima barra real
```

a ordem baseline será executada na:

```text
próxima barra efetivamente disponível
```

não em um candle artificial.

---

# 29. Exemplo de Gap

Signal gerado na sexta-feira.

Próxima barra disponível:

```text
segunda-feira
```

Se a Strategy permite manter intenção através do fim de semana:

```text
fill ocorre na abertura disponível
```

e o gap de preço é respeitado.

---

# 30. Stale Orders

A primeira versão poderá manter market orders até a próxima barra disponível.

No futuro poderá existir:

```text
max_order_age
```

para invalidar intenções antigas.

Status:

```text
PLANNED
```

---

# 31. Signal

A Strategy não gera diretamente uma ordem no broker.

Ela produz:

```text
Signal
```

Schema conceitual:

```text
signal_id

strategy_id

symbol

timestamp

action

reason

metadata
```

---

# 32. Signal Actions

Baseline sugerido:

```text
ENTER_LONG

ENTER_SHORT

EXIT

HOLD
```

No futuro:

```text
REVERSE

SCALE_IN

SCALE_OUT
```

podem ser adicionados.

---

# 33. HOLD

```text
HOLD
```

significa:

```text
nenhuma alteração desejada
```

Não deve criar ordem.

---

# 34. ENTER_LONG

Representa:

```text
intenção de abrir posição comprada.
```

Ainda não significa que a operação será executada.

---

# 35. ENTER_SHORT

Representa:

```text
intenção de abrir posição vendida.
```

---

# 36. EXIT

Representa:

```text
intenção de encerrar posição existente.
```

---

# 37. Signal != Order

Invariante:

```text
Signal != Order
```

Fluxo:

```text
Strategy
   ↓
Signal
   ↓
Risk
   ↓
Order Intent
```

---

# 38. Risk Gate

Mesmo no Backtest, uma intenção deverá passar pela camada de risco.

Inicialmente poderá existir um modelo simples:

```text
FixedSizeRiskModel
```

Exemplo:

```text
cada operação = tamanho fixo
```

---

# 39. Strategy Não Define Lote Final

A Strategy pode definir:

```text
direção
stop técnico
racional
```

mas o tamanho financeiro final pertence ao:

```text
Risk Engine
```

---

# 40. Order Intent

Depois de aprovado pelo risco:

```text
Order Intent
```

poderá possuir:

```text
order_id

signal_id

symbol

side

quantity

order_type

created_at

stop_loss

take_profit

metadata
```

---

# 41. Order Types Baseline

Na primeira versão:

```text
MARKET
```

será o tipo obrigatório.

Outros tipos:

```text
LIMIT
STOP
STOP_LIMIT
```

podem ser adicionados posteriormente.

---

# 42. Execução de Market Order

Uma market order gerada após fechamento de `t` será executada usando como referência:

```text
Open da próxima barra disponível
```

---

# 43. Reference Price

É importante distinguir:

```text
reference_price
```

de:

```text
execution_price
```

Exemplo:

```text
reference_price =
next_bar.open
```

Depois:

```text
CostModel
```

pode transformar esse preço.

---

# 44. Execution Price

Fluxo:

```text
reference_price
      ↓
spread
      ↓
slippage
      ↓
execution_price
```

---

# 45. OHLC Não É Preço Executável Garantido

Os candles históricos atuais são séries de preço fornecidas pela fonte.

O Engine não deve assumir silenciosamente que:

```text
Open
High
Low
Close
```

representam simultaneamente:

```text
Bid
e
Ask
```

Por isso custos de execução serão modelados separadamente.

---

# 46. CostModel

O BacktestEngine deverá utilizar um componente:

```text
CostModel
```

independente da Strategy.

Responsabilidades:

```text
spread

slippage

commission

futuramente swap
```

---

# 47. Baseline Cost Model

A primeira versão deverá permitir pelo menos:

```text
spread configurável

slippage configurável

commission configurável
```

Valores não devem ser escondidos no código.

---

# 48. Custos Zero

Será permitido executar:

```text
zero-cost backtest
```

apenas para testes de engenharia.

Nesse caso o resultado deverá ser claramente identificado como:

```text
ZERO COST / IDEALIZED
```

e não como backtest realista.

---

# 49. Spread Histórico MT5

O campo:

```text
spread
```

presente no M15 não será utilizado automaticamente.

Motivo:

```text
inconsistência histórica documentada
```

O CostModel determinará explicitamente qual spread será aplicado.

---

# 50. Fixed Spread

Modelo inicial possível:

```text
FixedSpreadModel
```

Exemplo:

```text
spread = 1 pip
```

O valor deverá ser configuração do experimento.

---

# 51. Spread Adverso

O spread deve piorar o preço para o trader.

Conceitualmente:

```text
LONG entry
→ preço maior

LONG exit
→ preço menor

SHORT entry
→ preço menor

SHORT exit
→ preço maior
```

comparado ao preço de referência neutro.

---

# 52. Half-Spread Model

Caso o preço OHLC seja tratado como referência neutra, uma convenção possível é:

```text
half_spread = spread / 2
```

Então:

```text
buy execution
=
reference + half_spread
```

e:

```text
sell execution
=
reference - half_spread
```

A implementação deverá manter a convenção explícita.

---

# 53. Bid/Ask Model Futuro

Quando dados históricos Bid/Ask suficientemente confiáveis estiverem disponíveis:

```text
Bid/Ask
```

poderá substituir o modelo sintético de spread.

Status:

```text
PLANNED
```

---

# 54. Slippage

Slippage representa diferença adicional entre:

```text
preço esperado
```

e:

```text
preço executado
```

No baseline deverá ser:

```text
configurável
```

---

# 55. Slippage Adverso

Por padrão o stress model deverá aplicar slippage:

```text
contra o trader
```

para evitar introdução de otimização artificial.

---

# 56. Commission

Commission deverá ser tratada separadamente de spread.

Configuração futura poderá especificar:

```text
por lote

por lado

round turn

valor fixo
```

A unidade deverá estar explícita.

---

# 57. Swap

Swap é relevante para operações mantidas overnight.

A arquitetura deverá possuir espaço para:

```text
swap_long

swap_short

rollover
```

---

# 58. Swap no Baseline

Se a primeira versão ainda não implementar swap:

```text
swap = 0
```

deverá ser explicitamente registrado no resultado.

Backtests com posições overnight deverão ser classificados como:

```text
PRE-SWAP
```

até a implementação adequada.

---

# 59. Cost Stress

O sistema deverá permitir testar:

```text
Base Cost

1.5 × Cost

2.0 × Cost
```

sem modificar a Strategy.

---

# 60. Position

A primeira versão utilizará:

```text
uma posição aberta por vez
```

por execução de estratégia.

Estados:

```text
FLAT

LONG

SHORT
```

---

# 61. FLAT

Significa:

```text
nenhuma posição aberta.
```

---

# 62. LONG

Uma posição comprada deverá registrar:

```text
symbol

quantity

entry_time

entry_price

stop_loss

take_profit

unrealized_pnl
```

---

# 63. SHORT

A estrutura é equivalente, porém com direção:

```text
SHORT
```

---

# 64. Entrada Duplicada

Se já existir:

```text
LONG
```

e a Strategy gerar:

```text
ENTER_LONG
```

no baseline:

```text
nenhuma nova posição será adicionada.
```

Pyramiding não será permitido inicialmente.

---

# 65. Sinal Oposto

Se existir:

```text
LONG
```

e surgir:

```text
ENTER_SHORT
```

não haverá reversão automática silenciosa.

A política inicial será:

```text
rejeitar a nova entrada
```

ou exigir:

```text
EXIT
```

explícito antes.

---

# 66. Reversal Futuro

Uma configuração futura poderá permitir:

```text
LONG
 ↓
close LONG
 ↓
open SHORT
```

com:

```text
dois fills
dois custos
```

Status:

```text
NOT BASELINE
```

---

# 67. Exit

Quando a Strategy gera:

```text
EXIT
```

em uma posição existente:

```text
Signal no fechamento
      ↓
Order de saída
      ↓
fill na próxima abertura
```

segundo a mesma política temporal da entrada.

---

# 68. Exit Sem Posição

Se:

```text
position = FLAT
```

e surgir:

```text
EXIT
```

a ação baseline será:

```text
IGNORE
```

com possibilidade de registrar evento de diagnóstico.

---

# 69. Stop Loss

Uma posição poderá possuir:

```text
stop_loss
```

definido no momento da entrada ou posteriormente conforme contrato futuro.

No baseline:

```text
stop técnico fixo
```

por trade é suficiente.

---

# 70. Take Profit

Uma posição poderá também possuir:

```text
take_profit
```

---

# 71. Trigger Intrabar

Como o backtester inicial usa OHLC, a sequência exata de preços dentro do candle é desconhecida.

Sabemos apenas:

```text
Open
High
Low
Close
```

---

# 72. Stop Long

Para LONG:

```text
Low <= Stop Loss
```

indica que o stop pode ter sido atingido durante o candle.

---

# 73. Take Profit Long

Para LONG:

```text
High >= Take Profit
```

indica que o target pode ter sido atingido.

---

# 74. Stop Short

Para SHORT:

```text
High >= Stop Loss
```

---

# 75. Take Profit Short

Para SHORT:

```text
Low <= Take Profit
```

---

# 76. Ambiguidade Intrabar

Considere LONG:

```text
Stop = 95
Take Profit = 105
```

Candle:

```text
Open = 100
High = 110
Low = 90
Close = 102
```

Sabemos que:

```text
Stop foi tocado
e
Take Profit foi tocado
```

Mas não sabemos qual ocorreu primeiro.

---

# 77. Regra Conservadora

A política baseline será:

```text
AMBIGUOUS_BAR_POLICY = WORST_CASE
```

Quando Stop e Take Profit forem atingidos na mesma barra e a ordem temporal não puder ser determinada:

```text
assumir o resultado desfavorável.
```

---

# 78. Motivo

Escolher sempre:

```text
Take Profit primeiro
```

introduziria viés otimista.

A política conservadora reduz esse risco.

---

# 79. Política Configurável

No futuro poderá existir:

```text
WORST_CASE

BEST_CASE

STOP_FIRST

TARGET_FIRST

LOWER_TIMEFRAME

TICK_RESOLUTION
```

Mas:

```text
WORST_CASE
```

será o default seguro.

---

# 80. Gap Through Stop

Exemplo LONG:

```text
Stop = 1.1000
```

próxima barra abre em:

```text
1.0950
```

Não é realista assumir fill garantido em:

```text
1.1000
```

---

# 81. Stop com Gap

A política será:

```text
se abertura for pior que o Stop,
usar a abertura como referência
de execução do Stop.
```

Depois aplicar custos/slippage conforme modelo.

---

# 82. Take Profit com Gap Favorável

Para evitar benefício artificial de price improvement, o baseline poderá usar:

```text
Take Profit price
```

como preço de referência quando a abertura ultrapassar favoravelmente o target.

Assim não se concede automaticamente ganho extra baseado apenas em OHLC.

---

# 83. Ordem de Eventos Baseline

Para cada nova barra:

```text
1. avançar simulation_time

2. processar ordens pendentes
   na abertura da barra

3. atualizar posição com fills

4. verificar gap de stop/target

5. avaliar stop/target intrabar

6. atualizar mark-to-market

7. fechar logicamente a barra

8. disponibilizar a barra fechada

9. disponibilizar timeframes superiores
   que fecharam nesse instante

10. chamar Strategy

11. gerar Signal

12. aplicar Risk

13. criar Order Intent
    para próxima barra

14. registrar estado/equity
```

---

# 84. Regra Importante

A Strategy é chamada:

```text
depois que a barra fecha
```

e novas market orders são executadas:

```text
na próxima abertura.
```

---

# 85. Posição Aberta na Mesma Barra

Uma posição executada na abertura de uma barra passa a estar exposta ao:

```text
High
Low
```

daquela barra.

Portanto Stop/Take Profit podem ser atingidos no mesmo candle da entrada.

---

# 86. Ambiguidade na Barra de Entrada

Se após entrada na abertura:

```text
Stop e TP
```

forem ambos tocados na mesma barra:

```text
WORST_CASE
```

também será aplicado.

---

# 87. Stop/TP e Spread

Na primeira implementação OHLC poderá ser utilizado como:

```text
reference price space
```

e o CostModel aplicado no momento dos fills.

Isso é uma aproximação.

Um modelo Bid/Ask completo será uma evolução futura.

---

# 88. PnL Bruto

Conceitualmente:

LONG:

```text
Gross PnL =
Exit Price - Entry Price
```

SHORT:

```text
Gross PnL =
Entry Price - Exit Price
```

antes da conversão para valor monetário.

---

# 89. Quantity

O PnL monetário precisa considerar:

```text
quantity
contract size
instrument specification
```

---

# 90. EURUSD

Para EURUSD, em cenário onde a moeda de PnL coincide com a moeda da conta, uma relação conceitual é:

```text
PnL =
price_difference
×
contract_size
×
lots
```

Mas a arquitetura não deverá tratar essa fórmula como universal para todos os pares e moedas de conta.

---

# 91. Instrument Specification

O BacktestEngine deverá receber propriedades do instrumento de uma estrutura específica.

Exemplo futuro:

```text
InstrumentSpecification
```

contendo:

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
```

---

# 92. Conversão de Moeda

Quando:

```text
profit currency
!=
account currency
```

poderá ser necessária conversão adicional.

Essa funcionalidade não precisa fazer parte do primeiro baseline EURUSD, mas a arquitetura não deve impedir sua implementação futura.

---

# 93. Gross vs Net PnL

O sistema deverá separar:

```text
Gross PnL
```

de:

```text
Net PnL
```

Relação:

```text
Net PnL
=
Gross PnL
-
Spread Cost
-
Slippage
-
Commission
-
Swap
```

considerando a convenção de cada CostModel.

---

# 94. Não Contar Spread Duas Vezes

Se o spread já foi incorporado diretamente ao:

```text
execution_price
```

ele não deve ser novamente subtraído do PnL como custo monetário separado.

A implementação deverá utilizar uma convenção única.

---

# 95. Cost Accounting

Embora o efeito financeiro possa estar incorporado ao preço, o sistema deverá registrar separadamente:

```text
spread impact

slippage impact

commission

swap
```

para auditoria.

---

# 96. Cash

O Portfolio deverá manter:

```text
cash
```

representando capital realizado.

---

# 97. Equity

Equity:

```text
cash
+
unrealized PnL
```

quando houver posição aberta.

---

# 98. Initial Capital

Cada experimento deverá possuir:

```text
initial_capital
```

explicitamente configurado.

Nunca depender de um valor escondido no código.

---

# 99. Unrealized PnL

Com posição aberta:

```text
unrealized_pnl
```

será atualizado utilizando uma convenção de mark-to-market documentada.

Baseline:

```text
Close da barra atual
```

ajustado conforme o modelo de preço escolhido.

---

# 100. Realized PnL

Quando uma posição é encerrada:

```text
realized_pnl
```

é incorporado ao:

```text
cash
```

---

# 101. Equity Curve

A cada período o Engine deverá registrar:

```text
time

cash

unrealized_pnl

equity

position
```

Isso permitirá construir:

```text
equity curve
drawdown
returns
```

---

# 102. Margin

A primeira implementação poderá não reproduzir completamente:

```text
margin

free margin

margin call

stop out
```

Se não implementado, essa limitação deverá aparecer claramente no relatório.

---

# 103. Leverage

Leverage não deverá ser utilizado para fabricar retorno.

O Risk Engine futuro deverá controlar exposição independentemente de o broker permitir alavancagem elevada.

---

# 104. Position Sizing Baseline

Para validar a engenharia do BacktestEngine, inicialmente poderá ser utilizado:

```text
Fixed Position Size
```

Exemplo:

```text
0.01 lot
```

configurável.

---

# 105. Risk-Based Sizing

Depois do baseline funcionar:

```text
risk per trade
```

poderá determinar o lote através de:

```text
capital

stop distance

instrument specification
```

Essa função pertencerá ao Risk Engine.

---

# 106. Order Ledger

Todas as ordens deverão ser registradas.

Schema conceitual:

```text
order_id

signal_id

created_at

scheduled_for

symbol

side

quantity

type

status

reason
```

---

# 107. Order Status

Possíveis estados iniciais:

```text
PENDING

FILLED

REJECTED

CANCELLED

UNFILLED
```

---

# 108. Fill Ledger

Cada execução deverá produzir:

```text
Fill
```

com:

```text
fill_id

order_id

fill_time

reference_price

execution_price

quantity

spread_impact

slippage

commission
```

---

# 109. Trade Ledger

Um trade completo deverá registrar:

```text
trade_id

strategy_id

symbol

side

entry_time

entry_price

exit_time

exit_price

quantity

gross_pnl

net_pnl

spread_cost

slippage_cost

commission

swap

bars_held

exit_reason
```

---

# 110. Exit Reason

Possíveis motivos:

```text
STRATEGY_EXIT

STOP_LOSS

TAKE_PROFIT

END_OF_BACKTEST

RISK_EXIT

KILL_SWITCH

MANUAL_TEST
```

---

# 111. Encerramento no Final do Backtest

O comportamento de posições ainda abertas no último candle deverá ser configurável.

Baseline recomendado:

```text
FORCE_CLOSE_AT_FINAL_AVAILABLE_CLOSE
```

para produzir PnL final completo.

---

# 112. Registro do Forced Close

Esse fechamento deverá possuir:

```text
exit_reason =
END_OF_BACKTEST
```

para não ser confundido com saída gerada pela Strategy.

---

# 113. Alternativa

Também poderá existir:

```text
LEAVE_OPEN
```

para análises específicas.

Mas resultados deverão informar que existe posição não realizada.

---

# 114. Multi-Timeframe

A arquitetura deverá futuramente permitir:

```text
H4 → regime

H1 → signal

M15 → execution
```

sem look-ahead.

---

# 115. Disponibilidade H1

Candle:

```text
H1 10:00
```

fica disponível apenas em:

```text
11:00
```

---

# 116. Disponibilidade H4

Candle:

```text
H4 08:00
```

fica disponível apenas em:

```text
12:00
```

---

# 117. Base Clock

Para estratégias multi-timeframe, uma abordagem futura será escolher um:

```text
base execution timeframe
```

Exemplo:

```text
M15
```

O relógio avança em M15 e libera H1/H4 somente quando seus respectivos fechamentos ocorrerem.

---

# 118. Não Usar Mesmo Índice

Não sincronizar:

```text
M15.iloc[i]

H1.iloc[i]

H4.iloc[i]
```

porque os índices representam frequências diferentes.

Sincronização deverá utilizar:

```text
timestamp
+
bar close time
```

---

# 119. Feature Availability

Features também herdam o tempo de disponibilidade do candle usado para calculá-las.

Exemplo:

```text
EMA(H1)
```

calculada com H1 10:00 só se torna atualizada quando esse H1 fecha às:

```text
11:00
```

---

# 120. Indicator Warm-Up

A Strategy deverá possuir período de warm-up.

Exemplo:

```text
EMA200
```

necessita histórico suficiente antes de gerar sinais.

Durante warm-up:

```text
no trade
```

por padrão.

---

# 121. NaN Features

Se qualquer feature obrigatória estiver:

```text
NaN
```

a Strategy não deverá gerar sinal.

---

# 122. Returns

Retornos utilizados em métricas deverão ser calculados sobre uma frequência explicitamente definida.

Não misturar:

```text
trade returns
```

com:

```text
bar returns
```

sem registrar a metodologia.

---

# 123. Performance

O BacktestEngine produzirá dados brutos.

Um componente separado:

```text
Performance
```

calculará métricas.

---

# 124. Métricas Planejadas

Exemplos:

```text
Net Profit

Total Return

CAGR

Maximum Drawdown

Sharpe Ratio

Sortino Ratio

Profit Factor

Win Rate

Average Win

Average Loss

Payoff Ratio

Expectancy

Trade Count

Exposure

Recovery Factor
```

---

# 125. Nenhuma Métrica Isolada Decide

Não utilizar uma regra universal como:

```text
Sharpe > X
=
Strategy aprovada
```

A avaliação será multidimensional.

---

# 126. Drawdown

Drawdown deverá ser calculado sobre:

```text
equity curve
```

e não apenas sequência de trades fechados.

---

# 127. Trade Statistics

Além de médias deverão ser preservadas distribuições de:

```text
PnL

holding period

MAE

MFE

costs
```

quando essas funcionalidades forem adicionadas.

---

# 128. MAE / MFE

Futuramente poderá ser calculado:

```text
Maximum Adverse Excursion

Maximum Favorable Excursion
```

por trade.

Isso ajudará a estudar Stops e Targets.

Status:

```text
PLANNED
```

---

# 129. Determinismo

Com:

```text
mesmo dataset

mesma Strategy

mesmos parâmetros

mesmos custos

mesmo initial capital

mesma configuração
```

o resultado deve ser idêntico.

---

# 130. Randomness

Caso uma futura simulação utilize aleatoriedade:

```text
Monte Carlo

random slippage
```

deverá registrar:

```text
random_seed
```

---

# 131. Run Configuration

Cada backtest deverá possuir configuração explícita.

Exemplo conceitual:

```text
symbol

timeframe

date_from

date_to

initial_capital

strategy

strategy_parameters

cost_model

risk_model

execution_model

ambiguous_bar_policy
```

---

# 132. Experiment ID

Cada execução deverá futuramente gerar:

```text
experiment_id
```

Exemplo:

```text
EXP-20260808-0001
```

O formato definitivo poderá mudar.

---

# 133. Experiment Manifest

Cada experimento deverá registrar algo equivalente a:

```text
experiment_id

created_at

dataset

dataset_hash

symbol

timeframe

date_from

date_to

strategy_name

strategy_version

parameters

initial_capital

cost_model

risk_model

engine_version

git_commit
```

---

# 134. Dataset Hash

Quando o versionamento de dataset for implementado:

```text
SHA256
```

deverá ser registrado no experimento.

Isso garante que:

```text
"EURUSD M15"
```

não seja uma referência ambígua.

---

# 135. Git Commit

Também será útil registrar:

```text
git commit hash
```

porque mudanças de código podem alterar resultados mesmo quando os parâmetros permanecem iguais.

---

# 136. Logs

O BacktestEngine deverá gerar logs estruturados para eventos relevantes.

Exemplos:

```text
SIGNAL

ORDER_CREATED

ORDER_REJECTED

ORDER_FILLED

POSITION_OPENED

POSITION_CLOSED

STOP_TRIGGERED

TARGET_TRIGGERED

BACKTEST_STARTED

BACKTEST_FINISHED
```

---

# 137. Auditabilidade

Para cada trade deverá ser possível responder:

```text
qual candle gerou o sinal?

qual dado estava disponível?

qual regra gerou o Signal?

qual Risk Model aprovou?

qual era o preço de referência?

qual spread foi aplicado?

qual slippage?

por que saiu?
```

---

# 138. Error Handling

Problemas estruturais deverão falhar explicitamente.

Exemplos:

```text
dataset vazio

timestamp duplicado

timezone incorreto

OHLC inválido

posição inválida

fill antes da ordem
```

---

# 139. Fail Fast

O BacktestEngine não deverá tentar corrigir silenciosamente datasets inválidos.

Essa responsabilidade pertence à camada de dados.

---

# 140. Dataset Validation

Antes de iniciar:

```text
dataset não vazio

UTC

ordenado

timestamps únicos

OHLC válido
```

devem ser verificados.

Para datasets processados:

```text
complete=True
```

por padrão.

---

# 141. Timeframe Validation

O Engine deverá conhecer explicitamente a duração do timeframe.

Exemplo:

```text
M15 = 15 minutos

H1 = 1 hora

H4 = 4 horas
```

Isso é necessário para calcular:

```text
bar_close_time
```

---

# 142. No datetime.now() na Simulação

A lógica histórica nunca deverá utilizar:

```python
datetime.now()
```

para tomar decisões do backtest.

O tempo oficial será:

```text
simulation_time
```

---

# 143. Real Time vs Simulation Time

Separação:

```text
real_time
```

serve para:

```text
logs
momento de execução do programa
```

Enquanto:

```text
simulation_time
```

representa:

```text
tempo histórico do experimento
```

---

# 144. Backtest Start

O experimento possui:

```text
date_from
```

Mas a Strategy poderá necessitar de dados anteriores para warm-up.

---

# 145. Warm-Up Data

Exemplo:

```text
Backtest começa:
2020-01-01

EMA200 H1 precisa de histórico anterior.
```

O Engine poderá carregar:

```text
pre-roll data
```

antes do início oficial.

---

# 146. Pre-Roll

Dados anteriores a:

```text
date_from
```

podem alimentar indicadores.

Porém trades não devem ser abertos antes do início oficial do experimento.

---

# 147. Evaluation Period

A separação deverá ser:

```text
Warm-Up Period
      ↓
Evaluation Period
```

Métricas consideram apenas:

```text
Evaluation Period
```

---

# 148. Date End

Após:

```text
date_to
```

nenhum novo sinal deve ser aberto.

Posições existentes seguem a política:

```text
force close
```

ou outra configuração explícita.

---

# 149. IS / Validation / OOS

A divisão dos períodos pertence à infraestrutura de experimentos.

Exemplo:

```text
Development

Validation

OOS Lockbox
```

O BacktestEngine simplesmente executa o intervalo recebido.

---

# 150. OOS Não Deve Ter Tratamento Especial

A lógica de execução deve ser exatamente a mesma entre:

```text
In-Sample

Validation

Out-of-Sample
```

Apenas o período muda.

---

# 151. Performance Optimization

A primeira prioridade será:

```text
correção
```

e não:

```text
velocidade máxima.
```

---

# 152. Vectorized vs Event-Driven

Indicadores podem utilizar operações vetorizadas.

Mas a execução deverá preservar:

```text
ordem temporal
```

e:

```text
estado da posição
```

---

# 153. Baseline Approach

A primeira versão será conceitualmente:

```text
event-driven / bar-by-bar
```

mesmo que algumas features sejam pré-calculadas.

---

# 154. Feature Precomputation

É aceitável pré-calcular:

```text
EMA
ATR
RSI
```

sobre todo o dataset desde que a fórmula seja causal.

Mas a Strategy ainda só poderá acessar valores correspondentes ao tempo disponível.

---

# 155. Feature Causality

Uma feature em `t` pode utilizar:

```text
t
t-1
t-2
...
```

quando `t` já estiver fechado.

Não pode utilizar:

```text
t+1
```

ou posterior.

---

# 156. Labels

Labels históricos podem utilizar futuro para avaliação supervisionada.

Exemplo:

```text
retorno nos próximos 10 candles
```

Mas labels:

```text
não podem ser utilizados como features
no mesmo instante.
```

---

# 157. Baseline Strategy

Depois do Engine estar validado, a primeira Strategy planejada será:

```text
Simple EMA Trend Following
```

Ela servirá como:

```text
engineering baseline
```

e não como afirmação de rentabilidade.

---

# 158. BacktestEngine Antes da Strategy

A ordem correta é:

```text
Engine

Tests

CostModel

Baseline Strategy
```

e não:

```text
Strategy complexa

→ construir Engine para produzir
o resultado desejado.
```

---

# 159. Testes Obrigatórios

Antes de considerar a primeira versão funcional, deverão existir testes para:

```text
sem look-ahead

signal time

order time

fill time

next-open execution

long PnL

short PnL

spread

slippage

commission

stop

take profit

ambiguous candle

gap through stop

position state

cash

equity

empty dataset

duplicate timestamp

incomplete candle

final forced close
```

---

# 160. Test Dataset

Esses testes deverão usar preferencialmente:

```text
datasets artificiais pequenos
```

onde o resultado possa ser calculado manualmente.

---

# 161. Regression Fixture

Depois de estabilizado, um pequeno dataset poderá produzir resultado fixo.

Exemplo:

```text
10 candles

3 signals

2 trades

resultado conhecido
```

Mudanças inesperadas deverão falhar no teste.

---

# 162. Baseline Execution Assumptions

Resumo do primeiro modelo:

```text
Data:
OHLC bars

Clock:
bar-by-bar

Signal:
after bar close

Market execution:
next available bar open

Position:
one at a time

Pyramiding:
disabled

Costs:
explicit CostModel

Incomplete bars:
excluded

Ambiguous SL/TP:
worst case

Gaps:
preserved

Look-ahead:
prohibited
```

---

# 163. Limitações do Baseline

A primeira versão não será uma reprodução completa da microestrutura real.

Limitações:

```text
sem ordem dos ticks intrabar

sem order book

sem latência real

sem partial fills

sem market impact

spread sintético inicialmente

slippage simplificado

margin model limitado

swap possivelmente ainda simplificado
```

---

# 164. Significado dos Resultados

Um resultado do baseline deverá ser interpretado como:

```text
pesquisa histórica sob um
modelo de execução explicitamente definido
```

e não como:

```text
garantia de execução real.
```

---

# 165. Evolução Posterior

Depois do baseline:

```text
Bar Engine
   ↓
Validated Costs
   ↓
Multi-Timeframe
   ↓
Advanced Orders
   ↓
Tick / Bid-Ask Validation
   ↓
Demo Execution
```

---

# 166. Critério de Conclusão da F5

A fase:

```text
F5 — Backtest Engine
```

só será considerada concluída quando:

```text
Engine implementado

event ordering definido

look-ahead protegido

position accounting validado

cost model integrado

trade ledger funcionando

equity funcionando

testes determinísticos passando

resultados reproduzíveis

documentação atualizada
```

---

# 167. Antes de Estratégias

Antes de iniciar F6:

```text
Simple EMA Trend Following
```

o BacktestEngine deverá passar por testes com:

```text
estratégias artificiais
```

criadas apenas para validar a infraestrutura.

---

# 168. Estratégia Artificial

Exemplo:

```text
BuyFirstBarStrategy
```

poderá gerar:

```text
ENTER_LONG
```

em momento conhecido.

Isso permite testar:

```text
quando entra

a qual preço

quando sai

quanto ganha/perde
```

sem depender de indicadores.

---

# 169. Outro Exemplo

```text
AlwaysLongStrategy
```

ou:

```text
ScheduledSignalStrategy
```

pode ser utilizada exclusivamente em testes.

Essas estratégias não pertencem à pesquisa quantitativa.

---

# 170. Definition of Done do Backtester

A primeira versão será considerada pronta para receber uma Strategy real quando:

```text
[ ] Dataset validation funciona

[ ] Clock funciona

[ ] Closed-bar availability funciona

[ ] No future access funciona

[ ] Signal funciona

[ ] Order Intent funciona

[ ] Next-open fill funciona

[ ] LONG funciona

[ ] SHORT funciona

[ ] EXIT funciona

[ ] Stop funciona

[ ] Take Profit funciona

[ ] Ambiguous-bar policy funciona

[ ] Gap execution funciona

[ ] Spread funciona

[ ] Slippage funciona

[ ] Commission funciona

[ ] Position funciona

[ ] Cash funciona

[ ] Equity funciona

[ ] Trade Ledger funciona

[ ] Order Ledger funciona

[ ] Fill Ledger funciona

[ ] Final position handling funciona

[ ] Tests estão verdes

[ ] Resultado é determinístico
```

---

# 171. Decisões Baseline

As principais decisões tomadas neste documento são:

```text
Signal:
CLOSE

Execution:
NEXT OPEN

Current/Open Candle:
não disponível como fechado

Market Orders:
baseline

Position:
uma por vez

Pyramiding:
não

Automatic Reversal:
não

Incomplete Derived Bars:
excluídos

Missing Bars:
não preenchidos

Ambiguous Stop/TP:
worst case

Gap Through Stop:
fill baseado na abertura pior

Costs:
componente separado

Spread MT5 Candle:
não usado automaticamente

Strategy:
não envia ordem

Risk:
gate separado

Clock:
controlado pelo Engine
```

---

# 172. Decisões que Ainda Podem Evoluir

Este documento não congela para sempre:

```text
multi-position

pending orders

reversal

partial exit

margin

swap detalhado

Bid/Ask histórico

tick execution

portfolio multi-asset

multi-strategy
```

Esses componentes poderão ser adicionados depois que o baseline estiver testado.

---

# 173. Regra para Evolução

Uma funcionalidade nova não deve alterar silenciosamente o comportamento baseline.

Quando houver alteração:

```text
documentar

testar

registrar no CHANGELOG
```

---

# 174. Backtest Result Metadata

Todo resultado deverá informar pelo menos:

```text
Strategy

Symbol

Timeframe

Period

Initial Capital

Position Size / Risk Model

Cost Model

Spread Assumption

Slippage Assumption

Commission Assumption

Swap Assumption

Execution Timing

Ambiguous Bar Policy

Number of Trades
```

---

# 175. Comparabilidade

Dois backtests só devem ser comparados diretamente quando diferenças relevantes forem conhecidas.

Exemplo:

```text
Strategy A:
spread 0.5 pip

Strategy B:
spread 0 pip
```

não representa comparação justa sem ajuste.

---

# 176. Config Snapshot

A configuração completa do experimento deverá ser salva junto aos resultados.

Isso evita:

```text
"Não lembro quais parâmetros usei."
```

---

# 177. Engine Version

Resultados deverão futuramente registrar:

```text
backtest_engine_version
```

para permitir comparação após mudanças de implementação.

---

# 178. Regra de Auditoria

Se um trade aparecer no relatório, deve ser possível reconstruí-lo usando:

```text
dataset
+
config
+
Strategy
+
Engine
```

---

# 179. Regra Principal do Backtest

A regra central desta fase é:

> Primeiro determinamos o que seria possível saber e executar naquele instante histórico; somente depois calculamos se a operação teria sido lucrativa.

---

# 180. Estado do Documento

Backtest Design:

```text
DESIGNED
```

Backtest Engine:

```text
NOT IMPLEMENTED
```

Marco atual:

```text
FOREX v0.1
```

Próximo marco:

```text
FOREX v0.2
Backtesting Infrastructure
```

---

# 181. Próximo Documento

O próximo documento é:

```text
docs/11_ROADMAP.md
```

Ele deverá consolidar:

```text
o que já foi concluído

o que está em desenvolvimento

ordem das próximas fases

critérios de conclusão

BacktestEngine

Strategies

Risk

Robustness

OOS

Demo

Execution futura
```
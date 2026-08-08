# MetaTrader 5 Integration

## 1. Objetivo

Este documento descreve a integração entre a plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

e o:

```text
MetaTrader 5
```

A integração é realizada através do pacote Python:

```text
MetaTrader5
```

O objetivo da camada de integração é fornecer uma interface controlada para:

- conexão com o terminal;
- consulta da conta;
- consulta de símbolos;
- leitura de Bid e Ask;
- leitura de ticks;
- leitura de candles;
- coleta histórica;
- consulta de propriedades dos instrumentos.

No estado atual do projeto, a integração é exclusivamente:

```text
READ ONLY
```

Nenhuma função de envio de ordens faz parte da implementação atual.

---

# 2. Ambiente Validado

A integração foi validada utilizando:

```text
Sistema Operacional: Windows
Python:             3.14.5
MetaTrader5:        5.0.6090
Terminal:           MetaTrader 5
Servidor:           MetaQuotes-Demo
Conta:              Demo
```

O terminal MetaTrader 5 é executado localmente no Windows.

O Python utiliza a sessão já autenticada no terminal.

---

# 3. Pacote Python

A biblioteca utilizada é:

```python
import MetaTrader5 as mt5
```

A versão validada pode ser consultada através de:

```python
print(mt5.__version__)
```

Resultado observado:

```text
5.0.6090
```

---

# 4. Responsabilidade da Integração

A camada de integração com MT5 está localizada em:

```text
broker/
└── mt5_client.py
```

Classe principal:

```text
MT5Client
```

O objetivo dessa classe é encapsular chamadas diretas à biblioteca `MetaTrader5`.

A aplicação deve preferir:

```python
client.current_tick("EURUSD")
```

em vez de espalhar chamadas como:

```python
mt5.symbol_info_tick("EURUSD")
```

por diversos módulos.

Isso cria uma fronteira clara entre:

```text
Aplicação
    ↓
MT5Client
    ↓
MetaTrader5 Python API
    ↓
MetaTrader 5 Terminal
```

---

# 5. Inicialização

A conexão é estabelecida através de:

```python
mt5.initialize()
```

No ambiente atual não foi necessário informar explicitamente:

```text
login
password
server
terminal path
```

porque o terminal já estava aberto e autenticado.

Fluxo:

```text
MetaTrader 5 aberto
        ↓
Conta Demo autenticada
        ↓
Python
        ↓
mt5.initialize()
        ↓
Conexão estabelecida
```

---

# 6. Tratamento de Erros na Inicialização

A inicialização nunca deve ser assumida como bem-sucedida.

Exemplo:

```python
if not mt5.initialize():
    raise RuntimeError(
        f"Falha ao conectar ao MetaTrader 5: "
        f"{mt5.last_error()}"
    )
```

A função:

```python
mt5.last_error()
```

é utilizada para diagnóstico quando a API retorna falha.

---

# 7. Terminal Info

Após a inicialização é possível consultar:

```python
mt5.terminal_info()
```

Essa informação é utilizada para verificar se o terminal realmente está conectado.

Exemplo conceitual:

```python
terminal = mt5.terminal_info()

if terminal is None or not terminal.connected:
    ...
```

A inicialização da biblioteca por si só não deve ser tratada como confirmação suficiente de conectividade operacional.

---

# 8. Encerramento da Conexão

A sessão é encerrada através de:

```python
mt5.shutdown()
```

O `MT5Client` encapsula esse comportamento através de:

```python
client.disconnect()
```

Também implementa suporte a context manager.

Exemplo:

```python
with MT5Client() as client:
    ...
```

Fluxo:

```text
__enter__
    ↓
connect()
    ↓
operações
    ↓
__exit__
    ↓
disconnect()
    ↓
mt5.shutdown()
```

Essa abordagem ajuda a garantir que a conexão seja encerrada mesmo quando ocorre uma exceção.

---

# 9. Account Info

Informações da conta podem ser consultadas através de:

```python
mt5.account_info()
```

No `MT5Client`:

```python
client.account_info()
```

Entre as informações disponíveis estão:

```text
login
server
currency
balance
equity
leverage
```

A aplicação não deve imprimir ou armazenar informações sensíveis sem necessidade.

O login completo da conta não é necessário para logs comuns.

---

# 10. Conta Demo

A configuração inicial utiliza uma conta:

```text
Demo
```

Isso é uma decisão de segurança.

O projeto não possui atualmente nenhuma necessidade de conta real.

A sequência prevista de evolução é:

```text
Research
   ↓
Backtest
   ↓
Out-of-Sample
   ↓
Demo
   ↓
somente futuramente considerar Live
```

---

# 11. Symbol Info

As propriedades de um instrumento são consultadas através de:

```python
mt5.symbol_info(symbol)
```

No projeto:

```python
client.symbol_info(symbol)
```

Esse método também garante que o símbolo esteja disponível no Market Watch quando necessário.

---

# 12. Seleção de Símbolo

Caso o símbolo exista, mas não esteja visível:

```python
mt5.symbol_select(
    symbol,
    True
)
```

pode ser utilizado.

O `MT5Client.symbol_info()` encapsula esse comportamento.

Fluxo:

```text
symbol_info()
     ↓
símbolo existe?
     ↓
visível?
   /     \
 sim     não
  │       ↓
  │  symbol_select()
  │
  ▼
retornar especificações
```

---

# 13. EURUSD

O instrumento inicial do projeto é:

```text
EURUSD
```

No ambiente observado:

```text
Digits:          5
Point:           0.00001
Contract Size:   100000
Volume mínimo:   0.01
Volume step:     0.01
```

Esses valores não devem ser codificados como regras universais.

Eles devem ser consultados dinamicamente através do broker.

---

# 14. Point

O campo:

```text
point
```

representa a menor unidade de preço utilizada pela cotação do símbolo.

Para o EURUSD observado:

```text
Point = 0.00001
```

---

# 15. Pip

Para o EURUSD de 5 dígitos:

```text
1 pip = 0.00010
```

Logo:

```text
1 pip = 10 points
```

Exemplo:

```text
Bid = 1.15571
Ask = 1.15573
```

Diferença:

```text
0.00002
```

ou:

```text
2 points
0.2 pip
```

---

# 16. Pip Não Deve Ser Universalmente Hardcoded

A relação:

```text
pip = point × 10
```

funciona para símbolos Forex típicos com:

```text
3 ou 5 digits
```

mas não deve ser tratada como universal para todos os instrumentos.

A implementação atual utiliza:

```python
if info.digits in (3, 5):
    pip_size = info.point * 10
else:
    pip_size = info.point
```

Essa lógica poderá ser refinada futuramente através de uma camada de especificação de instrumentos.

---

# 17. Bid e Ask

A cotação atual é obtida através de:

```python
mt5.symbol_info_tick(symbol)
```

No projeto:

```python
client.current_tick(symbol)
```

O tick fornece informações como:

```text
Bid
Ask
timestamp
```

O spread instantâneo pode ser calculado como:

```text
Ask - Bid
```

---

# 18. Regra Bid / Ask

Para uma cotação válida:

```text
Ask >= Bid
```

Essa propriedade possui teste automatizado.

Também são verificados:

```text
Bid > 0
Ask > 0
spread >= 0
```

---

# 19. Spread Atual

O spread atual é calculado através de:

```python
spread_price = tick.ask - tick.bid
```

Em points:

```python
spread_points = spread_price / info.point
```

Em pips:

```python
spread_pips = spread_price / pip_size
```

Esse spread representa a diferença Bid/Ask do tick observado naquele momento.

---

# 20. Ticks

O projeto validou acesso a ticks através da API MT5.

Além do último tick, também foi testada coleta histórica através de:

```python
mt5.copy_ticks_range()
```

Foram observados dados contendo:

```text
time
time_msc
bid
ask
```

Isso possibilita futuramente investigar modelos de custos baseados em Bid/Ask histórico.

---

# 21. Limitação Observada nos Ticks

Durante os testes no servidor MetaQuotes-Demo foi observada uma quantidade relevante de ticks com:

```text
Bid == Ask
```

produzindo:

```text
spread = 0
```

Isso mostra que o feed Demo não deve ser automaticamente tratado como representação perfeita de custos reais de execução.

Os ticks continuam úteis para desenvolvimento e investigação.

---

# 22. Candles

Candles são obtidos através de funções como:

```python
mt5.copy_rates_from_pos()
```

e:

```python
mt5.copy_rates_range()
```

Os registros retornados possuem campos como:

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

---

# 23. copy_rates_from_pos

Formato conceitual:

```python
mt5.copy_rates_from_pos(
    symbol,
    timeframe,
    start_pos,
    count,
)
```

O parâmetro:

```text
start_pos
```

define a posição inicial em relação às barras mais recentes.

---

# 24. Barra 0

No MetaTrader 5:

```text
posição 0
```

representa a barra mais recente.

Durante o mercado ativo ela normalmente corresponde ao candle ainda em formação.

Exemplo em M15:

```text
Hora atual: 23:59

Barra 0:
23:45 → 00:00
```

Essa barra ainda não está fechada antes de 00:00.

---

# 25. Barra 1

A posição:

```text
1
```

representa a barra imediatamente anterior à barra mais recente.

Durante uma sessão ativa:

```text
bar 0 = corrente
bar 1 = anterior fechada
```

Por isso a camada `MarketData` utiliza:

```python
start_pos=1
```

quando fornece candles fechados para consumo pela aplicação.

---

# 26. Nuance Importante sobre Barra Corrente

A regra:

```text
bar 0 = candle aberto
```

não deve ser interpretada de forma absoluta.

Tecnicamente:

```text
bar 0 = barra mais recente
```

Se o mercado estiver fechado e não houver novos ticks, a barra mais recente pode já ter finalizado efetivamente.

Por isso a arquitetura considera o conceito de disponibilidade temporal, e não apenas o número do índice.

---

# 27. Proteção Contra Candle Corrente

Existe um teste automatizado:

```text
test_closed_bars_do_not_include_current_bar
```

O teste compara:

```text
último candle fornecido pela MarketData
```

com:

```text
barra mais recente do MT5
```

e exige:

```text
last_closed_time < current_bar_time
```

no contexto de mercado testado.

Essa proteção ajuda a evitar regressões futuras.

---

# 28. Look-Ahead

Utilizar informações de uma barra antes que estejam disponíveis representa um dos principais riscos em backtesting.

Exemplo incorreto:

```text
23:45 candle começa
       ↓
usa Close de 00:00
       ↓
gera sinal em 23:45
```

O `Close` final ainda não era conhecido naquele momento.

O sistema deve respeitar:

```text
availability time
```

de cada dado.

---

# 29. Uso Correto de Candle Fechado

Modelo conceitual:

```text
Candle t
   ↓
fecha
   ↓
OHLC de t torna-se conhecido
   ↓
Strategy processa t
   ↓
ação futura ocorre segundo
modelo de execução
```

A especificação exata de execução será definida no documento do Backtest Engine.

---

# 30. Timeframes MT5

A API fornece constantes como:

```python
mt5.TIMEFRAME_M15
mt5.TIMEFRAME_H1
mt5.TIMEFRAME_H4
mt5.TIMEFRAME_D1
```

Atualmente o projeto utiliza diretamente o MT5 principalmente para:

```text
M15
```

e deriva H1 e H4 internamente.

---

# 31. Razão para M15 como Fonte Base

O dataset intraday principal atual é:

```text
EURUSD M15
```

A partir dele:

```text
M15
 ├── H1
 └── H4
```

Isso oferece maior controle sobre:

```text
fronteiras dos candles
consistência entre timeframes
gaps
contagem de candles fonte
```

---

# 32. copy_rates_range

Para histórico por intervalo é utilizada:

```python
mt5.copy_rates_range()
```

O `MT5Client` fornece:

```python
rates_range()
```

como wrapper.

---

# 33. Datas UTC

As datas recebidas pela aplicação devem ser:

```text
timezone-aware
UTC
```

Exemplo:

```python
from datetime import datetime, timezone

date_from = datetime(
    2020,
    1,
    1,
    tzinfo=timezone.utc,
)
```

Datas timezone-naive devem ser rejeitadas.

---

# 34. Conversão para Unix Timestamp

Durante o desenvolvimento, a integração passou a converter:

```text
datetime UTC
```

para:

```text
Unix timestamp inteiro
```

antes de chamar `copy_rates_range()`.

Exemplo:

```python
timestamp_from = int(
    date_from.timestamp()
)

timestamp_to = int(
    date_to.timestamp()
)
```

Fluxo:

```text
datetime UTC
    ↓
Unix timestamp
    ↓
MT5
```

---

# 35. Motivação da Conversão

Durante os testes foi observado:

```text
Terminal: Invalid params
```

em requisições históricas extensas.

A conversão explícita para timestamp Unix elimina ambiguidades na fronteira entre:

```text
Python datetime
```

e:

```text
binding nativo do MT5
```

Além disso, mantém clara a política de UTC do projeto.

---

# 36. Validação do Intervalo

O método `rates_range()` valida:

```text
date_from possui timezone
date_to possui timezone
date_from < date_to
```

Caso contrário, deve falhar explicitamente.

Exemplo:

```python
if date_from >= date_to:
    raise ValueError(
        "date_from precisa ser anterior a date_to."
    )
```

---

# 37. Histórico em Chunks

Uma chamada solicitando vários anos de histórico de uma única vez apresentou problemas durante o desenvolvimento.

Uma chamada curta, por exemplo de aproximadamente 7 dias, funcionou corretamente.

Por isso foi adotado:

```text
chunk_days = 90
```

na coleta histórica.

---

# 38. Fluxo de Coleta em Chunks

Exemplo:

```text
2015-01-01
    ↓
2015-04-01
    ↓
2015-06-30
    ↓
2015-09-28
    ↓
...
    ↓
2026
```

Cada intervalo é solicitado separadamente.

Depois:

```text
chunks
   ↓
concat
   ↓
sort
   ↓
deduplicate
   ↓
validate
```

---

# 39. Vantagens dos Chunks

A coleta em blocos:

- reduz o tamanho de cada requisição;
- facilita diagnóstico;
- evita perder toda a coleta se um intervalo falhar;
- permite observar disponibilidade histórica por período;
- facilita futura retomada parcial de downloads.

---

# 40. Resposta Fora da Janela Solicitada

Durante os primeiros testes históricos, pedidos referentes a períodos antigos retornaram registros inesperados fora da janela efetivamente solicitada.

Por esse motivo o `HistoricalData` aplica uma proteção adicional.

Após receber um chunk:

```python
chunk_df = chunk_df[
    (chunk_df["time"] >= current_from)
    & (chunk_df["time"] < current_to)
].copy()
```

Isso garante:

```text
dados aceitos
    ∈
janela solicitada
```

---

# 41. Regra de Confiança

Uma API externa não deve ser considerada correta apenas porque retornou dados.

O sistema deve validar:

```text
timestamp
intervalo
ordenação
OHLC
timezone
duplicados
```

antes de aceitar uma resposta.

Essa regra é aplicada também à integração MT5.

---

# 42. Max Bars in Chart

O MetaTrader 5 possui configuração relacionada ao número máximo de barras disponíveis nos gráficos.

No ambiente atual foi verificado:

```text
Max bars: 100000000
```

Durante os primeiros testes, antes do histórico completo estar disponível, foram obtidos aproximadamente:

```text
101 mil candles M15
```

Depois do histórico estar carregado adequadamente, a coleta produziu:

```text
288223 candles
```

---

# 43. Histórico Final Coletado

O histórico atual obtido através do MT5 é:

```text
EURUSD
M15
```

Período:

```text
2015-01-02 09:00 UTC
→
2026-08-07 23:45 UTC
```

Quantidade:

```text
288223 candles
```

---

# 44. Spread nos Candles

O campo:

```text
spread
```

também existe nas barras retornadas pelo MT5.

Entretanto, o comportamento observado foi inconsistente.

Em candles antigos foram encontrados valores como:

```text
11
14
18
```

points.

Em vários períodos recentes foram encontrados muitos:

```text
0
```

---

# 45. Distribuição Histórica do Spread

Na auditoria do dataset M15:

```text
Percentual de spread zero:
32.54%
```

Também houve diferenças significativas entre anos.

Isso indica que esse campo não deve ser tratado automaticamente como representação precisa do spread histórico negociável.

---

# 46. Decisão sobre Spread

O campo continuará preservado no dataset bruto.

Porém:

```text
spread dos candles MT5
        !=
CostModel oficial
```

O futuro Backtest Engine utilizará um componente específico de custos.

---

# 47. Tick Volume

O campo:

```text
tick_volume
```

foi consistente o suficiente para permanecer no dataset.

Ele representa atividade de ticks observada na fonte.

Não representa:

```text
volume total global negociado no Forex
```

---

# 48. Real Volume

O campo:

```text
real_volume
```

apresentou comportamento estruturalmente inconsistente.

Percentual de candles com valor maior que zero:

```text
2015   ~44%
2016  ~100%
2017   ~43%
2018+    0%
```

Esse comportamento indica que o significado/disponibilidade do campo mudou no histórico.

---

# 49. Decisão sobre Real Volume

O campo:

```text
real_volume
```

é preservado apenas como dado bruto.

Não será utilizado como:

```text
feature
filtro
sinal
regime
```

na configuração atual.

---

# 50. Timestamps Retornados

Os timestamps brutos do MT5 são convertidos através de:

```python
pd.to_datetime(
    df["time"],
    unit="s",
    utc=True,
)
```

Resultado:

```text
2026-08-07 23:45:00+00:00
```

O:

```text
+00:00
```

representa UTC.

---

# 51. Timezone Interno

O projeto define:

```text
UTC
```

como timezone interno oficial.

Fluxo:

```text
MetaTrader 5
      ↓
timestamp
      ↓
UTC
      ↓
DataFrame
      ↓
Parquet
      ↓
Backtest futuro
```

---

# 52. Sessões de Mercado

Estratégias futuras podem exigir horário local de sessões.

Exemplo:

```text
London
New York
```

Nesses casos a conversão deverá ocorrer a partir de UTC utilizando zonas reais:

```text
Europe/London
America/New_York
```

Não utilizar offsets fixos durante todo o ano.

---

# 53. DST

Horários de sessão não devem ser definidos através de regras fixas como:

```text
London = GMT
```

durante todo o ano.

O sistema deverá utilizar timezone que represente horário de verão corretamente.

Essa conversão pertence à camada de estratégia/sessão, não à fonte bruta de dados.

---

# 54. Histórico e Mercado Fechado

Durante finais de semana não existem candles normais de negociação Forex.

Portanto:

```text
ausência de candles
```

não significa automaticamente:

```text
erro de API
```

A auditoria encontrou:

```text
659 gaps
```

dos quais:

```text
605
```

atravessam finais de semana.

---

# 55. Gaps Intraweek

Também foram identificados:

```text
54 gaps intraweek
```

Parte deles corresponde a períodos como:

```text
Natal
Ano Novo
feriados
```

Outros permanecem como descontinuidades da fonte.

Eles não são preenchidos artificialmente.

---

# 56. Integration Tests

A interação com o MetaTrader 5 é coberta por testes automatizados de integração.

Entre eles:

```text
test_current_quote_is_valid
test_closed_bars_count
test_closed_bars_are_sorted
test_closed_bars_have_no_duplicate_timestamps
test_closed_bars_are_utc
test_ohlc_integrity
test_prices_are_positive
test_tick_volume_is_non_negative
test_closed_bars_do_not_include_current_bar
```

---

# 57. Pytest Marker

O projeto utiliza:

```ini
[pytest]
markers =
    integration: testes que necessitam do MetaTrader 5 conectado
```

Isso permite distinguir:

```text
testes locais
```

de:

```text
testes que dependem do terminal
```

---

# 58. Estado Atual dos Testes

No marco atual:

```text
25 tests
25 passed
0 failed
```

Os testes não cobrem apenas MT5, mas também:

```text
HistoricalData
TimeframeBuilder
```

---

# 59. Read-Only

Não existem atualmente chamadas a:

```python
mt5.order_send()
```

no fluxo do projeto.

O estado de segurança é:

```text
READ ONLY
```

---

# 60. Algo Trading

Para as operações atuais de leitura não existe necessidade de habilitar execução algorítmica de ordens.

A implementação de trading será tratada apenas em fase futura.

Nesse momento deverão ser criadas proteções específicas para execução.

---

# 61. TRADING_ENABLED

O arquivo `.env` possui:

```env
TRADING_ENABLED=false
```

Essa configuração documenta a intenção atual de impedir operações.

Entretanto, quando a execução for desenvolvida, ela não será a única barreira.

---

# 62. Futuro MT5Execution

A arquitetura futura poderá possuir:

```text
execution/
└── mt5_execution.py
```

Responsável por operações como:

```text
order validation
order sending
result validation
fill handling
```

Esse componente ainda não existe.

---

# 63. Separação MT5Client / MT5Execution

A arquitetura futura deve manter distinção entre:

```text
MT5Client
```

responsável por acesso ao broker e dados,

e:

```text
MT5Execution
```

responsável por execução de ordens.

Isso evita transformar `MT5Client` em uma classe monolítica.

---

# 64. Estratégia Não Conhece MT5

Uma Strategy futura não deverá importar:

```python
MetaTrader5
```

e não deverá chamar:

```python
mt5.order_send()
```

Fluxo correto:

```text
MT5
 ↓
Data
 ↓
Strategy
 ↓
Signal
 ↓
Risk
 ↓
Execution
 ↓
MT5
```

---

# 65. Erros Externos

Chamadas MT5 podem retornar:

```text
None
False
erro
```

O código deve sempre tratar essas situações.

Exemplo:

```python
rates = mt5.copy_rates_from_pos(...)

if rates is None:
    raise RuntimeError(
        f"Erro: {mt5.last_error()}"
    )
```

Falhas não devem ser convertidas silenciosamente em datasets vazios sem diagnóstico.

---

# 66. Context Manager

A implementação:

```python
with MT5Client() as client:
```

é preferida em scripts porque torna explícito o ciclo de vida da conexão.

Exemplo:

```python
with MT5Client() as client:
    tick = client.current_tick("EURUSD")
```

Ao sair do bloco:

```text
disconnect()
```

é executado.

---

# 67. Métodos Atuais do MT5Client

No estado atual, a classe possui funcionalidades equivalentes a:

```text
connect
disconnect
account_info
symbol_info
current_tick
current_bar
rates
rates_range
```

Esses métodos podem evoluir, mas devem preservar a responsabilidade da camada de broker.

---

# 68. current_tick()

Responsabilidade:

```text
obter último tick disponível
```

Fluxo:

```text
ensure connected
      ↓
ensure symbol
      ↓
symbol_info_tick
      ↓
validate response
      ↓
return tick
```

---

# 69. current_bar()

Responsabilidade:

```text
obter a barra mais recente
```

Utiliza:

```python
copy_rates_from_pos(
    symbol,
    timeframe,
    0,
    1,
)
```

Atualmente é utilizado principalmente para validação/testes da proteção contra candle corrente.

---

# 70. rates()

Responsabilidade:

```text
obter uma quantidade N de barras
a partir de determinada posição
```

É utilizado pela camada `MarketData`.

Exemplo:

```text
start_pos=1
count=100
```

---

# 71. rates_range()

Responsabilidade:

```text
obter barras entre duas datas
```

É utilizado pela camada `HistoricalData`.

O método:

- valida timezone;
- valida intervalo;
- converte datetime para Unix;
- chama `copy_rates_range`;
- trata erros.

---

# 72. Dependência Permitida

A direção atual é:

```text
MetaTrader5 library
       ↑
MT5Client
       ↑
MarketData / HistoricalData
```

O inverso não deve ocorrer.

`MT5Client` não deve importar:

```text
MarketData
HistoricalData
Strategy
BacktestEngine
```

---

# 73. Possibilidade de Outro Broker

A arquitetura deve permitir futuramente algo como:

```text
Broker Interface
     │
     ├── MT5Client
     ├── BrokerXClient
     └── HistoricalProviderClient
```

Esse desacoplamento ainda não está formalizado através de uma interface abstrata, mas é um objetivo arquitetural.

---

# 74. Limitações Conhecidas do MetaQuotes-Demo

Com base nos testes do projeto, o feed atual é considerado adequado para:

```text
desenvolvimento
integração
testes funcionais
histórico OHLC
prototipagem
```

Mas apresenta limitações para:

```text
custos históricos precisos
spread histórico definitivo
real volume
modelagem final de execução
```

---

# 75. Uso Pretendido do Feed Atual

Classificação atual:

```text
MetaQuotes-Demo

Infrastructure Development      ✅
OHLC Research                   ✅
Timeframe Construction          ✅
Testing                         ✅

Final Cost Validation           ❌
Production Execution Model      ❌
Reliable Real Volume            ❌
```

---

# 76. Fonte de Dados Futura

Antes de validação final de estratégias poderão ser investigadas fontes adicionais.

Possibilidades conceituais:

```text
broker específico
ticks Bid/Ask
provider histórico especializado
```

A fonte definitiva ainda não foi escolhida.

---

# 77. Princípio de Independência

A lógica de uma estratégia não deve depender de peculiaridades do MetaQuotes-Demo.

Por exemplo, a Strategy não deve assumir:

```text
spread == coluna spread do MT5
```

nem:

```text
real_volume sempre existe
```

A estratégia deve consumir dados padronizados pela plataforma.

---

# 78. Diagnóstico

Comandos úteis durante desenvolvimento:

Verificar pacote:

```powershell
python -c "import MetaTrader5 as mt5; print(mt5.__version__)"
```

Verificar conexão:

```powershell
python -c "import MetaTrader5 as mt5; print(mt5.initialize()); print(mt5.last_error()); mt5.shutdown()"
```

Verificar caminho do módulo do projeto:

```powershell
python -c "import broker.mt5_client as m; print(m.__file__)"
```

Verificar método:

```powershell
python -c "from broker.mt5_client import MT5Client; print(hasattr(MT5Client, 'rates_range'))"
```

---

# 79. Falha de Método Ausente

Durante desenvolvimento foram encontrados erros como:

```text
AttributeError:
'MT5Client' object has no attribute 'current_bar'
```

e:

```text
AttributeError:
'MT5Client' object has no attribute 'rates_range'
```

Esses casos ocorreram quando o método ainda não estava presente corretamente na classe.

Para diagnóstico:

```python
hasattr(
    MT5Client,
    "rates_range"
)
```

pode ser utilizado.

---

# 80. Import Path

Quando houver dúvida sobre qual arquivo está sendo importado:

```python
import broker.mt5_client as m

print(m.__file__)
```

O resultado deve apontar para o arquivo dentro do projeto atual.

Isso ajuda a identificar conflitos de importação.

---

# 81. Regras de Segurança da Integração

Durante o estado atual:

```text
Não armazenar senha no código.

Não solicitar credenciais desnecessariamente.

Não executar order_send.

Não conectar estratégia diretamente ao broker.

Não assumir spread histórico como custo real.

Não assumir que resposta da API é válida sem verificar.

Não utilizar candle corrente como candle fechado.
```

---

# 82. Invariantes da Integração

A camada MT5 deve respeitar:

```text
Conexão explícita

Erro explícito

Símbolo validado

Timestamp normalizado

Bid <= Ask

Dados históricos dentro da janela

Sem execução de ordens nesta fase
```

---

# 83. Relação com Outros Documentos

Visão geral:

```text
docs/01_PROJECT_OVERVIEW.md
```

Arquitetura:

```text
docs/02_ARCHITECTURE.md
```

Setup:

```text
docs/03_ENVIRONMENT_SETUP.md
```

Market Data:

```text
docs/05_MARKET_DATA.md
```

Historical Data:

```text
docs/06_HISTORICAL_DATA.md
```

Data Quality:

```text
docs/07_DATA_QUALITY.md
```

---

# 84. Estado Atual

Integração MT5 no marco:

```text
FOREX v0.1
```

Status:

```text
MT5 initialization          COMPLETE
Terminal validation         COMPLETE
Account reading             COMPLETE
Symbol specification        COMPLETE
Current tick                COMPLETE
Bid / Ask                   COMPLETE
Current bar                 COMPLETE
Closed bars                 COMPLETE
Historical range            COMPLETE
Chunked collection          COMPLETE
UTC normalization           COMPLETE
Integration tests           COMPLETE

Order execution             NOT IMPLEMENTED
Live trading                NOT IMPLEMENTED
```

---

# 85. Resultado

A integração atual fornece uma camada suficiente para suportar:

```text
MarketData
HistoricalData
Data Quality
TimeframeBuilder
```

sem expor diretamente o restante da aplicação à biblioteca `MetaTrader5`.

O próximo documento é:

```text
docs/05_MARKET_DATA.md
```

Ele documentará formalmente o contrato dos dados de mercado usados pela plataforma, incluindo:

```text
OHLC
timestamps
UTC
Bid / Ask
Point
Pip
Spread
Tick Volume
Real Volume
Closed Bars
DataFrame Schema
regras de validade
```
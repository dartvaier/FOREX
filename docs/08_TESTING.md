# Testing

## 1. Objetivo

Este documento define a estratégia de testes automatizados da plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

O objetivo dos testes não é apenas verificar se o código executa.

Os testes devem proteger propriedades essenciais do sistema contra regressões futuras.

O princípio central é:

> Um comportamento crítico do sistema deve ser protegido por teste sempre que possível.

Isso é especialmente importante em software quantitativo, onde pequenos erros podem gerar resultados aparentemente plausíveis, porém incorretos.

---

# 2. Framework

O projeto utiliza:

```text
pytest
```

como framework principal de testes automatizados.

Ambiente atualmente validado:

```text
pytest 9.1.1
```

Execução:

```powershell
pytest -v
```

---

# 3. Estado Atual

No marco atual do projeto:

```text
25 tests
25 passed
0 failed
```

Áreas cobertas:

```text
MarketData
HistoricalData
TimeframeBuilder
```

Ainda não existem testes de:

```text
BacktestEngine
Strategy
Risk
CostModel
Execution
Portfolio
Performance
```

porque esses componentes ainda não foram implementados.

---

# 4. Estrutura Atual

Diretório:

```text
tests/
```

Arquivos atuais:

```text
tests/
├── test_market_data.py
├── test_historical_data.py
└── test_timeframe_builder.py
```

---

# 5. Tipos de Teste

O projeto diferencia principalmente:

```text
Unit Tests

Integration Tests

Regression Tests
```

Outras categorias poderão ser adicionadas no futuro.

---

# 6. Unit Tests

Unit Tests validam componentes isolados.

Idealmente:

```text
não dependem de MT5
não dependem de rede
não dependem de horário atual
não dependem de conta Demo
```

Exemplos futuros:

```text
cálculo de PnL

CostModel

position sizing

risk limits

EMA strategy

order state transitions

drawdown

metrics
```

---

# 7. Integration Tests

Integration Tests validam a interação entre o projeto e componentes externos.

Exemplo atual:

```text
Python
   ↓
MT5Client
   ↓
MetaTrader 5
```

Esses testes podem exigir:

```text
MetaTrader 5 instalado
terminal aberto
conta conectada
símbolo disponível
```

---

# 8. Marker de Integração

O projeto utiliza:

```text
pytest.ini
```

com:

```ini
[pytest]
markers =
    integration: testes que necessitam do MetaTrader 5 conectado
```

Isso permite marcar testes dependentes do terminal.

---

# 9. Executar Integration Tests

Exemplo:

```powershell
pytest -v -m integration
```

Esse comando deve executar apenas os testes marcados como:

```text
integration
```

---

# 10. Executar Todos os Testes

Comando padrão:

```powershell
pytest -v
```

No estado atual:

```text
25 passed
```

---

# 11. Regression Tests

Regression Tests serão importantes quando o BacktestEngine existir.

Objetivo:

> Garantir que uma alteração no código não mude silenciosamente um resultado previamente conhecido.

Exemplo futuro:

```text
Dataset artificial fixo
+
Strategy fixa
+
CostModel fixo
=
Trades esperados fixos
```

Se o resultado mudar sem intenção, o teste deve falhar.

---

# 12. Testes como Contrato Executável

A documentação descreve as regras do sistema.

Os testes devem transformar parte dessas regras em código executável.

Exemplo documental:

```text
Strategy não deve receber candle corrente.
```

Teste:

```text
test_closed_bars_do_not_include_current_bar
```

Assim uma mudança futura que viole a regra produz falha imediata.

---

# 13. Market Data Tests

Arquivo:

```text
tests/test_market_data.py
```

A suíte atual contém nove testes.

---

# 14. test_current_quote_is_valid

Valida a cotação corrente.

Propriedades:

```text
symbol correto

Bid > 0

Ask > 0

Ask >= Bid

Point > 0

Pip Size > 0

Spread Points >= 0

Spread Pips >= 0
```

Esse teste depende do MetaTrader 5.

---

# 15. Por que Ask >= Bid

Uma cotação normal deve satisfazer:

```text
Ask >= Bid
```

Caso:

```text
Ask < Bid
```

exista, o dado deve ser considerado estruturalmente inválido para o modelo atual.

---

# 16. test_closed_bars_count

Solicita determinada quantidade de candles fechados.

Exemplo atual:

```text
100
```

e verifica:

```text
len(bars) == 100
```

Isso detecta regressões básicas na coleta.

---

# 17. test_closed_bars_are_sorted

Valida:

```python
bars["time"].is_monotonic_increasing
```

O dataset entregue pela MarketData deve estar em ordem cronológica crescente.

---

# 18. test_closed_bars_have_no_duplicate_timestamps

Valida:

```text
duplicados de time = 0
```

Dois candles do mesmo símbolo/timeframe não devem possuir o mesmo timestamp na série entregue.

---

# 19. test_closed_bars_are_utc

Valida que:

```text
time
```

possui timezone.

E:

```text
timezone == UTC
```

Isso protege contra regressões de timezone.

---

# 20. test_ohlc_integrity

Valida:

```text
High >= Open
High >= Close

Low <= Open
Low <= Close

High >= Low
```

Um candle que não satisfaz essas condições representa uma violação estrutural.

---

# 21. test_prices_are_positive

Valida:

```text
Open > 0
High > 0
Low > 0
Close > 0
```

para o instrumento atual.

---

# 22. test_tick_volume_is_non_negative

Valida:

```text
tick_volume >= 0
```

Valores negativos seriam incompatíveis com a interpretação atual do campo.

---

# 23. test_closed_bars_do_not_include_current_bar

Esse é um dos testes mais importantes da suíte atual.

Objetivo:

> Garantir que a barra mais recente do MT5 não seja entregue como candle fechado pela MarketData.

Fluxo:

```text
MarketData
    ↓
último candle fechado

MT5Client
    ↓
barra mais recente

comparação
```

Condição:

```text
last_closed_time < current_bar_time
```

no cenário de mercado testado.

---

# 24. Por que Esse Teste Existe

Um erro simples como alterar:

```python
start_pos=1
```

para:

```python
start_pos=0
```

poderia inserir a barra corrente nas séries destinadas à estratégia.

Isso poderia causar:

```text
repainting
look-ahead prático
sinais inconsistentes
backtests irreproduzíveis
```

O teste transforma essa regra em proteção automática.

---

# 25. Historical Data Tests

Arquivo:

```text
tests/test_historical_data.py
```

Contém atualmente oito testes.

---

# 26. test_historical_file_exists

Valida a existência de:

```text
data/raw/EURUSD/M15.parquet
```

Sem o dataset esperado, os testes históricos não devem prosseguir silenciosamente.

---

# 27. test_historical_dataset_not_empty

Valida:

```text
dataset não vazio
```

Um arquivo Parquet válido, porém sem linhas, não representa histórico utilizável.

---

# 28. test_historical_timestamps_are_unique

Valida:

```text
duplicated(time) == 0
```

no arquivo histórico persistido.

---

# 29. test_historical_timestamps_are_sorted

Valida ordem cronológica crescente.

Essa propriedade é fundamental para:

```text
indicadores

resample

backtest

returns

walk-forward
```

---

# 30. test_historical_data_is_utc

Valida:

```text
timezone == UTC
```

no dataset persistido.

Isso garante que o timezone não se perca durante:

```text
Parquet write

Parquet read
```

---

# 31. test_historical_has_no_nulls

Valida:

```text
NaN total = 0
```

nas colunas atuais do dataset.

Isso não verifica gaps temporais.

Gaps e valores nulos são conceitos distintos.

---

# 32. test_historical_ohlc_integrity

Repete as invariantes OHLC sobre todo o histórico persistido.

Isso permite detectar corrupção ou alterações no dataset.

---

# 33. test_historical_prices_are_positive

Valida preços positivos em:

```text
open
high
low
close
```

sobre todo o arquivo M15.

---

# 34. TimeframeBuilder Tests

Arquivo:

```text
tests/test_timeframe_builder.py
```

Contém atualmente oito testes.

---

# 35. test_h1_is_created

Valida que:

```text
M15
 ↓
H1
```

produz um DataFrame não vazio.

---

# 36. test_h4_is_created

Valida que:

```text
M15
 ↓
H4
```

produz um DataFrame não vazio.

---

# 37. test_h1_complete_bars_have_four_m15

Para:

```text
complete == True
```

valida:

```text
source_bar_count == 4
```

Isso formaliza o contrato de H1.

---

# 38. test_h4_complete_bars_have_sixteen_m15

Para H4 completo:

```text
source_bar_count == 16
```

Essa proteção é importante porque um simples resample do pandas poderia criar um candle H4 mesmo quando parte dos M15 estivesse ausente.

---

# 39. test_h1_alignment

Valida:

```text
minute == 0
```

nos timestamps H1.

Exemplos válidos:

```text
09:00
10:00
11:00
```

---

# 40. test_h4_alignment

Valida:

```text
minute == 0
```

e:

```text
hour % 4 == 0
```

Fronteiras atuais:

```text
00:00

04:00

08:00

12:00

16:00

20:00
```

em UTC.

---

# 41. test_generated_timeframes_are_utc

Valida que H1 e H4 continuam:

```text
UTC timezone-aware
```

depois do resample.

---

# 42. test_generated_ohlc_integrity

Valida novamente as regras OHLC sobre:

```text
H1
H4
```

Isso protege a transformação.

---

# 43. Resumo da Suíte Atual

Distribuição:

```text
MarketData          9

HistoricalData      8

TimeframeBuilder    8
```

Total:

```text
25
```

Estado:

```text
25 passed
```

---

# 44. O Que os Testes Atuais Garantem

A suíte fornece proteção contra regressões relacionadas a:

```text
cotação inválida

Ask < Bid

preços não positivos

timezone incorreto

duplicados

ordenação

OHLC inválido

candle corrente

arquivo histórico ausente

dataset vazio

nulls

resample incorreto

H1 incompleto marcado como completo

H4 incompleto marcado como completo

alinhamento temporal errado
```

---

# 45. O Que os Testes Atuais Não Garantem

Os testes não demonstram que:

```text
o spread é realista

todos os gaps são corretos

o feed é perfeito

a estratégia será lucrativa

o histórico representa outro broker

slippage é conhecido

custos estão corretos
```

Essas questões pertencem a outras análises.

---

# 46. Tests != Statistical Validation

É importante distinguir:

```text
Software Test
```

de:

```text
Statistical Test
```

Exemplo:

```text
test_ohlc_integrity
```

é teste de software/dados.

Já:

```text
Sharpe significativamente maior que zero
```

seria uma análise estatística.

São problemas diferentes.

---

# 47. Tests != Strategy Validation

Uma Strategy pode passar em:

```text
100% dos unit tests
```

e ainda ser:

```text
não lucrativa
overfit
sem fundamento
instável
```

Os testes verificam implementação.

A validação quantitativa verifica comportamento.

---

# 48. Filosofia de Testes

O projeto deve priorizar testes sobre propriedades importantes, e não apenas cobertura percentual.

Exemplo:

```text
100% line coverage
```

não garante que as regras financeiras críticas estão corretas.

Preferimos testar:

```text
invariantes
casos-limite
ordem temporal
PnL
custos
estado
```

---

# 49. Testes Determinísticos

Sempre que possível:

```text
mesma entrada
    ↓
mesma saída
```

Testes não devem depender de aleatoriedade descontrolada.

Caso exista aleatoriedade futura:

```text
random seed
```

deve ser configurável.

---

# 50. Fixtures Futuras

O projeto deverá utilizar datasets artificiais pequenos para testes do BacktestEngine.

Exemplo:

```text
time   open high low close

10:00  100  102  99  101

10:15  101  104 100  103

10:30  103  103  97   98
```

Com poucos candles, é possível calcular manualmente o resultado esperado.

---

# 51. Por que Dados Artificiais

Testar o BacktestEngine apenas com:

```text
288223 candles EURUSD
```

tornaria erros difíceis de interpretar.

Um dataset artificial permite saber exatamente:

```text
quando a ordem deveria nascer

onde deveria executar

qual PnL deveria resultar
```

---

# 52. BacktestEngine Tests

Antes de o BacktestEngine ser considerado funcional, deverá existir uma suíte específica.

Exemplos obrigatórios são descritos abaixo.

---

# 53. Test: Sem Acesso ao Futuro

A Strategy não deve conseguir utilizar barras posteriores ao timestamp simulado.

Exemplo:

```text
Engine está em t=5

Strategy recebe:
t0..t5

Nunca:
t6..tN
```

Esse deverá ser um dos testes mais críticos do BacktestEngine.

---

# 54. Test: Signal Time

Se uma estratégia utiliza o fechamento da barra `t`:

```text
signal_time
```

não pode ocorrer antes do fechamento real dessa barra.

Exemplo M15:

```text
bar_start = 10:00

bar_close = 10:15

signal baseado no Close:
>= 10:15
```

---

# 55. Test: Order Não Pode Preceder Signal

Invariante futura:

```text
order_time >= signal_time
```

Uma ordem anterior ao sinal representa impossibilidade temporal.

---

# 56. Test: Fill Não Pode Preceder Order

Invariante:

```text
fill_time >= order_time
```

Nunca:

```text
fill
 ↓
order
```

---

# 57. Test: Entry Antes de Exit

Para um trade comum:

```text
exit_time >= entry_time
```

Uma saída anterior à entrada representa estado inválido.

---

# 58. Test: Execução na Próxima Barra

Se o modelo inicial definir:

```text
sinal no fechamento de t

entrada na abertura de t+1
```

deverá existir teste verificando exatamente essa regra.

Exemplo:

```text
Close t = 100

Open t+1 = 105
```

A entrada deve ocorrer a:

```text
105
```

e não:

```text
100
```

Isso detecta look-ahead de execução.

---

# 59. Test: Long PnL

Exemplo futuro:

```text
Long

entry = 100

exit = 110

quantity = 1

cost = 0
```

Resultado esperado:

```text
PnL = +10
```

---

# 60. Test: Short PnL

Exemplo:

```text
Short

entry = 100

exit = 90

quantity = 1
```

Resultado esperado:

```text
PnL = +10
```

Esse teste evita erros de sinal em posições vendidas.

---

# 61. Test: Losing Long

```text
Long

entry = 100

exit = 90
```

Resultado:

```text
PnL = -10
```

---

# 62. Test: Losing Short

```text
Short

entry = 100

exit = 110
```

Resultado:

```text
PnL = -10
```

---

# 63. Test: Spread em Compra

Quando o modelo utilizar Bid/Ask:

```text
Buy
```

deve respeitar o lado correto do mercado.

Conceitualmente:

```text
entrada LONG
→ Ask
```

dependendo do modelo definido.

Essa regra será formalizada em:

```text
10_BACKTEST_DESIGN.md
```

---

# 64. Test: Spread em Venda

Conceitualmente:

```text
entrada SHORT
→ Bid
```

e fechamento conforme lado oposto.

A implementação deverá ser testada explicitamente.

---

# 65. Test: Zero Cost

Com:

```text
spread = 0
commission = 0
slippage = 0
swap = 0
```

o resultado deve corresponder exatamente ao PnL matemático puro.

---

# 66. Test: Commission

Exemplo:

```text
Gross PnL = +10

Commission = 2
```

Resultado:

```text
Net PnL = +8
```

A comissão não pode ser esquecida ou aplicada duas vezes.

---

# 67. Test: Slippage

Se:

```text
requested = 100
slippage = +1
```

o preço efetivo deverá seguir a convenção definida pelo CostModel.

A direção do impacto deverá ser testada para:

```text
Long

Short
```

---

# 68. Test: Position State

Após entrada:

```text
position != None
```

Após fechamento:

```text
position == None
```

ou equivalente ao modelo adotado.

---

# 69. Test: Duplicate Entry

Se o sistema não permitir múltiplas posições simultâneas no baseline inicial, duas entradas seguidas deverão ser bloqueadas ou tratadas conforme regra explícita.

Não pode ocorrer comportamento implícito.

---

# 70. Test: Exit Sem Position

Uma ordem de saída sem posição deve produzir comportamento definido.

Possibilidades:

```text
ignore

reject

raise error
```

A escolha deverá ser documentada e testada.

---

# 71. Test: Equity

Exemplo:

```text
initial_cash = 1000

realized_pnl = +100
```

Após posição fechada:

```text
equity = 1100
```

quando não houver outras posições/custos.

---

# 72. Test: Unrealized PnL

Com posição aberta:

```text
cash
```

e:

```text
equity
```

podem diferir.

O Portfolio deverá ter testes específicos para essa distinção.

---

# 73. Test: Drawdown

Exemplo de curva:

```text
100
120
90
110
```

Peak:

```text
120
```

Trough:

```text
90
```

Drawdown:

```text
-25%
```

O cálculo deverá ser testado com casos simples.

---

# 74. Test: Win Rate

Exemplo:

```text
4 trades

3 wins
1 loss
```

Resultado:

```text
Win Rate = 75%
```

---

# 75. Test: Profit Factor

Exemplo:

```text
Gross Profit = 300

Gross Loss = 100
```

Resultado:

```text
Profit Factor = 3.0
```

Casos com:

```text
Gross Loss = 0
```

precisam de comportamento definido.

---

# 76. Test: Expectancy

Exemplo:

```text
Win Rate = 50%

Avg Win = +2R

Loss Rate = 50%

Avg Loss = -1R
```

Expectancy:

```text
+0.5R
```

---

# 77. Test: No Trades

Um backtest sem trades não deve quebrar.

Métricas como:

```text
Win Rate
Profit Factor
Sharpe
```

precisam ter comportamento definido quando não existem observações suficientes.

---

# 78. Test: One Trade

Também deve existir caso com apenas:

```text
1 trade
```

para evitar divisões por zero ou métricas inválidas.

---

# 79. Test: Empty Dataset

O BacktestEngine deverá rejeitar:

```text
dataset vazio
```

antes de iniciar.

---

# 80. Test: Unsorted Dataset

Dataset fora de ordem temporal deverá:

```text
ser rejeitado
```

ou explicitamente normalizado antes do backtest.

A política deverá ser definida.

Preferência arquitetural:

```text
fail fast
```

para dados validados.

---

# 81. Test: Duplicate Timestamp

O BacktestEngine não deve aceitar silenciosamente timestamps duplicados.

A camada de dados deveria impedir isso antes.

Um teste de defesa adicional é recomendável.

---

# 82. Test: Incomplete Bars

Por padrão:

```text
complete=False
```

não deve ser entregue à estratégia.

Deverá existir teste específico para essa regra.

---

# 83. Test: H1 Availability

Em multi-timeframe futuro:

```text
H1 10:00 → 11:00
```

não pode estar disponível às:

```text
10:30
```

como candle fechado.

Isso requer teste temporal específico.

---

# 84. Test: H4 Availability

Da mesma forma:

```text
H4 08:00 → 12:00
```

não pode ser disponibilizado como fechado às:

```text
10:00
```

---

# 85. Test: Risk Rejects Order

Exemplo futuro:

```text
Signal = LONG

Risk limit = exceeded
```

Resultado:

```text
Order não criada
```

---

# 86. Test: Risk Position Size

Se o risco máximo permitido resultar em:

```text
0.07 lot
```

e:

```text
volume_step = 0.01
```

o resultado deve respeitar a regra definida de arredondamento.

---

# 87. Test: Volume Min

Se o position sizing gerar:

```text
0.004
```

mas:

```text
volume_min = 0.01
```

o comportamento deverá ser explícito.

Exemplo:

```text
reject trade
```

ou outra política documentada.

---

# 88. Test: Volume Max

O tamanho nunca deverá exceder:

```text
volume_max
```

---

# 89. Test: Trading Disabled

Antes da execução Demo deverá existir um teste crítico:

```text
TRADING_ENABLED=false
```

implica:

```text
nenhuma ordem externa enviada
```

---

# 90. Test: Kill Switch

Futuramente:

```text
kill_switch = active
```

deve impedir novas ordens independentemente do sinal da Strategy.

---

# 91. Test: Daily Loss Limit

Quando:

```text
daily loss >= limit
```

o Risk Engine deverá bloquear novas operações.

---

# 92. Test: Max Drawdown Protection

Caso exista proteção operacional por drawdown:

```text
drawdown >= configured limit
```

novas operações devem ser bloqueadas conforme configuração.

---

# 93. Strategy Tests

Cada Strategy deverá possuir testes próprios.

O teste não deve verificar:

```text
se a estratégia ganha dinheiro
```

e sim:

```text
se implementa corretamente suas regras.
```

---

# 94. Exemplo EMA Strategy

Supondo regra:

```text
EMA fast cruza acima EMA slow
→ LONG
```

deverão existir séries artificiais onde:

```text
não existe cruzamento

existe cruzamento para cima

existe cruzamento para baixo
```

e a saída esperada deve ser conhecida.

---

# 95. Testar Warm-Up

Indicadores precisam de histórico mínimo.

Exemplo:

```text
EMA200
```

não deve gerar sinal significativo antes de possuir dados suficientes conforme a política definida.

---

# 96. NaN em Indicators

Features derivadas podem começar com:

```text
NaN
```

devido ao warm-up.

A Strategy não deve gerar sinal por acidente nesses períodos.

---

# 97. Parameter Validation

Parâmetros inválidos devem ser rejeitados.

Exemplo:

```text
fast_period >= slow_period
```

pode ou não ser permitido dependendo da Strategy.

Se não for, deve existir:

```text
ValueError
```

e teste.

---

# 98. CostModel Tests

Cada CostModel deverá ser testado isoladamente.

Exemplos:

```text
FixedSpreadModel

ConservativeSpreadModel

TickBidAskModel
```

---

# 99. Cost Stress Test

Se:

```text
base spread = 1
```

um multiplicador:

```text
2.0
```

deve resultar exatamente em:

```text
2
```

segundo a unidade utilizada.

---

# 100. Performance Tests

Performance Analytics deverá possuir testes para:

```text
trade count

gross profit

gross loss

net profit

win rate

payoff

profit factor

drawdown

returns
```

---

# 101. Sharpe Tests

Sharpe exige cuidado.

Deverão existir testes para:

```text
retornos constantes

zero variance

número insuficiente de períodos

frequência
```

O comportamento em situações matematicamente indefinidas deve ser explícito.

---

# 102. Floating Point

Valores monetários e preços podem apresentar pequenas diferenças de ponto flutuante.

Testes numéricos deverão preferir:

```python
pytest.approx(...)
```

quando apropriado.

Exemplo:

```python
assert pnl == pytest.approx(10.0)
```

---

# 103. Exact Equality

Não utilizar igualdade exata para floats quando a operação pode introduzir erro numérico.

Exemplo potencialmente frágil:

```python
assert result == 0.3
```

Melhor:

```python
assert result == pytest.approx(0.3)
```

---

# 104. Test Isolation

Um teste não deve depender do resultado de outro.

Cada teste deve preparar seu próprio estado ou utilizar fixtures controladas.

---

# 105. Test Order

A suíte deve funcionar independentemente da ordem em que os testes forem executados.

Não assumir:

```text
teste A roda antes do teste B
```

---

# 106. External State

Integration Tests devem reconhecer que dependem de estado externo.

Exemplos:

```text
MT5 aberto

mercado aberto/fechado

conta conectada

símbolo disponível
```

Quando apropriado, erros causados por ausência da infraestrutura deverão ser claramente diagnosticados.

---

# 107. Market Closed

Alguns testes de integração podem se comportar diferente com mercado fechado.

Particularmente:

```text
barra mais recente
tick atual
```

podem não avançar.

Os testes devem evitar assumir comportamento temporal impossível durante finais de semana.

---

# 108. Mocking Futuro

Para reduzir dependência do MT5, poderão ser utilizados:

```text
mocks

fake broker

stub data provider
```

Exemplo:

```text
FakeBroker
```

retorna:

```text
ticks conhecidos
candles conhecidos
```

permitindo testar MarketData sem terminal externo.

---

# 109. Broker Interface

Uma futura abstração de broker facilitará:

```text
MT5Client real
```

vs:

```text
FakeBroker
```

nos testes.

Isso aumentará isolamento e velocidade da suíte.

---

# 110. Test Performance

Unit Tests devem permanecer rápidos.

Integration Tests podem ser mais lentos.

A suíte atual executou em aproximadamente:

```text
0.84 segundos
```

no ambiente validado.

Esse valor é apenas uma observação do marco atual, não um requisito rígido.

---

# 111. Test Data Fixtures

Datasets artificiais futuros podem ficar em:

```text
tests/fixtures/
```

Exemplo:

```text
tests/fixtures/
├── simple_uptrend.parquet
├── simple_downtrend.parquet
├── gap_case.parquet
└── execution_case.csv
```

Alternativamente, pequenas séries podem ser criadas diretamente em código.

---

# 112. Preferência para Fixtures Pequenas

Para regras matemáticas simples, é preferível criar o DataFrame no próprio teste.

Isso torna o cenário visível e fácil de auditar.

---

# 113. Example Fixture

Exemplo:

```python
df = pd.DataFrame(
    {
        "time": [...],
        "open": [...],
        "high": [...],
        "low": [...],
        "close": [...],
    }
)
```

O resultado esperado pode ser calculado manualmente.

---

# 114. Property-Based Testing

Futuramente pode ser investigado:

```text
property-based testing
```

para invariantes como:

```text
High >= Low

equity accounting

position size bounds
```

Ferramentas como Hypothesis poderiam ser consideradas.

Status:

```text
NÃO IMPLEMENTADO
```

---

# 115. CI Futuro

A suíte deverá futuramente ser executada automaticamente em:

```text
GitHub Actions
```

ou outra plataforma de CI.

Fluxo:

```text
push / pull request
      ↓
install
      ↓
pytest
      ↓
pass / fail
```

Status:

```text
NÃO IMPLEMENTADO
```

---

# 116. Integration Tests em CI

Testes que exigem MetaTrader 5 podem não ser apropriados para runners Linux comuns.

Por isso a suíte futura poderá separar:

```text
unit suite
```

de:

```text
MT5 integration suite
```

---

# 117. Exemplo de CI Futuro

Conceitualmente:

```text
pytest -m "not integration"
```

em cada commit.

E Integration Tests:

```text
ambiente Windows dedicado
```

quando necessário.

---

# 118. Coverage

Cobertura de código poderá ser medida futuramente.

Exemplo:

```text
pytest-cov
```

Mas:

```text
coverage %
```

não será o principal indicador de qualidade.

---

# 119. Prioridade de Coverage

Maior prioridade:

```text
core accounting

time handling

look-ahead prevention

risk

execution

costs
```

Menor prioridade relativa:

```text
scripts de impressão

diagnóstico simples
```

---

# 120. Naming

Os testes devem possuir nomes que expressem claramente a regra.

Exemplo bom:

```text
test_closed_bars_do_not_include_current_bar
```

Melhor que:

```text
test_case_9
```

---

# 121. Arrange / Act / Assert

Quando útil, testes devem seguir mentalmente:

```text
Arrange

Act

Assert
```

Exemplo:

```text
Arrange:
criar ordem

Act:
executar fill

Assert:
posição e cash corretos
```

---

# 122. One Behavior per Test

Preferencialmente cada teste deve proteger uma regra principal.

Isso facilita identificar a causa da falha.

---

# 123. Fail Messages

Quando uma asserção complexa precisar de contexto, pode ser utilizado:

```python
assert condition, "mensagem"
```

Mas nomes de testes claros devem continuar sendo prioridade.

---

# 124. Regressões Quantitativas

Quando uma estratégia for estabilizada, poderão existir snapshots de resultados.

Exemplo:

```text
Strategy v1
Dataset fixture v1

Trades = 12

Net PnL = 4.5R
```

Alterações intencionais deverão atualizar o snapshot conscientemente.

---

# 125. Cuidado com Regression Tests de Mercado Real

Não é ideal fixar resultados utilizando um dataset externo que pode ser atualizado silenciosamente.

Regression Tests devem preferir:

```text
fixture imutável
```

ou dataset versionado/hash conhecido.

---

# 126. Dataset Hash Futuro

Quando implementado:

```text
SHA256
```

poderá garantir que o fixture utilizado no teste não mudou.

---

# 127. Testes e Documentação

Ao adicionar um componente crítico:

```text
implementar
    ↓
testar
    ↓
documentar
```

A documentação e a suíte devem evoluir juntas.

---

# 128. Bug Fix Rule

Quando um bug importante for encontrado:

```text
1. reproduzir o bug em teste

2. confirmar que teste falha

3. corrigir o código

4. confirmar que teste passa
```

Isso transforma o bug corrigido em proteção permanente.

---

# 129. Exemplo Histórico

Um exemplo conceitual já ocorrido no desenvolvimento foi a preocupação com:

```text
candle corrente
```

Em vez de apenas confiar em:

```text
start_pos=1
```

foi criado um teste específico.

Essa é a abordagem desejada para futuros bugs críticos.

---

# 130. Backtest Minimum Test Gate

O BacktestEngine não deverá ser considerado concluído apenas porque produz uma equity curve.

Antes disso, deverá passar pelo menos por testes de:

```text
time ordering

no look-ahead

signal time

order time

fill time

long PnL

short PnL

cost application

position state

cash/equity

empty dataset

incomplete candles
```

---

# 131. Risk Minimum Test Gate

Antes de Demo:

```text
position size

volume step

volume min/max

risk per trade

max loss

trading disabled

kill switch
```

deverão possuir testes automatizados.

---

# 132. Execution Minimum Test Gate

Antes de qualquer `order_send()`:

```text
demo account validation

symbol validation

trade mode validation

lot validation

duplicate order protection

TRADING_ENABLED

kill switch

error handling
```

deverão ser testados.

---

# 133. Live Execution

Nenhuma suite relacionada à execução real existe atualmente.

Status:

```text
NOT IMPLEMENTED
```

---

# 134. Test Philosophy Summary

A filosofia pode ser resumida em:

```text
Testar comportamento,
não apenas código.

Testar invariantes,
não apenas casos felizes.

Testar tempo,
porque tempo é parte da lógica.

Testar custos,
porque custos alteram resultados.

Testar risco,
antes de permitir execução.

Transformar bugs
em regression tests.
```

---

# 135. Estado Atual

Testing no marco:

```text
FOREX v0.1
```

Status:

```text
pytest setup                  COMPLETE

MarketData tests              COMPLETE

HistoricalData tests          COMPLETE

TimeframeBuilder tests        COMPLETE

Integration marker            COMPLETE

Current suite                 25 / 25 PASS

BacktestEngine tests          NOT IMPLEMENTED

Strategy tests                NOT IMPLEMENTED

Risk tests                    NOT IMPLEMENTED

CostModel tests               NOT IMPLEMENTED

Execution tests               NOT IMPLEMENTED

CI                            NOT IMPLEMENTED

Coverage                      NOT IMPLEMENTED
```

---

# 136. Test Suite Atual

Resumo:

```text
MarketData
9 tests

HistoricalData
8 tests

TimeframeBuilder
8 tests

Total
25 tests

Result
25 passed
```

---

# 137. Quality Gate Atual

Antes de avançar para o BacktestEngine, o estado esperado é:

```text
pytest -v

25 passed
```

Qualquer regressão nas camadas já concluídas deve ser investigada antes de construir novas funcionalidades em cima delas.

---

# 138. Próximo Documento

O próximo documento é:

```text
docs/09_DATA_TRANSFORMATION.md
```

Ele documentará em detalhe:

```text
M15 → H1

M15 → H4

resample

OHLC aggregation

tick_volume aggregation

source_bar_count

expected_bar_count

complete

alinhamento UTC

candles incompletos

reprodutibilidade
```
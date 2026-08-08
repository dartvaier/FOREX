# Data Transformation

## 1. Objetivo

Este documento descreve a camada de transformação temporal da plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

O objetivo dessa camada é construir timeframes superiores a partir de uma fonte intraday base, preservando:

- integridade temporal;
- OHLC correto;
- timezone UTC;
- rastreabilidade;
- quantidade de candles fonte;
- identificação de candles incompletos;
- reprodutibilidade.

No estado atual do projeto, o timeframe base é:

```text
M15
```

e os timeframes derivados são:

```text
H1
H4
```

---

# 2. Componente Principal

Arquivo:

```text
data/timeframe_builder.py
```

Classe:

```text
TimeframeBuilder
```

Responsabilidade:

> Construir timeframes superiores de maneira determinística a partir de candles M15 previamente validados.

---

# 3. Fluxo Atual

A pipeline é:

```text
EURUSD M15 Raw
      ↓
TimeframeBuilder
      ↓
 ┌────┴────┐
 ↓         ↓
H1        H4
```

Arquivos gerados:

```text
data/processed/EURUSD/H1.parquet
data/processed/EURUSD/H4.parquet
```

---

# 4. Fonte de Verdade

No estado atual do projeto:

```text
M15 Raw
```

é a fonte primária intraday.

Isso significa que H1 e H4 não são considerados fontes independentes.

A linhagem é:

```text
MetaQuotes-Demo
      ↓
EURUSD M15
      ↓
TimeframeBuilder
      ├── H1
      └── H4
```

---

# 5. Dataset M15 de Origem

Arquivo:

```text
data/raw/EURUSD/M15.parquet
```

Cobertura:

```text
2015-01-02 09:00 UTC
→
2026-08-07 23:45 UTC
```

Quantidade:

```text
288223 candles
```

Schema principal:

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

# 6. Colunas Utilizadas na Transformação

Para construir H1 e H4 são utilizadas:

```text
time
open
high
low
close
tick_volume
```

Os campos:

```text
spread
real_volume
```

não são agregados atualmente.

---

# 7. Motivo para Não Agregar Spread

O campo histórico:

```text
spread
```

apresentou inconsistência ao longo dos anos.

Além disso, transformar spread M15 em H1/H4 exige definir explicitamente uma semântica.

Possibilidades seriam:

```text
média
máximo
mediana
último valor
```

Nenhuma dessas opções representa automaticamente custo real de execução.

Por isso:

```text
spread
```

não faz parte do dataset processado atual.

---

# 8. Motivo para Não Agregar Real Volume

O campo:

```text
real_volume
```

apresentou quebra estrutural importante no histórico.

Foi observado:

```text
2015 parcialmente preenchido
2016 praticamente 100%
2017 parcialmente preenchido
2018+ zero
```

Por isso ele não é utilizado como feature e também não é agregado nos timeframes processados.

---

# 9. Tick Volume

O campo:

```text
tick_volume
```

é agregado.

Para um candle superior:

```text
tick_volume
```

é igual à soma do tick volume dos candles M15 que pertencem ao intervalo.

Exemplo:

```text
M15 10:00 → 100
M15 10:15 → 120
M15 10:30 → 140
M15 10:45 → 110
```

H1:

```text
tick_volume = 470
```

---

# 10. Timezone

Todo o processo ocorre em:

```text
UTC
```

O dataset de entrada deve ser:

```text
timezone-aware
UTC
```

O dataset de saída também deve permanecer:

```text
timezone-aware
UTC
```

---

# 11. Validação da Fonte

Antes do resample, o `TimeframeBuilder` valida que o DataFrame contém:

```text
time
open
high
low
close
tick_volume
```

Se uma dessas colunas estiver ausente, a transformação deve falhar.

---

# 12. Dataset Vazio

Um DataFrame vazio não é aceito.

O comportamento esperado é:

```text
raise ValueError
```

em vez de produzir um arquivo processado vazio silenciosamente.

---

# 13. Timezone da Fonte

O campo:

```text
time
```

deve possuir timezone.

Se:

```text
timezone == None
```

o dataset é rejeitado.

---

# 14. UTC Obrigatório

Além de possuir timezone, o dataset precisa estar em:

```text
UTC
```

A transformação não tenta adivinhar o timezone de uma série recebida.

Isso evita introduzir deslocamentos silenciosos.

---

# 15. Ordenação

Antes da transformação:

```text
time
```

é ordenado em ordem crescente.

Fluxo:

```text
source
  ↓
sort_values("time")
  ↓
set_index("time")
```

---

# 16. Resample

A implementação utiliza:

```text
pandas.DataFrame.resample()
```

para agrupar os candles de acordo com a fronteira temporal desejada.

Configuração conceitual:

```python
source.resample(
    rule,
    label="left",
    closed="left",
    origin="epoch",
)
```

---

# 17. label="left"

Essa configuração determina que o timestamp do candle resultante representa:

```text
início do intervalo
```

Exemplo H1:

```text
10:00
```

representa:

```text
10:00 → 11:00
```

---

# 18. closed="left"

A fronteira é tratada como:

```text
[início, fim)
```

Exemplo:

```text
10:00 pertence ao grupo 10:00

10:59:59 pertence ao grupo 10:00

11:00 pertence ao grupo 11:00
```

---

# 19. origin="epoch"

Essa configuração ajuda a manter alinhamento determinístico das fronteiras de tempo.

Para H4, por exemplo, os grupos ficam alinhados em UTC como:

```text
00:00
04:00
08:00
12:00
16:00
20:00
```

---

# 20. Agregação OHLC

A transformação utiliza as regras clássicas:

```text
Open  = primeiro Open
High  = maior High
Low   = menor Low
Close = último Close
```

---

# 21. Exemplo H1

Candles M15:

```text
10:00
Open  = 1.1000
High  = 1.1020
Low   = 1.0990
Close = 1.1010

10:15
Open  = 1.1010
High  = 1.1030
Low   = 1.1000
Close = 1.1020

10:30
Open  = 1.1020
High  = 1.1040
Low   = 1.1010
Close = 1.1030

10:45
Open  = 1.1030
High  = 1.1050
Low   = 1.1020
Close = 1.1040
```

Resultado H1:

```text
Time  = 10:00

Open  = 1.1000

High  = 1.1050

Low   = 1.0990

Close = 1.1040
```

---

# 22. H1

Configuração:

```text
rule = 1h
```

Número esperado de candles M15:

```text
4
```

---

# 23. H4

Configuração:

```text
rule = 4h
```

Número esperado de candles M15:

```text
16
```

---

# 24. source_bar_count

Além de OHLC e tick volume, cada candle processado registra:

```text
source_bar_count
```

Esse campo informa quantos M15 realmente estavam presentes no intervalo.

---

# 25. expected_bar_count

Também é registrado:

```text
expected_bar_count
```

Para H1:

```text
4
```

Para H4:

```text
16
```

---

# 26. complete

A flag:

```text
complete
```

é calculada como:

```text
source_bar_count == expected_bar_count
```

---

# 27. Exemplo H1 Completo

```text
source_bar_count   = 4
expected_bar_count = 4
complete           = True
```

---

# 28. Exemplo H1 Incompleto

```text
source_bar_count   = 3
expected_bar_count = 4
complete           = False
```

---

# 29. Exemplo H4 Completo

```text
source_bar_count   = 16
expected_bar_count = 16
complete           = True
```

---

# 30. Exemplo H4 Incompleto

```text
source_bar_count   = 15
expected_bar_count = 16
complete           = False
```

---

# 31. Por que Não Excluir Incompletos

Candles incompletos são preservados porque representam informação relevante sobre o dataset.

Possíveis causas:

```text
gap
feriado
problema de feed
início parcial do histórico
fim parcial do histórico
```

Excluir essas linhas durante o processamento esconderia parte da qualidade da fonte.

---

# 32. Data Quality vs Strategy Data

A arquitetura separa:

```text
processed dataset
```

de:

```text
strategy dataset
```

Processed:

```text
completos + incompletos
```

Strategy:

```text
somente completos
```

por padrão.

---

# 33. Regra para o Backtester

O futuro BacktestEngine deverá utilizar, por padrão:

```python
df[df["complete"]]
```

ou lógica equivalente.

Candles:

```text
complete=False
```

não devem gerar sinais normalmente.

---

# 34. Razão

Caso um H4 seja construído com apenas:

```text
8 de 16 M15
```

ele ainda possuiria:

```text
Open
High
Low
Close
```

matematicamente válidos.

Mas não representa um período H4 completo.

Sem a flag:

```text
complete
```

esse problema poderia passar despercebido.

---

# 35. Intervalos Vazios

O resample pode produzir intervalos sem nenhum candle fonte.

Exemplo:

```text
fim de semana
```

Esses grupos possuem:

```text
source_bar_count = 0
```

e são removidos.

---

# 36. Motivo para Remover Grupos Vazios

Um intervalo sem qualquer candle não representa um candle de mercado real.

Criar:

```text
H1 vazio
```

ou:

```text
H4 vazio
```

não agrega informação útil.

Por isso:

```text
source_bar_count > 0
```

é exigido para permanecer no dataset processado.

---

# 37. Diferença entre Vazio e Incompleto

## Vazio

```text
source_bar_count = 0
```

Resultado:

```text
removido
```

## Incompleto

```text
0 < source_bar_count < expected_bar_count
```

Resultado:

```text
preservado
complete=False
```

---

# 38. Primeiro H4

O primeiro M15 disponível no dataset é:

```text
2015-01-02 09:00 UTC
```

A fronteira H4 correspondente começa em:

```text
08:00 UTC
```

O intervalo seria:

```text
08:00 → 12:00
```

Porém não existem M15 de:

```text
08:00
08:15
08:30
08:45
```

na fonte atual.

Logo o primeiro H4 é:

```text
incompleto
```

---

# 39. Isso é Esperado

O timestamp:

```text
2015-01-02 08:00 UTC
```

no primeiro H4 não significa que o M15 possua dados desde 08:00.

Significa que o candle pertence ao bucket H4 iniciado às 08:00.

A flag:

```text
complete=False
```

fornece a informação correta sobre sua qualidade.

---

# 40. Resultado H1 Atual

Arquivo:

```text
data/processed/EURUSD/H1.parquet
```

Resultado:

```text
Candles totais:
72080

Completos:
72018

Incompletos:
62
```

---

# 41. Período H1

Primeiro:

```text
2015-01-02 09:00 UTC
```

Último:

```text
2026-08-07 23:00 UTC
```

---

# 42. Taxa de Completude H1

Com:

```text
72018 completos
```

de:

```text
72080 totais
```

a taxa de candles completos é aproximadamente:

```text
99.914%
```

---

# 43. Taxa de Incompletude H1

Candles incompletos:

```text
62
```

Proporção aproximada:

```text
0.086%
```

---

# 44. Resultado H4 Atual

Arquivo:

```text
data/processed/EURUSD/H4.parquet
```

Resultado:

```text
Candles totais:
18046

Completos:
17929

Incompletos:
117
```

---

# 45. Período H4

Primeiro:

```text
2015-01-02 08:00 UTC
```

Último:

```text
2026-08-07 20:00 UTC
```

---

# 46. Taxa de Completude H4

Com:

```text
17929 completos
```

de:

```text
18046 totais
```

a taxa de candles completos é aproximadamente:

```text
99.352%
```

---

# 47. Taxa de Incompletude H4

Candles incompletos:

```text
117
```

Proporção aproximada:

```text
0.648%
```

---

# 48. Por que H4 Tem Mais Incompletos

Cada H4 depende de:

```text
16 M15
```

enquanto H1 depende de:

```text
4 M15
```

Assim, um único M15 ausente pode invalidar:

```text
um H1
```

e também:

```text
um H4
```

Além disso, fronteiras de feriados e períodos parciais têm maior chance de produzir H4 incompleto.

---

# 49. Schema Processado

H1 e H4 possuem:

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

---

# 50. time

Representa:

```text
início do bucket
```

e permanece em:

```text
UTC
```

---

# 51. open

Representa:

```text
primeiro Open disponível
```

dentro do grupo.

---

# 52. high

Representa:

```text
máximo High
```

dos candles fonte.

---

# 53. low

Representa:

```text
mínimo Low
```

dos candles fonte.

---

# 54. close

Representa:

```text
último Close disponível
```

dentro do grupo.

Em um candle incompleto, esse valor é o último Close observado no subconjunto disponível.

Por isso não deve ser tratado como fechamento real do período completo.

---

# 55. tick_volume

Representa:

```text
soma do tick_volume
```

dos M15 disponíveis.

Em candle incompleto, também é uma soma parcial.

---

# 56. source_bar_count

Tipo conceitual:

```text
integer
```

Representa a quantidade real de M15 utilizados.

---

# 57. expected_bar_count

Tipo conceitual:

```text
integer
```

Representa a quantidade exigida para completude.

---

# 58. complete

Tipo conceitual:

```text
boolean
```

Valores:

```text
True
False
```

---

# 59. Integridade OHLC dos Derivados

Após o resample são verificadas:

```text
High >= Low

High >= Open

High >= Close

Low <= Open

Low <= Close
```

Se alguma dessas regras falhar, o dataset é rejeitado.

---

# 60. Timestamps Duplicados

O dataset derivado não pode possuir timestamps duplicados.

Invariante:

```text
duplicated(time) == 0
```

---

# 61. Ordem Cronológica

O resultado deve permanecer:

```text
monotonic increasing
```

em relação a:

```text
time
```

---

# 62. H1 Alignment

Todos os H1 devem possuir:

```text
minute == 0
```

Exemplos:

```text
09:00
10:00
11:00
12:00
```

---

# 63. H4 Alignment

Todos os H4 devem possuir:

```text
minute == 0
```

e:

```text
hour % 4 == 0
```

Fronteiras:

```text
00:00
04:00
08:00
12:00
16:00
20:00
```

---

# 64. H4 em UTC

O alinhamento atual é explicitamente:

```text
UTC
```

Não:

```text
broker local time
London
New York
```

---

# 65. Implicação para Estratégias

Uma Strategy H4 futura deve saber que:

```text
H4 08:00
```

representa:

```text
08:00 → 12:00 UTC
```

---

# 66. Disponibilidade Temporal

Embora o timestamp seja:

```text
08:00
```

o candle H4 completo só se torna totalmente conhecido ao final do intervalo:

```text
12:00
```

Esse conceito será tratado pelo BacktestEngine.

---

# 67. Look-Ahead Multi-Timeframe

Exemplo incorreto:

```text
10:30 UTC

Strategy consulta H4 08:00
como se estivesse fechado
```

Mas:

```text
H4 08:00
```

só fecha em:

```text
12:00
```

Isso seria look-ahead.

---

# 68. Regra Futura

O BacktestEngine deverá diferenciar:

```text
bar timestamp
```

de:

```text
bar availability time
```

---

# 69. H1 Availability

Para:

```text
H1 10:00
```

o intervalo termina em:

```text
11:00
```

O candle completo deve ser considerado disponível somente após esse ponto.

---

# 70. H4 Availability

Para:

```text
H4 08:00
```

o intervalo termina em:

```text
12:00
```

O candle completo não pode ser utilizado antes.

---

# 71. Resample Não Resolve Disponibilidade

O pandas pode construir todo o dataset de uma vez.

Isso não significa que, em um backtest, todas as linhas estejam disponíveis desde o início.

O BacktestEngine deverá simular a disponibilidade cronológica.

---

# 72. Transformação Offline

O `TimeframeBuilder` é uma transformação:

```text
offline
```

Ele conhece todo o histórico para gerar os arquivos.

Isso é aceitável porque ele não gera sinais.

---

# 73. Consumo Online Simulado

No backtest:

```text
H1/H4 pré-computados
```

podem ser utilizados desde que o Engine imponha:

```text
availability time
```

corretamente.

---

# 74. Resample e Gaps

Exemplo:

```text
10:00 ✅
10:15 ✅
10:30 ❌
10:45 ✅
```

O pandas ainda pode gerar:

```text
H1 10:00
```

com:

```text
Open
High
Low
Close
```

válidos.

Por isso só validar OHLC não é suficiente.

---

# 75. Necessidade do source_bar_count

Sem:

```text
source_bar_count
```

não seria possível distinguir:

```text
H1 completo
```

de:

```text
H1 construído com 3 candles
```

apenas observando OHLC.

---

# 76. complete como Quality Flag

A coluna:

```text
complete
```

é uma quality flag.

Ela não é:

```text
feature de estratégia
```

e não representa comportamento de mercado.

Ela representa qualidade estrutural do dado derivado.

---

# 77. Strategy não Deve Usar complete Como Alpha

Exemplo inadequado:

```text
complete=False
→ SHORT
```

Essa coluna não deve ser interpretada como sinal de mercado.

---

# 78. Warm-Up de Indicadores

Depois que H1/H4 são construídos, indicadores futuros podem exigir warm-up.

Exemplo:

```text
EMA200 H1
```

necessita de histórico anterior suficiente.

Essa responsabilidade pertence à camada futura de features/strategy, não ao TimeframeBuilder.

---

# 79. NaN de Features

O `TimeframeBuilder` não adiciona:

```text
EMA
RSI
ATR
ADX
```

Portanto não cria NaNs relacionados a warm-up de indicadores.

Essa separação é intencional.

---

# 80. Transformação Determinística

Com:

```text
mesmo M15
mesma configuração
mesmo código
```

deve resultar:

```text
mesmo H1
mesmo H4
```

Essa propriedade é importante para reprodutibilidade.

---

# 81. Script de Construção

Arquivo:

```text
build_timeframes.py
```

Responsabilidade:

```text
carregar M15
      ↓
construir H1
      ↓
salvar H1
      ↓
construir H4
      ↓
salvar H4
```

---

# 82. Execução

Comando:

```powershell
python build_timeframes.py
```

---

# 83. Saída Atual H1

Exemplo do resultado validado:

```text
Construindo H1...

Candles: 72080

Completos: 72018

Incompletos: 62

Primeiro:
2015-01-02 09:00:00+00:00

Último:
2026-08-07 23:00:00+00:00
```

---

# 84. Saída Atual H4

```text
Construindo H4...

Candles: 18046

Completos: 17929

Incompletos: 117

Primeiro:
2015-01-02 08:00:00+00:00

Último:
2026-08-07 20:00:00+00:00
```

---

# 85. Persistência

Arquivos:

```text
data/processed/EURUSD/H1.parquet

data/processed/EURUSD/H4.parquet
```

Utilizam:

```text
Parquet
```

---

# 86. Processed é Regenerável

Caso os arquivos H1/H4 sejam apagados:

```text
M15 raw
+
TimeframeBuilder
```

permitem recriá-los.

Isso significa que o raw deve possuir maior prioridade de preservação.

---

# 87. Atualização Futura

Quando o M15 receber novos candles:

```text
M15 updated
      ↓
build_timeframes.py
      ↓
H1/H4 regenerated
```

Essa é a abordagem atual.

---

# 88. Atualização Incremental

No futuro poderá existir transformação incremental.

Exemplo:

```text
último H1 conhecido
      ↓
novos M15
      ↓
recalcular somente buckets afetados
```

Status:

```text
NÃO IMPLEMENTADO
```

---

# 89. Cuidado com Bucket Parcial Final

Ao atualizar um dataset enquanto o mercado está ativo, o último bucket H1/H4 pode estar parcial.

A lógica:

```text
source_bar_count
expected_bar_count
complete
```

continua necessária.

---

# 90. Historical vs Live Transformation

Atualmente o resample é aplicado ao histórico.

No futuro, o sistema em Demo poderá precisar manter:

```text
H1/H4 incrementalmente
```

a partir dos M15 recebidos.

Essa lógica deverá preservar as mesmas fronteiras.

---

# 91. Mesma Semântica em Backtest e Demo

É desejável que:

```text
Backtest H1/H4
```

e:

```text
Demo H1/H4
```

usem as mesmas regras de construção.

Assim reduzimos divergências entre ambientes.

---

# 92. Testes Automatizados

Arquivo:

```text
tests/test_timeframe_builder.py
```

A camada possui atualmente oito testes.

---

# 93. Teste de Criação H1

```text
test_h1_is_created
```

Valida que a transformação produz dados.

---

# 94. Teste de Criação H4

```text
test_h4_is_created
```

Valida que H4 é produzido corretamente como estrutura não vazia.

---

# 95. Teste H1 Completo

```text
test_h1_complete_bars_have_four_m15
```

Para todos:

```text
complete=True
```

é exigido:

```text
source_bar_count == 4
```

---

# 96. Teste H4 Completo

```text
test_h4_complete_bars_have_sixteen_m15
```

Exige:

```text
source_bar_count == 16
```

para candles H4 completos.

---

# 97. Teste de Alinhamento H1

```text
test_h1_alignment
```

Exige:

```text
minute == 0
```

---

# 98. Teste de Alinhamento H4

```text
test_h4_alignment
```

Exige:

```text
minute == 0

hour % 4 == 0
```

---

# 99. Teste UTC

```text
test_generated_timeframes_are_utc
```

garante que H1/H4 preservem:

```text
UTC
```

---

# 100. Teste OHLC

```text
test_generated_ohlc_integrity
```

garante a integridade dos candles derivados.

---

# 101. Estado Atual dos Testes

Toda a suíte do projeto está em:

```text
25 passed
```

Os testes do `TimeframeBuilder` representam:

```text
8
```

desses testes.

---

# 102. Testes Futuros Recomendados

A camada poderá futuramente ganhar testes adicionais para:

```text
grupo completamente vazio

primeiro bucket parcial

último bucket parcial

gap exato de um M15

tick_volume agregado

Open/Close conhecido manualmente

resultado determinístico
```

---

# 103. Fixture Artificial H1

Exemplo futuro:

Criar exatamente quatro M15 conhecidos:

```text
10:00
10:15
10:30
10:45
```

e verificar manualmente:

```text
Open
High
Low
Close
tick_volume
```

do H1 produzido.

---

# 104. Fixture Artificial H4

Criar:

```text
16 candles M15
```

e validar o resultado H4 esperado.

Isso reduz dependência do dataset real nos unit tests.

---

# 105. Teste de Incompletude

Também será útil criar explicitamente:

```text
15 M15
```

em um bucket H4.

Resultado esperado:

```text
source_bar_count = 15

expected_bar_count = 16

complete = False
```

---

# 106. Teste de Grupo Vazio

Criar dois blocos separados por várias horas e verificar que:

```text
bucket com zero candles
```

não é persistido.

---

# 107. Resample e Finais de Semana

O sistema não cria candles artificiais durante:

```text
sábado
domingo
```

Buckets vazios são simplesmente ausentes.

---

# 108. D1

Daily ainda não é construído pelo `TimeframeBuilder`.

Isso é uma decisão deliberada.

---

# 109. Motivo do D1 Separado

Um candle diário depende da definição de:

```text
fronteira do dia de trading
```

Possíveis convenções:

```text
00:00 UTC

broker midnight

New York close

outra sessão
```

Essas convenções produzem candles diferentes.

---

# 110. Não Assumir Daily UTC

O projeto não deve criar D1 automaticamente com:

```text
00:00 UTC
```

sem antes definir a convenção desejada.

---

# 111. Multi-Timeframe Strategy

A transformação H1/H4 prepara o projeto para estratégias como:

```text
H4
→ regime

H1
→ signal

M15
→ execution
```

Mas a sincronização temporal ainda pertencerá ao BacktestEngine.

---

# 112. Sincronização Multi-Timeframe

O BacktestEngine deverá responder:

```text
qual é o último H1 fechado neste instante?

qual é o último H4 fechado neste instante?
```

e nunca simplesmente:

```text
qual linha possui mesmo índice?
```

---

# 113. Índice de DataFrame Não Representa Tempo Disponível

Exemplo:

```text
M15 row 100
H1 row 100
```

não significa que as duas linhas representem o mesmo instante.

Sincronização deverá ser por:

```text
timestamp
+
availability
```

---

# 114. Data Transformation != Feature Engineering

Essa distinção é importante.

## Data Transformation

```text
M15 → H1
M15 → H4
```

estrutura temporal.

## Feature Engineering

```text
EMA
ATR
RSI
returns
volatility
```

informações derivadas para estratégia.

Feature Engineering ainda não foi implementada como camada própria.

---

# 115. Data Transformation != Strategy

O `TimeframeBuilder` nunca deve gerar:

```text
LONG
SHORT
BUY
SELL
```

Ele apenas transforma dados.

---

# 116. Data Transformation != Backtest

O `TimeframeBuilder` conhece todo o histórico porque sua função é preparar o dataset.

O BacktestEngine será responsável por restringir a visibilidade cronológica durante a simulação.

---

# 117. Data Transformation Invariants

As invariantes atuais são:

```text
source não vazio

source UTC

colunas obrigatórias presentes

resultado ordenado

timestamps únicos

resultado UTC

OHLC válido

H1 alinhado

H4 alinhado

H1 completo = 4 M15

H4 completo = 16 M15

bucket vazio removido

bucket parcial preservado e marcado
```

---

# 118. Data Quality Inheritance

Um candle derivado não pode possuir qualidade superior à sua fonte.

Se o M15 contém gap:

```text
H1/H4
```

afetado deve refletir essa limitação através de:

```text
complete=False
```

---

# 119. Limitação Atual

A flag:

```text
complete
```

detecta quantidade de candles fonte.

Ela não detecta necessariamente todos os tipos de problemas possíveis.

Exemplo:

```text
4 M15 presentes,
mas um deles contém dado economicamente suspeito.
```

Nesse caso:

```text
complete=True
```

ainda pode ocorrer.

Portanto `complete` representa:

```text
completude temporal estrutural
```

e não qualidade absoluta.

---

# 120. Outra Limitação

Um H1 pode conter quatro M15 com:

```text
15 minutos de espaçamento correto
```

mas o feed ainda pode ter:

```text
spread inconsistente
```

ou outras limitações.

A flag `complete` não pretende resolver essas questões.

---

# 121. Futuro Data Quality Flag

Pode ser útil futuramente possuir múltiplas flags:

```text
complete

has_gap

source_valid

quality_status
```

Status:

```text
NÃO IMPLEMENTADO
```

---

# 122. Futuro Dataset Manifest

Também poderá existir metadata específica:

```text
EURUSD_H1.json
EURUSD_H4.json
```

com:

```text
source dataset
builder version
bars
complete bars
incomplete bars
first
last
```

Status:

```text
PLANEJADO
```

---

# 123. Reprodutibilidade

Um experimento futuro deverá ser capaz de registrar:

```text
M15 dataset version
+
TimeframeBuilder version
```

para saber exatamente como H1/H4 foram construídos.

---

# 124. Hash Futuro

Uma possibilidade futura:

```text
M15 SHA256

H1 SHA256

H4 SHA256
```

Isso garantiria integridade dos arquivos usados em experimentos.

---

# 125. Política Atual

No momento:

```text
M15 é preservado

H1/H4 são regeneráveis

transformação é determinística

25 testes estão verdes
```

Isso é suficiente para avançar para o design do BacktestEngine.

---

# 126. Estado Atual

Data Transformation no marco:

```text
FOREX v0.1
```

Status:

```text
M15 Source                  COMPLETE

H1 Builder                  COMPLETE

H4 Builder                  COMPLETE

OHLC Aggregation            COMPLETE

Tick Volume Aggregation     COMPLETE

UTC Alignment               COMPLETE

Source Bar Count            COMPLETE

Expected Bar Count          COMPLETE

Complete Flag               COMPLETE

Incomplete Preservation     COMPLETE

Parquet Persistence         COMPLETE

Automated Tests             COMPLETE

D1 Transformation           NOT IMPLEMENTED

Incremental Resample        NOT IMPLEMENTED

Multi-Timeframe Runtime     NOT IMPLEMENTED

Feature Engineering Layer   NOT IMPLEMENTED
```

---

# 127. Resumo

Pipeline atual:

```text
288223 M15
      ↓
TimeframeBuilder
      ↓
 ┌──────────────┬──────────────┐
 ↓              ↓
H1             H4

72080          18046
total          total

72018          17929
complete       complete

62             117
incomplete     incomplete
```

Arquitetura:

```text
Raw
 ↓
Validated Transformation
 ↓
Processed
 ↓
Future Backtest
```

---

# 128. Regra Principal

A regra principal da transformação é:

> Um candle agregado só é considerado completo quando todas as barras fonte esperadas para aquele intervalo estão presentes.

Candles parciais podem ser preservados para auditoria, mas não devem ser tratados silenciosamente como períodos completos.

---

# 129. Próximo Documento

O próximo documento é:

```text
docs/10_BACKTEST_DESIGN.md
```

Esse documento será elaborado antes da implementação do BacktestEngine.

Ele deverá definir formalmente:

```text
relógio da simulação

ordem dos eventos

signal time

order time

fill time

preço de entrada

preço de saída

Long / Short

Bid / Ask

spread

slippage

commission

swap

posição

cash

equity

PnL

stop loss

take profit

candles incompletos

multi-timeframe

look-ahead prevention

CostModel

Risk integration
```

Nenhuma dessas regras deverá ficar implícita na implementação.
# Data Quality

## 1. Objetivo

Este documento registra a análise de qualidade dos dados históricos utilizados pela plataforma:

```text
FOREX Algorithmic Trading Research Platform
```

O objetivo é documentar:

- integridade estrutural;
- cobertura temporal;
- duplicados;
- valores ausentes;
- integridade OHLC;
- gaps;
- distribuição anual;
- spread histórico;
- tick volume;
- real volume;
- limitações conhecidas;
- critérios atuais de utilização do dataset.

O princípio central é:

> Um backtest só pode ser interpretado corretamente quando as limitações do dataset utilizado são conhecidas antes da análise da estratégia.

---

# 2. Dataset Auditado

Dataset principal:

```text
Symbol:     EURUSD
Timeframe:  M15
Source:     MetaQuotes-Demo
Timezone:   UTC
Format:     Parquet
```

Arquivo:

```text
data/raw/EURUSD/M15.parquet
```

---

# 3. Cobertura Temporal

Primeiro candle:

```text
2015-01-02 09:00:00 UTC
```

Último candle:

```text
2026-08-07 23:45:00 UTC
```

Total:

```text
288223 candles
```

---

# 4. Resultado Geral da Auditoria

Resumo:

```text
Candles:          288223

Duplicados:       0

Null values:      0

OHLC inválidos:   0

Gaps totais:      659

Weekend gaps:     605

Intraweek gaps:    54
```

A conclusão atual é:

```text
Dataset adequado para
desenvolvimento e pesquisa,
com limitações conhecidas.
```

Essa classificação não significa que o dataset seja uma representação perfeita de execução real.

---

# 5. Script de Auditoria

A análise é realizada através de:

```text
analyze_history.py
```

O script verifica:

```text
cobertura temporal
duplicados
nulls
OHLC
candles por ano
gaps
spread
tick volume
real volume
```

---

# 6. Integridade dos Timestamps

O dataset utiliza:

```text
UTC
```

e os timestamps são:

```text
timezone-aware
```

O campo:

```text
time
```

representa o início do candle.

Exemplo:

```text
2026-08-07 23:45 UTC
```

para M15 representa aproximadamente:

```text
23:45 → 00:00
```

---

# 7. Ordenação Temporal

Os dados devem estar em ordem cronológica crescente.

A propriedade verificada é equivalente a:

```python
df["time"].is_monotonic_increasing
```

Resultado atual:

```text
PASS
```

---

# 8. Duplicados

Foi analisada a ocorrência de timestamps repetidos.

Resultado:

```text
Timestamps duplicados: 0
```

Isso significa que não existem atualmente dois candles M15 persistidos com o mesmo timestamp.

---

# 9. Importância dos Duplicados

Duplicados poderiam causar:

```text
indicadores incorretos
retornos duplicados
entradas repetidas
agregação H1/H4 incorreta
resultados de backtest distorcidos
```

Por isso:

```text
timestamp único
```

é uma invariante da camada histórica.

---

# 10. Valores Ausentes

Resultado:

```text
time           0
open           0
high           0
low            0
close          0
tick_volume    0
spread         0
real_volume    0
```

Não existem valores `NaN` nas colunas persistidas do dataset atual.

---

# 11. Null != Gap

A ausência de `NaN` não significa que a série temporal seja perfeitamente contínua.

Exemplo:

```text
10:00
10:15
10:30
11:00
```

Não existe:

```text
10:45
```

Nesse caso não há uma linha contendo `NaN`.

Existe:

```text
um candle ausente
```

ou:

```text
gap temporal
```

---

# 12. Integridade OHLC

Foram verificados os seguintes invariantes:

```text
High >= Low

High >= Open

High >= Close

Low <= Open

Low <= Close
```

Resultado:

```text
Candles OHLC inválidos: 0
```

---

# 13. Preços Positivos

Também é exigido:

```text
Open  > 0
High  > 0
Low   > 0
Close > 0
```

Os testes automatizados atuais validam essa propriedade.

---

# 14. Cobertura por Ano

Número de candles M15 por ano:

```text
2015    24776
2016    24898
2017    24804
2018    24812
2019    24784
2020    24901
2021    24914
2022    24912
2023    24824
2024    24897
2025    24757
2026    14944
```

---

# 15. Ano Parcial

O ano:

```text
2026
```

possui menos candles porque o dataset termina em:

```text
2026-08-07
```

Portanto ele não deve ser comparado diretamente com anos completos.

---

# 16. Consistência Anual

Entre 2015 e 2025 os anos completos possuem aproximadamente:

```text
24.7k → 24.9k candles
```

Essa distribuição é bastante estável.

Ela oferece evidência de que não existe uma perda grosseira de vários meses ou anos completos no histórico.

---

# 17. Consistência Anual Não Garante Perfeição

Mesmo com quantidade anual consistente podem existir:

```text
gaps de horas
gaps de minutos
feriados
interrupções do feed
problemas intraday
```

Por isso também é necessária uma análise de continuidade temporal.

---

# 18. Detecção de Gaps

Para M15, o intervalo esperado entre candles consecutivos é:

```text
15 minutos
```

A análise calcula:

```python
df["delta"] = df["time"].diff()
```

Quando:

```text
delta > 15 minutos
```

é identificada uma descontinuidade.

---

# 19. Resultado de Gaps

Foram encontrados:

```text
659 gaps
```

no histórico M15.

Classificação inicial:

```text
605 atravessam fim de semana

54 ocorrem inteiramente
em dias úteis
```

---

# 20. Weekend Gaps

Forex possui interrupção semanal normal.

Exemplo conceitual:

```text
sexta-feira
      ↓
mercado fecha
      ↓
fim de semana
      ↓
reabertura
```

Portanto um gap desse tipo é esperado e não representa automaticamente corrupção do dataset.

---

# 21. Proporção dos Gaps

Do total de:

```text
659
```

gaps detectados:

```text
605
```

atravessam sábado ou domingo.

Isso representa aproximadamente:

```text
91.8%
```

dos gaps identificados.

---

# 22. Gaps Intraweek

Restaram:

```text
54
```

gaps que não atravessam fim de semana.

Esses intervalos precisam ser tratados com maior cuidado.

---

# 23. Exemplos de Gaps Intraweek Longos

Foram observados intervalos como:

```text
2018-12-24 20:45
→
2018-12-26 06:00

1 dia 09:15
```

e:

```text
2019-12-31 22:45
→
2020-01-02 06:00

1 dia 07:15
```

Esses casos coincidem com períodos de Natal e Ano Novo.

---

# 24. Feriados e Liquidez

Alguns gaps intraweek podem ser explicados por:

```text
feriados
liquidez extremamente reduzida
sessões especiais
fechamento do feed
```

Isso não significa que todos os 54 gaps possuam explicação confirmada.

---

# 25. Gaps Ainda Não Classificados

Também existem intervalos como:

```text
2026-02-26 21:45
→
2026-02-27 03:15

5h30
```

ou:

```text
2016-03-23 17:15
→
2016-03-23 20:30

3h15
```

e outros semelhantes.

A causa desses intervalos não foi determinada.

---

# 26. Possíveis Causas

Possibilidades incluem:

```text
manutenção
problema do servidor
interrupção do feed
ausência de dados
ausência real de cotações na fonte
```

Nenhuma delas deve ser assumida sem evidência adicional.

---

# 27. Política para Gaps Não Classificados

A regra atual é:

```text
preservar o gap
```

e não:

```text
inventar a causa
```

ou:

```text
fabricar candles
```

---

# 28. Forward Fill

Não utilizar:

```python
df.ffill()
```

para preencher OHLC ausente em gaps.

Isso criaria preços artificiais.

---

# 29. Exemplo de Problema do Forward Fill

Dataset real:

```text
10:00
10:15
10:30
11:00
```

Aplicar uma reconstrução artificial poderia gerar:

```text
10:45
```

com preço copiado de:

```text
10:30
```

Esse candle:

```text
nunca existiu na fonte
```

mas poderia posteriormente alterar:

```text
EMA
ATR
RSI
breakout
stop
sinal
```

---

# 30. Decisão

Gaps não são preenchidos automaticamente.

Essa é uma decisão arquitetural do projeto.

---

# 31. Relação com Timeframes Superiores

Os gaps M15 afetam diretamente:

```text
H1
H4
```

Por isso o `TimeframeBuilder` mantém:

```text
source_bar_count
expected_bar_count
complete
```

---

# 32. H1 Incompleto

H1 exige:

```text
4 M15
```

Se existirem apenas:

```text
3
```

o resultado será:

```text
complete = False
```

---

# 33. H4 Incompleto

H4 exige:

```text
16 M15
```

Se existirem:

```text
15
```

o resultado será:

```text
complete = False
```

---

# 34. Resultado H1

Dataset:

```text
data/processed/EURUSD/H1.parquet
```

Resultado:

```text
Total:        72080

Completos:    72018

Incompletos:     62
```

---

# 35. Proporção de H1 Incompletos

Aproximadamente:

```text
0.086%
```

dos candles H1 gerados foram marcados como incompletos.

Essa proporção é baixa, mas não deve ser ignorada.

---

# 36. Resultado H4

Dataset:

```text
data/processed/EURUSD/H4.parquet
```

Resultado:

```text
Total:        18046

Completos:    17929

Incompletos:    117
```

---

# 37. Proporção de H4 Incompletos

Aproximadamente:

```text
0.65%
```

dos candles H4 gerados foram marcados como incompletos.

H4 é mais sensível a gaps porque depende de:

```text
16 candles M15
```

em vez de apenas quatro.

---

# 38. Política para Candles Processados

Candles incompletos permanecem armazenados.

Eles não são removidos durante a construção do dataset.

Motivo:

```text
auditoria
rastreabilidade
diagnóstico
```

---

# 39. Uso por Estratégias

A regra padrão futura será utilizar somente:

```text
complete == True
```

nos datasets processados.

Candles incompletos não devem gerar sinais por padrão.

---

# 40. Spread Histórico

O campo:

```text
spread
```

foi analisado separadamente.

Resultado geral:

```text
count     288223

mean      3.636688 points

median    2 points

min       0 points

max       129 points
```

---

# 41. Conversão para Pip

Para o EURUSD atual:

```text
10 points = 1 pip
```

Logo:

```text
média ≈ 0.364 pip

mediana = 0.2 pip

máximo = 12.9 pips
```

---

# 42. Spread Zero

Foi observado:

```text
32.54%
```

dos candles com:

```text
spread = 0
```

Essa proporção é alta demais para que o campo seja utilizado sem investigação como representação direta de custos reais de execução.

---

# 43. Spread por Ano

Resultados observados:

```text
2015 mean   7.91
2016 mean   7.17
2017 mean   5.14
2018 mean   4.16
2019 mean   4.90
2020 mean   1.31
2021 mean   0.96
2022 mean   1.28
2023 mean   1.15
2024 mean   2.41
2025 mean   5.47
2026 mean   0.61
```

Valores em:

```text
points
```

---

# 44. Mediana do Spread por Ano

Também foram observadas medianas como:

```text
2015    7
2016    7
2017    7
2018    1
2019    4
2020    1
2021    0
2022    0
2023    0
2024    1
2025    4
2026    0
```

---

# 45. Interpretação

O comportamento do campo:

```text
spread
```

muda significativamente ao longo do histórico.

Não foi determinado se isso decorre de:

```text
mudança de feed
mudança de metodologia
mudança no servidor
mudança de mercado
combinação desses fatores
```

---

# 46. Decisão sobre Spread

O projeto estabelece:

```text
spread histórico dos candles
não é CostModel oficial.
```

O campo permanece disponível para:

```text
pesquisa
auditoria
comparação
```

---

# 47. CostModel Futuro

O BacktestEngine deverá receber custos através de uma camada independente.

Possíveis modelos:

```text
FixedSpreadModel

ConservativeSpreadModel

TickBidAskModel

BrokerHistoricalCostModel
```

---

# 48. Stress Test de Custos

Estratégias futuras deverão poder ser testadas com cenários como:

```text
custo base

custo × 1.5

custo × 2.0
```

Uma estratégia extremamente sensível a pequenas alterações de custo merece maior cautela.

---

# 49. Tick Volume

Estatísticas observadas:

```text
count    288223

mean       926

median     680

min          1

max      21483
```

---

# 50. Decisão sobre Tick Volume

O campo:

```text
tick_volume
```

pode permanecer disponível para pesquisa.

Ele pode representar:

```text
atividade relativa do feed
```

---

# 51. Limitação do Tick Volume

Não interpretar:

```text
tick_volume
```

como:

```text
volume global negociado de EURUSD
```

O mercado spot Forex é descentralizado.

---

# 52. Uso Futuro Possível

Exemplos de hipóteses que podem utilizar tick volume:

```text
breakout com atividade acima da média

expansão de volatilidade + atividade

regime de atividade elevada

confirmação relativa de movimento
```

Qualquer benefício deverá ser testado empiricamente.

---

# 53. Real Volume

O campo:

```text
real_volume
```

apresentou comportamento muito diferente entre anos.

---

# 54. Real Volume por Ano

Percentual de candles com:

```text
real_volume > 0
```

observado:

```text
2015     44.15%

2016    100.00%

2017     42.53%

2018      0.00%

2019      0.00%

2020      0.00%

2021      0.00%

2022      0.00%

2023      0.00%

2024      0.00%

2025      0.00%

2026      0.00%
```

---

# 55. Interpretação do Real Volume

Essa quebra estrutural indica que o campo não possui comportamento consistente ao longo da série.

Não existe evidência suficiente na análise atual para tratá-lo como uma feature homogênea entre:

```text
2015
```

e:

```text
2026
```

---

# 56. Decisão sobre Real Volume

O campo:

```text
real_volume
```

não será utilizado atualmente para:

```text
signals
filters
features
regime detection
position sizing
```

---

# 57. Preservação do Real Volume

Apesar disso, o campo continua armazenado no:

```text
M15 raw
```

porque removê-lo dificultaria futuras investigações sobre a origem do histórico.

---

# 58. Mudanças Estruturais no Feed

Tanto:

```text
spread
```

quanto:

```text
real_volume
```

apresentam sinais de comportamento não homogêneo ao longo do histórico.

Isso sugere que o dataset não deve ser tratado como se todas as suas propriedades fossem igualmente comparáveis entre 2015 e 2026.

---

# 59. OHLC vs Campos Auxiliares

A avaliação atual separa:

```text
OHLC
```

de:

```text
spread
real_volume
```

O OHLC passou pelas verificações estruturais atuais.

Os campos auxiliares apresentaram limitações adicionais.

---

# 60. Classificação Atual

## OHLC

```text
APROVADO PARA DESENVOLVIMENTO
```

## Timestamp / UTC

```text
APROVADO
```

## Tick Volume

```text
UTILIZÁVEL COM RESSALVAS
```

## Spread Histórico

```text
NÃO UTILIZAR COMO
CUSTO OFICIAL
```

## Real Volume

```text
NÃO UTILIZAR COMO FEATURE
```

---

# 61. O Significado de "Aprovado"

Neste documento:

```text
aprovado
```

significa:

> Adequado para continuar o desenvolvimento e pesquisa do projeto dentro das limitações documentadas.

Não significa:

```text
certificado como representação perfeita do mercado
```

ou:

```text
adequado automaticamente para execução real.
```

---

# 62. Dataset de Desenvolvimento

Classificação atual:

```text
development_and_research
```

Usos considerados adequados:

```text
desenvolvimento do BacktestEngine

testes das estratégias iniciais

validação da arquitetura

engenharia de features

estudos exploratórios

testes de robustez iniciais
```

---

# 63. Uso Final

Antes de decisões de execução real poderão ser necessárias validações adicionais relacionadas a:

```text
broker escolhido

spread

commission

swap

slippage

ticks

liquidez

horário do broker
```

---

# 64. Dados Recentes e Spread Zero

Nos testes correntes também foram observados candles recentes com:

```text
spread = 0
```

enquanto o tick instantâneo apresentava:

```text
Ask > Bid
```

Esse comportamento reforça que:

```text
spread do candle
```

e:

```text
spread instantâneo Bid/Ask
```

não devem ser tratados como a mesma fonte de informação.

---

# 65. Ticks Históricos

Foi validada a disponibilidade de ticks históricos contendo:

```text
bid
ask
time_msc
```

Isso abre possibilidade para modelagem futura de spread mais granular.

---

# 66. Limitação dos Ticks

Também foram observados muitos ticks com:

```text
Bid == Ask
```

no MetaQuotes-Demo.

Portanto nem o histórico de ticks atual deve ser aceito automaticamente como referência final de custos.

---

# 67. Outliers de Spread

O maior valor observado no campo histórico foi:

```text
129 points
```

equivalente a aproximadamente:

```text
12.9 pips
```

Antes de qualquer uso desse campo, esses valores devem ser investigados em contexto temporal.

Possíveis causas podem incluir períodos de baixa liquidez, eventos ou características do feed.

Nenhuma causa é assumida automaticamente.

---

# 68. Outliers de Tick Volume

O maior `tick_volume` observado foi:

```text
21483
```

Isso não é tratado automaticamente como erro.

Valores extremos podem ocorrer em períodos de grande atividade.

Caso o tick volume seja utilizado como feature, sua distribuição deverá ser estudada de forma robusta.

---

# 69. Qualidade por Estratégia

A qualidade necessária dos dados depende da estratégia.

Exemplo:

```text
Trend Following H4
```

pode ser relativamente menos sensível a pequenos detalhes de microestrutura.

Já:

```text
Scalping M1
```

seria extremamente sensível a:

```text
spread
ticks
slippage
latência
Bid/Ask
```

---

# 70. Escopo Atual

O dataset atual é considerado apropriado principalmente para estratégias em horizontes como:

```text
M15
H1
H4
```

dentro das limitações de custos já documentadas.

O projeto atualmente não está focado em:

```text
HFT
tick scalping
latency arbitrage
```

---

# 71. Estratégias Sensíveis a Custos

Estratégias com:

```text
muitos trades
pequeno target
baixo payoff bruto
```

devem ser analisadas com atenção especial.

Um pequeno erro no modelo de spread pode alterar significativamente seu resultado.

---

# 72. Data Quality e Backtest

O futuro BacktestEngine não deverá esconder problemas de qualidade.

Exemplo:

```text
complete=False
```

não deverá ser convertido automaticamente em:

```text
complete=True
```

---

# 73. Data Quality e Strategy

A Strategy não deverá decidir individualmente como corrigir gaps.

Isso poderia criar comportamentos diferentes entre estratégias.

A política de dados deve ser centralizada.

---

# 74. Data Quality e Features

Features derivadas também devem respeitar gaps.

Exemplo:

```text
ATR
EMA
RSI
```

podem atravessar uma descontinuidade temporal mesmo quando pandas continua calculando normalmente pelas linhas existentes.

Isso deverá ser considerado durante a futura Feature Layer.

---

# 75. Continuidade por Número de Linhas

Indicadores tradicionais normalmente trabalham sobre:

```text
N barras
```

e não necessariamente:

```text
N unidades reais de tempo
```

Em presença de gaps:

```text
20 candles
```

podem cobrir um intervalo de relógio maior que o esperado.

Esse comportamento deve ser conhecido.

---

# 76. Weekend Gaps em Indicadores

Weekend gaps são parte natural de séries Forex.

Eles não devem ser preenchidos apenas para tornar:

```text
EMA
ATR
```

cronologicamente uniformes.

---

# 77. Intraweek Gaps e Estratégias

Para gaps intraweek maiores, poderá ser necessário futuramente implementar políticas como:

```text
invalidar sinal próximo ao gap

resetar determinados estados

registrar regime de data discontinuity
```

Nenhuma dessas regras está implementada atualmente.

---

# 78. Regra Atual

Neste momento:

```text
preservar dado
marcar incompletos
documentar limitações
```

é preferido a tentar corrigir todos os casos antes do BacktestEngine existir.

---

# 79. Validação Independente Futura

Antes da validação final de estratégias será útil comparar parte do histórico com outra fonte.

Possível fluxo:

```text
MetaQuotes-Demo
       ↓
comparar OHLC
       ↕
Provider independente
```

Objetivo:

```text
identificar divergências relevantes
```

---

# 80. Critérios de Comparação Futuros

Possíveis métricas:

```text
diferença de Close

diferença de High

diferença de Low

candles ausentes

timestamp

spread

gaps

distribuição de retornos
```

Status:

```text
NÃO IMPLEMENTADO
```

---

# 81. Data Quality Tests

Parte da qualidade está protegida por testes automatizados.

Arquivo:

```text
tests/test_historical_data.py
```

Verificações atuais:

```text
arquivo existe

dataset não vazio

timestamps únicos

ordenação temporal

UTC

zero nulls

OHLC válido

preços positivos
```

---

# 82. Timeframe Tests

Arquivo:

```text
tests/test_timeframe_builder.py
```

Verifica:

```text
H1 criado

H4 criado

H1 completo = 4 M15

H4 completo = 16 M15

alinhamento temporal

UTC

OHLC derivado
```

---

# 83. Estado dos Testes

No marco atual:

```text
25 collected

25 passed

0 failed
```

---

# 84. Testes Não Substituem Auditoria

Um dataset pode passar em todos os testes estruturais e ainda possuir:

```text
spread incorreto

feed ruim

problemas econômicos

outliers suspeitos

mudanças de metodologia
```

Por isso existem duas camadas:

```text
Automated Validation
+
Data Quality Analysis
```

---

# 85. Automated Validation

Objetivo:

```text
detectar violações objetivas
e regressões
```

Exemplos:

```text
duplicado
OHLC impossível
timezone incorreto
```

---

# 86. Data Quality Analysis

Objetivo:

```text
investigar características
que exigem contexto
```

Exemplos:

```text
gap
spread
volume
mudanças entre anos
```

---

# 87. Metadata

Parte das conclusões atuais também é registrada na metadata.

Exemplo:

```text
spread_reliable_for_execution = false

real_volume_reliable = false
```

Isso permite que outras partes do projeto conheçam limitações importantes do dataset.

---

# 88. Future Quality Report

No futuro poderá ser criado um relatório persistente contendo:

```text
dataset_id
audit_date
bars
duplicates
nulls
gaps
weekend_gaps
intraweek_gaps
invalid_ohlc
spread_zero_pct
outliers
quality_status
```

Status:

```text
PLANEJADO
```

---

# 89. Quality Gates

O projeto poderá futuramente implementar:

```text
Quality Gates
```

antes de permitir um dataset em backtest.

Exemplo:

```text
duplicates == 0

invalid_ohlc == 0

timezone == UTC
```

e políticas específicas para gaps.

---

# 90. Hard Fail vs Warning

Nem todo problema deve produzir o mesmo comportamento.

## Hard Fail

Exemplos:

```text
OHLC impossível

timestamp duplicado inesperado

timezone ausente

preço <= 0
```

## Warning / Metadata

Exemplos:

```text
gap

spread zero

real_volume inconsistente
```

---

# 91. Razão para a Distinção

Excluir todo dataset com qualquer gap seria impraticável para séries reais.

Por outro lado, aceitar:

```text
High < Low
```

seria claramente incorreto.

A política deve diferenciar:

```text
violação estrutural
```

de:

```text
limitação da fonte
```

---

# 92. Data Quality Status

Estado atual do EURUSD M15:

```text
STRUCTURAL QUALITY:
PASS

TEMPORAL CONTINUITY:
PASS WITH KNOWN GAPS

SPREAD QUALITY:
NOT APPROVED FOR OFFICIAL COST MODEL

TICK VOLUME:
AVAILABLE WITH INTERPRETATION LIMITS

REAL VOLUME:
NOT APPROVED AS FEATURE
```

---

# 93. Approval Matrix

| Campo / Propriedade | Status | Uso atual |
|---|---|---|
| Time | ✅ | Permitido |
| UTC | ✅ | Obrigatório |
| Open | ✅ | Permitido |
| High | ✅ | Permitido |
| Low | ✅ | Permitido |
| Close | ✅ | Permitido |
| Tick Volume | 🟡 | Com ressalvas |
| Spread histórico | 🟠 | Auditoria, não custo oficial |
| Real Volume | 🔴 | Não usar como feature |
| H1 completo | ✅ | Permitido |
| H4 completo | ✅ | Permitido |
| H1/H4 incompleto | 🟠 | Auditoria, não Strategy por padrão |
| Gaps | 🟡 | Preservados |

---

# 94. Fonte Atual vs Fonte Definitiva

MetaQuotes-Demo é a fonte atual de desenvolvimento.

Isso não implica:

```text
fonte definitiva de produção
```

Antes da execução futura a fonte deverá ser reconsiderada de acordo com o broker e a estratégia.

---

# 95. Qualidade e Reprodutibilidade

As conclusões deste documento correspondem ao dataset atual:

```text
288223 candles
```

Caso o arquivo seja atualizado ou substituído, a auditoria deverá ser executada novamente.

---

# 96. Dataset Mutability

Uma futura atualização histórica pode alterar:

```text
último timestamp
quantidade de candles
gaps
spread
volume
```

Portanto números deste documento representam um snapshot da versão atual do dataset.

---

# 97. Dataset Versioning

No futuro a auditoria deverá ser associada a:

```text
dataset_version
```

ou:

```text
hash
```

para evitar ambiguidade.

Status atual:

```text
NÃO IMPLEMENTADO
```

---

# 98. Critério Atual para Avançar

Para iniciar o desenvolvimento do BacktestEngine, o dataset atual cumpre as condições mínimas definidas pelo projeto:

```text
histórico suficiente

OHLC válido

UTC

zero duplicados

zero nulls

timeframes superiores controlados

gaps identificados

limitações conhecidas

testes automatizados
```

---

# 99. O Que Não Deve Ser Concluído

Os resultados deste relatório não demonstram que:

```text
uma estratégia será lucrativa

o spread histórico é preciso

o feed representa qualquer broker específico

slippage pode ser ignorado

todos os gaps são normais

todos os campos possuem mesma qualidade
```

Essas seriam conclusões além do que a análise suporta.

---

# 100. Regra Principal

A regra principal de qualidade do projeto é:

> Problemas conhecidos devem ser preservados, medidos e documentados; não escondidos por transformações silenciosas.

---

# 101. Estado Atual

Data Quality no marco:

```text
FOREX v0.1
```

Status:

```text
Dataset audit                  COMPLETE

Duplicate analysis             COMPLETE

Null analysis                  COMPLETE

OHLC integrity                 COMPLETE

Annual coverage                COMPLETE

Gap detection                  COMPLETE

Weekend classification         COMPLETE

Intraweek gap identification   COMPLETE

Spread analysis                COMPLETE

Tick volume analysis           COMPLETE

Real volume analysis           COMPLETE

Quality decisions              COMPLETE

Alternative source comparison  NOT IMPLEMENTED

Automated quality report       NOT IMPLEMENTED

Dataset version/hash           NOT IMPLEMENTED
```

---

# 102. Resumo Executivo

Dataset atual:

```text
EURUSD M15

2015-01-02
→
2026-08-07

288223 candles
```

Estruturalmente:

```text
0 duplicados

0 nulls

0 OHLC inválidos
```

Temporalmente:

```text
659 gaps

605 weekend

54 intraweek
```

Campos auxiliares:

```text
tick_volume
→ utilizável com ressalvas

spread
→ não utilizar como custo oficial

real_volume
→ não utilizar como feature
```

Timeframes derivados:

```text
H1
72018 completos
62 incompletos

H4
17929 completos
117 incompletos
```

Classificação:

```text
APPROVED FOR DEVELOPMENT
AND RESEARCH

WITH KNOWN LIMITATIONS
```

---

# 103. Próximo Documento

O próximo documento é:

```text
docs/08_TESTING.md
```

Ele documentará:

```text
pytest

unit tests

integration tests

test suite atual

25 testes

invariantes protegidas

regression tests futuros

testes planejados para BacktestEngine

estratégia de testes do projeto
```
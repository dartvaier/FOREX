# Project Overview

## 1. Visão Geral

O projeto **FOREX Algorithmic Trading Research Platform** é uma plataforma de pesquisa e desenvolvimento de sistemas quantitativos para o mercado Forex.

A plataforma é construída em Python e utiliza o MetaTrader 5 como primeira interface de acesso ao mercado.

O objetivo não é criar apenas um script que gere sinais de compra e venda.

O projeto busca construir uma infraestrutura modular capaz de suportar todo o ciclo de desenvolvimento de uma estratégia quantitativa:

```text
Pesquisa
   ↓
Hipótese
   ↓
Dados
   ↓
Validação dos dados
   ↓
Backtesting
   ↓
Análise estatística
   ↓
Robustez
   ↓
Out-of-sample
   ↓
Conta Demo
   ↓
Execução futura
Cada uma dessas etapas deve possuir responsabilidades claramente separadas.
2. Objetivo Principal
O objetivo principal da plataforma é permitir que estratégias de Forex possam ser:
definidas de maneira objetiva;
implementadas de forma reproduzível;
testadas utilizando dados historicamente consistentes;
avaliadas considerando custos de negociação;
comparadas utilizando métricas padronizadas;
submetidas a testes de robustez;
validadas fora da amostra utilizada no desenvolvimento;
posteriormente testadas em ambiente Demo.
Uma estratégia não é considerada válida apenas porque apresentou lucro em um backtest.
O projeto busca avaliar se um comportamento possui evidência suficiente para continuar sendo investigado.
3. Filosofia do Projeto
A filosofia de desenvolvimento pode ser resumida em:
Integridade antes de estratégia.

Robustez antes de otimização.

Validação antes de execução.

Risco antes de retorno.
O desenvolvimento da infraestrutura ocorre antes da tentativa de encontrar estratégias lucrativas.
Isso reduz o risco de interpretar como vantagem estatística algo que na realidade foi causado por:
look-ahead bias
data leakage
overfitting
custos ignorados
candles incompletos
timezone incorreto
gaps artificiais
execução impossível
erro na construção dos indicadores
4. Mercado Inicial
O primeiro mercado utilizado no desenvolvimento é:
Mercado: Forex
Símbolo inicial: EURUSD
O EURUSD foi escolhido como ativo inicial por permitir que toda a infraestrutura seja construída e validada sobre apenas um instrumento antes da expansão para múltiplos pares.
A arquitetura não deve, entretanto, depender especificamente do EURUSD.
No futuro o sistema poderá suportar outros instrumentos desde que suas especificações sejam obtidas dinamicamente.
Exemplos:
GBPUSD
USDJPY
USDCHF
AUDUSD
USDCAD
NZDUSD
EURJPY
GBPJPY
A inclusão de novos instrumentos deverá ocorrer somente após a estabilização da infraestrutura principal.
5. Fonte Inicial de Mercado
A primeira integração utiliza:
MetaTrader 5
MetaQuotes-Demo
O MetaTrader 5 fornece inicialmente:
candles
ticks
Bid
Ask
especificações do símbolo
dados da conta
histórico
Essa fonte é adequada para:
desenvolvimento
integração
testes
prototipagem
validação da infraestrutura
Ela não é automaticamente considerada a fonte definitiva para backtests de produção.
Particularmente, os campos históricos relacionados a spread e volume apresentaram inconsistências que são documentadas separadamente.
6. Escopo Atual
O escopo atualmente implementado inclui:
MetaTrader 5 integration
        ↓
Market Data Layer
        ↓
Historical Data Layer
        ↓
Data Quality Analysis
        ↓
Timeframe Transformation
Até o marco atual do projeto já existem:
conexão Python ↔ MetaTrader 5
consulta de Bid e Ask
consulta de especificações do símbolo
coleta de candles
controle de candle corrente
download histórico por intervalos
normalização UTC
armazenamento Parquet
validação OHLC
detecção de duplicados
detecção de gaps
construção M15 → H1
construção M15 → H4
identificação de candles incompletos
testes automatizados
metadata do dataset
7. Componentes Ainda Não Implementados
Os seguintes componentes fazem parte da arquitetura futura, mas ainda não devem ser considerados implementados:
Backtest Engine
Strategy Engine
Cost Model
Risk Engine
Portfolio Layer
Execution Engine
Monitoring
Trade Journal
Performance Analytics completo
Walk-Forward Engine
Out-of-Sample Manager
Monte Carlo Analysis
Paper/Demo Trading Engine
A documentação pode especificar o design pretendido desses componentes, mas deve sempre diferenciar:
IMPLEMENTADO
de:
PLANEJADO
8. Separação entre Pesquisa e Engenharia
O projeto possui duas áreas conceitualmente diferentes.
Pesquisa quantitativa
Responsável por responder perguntas como:
Existe evidência para momentum em Forex?

Trend Following funciona em quais regimes?

Carry possui fundamento econômico?

Mean Reversion aparece em quais horizontes?

Breakouts possuem comportamento persistente?

Quais filtros de regime podem ser testados?
A pesquisa quantitativa é registrada separadamente na documentação metodológica do projeto.
Engenharia
Responsável por perguntas como:
Os candles estão corretos?

O timezone está correto?

Existe look-ahead?

O backtester executa na barra correta?

Os custos são aplicados corretamente?

Os resultados são reproduzíveis?

Os dados possuem gaps?

Os datasets são consistentes?
Uma estratégia só pode ser analisada de forma confiável se a infraestrutura de engenharia estiver correta.
9. Princípio de Evidência
As afirmações utilizadas no projeto devem ser classificadas conceitualmente como:
DEFINIÇÃO
EVIDÊNCIA
HEURÍSTICA
HIPÓTESE
DEFINIÇÃO
Uma propriedade matemática ou mecânica.
Exemplo:
EMA é uma média móvel exponencial.
EVIDÊNCIA
Uma afirmação sustentada diretamente por estudos ou dados apropriados.
Exemplo:
Time-Series Momentum possui evidência documentada
em diferentes classes de ativos.
HEURÍSTICA
Uma convenção prática que pode ser útil, mas não representa uma lei universal.
Exemplo:
ADX > determinado valor pode ser utilizado
como filtro experimental de tendência.
HIPÓTESE
Uma afirmação que será submetida a teste.
Exemplo:
Um breakout de volatilidade no EURUSD H1
possui expectativa positiva após custos.
Essa classificação ajuda a impedir que hipóteses sejam tratadas como fatos.
10. Processo de Desenvolvimento de Estratégias
Cada estratégia deverá começar com uma hipótese explicitamente definida.
Fluxo esperado:
1. Hipótese

2. Racional econômico ou comportamental

3. Regra primária definida antes do resultado

4. Dataset de desenvolvimento

5. Backtest

6. Custos

7. Sensibilidade local

8. Robustez

9. Validação

10. Lockbox Out-of-Sample

11. Demo

12. Aprovação ou descarte
A maioria das estratégias testadas pode e provavelmente deverá ser descartada.
O objetivo não é fazer toda estratégia funcionar.
O objetivo é identificar aquelas que sobrevivem a critérios rigorosos de validação.
11. Controle de Overfitting
O projeto deve evitar buscas excessivas de parâmetros.
Uma estratégia não deve ser otimizada através de milhares de combinações simplesmente para selecionar o melhor resultado histórico.
Exemplo indesejado:
EMA curta: 5 → 100
EMA longa: 50 → 500
ADX: 10 → 50
ATR: 5 → 100
Stop: dezenas de valores
Take Profit: dezenas de valores
Combinações desse tipo criam um grande espaço de busca e aumentam o risco de data snooping.
A abordagem preferida é:
especificação primária
        ↓
pequena análise de sensibilidade
        ↓
regiões estáveis
        ↓
validação independente
O projeto deve preferir estabilidade a máximos locais de performance.
12. Dados e Disponibilidade Temporal
Uma das regras mais importantes da plataforma é:
Um dado só pode ser utilizado se estivesse disponível no momento da decisão simulada.

Exemplo correto:
Candle t fecha
      ↓
dados do candle t tornam-se conhecidos
      ↓
estratégia calcula sinal
      ↓
ordem pode ser executada em t+1
Exemplo incorreto:
Candle t ainda está aberto
      ↓
estratégia utiliza fechamento futuro de t
      ↓
backtest gera sinal
O segundo caso representa look-ahead.
13. Candle Corrente
A API do MetaTrader 5 considera:
bar 0 = barra mais recente
Durante mercado ativo essa barra normalmente ainda está em formação.
Por isso a camada de dados utilizada pelas estratégias exclui deliberadamente o candle corrente.
Existe também um teste automatizado específico para impedir regressões dessa regra.
14. Timezone
O timezone interno oficial da plataforma é:
UTC
Todos os timestamps utilizados internamente devem ser timezone-aware.
Conversões para fusos específicos só devem ocorrer em componentes que realmente dependam disso.
Exemplos:
Europe/London
America/New_York
Isso será especialmente importante em estratégias baseadas em sessões.
Nunca devem ser utilizadas regras como:
London = horário GMT fixo
porque Londres possui mudanças de horário relacionadas ao DST.
15. Histórico Atual
O dataset principal de desenvolvimento é:
EURUSD
M15
2015-01-02 → 2026-08-07
Quantidade:
288223 candles
Os dados estão armazenados em:
data/raw/EURUSD/M15.parquet
A análise inicial encontrou:
Duplicados:      0
Nulls:           0
OHLC inválidos:  0
O histórico apresenta gaps naturais e alguns gaps intraweek.
Essas descontinuidades são preservadas.
16. Política de Gaps
Gaps não devem ser preenchidos automaticamente.
Métodos como:
ffill()
não devem ser aplicados ao preço simplesmente para criar uma grade temporal perfeita.
Caso uma barra não exista na fonte:
barra ausente
     ↓
permanece ausente
Os componentes superiores devem ser capazes de lidar com essa situação.
17. Construção de Timeframes
O M15 é atualmente utilizado como timeframe base.
A partir dele são construídos:
M15
 ├── H1
 └── H4
Cada H1 completo necessita de:
4 M15
Cada H4 completo necessita de:
16 M15
Candles que não possuem todas as barras necessárias são preservados, porém marcados como:
complete = False
Isso permite distinguir:
candle real completo
de:
agregação parcial causada por dados ausentes
18. Dataset H1
Dataset processado:
data/processed/EURUSD/H1.parquet
Estado atual:
Candles totais:     72080
Completos:          72018
Incompletos:           62
Período:
2015-01-02 09:00 UTC
→
2026-08-07 23:00 UTC
19. Dataset H4
Dataset processado:
data/processed/EURUSD/H4.parquet
Estado atual:
Candles totais:     18046
Completos:          17929
Incompletos:          117
Período:
2015-01-02 08:00 UTC
→
2026-08-07 20:00 UTC
20. Spread e Custos
O campo histórico de spread fornecido pelo feed atual não é considerado suficientemente consistente para representar sozinho os custos de execução.
A arquitetura futura deverá separar:
Market Data
de:
Cost Model
Isso permitirá simulações como:
spread normal
spread conservador
spread estressado
slippage
commission
swap
O resultado de uma estratégia deverá ser analisado após custos.
21. Volume
O projeto diferencia:
tick_volume
de:
real_volume
O tick_volume pode ser preservado como uma medida de atividade do feed.
Não deve ser interpretado como volume total negociado globalmente no mercado Forex.
O real_volume apresentou mudanças estruturais significativas no histórico e não é considerado confiável como feature na configuração atual.
22. Testes Automatizados
O projeto possui atualmente:
25 testes
25 passed
0 failed
Os testes cobrem três áreas principais:
MarketData
HistoricalData
TimeframeBuilder
Entre as propriedades validadas estão:
UTC
OHLC
ordenação
duplicados
preços positivos
candles fechados
integridade dos datasets
H1
H4
quantidade de barras fonte
alinhamento temporal
23. Reprodutibilidade
Uma das metas da plataforma é permitir que um experimento possa ser reproduzido.
Por isso deverão ser registrados:
dataset utilizado
período
símbolo
timeframe
parâmetros
versão da estratégia
custos
versão do código
resultado
No futuro cada backtest deverá produzir um identificador ou manifesto de experimento.
24. Separação de Responsabilidades
O projeto deve evitar componentes monolíticos.
Exemplo incorreto:
Strategy
  ├── calcula indicador
  ├── decide sinal
  ├── calcula lote
  ├── envia ordem
  ├── calcula slippage
  ├── controla risco
  └── salva resultado
Arquitetura desejada:
Strategy
    ↓
Signal

Risk Engine
    ↓
Approved Order

Execution
    ↓
Fill

Cost Model
    ↓
Costs

Portfolio
    ↓
Position / Equity

Performance
    ↓
Metrics
Cada componente deve possuir responsabilidade limitada.
25. Segurança
Nenhuma execução real faz parte do estado atual do projeto.
A configuração inicial utiliza:
TRADING_ENABLED=false
O desenvolvimento atual permanece:
READ ONLY
Qualquer implementação futura de execução deverá conter proteções independentes.
Entre elas:
trading enable flag
account validation
demo validation
max position size
max daily loss
max drawdown
order validation
duplicate-order protection
kill switch
logging
26. Backtesting
O Backtest Engine ainda não foi implementado.
Antes da implementação devem ser definidos explicitamente:
timing do sinal
timing da ordem
preço de entrada
preço de saída
Bid / Ask
spread
slippage
stop
take profit
position sizing
comissão
swap
ordem dos eventos dentro de cada candle
Essas decisões serão documentadas em:
docs/10_BACKTEST_DESIGN.md
antes da implementação completa.
27. Estratégias Iniciais de Pesquisa
A pesquisa metodológica identificou famílias de estratégias candidatas.
A ordem de implementação definida para experimentos iniciais é:
1. Simple EMA Trend Following

2. Simple Volatility Breakout

3. Time-Series Momentum

4. Simple Mean Reversion

5. Asian Range Breakout

6. Carry Trade

7. Regime Detection

8. Multi-Timeframe / modelos avançados
Essa ordem representa prioridade de engenharia e pesquisa.
Não representa uma afirmação de rentabilidade.
28. Machine Learning
Machine Learning não faz parte da primeira etapa do projeto.
A prioridade inicial é construir estratégias simples, auditáveis e interpretáveis.
Somente após existir:
dados confiáveis
backtester confiável
baseline simples
processo OOS
controle de overfitting
será apropriado investigar modelos mais complexos.
Isso reduz o risco de utilizar Machine Learning para aprender artefatos do dataset.
29. Métricas Futuras
O Backtest Engine deverá futuramente fornecer métricas como:
Net Profit
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
Number of Trades
Exposure
Recovery Factor
Nenhuma métrica individual será utilizada como critério universal de aprovação.
A análise deverá considerar múltiplas dimensões de risco e retorno.
30. Critério de Sucesso do Projeto
O sucesso do projeto não será definido simplesmente por:
"o bot ganhou dinheiro no backtest"
O sucesso da plataforma será definido por sua capacidade de:
reproduzir resultados
detectar erros
evitar look-ahead
controlar custos
controlar risco
testar hipóteses
descartar estratégias ruins
validar estratégias boas
operar de forma previsível
Mesmo uma estratégia descartada representa um resultado útil quando o processo de validação foi correto.
31. Estado Atual
Marco atual:
FOREX v0.1

Research                 COMPLETE
Environment              COMPLETE
Market Data              COMPLETE
Historical Data          COMPLETE
Data Quality             COMPLETE
Data Transformation      COMPLETE
Automated Tests          25 / 25
Documentation            IN PROGRESS

Backtest Engine           NOT STARTED
Strategy Engine           NOT STARTED
Risk Engine               NOT STARTED
Execution Engine          NOT STARTED
Demo Validation           NOT STARTED
32. Próximo Marco
O próximo grande marco será:
FOREX v0.2
Backtesting Infrastructure

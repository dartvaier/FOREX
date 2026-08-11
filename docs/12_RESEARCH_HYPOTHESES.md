# Hipóteses de Pesquisa para Estratégias

## 1. Objetivo

Este documento registra hipóteses quantitativas candidatas para futura implementação na plataforma FOREX Algorithmic Trading Research Platform.

As hipóteses ainda não representam estratégias aprovadas, sinais de produção ou recomendação de investimento. O objetivo é transformar ideias de mercado em especificações causais, testáveis, reproduzíveis, auditáveis e passíveis de rejeição.

Fluxo esperado:

~~~text
Hipótese
   ↓
Especificação primária
   ↓
Implementação
   ↓
Teste estatístico
   ↓
Backtest com custos
   ↓
Robustez
   ↓
Out-of-sample
   ↓
Demo
~~~

Um resultado negativo é válido. As regras não devem ser alteradas repetidamente até que uma curva lucrativa seja encontrada.

---

## 2. Escopo dos Dados

As hipóteses iniciais consideram a infraestrutura atual:

~~~text
Símbolo:       EURUSD
Fonte:         MetaQuotes-Demo
Base canônica: M15
Derivados:     H1 e H4
Período:       2015–2026
Timezone:      UTC
Campos:        OHLC, tick_volume e metadados disponíveis
~~~

Regras já estabelecidas pelo projeto continuam obrigatórias:

- utilizar somente candles fechados;
- utilizar somente candles agregados completos por padrão;
- não preencher gaps artificialmente;
- não utilizar real_volume como feature;
- interpretar tick_volume apenas como atividade relativa do feed;
- gerar o sinal no fechamento e executar no próximo open disponível;
- separar Strategy, Risk e CostModel;
- utilizar política conservadora para ambiguidades intrabar.

Sessões de mercado devem ser calculadas com timezones reais, como Europe/London e America/New_York. Offsets UTC fixos não devem substituir timezones com horário de verão.

---

## 3. Status das Hipóteses

Status possíveis:

~~~text
PROPOSED
SPECIFIED
IMPLEMENTED
IN_RESEARCH
VALIDATED
REJECTED
DEFERRED
~~~

Todas as hipóteses deste documento possuem inicialmente status PROPOSED.

Os valores numéricos apresentados são parâmetros primários candidatos. Eles devem ser registrados antes do primeiro backtest e não devem ser interpretados como valores já otimizados.

---

# H01 — Falso Rompimento da Faixa Asiática

## Status

~~~text
PROPOSED
~~~

## Hipótese

> Quando o EURUSD rompe a máxima ou a mínima da sessão asiática e fecha novamente dentro da faixa em até dois candles M15, aumenta a probabilidade de reversão em direção ao centro da faixa.

## Racional

Um rompimento que não consegue permanecer fora da faixa pode indicar rejeição de preço, ausência de continuidade, absorção do fluxo ou captura de stops sem deslocamento persistente.

Esta hipótese é complementar, e não equivalente, ao Asian Range Breakout planejado no roadmap.

## Especificação Primária Candidata

Sessão asiática:

~~~text
00:00–07:00 Europe/London
~~~

Evento:

1. calcular máxima, mínima e midpoint da faixa;
2. exigir rompimento mínimo de 0,15 × ATR(H1, 14);
3. considerar no máximo os dois primeiros candles M15 após o rompimento;
4. confirmar quando um candle fechar novamente dentro da faixa;
5. gerar sinal no fechamento da confirmação;
6. executar no próximo open disponível.

Direção:

~~~text
falso rompimento superior → SHORT
falso rompimento inferior → LONG
~~~

Saída inicial:

~~~text
alvo: midpoint da faixa asiática
stop: extremo do falso rompimento + buffer
~~~

## Variáveis de Análise

- lado e distância do rompimento;
- duração fora da faixa;
- faixa asiática relativa ao histórico;
- tick volume relativo ao mesmo horário;
- volatilidade da primeira hora de Londres;
- retorno até o midpoint e até a borda oposta.

## Critério Inicial de Rejeição

Rejeitar ou reformular se o efeito desaparecer com custos conservadores, depender de um único subperíodo ou funcionar somente em um valor muito específico de buffer.

---

# H02 — Handoff Ásia–Londres Condicionado ao Formato da Sessão

## Status

~~~text
PROPOSED
~~~

## Hipótese

> O movimento asiático tende a continuar durante a abertura de Londres quando a sessão termina próxima de um extremo após uma faixa comprimida, mas tende a reverter quando a Ásia já percorreu uma faixa excepcionalmente grande.

## Racional

O mesmo retorno asiático pode representar deslocamento eficiente ainda não saturado, baixa liquidez com fechamento no extremo ou movimento já excessivo. A direção asiática isolada não é suficiente; o formato e o tamanho relativo da sessão devem condicionar a expectativa.

## Features Primárias

~~~text
asian_return
asian_range
asian_range_percentile
close_location_value
distance_to_high
distance_to_low
relative_tick_volume
~~~

Definição candidata:

~~~text
close_location_value =
(close - asian_low) / (asian_high - asian_low)
~~~

## Grupos Primários

| Faixa asiática | Fechamento | Comportamento esperado |
|---|---|---|
| Abaixo do percentil 30 | Próximo da máxima | Continuação compradora |
| Abaixo do percentil 30 | Próximo da mínima | Continuação vendedora |
| Acima do percentil 70 | Próximo da máxima | Reversão vendedora |
| Acima do percentil 70 | Próximo da mínima | Reversão compradora |

close_location_value maior ou igual a 0,80 representa fechamento próximo da máxima. Valor menor ou igual a 0,20 representa fechamento próximo da mínima.

## Horizonte Inicial

Avaliar retornos após a abertura de Londres em 1, 2 e 4 horas. O primeiro estágio deve testar a relação estatística. Regras de trade completas só devem ser criadas se existir um efeito consistente.

## Critério Inicial de Rejeição

Rejeitar se a direção esperada não permanecer estável entre subperíodos, regimes de volatilidade, custos e pequenas variações das fronteiras de percentil.

---

# H03 — Surpresa de Volatilidade Ajustada pelo Relógio Intradiário

## Status

~~~text
PROPOSED
~~~

## Hipótese

> Um candle representa uma verdadeira expansão de volatilidade somente quando seu range é anormal para aquele mesmo horário do dia, e não apenas quando é grande em comparação aos candles imediatamente anteriores.

## Racional

A volatilidade do Forex apresenta sazonalidade intradiária. Um candle normal da abertura de Londres pode parecer excepcional quando comparado apenas à sessão asiática.

Um filtro ajustado ao horário pode distinguir volatilidade esperada da sessão de uma surpresa real de volatilidade.

## Feature Primária

Para cada slot M15:

~~~text
volatility_surprise =
true_range_atual /
mediana(true_range do mesmo slot nos últimos 60 dias úteis)
~~~

Somente observações anteriores ao candle atual podem integrar a mediana.

## Experimento Primário

Comparar três modelos:

1. breakout sem filtro de volatilidade;
2. breakout filtrado por ATR rolling tradicional;
3. breakout filtrado por volatility_surprise.

Threshold candidato:

~~~text
volatility_surprise >= 1,50
~~~

## Métricas Principais

- retorno futuro condicional;
- hit rate;
- expectancy líquida;
- quantidade e turnover de trades;
- estabilidade por horário e ano;
- sensibilidade das janelas de 40, 60 e 80 dias.

## Uso Arquitetural Futuro

Se validada, a feature pode ser reutilizada em volatility breakout, time-series momentum, mean reversion, detecção simples de regimes e na análise dos choques H05/H06.

---

# H04 — Compressão Seguida por Choque de Preço e Atividade

## Status

~~~text
PROPOSED
~~~

## Hipótese

> Uma expansão de range após um período de compressão possui maior probabilidade de continuidade quando vem acompanhada de tick volume excepcional e fechamento próximo ao extremo do candle.

## Racional

Uma expansão isolada pode ser ruído. A combinação de compressão anterior, range anormal, aumento de atividade e fechamento direcionalmente eficiente pode representar uma mudança mais relevante no estado do mercado.

## Especificação Primária Candidata

Compressão:

~~~text
realized_range das últimas 16 barras
abaixo do percentil 25 dos últimos 60 dias
~~~

Choque:

~~~text
true_range acima do percentil 90
tick_volume acima do percentil 80 para o mesmo slot M15
~~~

Confirmação direcional:

~~~text
LONG:  close_location_value do candle >= 0,75
SHORT: close_location_value do candle <= 0,25
~~~

O sinal é gerado no fechamento do candle de choque e executado no próximo open disponível.

## Ablation Test Obrigatório

Testar separadamente:

1. somente compressão;
2. compressão + choque de range;
3. compressão + range + tick volume;
4. modelo completo com posição do fechamento.

A contribuição incremental de cada componente deve ser registrada.

## Critério Inicial de Rejeição

Rejeitar se o desempenho vier apenas do filtro de horário, não superar o breakout simples, desaparecer sob 1,5 × o custo base ou depender exclusivamente de poucos eventos extremos.

---

# H05 — Reversão após Choque sem Eficiência Direcional

## Status

~~~text
PROPOSED
~~~

## Hipótese

> Candles com range e tick volume excepcionalmente altos, mas corpo pequeno e sombras grandes, representam possível absorção ou exaustão e apresentam reversão de curto prazo.

## Feature Principal

~~~text
directional_efficiency =
abs(close - open) / (high - low)
~~~

Candles com high igual a low devem ser tratados explicitamente e nunca produzir divisão por zero.

## Especificação Primária Candidata

~~~text
true_range >= percentil 90 para o mesmo horário
tick_volume >= percentil 90 para o mesmo horário
directional_efficiency <= 0,25
~~~

Direção candidata:

~~~text
deslocamento anterior positivo → expectativa de reversão negativa
deslocamento anterior negativo → expectativa de reversão positiva
~~~

O deslocamento anterior deve ser definido previamente, por exemplo pelo retorno acumulado das quatro barras anteriores.

## Horizonte Inicial

Avaliar retornos futuros de 1, 2, 4 e 8 candles M15. Primeiro testar a previsão condicional; a transformação em trade deve ocorrer somente depois.

## Controles

- horário do dia;
- volatilidade e direção anteriores;
- proximidade de abertura de sessão;
- presença de gap;
- candles incompletos;
- assimetria entre eventos positivos e negativos.

---

# H06 — Continuação após Choque Eficiente

## Status

~~~text
PROPOSED
~~~

## Hipótese

> Um choque de preço e atividade com corpo grande e fechamento junto ao extremo possui continuidade de curto prazo, enquanto um choque ineficiente tende à reversão.

## Relação com H05

H05 e H06 devem ser avaliadas no mesmo experimento. O objetivo é determinar se o comportamento futuro depende apenas do tamanho do choque, do tick volume ou da eficiência direcional do candle.

## Especificação Primária Candidata

~~~text
true_range >= percentil 90 para o mesmo horário
tick_volume >= percentil 90 para o mesmo horário
directional_efficiency >= 0,70
~~~

Confirmação:

~~~text
candle positivo: close_location_value >= 0,90
candle negativo: close_location_value <= 0,10
~~~

Direção esperada:

~~~text
candle positivo eficiente → continuidade positiva
candle negativo eficiente → continuidade negativa
~~~

## Matriz Experimental

| Range | Tick volume | Eficiência | Hipótese |
|---|---|---|---|
| Alto | Alto | Baixa | Reversão |
| Alto | Alto | Alta | Continuação |
| Alto | Normal | Baixa | Controle |
| Alto | Normal | Alta | Controle |
| Normal | Alto | Baixa | Controle |
| Normal | Alto | Alta | Controle |

## Critério Inicial de Rejeição

Rejeitar a distinção H05/H06 se a eficiência direcional não adicionar poder explicativo ou econômico ao tamanho do range e ao horário.

---

# H07 — Reversão Parcial do Gap Semanal

## Status

~~~text
PROPOSED
LOW SAMPLE PRIORITY
~~~

## Hipótese

> Gaps entre o último candle disponível da sexta-feira e a primeira barra disponível da nova semana apresentam reversão parcial quando não são acompanhados por expansão persistente de atividade.

## Racional

O fim de semana cria descontinuidade real. Nem todo gap representa uma nova tendência; parte dele pode ser corrigida durante a normalização da liquidez. Entretanto, gaps podem refletir informação nova e custos elevados, exigindo teste conservador.

## Definição do Evento

~~~text
weekly_gap =
first_open_new_week - last_close_previous_week

normalized_gap =
abs(weekly_gap) / ATR(H1, 14)
~~~

Threshold candidato:

~~~text
normalized_gap >= 0,50
~~~

## Variáveis

- tamanho e direção do gap;
- primeira barra realmente disponível;
- range e fechamento da primeira hora;
- tick volume relativo;
- percentual do gap fechado;
- tempo necessário para fechamento parcial;
- regime de volatilidade anterior.

## Horizontes

Avaliar 1, 4, 8 e 16 horas.

## Regras de Execução

- não criar candles durante o fim de semana;
- não assumir fill no fechamento de sexta-feira;
- usar o primeiro preço disponível;
- aplicar spread e slippage conservadores;
- respeitar gaps através de stops;
- não tratar o fechamento integral do gap como garantido.

## Limitação Estatística

O número de eventos semanais é pequeno. Reportar intervalo de confiança, quantidade exata de eventos, análise leave-one-year-out, impacto dos maiores gaps e teste sem os cinco maiores eventos.

A hipótese tem prioridade inferior até existir infraestrutura robusta para eventos raros.

---

## 4. Priorização Recomendada

| Prioridade | Hipótese | Justificativa |
|---:|---|---|
| 1 | H03 — Surpresa de volatilidade intradiária | Feature reutilizável em várias estratégias |
| 2 | H05/H06 — Choques eficientes e ineficientes | Simples, causal e compatível com OHLC + tick volume |
| 3 | H01 — Falso rompimento asiático | Complementa o Asian Range Breakout |
| 4 | H02 — Handoff Ásia–Londres | Explora estrutura intradiária sem dados externos |
| 5 | H04 — Compressão + atividade | Promissora, mas próxima do volatility breakout |
| 6 | H07 — Gap semanal | Menor amostra e maior sensibilidade a custos |

---

## 5. Protocolo Experimental Comum

Antes do primeiro backtest, cada hipótese deve possuir um registro imutável contendo:

~~~text
hypothesis_id
version
status
rationale
expected_direction
dataset_version
timeframe
session_definition
features
primary_parameters
allowed_sensitivity_range
entry_rule
exit_rule
cost_model
risk_model
development_period
validation_period
oos_period
rejection_criteria
git_commit
~~~

## Divisão Temporal Candidata

~~~text
Development: 2015–2020
Validation:  2021–2023
Lockbox OOS: 2024–2026
~~~

O período 2024–2026 somente poderá ser chamado de lockbox se ainda não tiver sido consultado para selecionar regras ou parâmetros.

Caso já tenha sido explorado:

- não declarar OOS intocado;
- utilizar validação rolling ou walk-forward;
- registrar a contaminação metodológica;
- reservar dados futuros para nova validação.

## Custos

Testes mínimos:

~~~text
custo base
1,5 × custo base
2,0 × custo base
~~~

O spread histórico do candle não deve ser promovido automaticamente a CostModel oficial.

## Robustez Mínima

- pequenas variações dos parâmetros;
- análise por ano e subperíodo;
- long e short separados;
- horários e sessões separados;
- regimes de volatilidade;
- quantidade e concentração de trades;
- impacto dos maiores trades;
- comparação com baseline simples;
- teste com custos;
- validação fora da amostra.

Não procurar somente o melhor parâmetro. Procurar regiões estáveis.

## Métricas Mínimas

Além de retorno e Sharpe:

- expectancy por trade;
- hit rate e payoff médio;
- profit factor;
- maximum drawdown;
- turnover e exposição;
- duração e quantidade de trades;
- custos totais;
- retorno antes e depois de custos;
- concentração temporal;
- estabilidade entre subperíodos.

## Multiple Testing

Cada variação experimentada deve ser contabilizada. Não testar centenas de combinações, selecionar apenas a melhor e reportá-la como hipótese original.

Métodos como Deflated Sharpe Ratio, PBO e CSCV podem ser adicionados após a infraestrutura de experiment tracking estar estabilizada.

---

## 6. Requisitos de Implementação

As hipóteses não devem ser implementadas antes de existir suporte confiável para:

- clock do BacktestEngine;
- sincronização temporal M15/H1/H4;
- execução no próximo open;
- Signal, Order, Fill, Position e Trade;
- CostModel independente;
- trade ledger;
- métricas reproduzíveis;
- identificação de dataset e commit;
- logs de experimento.

A Strategy deve apenas produzir intenção. Ela não deve acessar diretamente o broker, enviar ordens, calcular custos, controlar o relógio, dimensionar risco global ou consultar candles futuros.

---

## 7. Referências de Motivação

As referências motivam a investigação, mas não provam que as hipóteses serão lucrativas no dataset do projeto.

1. Ito, T.; Hashimoto, Y. Intra-day Seasonality in Activities of the Foreign Exchange Markets: Evidence from the Electronic Broking System. NBER Working Paper 12413.  
   https://www.nber.org/papers/w12413

2. Andersen, T. G.; Bollerslev, T.; Diebold, F. X.; Vega, C. Real-Time Price Discovery in Foreign Exchange. NBER Working Paper 8959.  
   https://www.nber.org/papers/w8959

3. Ito, T.; Hashimoto, Y. Price Impacts of Deals and Predictability of the Exchange Rate Movements.  
   https://users.nber.org/~confer/2006/ease06/ito.pdf

4. Moskowitz, T. J.; Ooi, Y. H.; Pedersen, L. H. Time Series Momentum.  
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463

---

## 8. Regra Final

> Estas hipóteses são perguntas a serem testadas, não resultados a serem defendidos.

Uma hipótese somente poderá avançar quando especificação prévia, implementação causal, custos, robustez e validação forem suficientes para distinguir um possível edge de ruído, data snooping ou erro de backtest.

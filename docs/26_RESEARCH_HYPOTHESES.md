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


---

# 9. Registro do Programa (2026-08-12)

## Abertura

- **Decisao**: abrir novo programa de pesquisa (docs/25 §11 cumprido:
  v0.6.1..v0.6.4 DONE; busca de edge baseline ENCERRADA, docs/24).
- **Hipotese ativa inicial**: H03 (prioridade 1 do §4 deste documento).
- **Commit do programa**: integracao da branch
  `agent/document-research-hypotheses` (merge `2a94589`) + renumeracao
  do documento para docs/26 (docs/12 ja era STRATEGY_RESEARCH).

## Periodos (decisao registrada)

O §5 deste documento propoe "Divisao Temporal Candidata"
(DEV 2015-2020 / VAL 2021-2023 / OOS 2024-2026). DECISAO: os
periodos FORMAIS pre-registrados da plataforma (research/periods.py)
sao mantidos, por serem a infraestrutura ja validada e pre-registrada
antes de qualquer resultado:

```text
DEVELOPMENT  2015-01-01 .. 2021-01-01
VALIDATION   2021-01-01 .. 2024-01-01
OOS          2024-01-01 .. 2027-01-01   (CONTAMINADO - ver abaixo)
```

## Politica OOS (contaminacao metodologica registrada)

O periodo 2024-2027 foi consultado UMA vez (2026-08-10, fechamento do
baseline, com `--allow-oos` e evento logado - docs/15 e docs/18).
Portanto:

- **NAO sera declarado "OOS intocado"** para este programa;
- validacao primaria = **walk-forward** (harness existente,
  research/walkforward.py) + validacao temporal DEV/VAL;
- o periodo 2024-2027 so pode ser usado como CONFIRMACAO final, com
  `--allow-oos` + evento logado, nunca para selecao de regras;
- dados futuros (apos 2026-08) serao reservados como validacao limpa
  quando existirem.

## Custos e robustez

- Testes minimos: custo base, 1.5x, 2.0x (harness cost stress).
- Robustez minima do §5: sensibilidade local, por ano/subperiodo,
  long/short separados, concentracao, comparacao com baseline.

---

# 10. Registro Imutavel - H03 (primeira versao)

```text
hypothesis_id:            H03
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
rationale:                a volatilidade Forex tem sazonalidade intradiaria;
                          um candle "grande" vs os vizinhos pode ser normal para
                          o horario; o ajuste por slot M15 separa surpresa real
                          de volatilidade esperada da sessao
expected_direction:       retorno futuro condicional positivo apos
                          volatility_surprise >= 1.50 (a verificar por horario)
dataset_version:          EURUSD M15 parquet 2015-01-01..2026-08-10
                          (sha256 no report do runner)
timeframe:                M15 (slots de 15min)
session_definition:       slots M15 por horario UTC (sessoes calculadas com
                          Europe/London e America/New_York, nunca offset fixo)
features:                 volatility_surprise =
                          true_range(candle) /
                          mediana(true_range mesmo slot, ultimos 60 dias uteis,
                          somente candles fechados anteriores)
primary_parameters:       threshold >= 1.50
                          janela 60 dias uteis
allowed_sensitivity:      janelas 40, 60, 80 dias (declarado ANTES dos
                          resultados; variar um parametro por vez)
entry_rule:               ESTAGIO 1 = previsao condicional (retorno futuro
                          1/2/4/8 candles), SEM trade
                          ESTAGIO 2 (so se efeito existir) = trade completo
exit_rule:                a definir no estagio 2, pre-registrada
cost_model:               base (2.0/0.5/3.5) e estresse 1.5x / 2.0x
risk_model:               FixedSizeRiskGate 0.01 (estagio 2)
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado - confirmacao
                          final com --allow-oos + evento)
rejection_criteria:       rejeitar se: efeito nao estavel entre subperiodos/
                          horarios/anos; nao sobreviver a 1.5x custo; depender
                          de parametro isolado; sem edge vs breakout simples
git_commit:               merge 2a94589 + renumeracao docs/26
```

## Experimento primario (comparacao de 3 modelos)

```text
1. breakout sem filtro de volatilidade
2. breakout filtrado por ATR rolling tradicional
3. breakout filtrado por volatility_surprise (H03)
```

Metricas: retorno futuro condicional, hit rate, expectancy liquida,
turnover, estabilidade por horario/ano, sensibilidade 40/60/80.


---

# 11. Resultado H03 - Estagio 1 (2026-08-12) — REJECTED

## Execucao

- Feature `volatility_surprise` implementada em `research/features.py`
  (pura, causal, 11 testes) e experimento em `research/h03_experiment.py`.
- Dataset: EURUSD M15 2015-01-02..2026-08-10 (288,223 candles),
  threshold 1.50, janelas de sensibilidade pre-registradas 40/60/80.
- Etapa 1 (previsao condicional, SEM trade): retorno futuro 1/2/4/8
  candles apos sinal vs baseline sem filtro vs ATR rolling 60.

## Resultados (mean fwd return, overall)

| modelo | h1 | h8 | eventos |
|---|---|---|---|
| no_filter | 0.000% | 0.000% | 288k |
| rolling_atr | 0.000% | -0.002% | 58,146 |
| volatility_surprise (60) | 0.000% | 0.000% | 54,711 |
| volatility_surprise (40) | 0.000% | 0.000% | 54,338 |
| volatility_surprise (80) | 0.000% | 0.000% | 55,057 |

## Por ano e por hora

- Por ano (h8): sinal oscila entre -0.011% e +0.012% sem direcao
  estavel (7/12 anos positivos, magnitudes ~0.005%).
- Por hora UTC (h8): agregado nulo. Unico destaque: slot 00:00 UTC
  com +0.018% (61.3% pos, 2,691 eventos).

## Decisao

**H03 REJEITADA (estagio 1)**, conforme criterios pre-registrados
(docs/26 §10): o retorno condicional medio e indistinguivel de zero
nas 3 janelas; o destaque 00:00 representa ~1.98 pips BRUTOS por
evento, abaixo do custo round-trip de 3.7 pips (nao sobreviveria a
custos conservadores), e foi identificado por inspecao de 24 slots
(risco de multiple testing — nao e declarado hipotese nova).

Feature mantida no codigo como ferramenta reutilizavel
(volatility_surprise e reutilizavel em H04/H05/H06 e futuros).

## Proxima hipotese ativa

H05/H06 (prioridade 2, docs/26 §4): choques eficientes e ineficientes
(directional_efficiency). Requer pre-registro antes de qualquer
backtest (protocolo §5).


---

# 12. Registro Imutavel - H05/H06 (primeira versao, pre-backtest)

```text
hypothesis_id:            H05/H06 (avaliadas no MESMO experimento,
                          docs/26 H05/H06; decisoes conjuntas)
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
rationale:                choque de preco+atividade com corpo pequeno e
                          sombras grandes (DE baixa) = absorcao/exaustao ->
                          reversao curto prazo (H05); corpo grande com
                          fechamento no extremo (DE alta + CLV) = continuacao
                          (H06). A eficiencia direcional e o discriminatorio.
expected_direction:       H05: reversao vs deslocamento anterior
                          H06: continuacao na direcao do candle eficiente
dataset_version:          EURUSD M15 parquet 2015-01-02..2026-08-10
timeframe:                M15
session_definition:       slots M15 por horario UTC (sessoes com timezones
                          reais, nunca offset fixo)
features:                 directional_efficiency = abs(close-open)/(high-low);
                          high == low -> sem sinal (nunca divisao por zero)
                          true_range_percentile: percentil do TR no mesmo
                          slot, janela 60 dias uteis, somente anteriores
                          tick_volume_percentile: idem para tick_volume
primary_parameters:       TR >= p90 do slot
                          TV >= p90 do slot
                          H05: DE <= 0.25 (candle ineficiente)
                          H06: DE >= 0.70 E confirmacao
                          (CLV >= 0.90 positivo / <= 0.10 negativo)
                          deslocamento anterior = retorno acumulado das
                          4 barras anteriores (H05)
allowed_sensitivity:      percentis p85 / p90 / p95 (declarado ANTES;
                          variar um parametro por vez)
entry_rule:               ESTAGIO 1 = previsao condicional (fwd 1/2/4/8
                          candles), SEM trade; metricas assinadas
                          (H05: reversao vs deslocamento anterior;
                          H06: continuacao vs direcao do candle)
exit_rule:                a definir no estagio 2, pre-registrada
cost_model:               base (2.0/0.5/3.5) + estresse 1.5x / 2.0x (estagio 2)
risk_model:               FixedSizeRiskGate 0.01 (estagio 2)
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado -
                          confirmacao final com --allow-oos + evento)
rejection_criteria:       rejeitar H05/H06 se a eficiencia direcional NAO
                          adicionar poder explicativo/economico vs tamanho
                          do range + horario (celulas de controle); se nao
                          estavel entre subperiodos; se nao sobreviver a
                          1.5x custo (estagio 2); se depender de poucos
                          eventos extremos
git_commit:               commit do pre-registro (docs/26 §12)
```

## Matriz experimental (6 celulas, docs/26 H05/H06)

```text
| range | tick vol | eficiencia | rotulo     |
|---|---|---|---|
| alto  | alto     | baixa      | H05 (reversao)   |
| alto  | alto     | alta       | H06 (continuacao)|
| alto  | normal   | baixa      | controle         |
| alto  | normal   | alta       | controle         |
| normal| alto     | baixa      | controle         |
| normal| alto     | alta       | controle         |
```

Metricas por celula e horizonte: retorno assinado medio, positive rate,
eventos, decomposicao por ano. Comparacao H05/H06 vs controles.


---

# 13. Resultado H05/H06 - Estagio 1 (2026-08-12) — REJECTED

## Execucao

- Features: `directional_efficiency` + `slot_percentile` em
  `research/features.py` (puras, causais, 8 testes novos) e
  experimento `research/h05_h06_experiment.py`.
- Dataset: EURUSD M15 2015-01-02..2026-08-10 (288,223 candles),
  p90 por slot (sensibilidade pre-registrada p85/p90/p95), janela
  60 slots, DE <= 0.25 (H05) / DE >= 0.70 + CLV confirmacao (H06).
- Etapa 1 (previsao condicional, SEM trade): retorno assinado
  (H05: reversao vs deslocamento 4 barras; H06: continuacao vs
  direcao do candle) em h1/2/4/8.

## Resultados (signed mean %, p90)

| celula | h1 | h4 | h8 | eventos | rotulo |
|---|---|---|---|---|---|
| H05_reversal | -0.002% | -0.000% | +0.003% | 2,999 | alvo |
| H06_continuation | -0.005% | -0.005% | -0.004% | 3,296 | alvo |
| ctrl range alto/tick normal/DE baixa | -0.003% | -0.000% | -0.001% | 1,426 | controle |
| ctrl range alto/tick normal/DE alta | -0.004% | -0.006% | -0.007% | 7,461 | controle |
| ctrl range normal/tick alto/DE baixa | +0.001% | +0.000% | -0.001% | 6,615 | controle |
| ctrl range normal/tick alto/DE alta | -0.003% | -0.004% | -0.006% | 3,339 | controle |

Sensibilidade: p85 (H05 ~0, H06 -0.005% a -0.006%) e p95
(H05 ~0, H06 -0.003% a -0.006%) — mesmo padrao.

## Por ano (h8 signed)

- H05: oscila entre -0.037% e +0.024% com tres inversoes de sinal
  (2015-16 neg, 2017-20 pos, 2021-22 neg, 2023-26 pos) — sem
  direcao estavel.
- H06: negativo ou ~0 em todos os anos (-0.020% em 2016;
  2021+ aproximadamente zero) — o efeito de continuacao NAO existe;
  quando muito, ligeiramente contrario a hipotese.

## Decisao

**H05/H06 REJEITADAS (estagio 1)**, conforme criterios
pre-registrados (docs/26 §12):

- a eficiencia direcional NAO adiciona poder explicativo/economico:
  os controles com DE alta apresentam o mesmo padrao (negativo) da
  celula H06, e a celula H05 e indistinguivel de zero;
- sinais instaveis entre subperiodos (H05 inverte 3x; H06 negativo
  -> ~0);
- magnitudes <= 0.037%, na escala do custo round-trip (3.7 pips),
  sem consistencia para sobreviver a 1.5x custo no estagio 2.

Features mantidas no codigo como ferramentas reutilizaveis
(directional_efficiency e slot_percentile servem H01/H02/H04).

## Proxima hipotese ativa

H01 (prioridade 3, docs/26 §4): falso rompimento da faixa asiatica.
Pre-registro obrigatorio antes de qualquer backtest (protocolo §5).


---

# 14. Registro Imutavel - H01 (primeira versao, pre-backtest)

```text
hypothesis_id:            H01
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
rationale:                rompimento da faixa asiatica que nao permanece
                          fora (fecha dentro em ate 2 candles) indica
                          rejeicao/absorcao -> reversao em direcao ao
                          midpoint da faixa
expected_direction:       falso rompimento superior -> retorno negativo
                          falso rompimento inferior -> retorno positivo
dataset_version:          EURUSD M15 parquet 2015-01-02..2026-08-10
                          + H1 processado (ATR)
timeframe:                M15 (evento) + H1 (ATR)
session_definition:       faixa asiatica = candles M15 com hora em
                          Europe/London [00:00, 07:00) (zoneinfo, DST
                          correto; nunca offset fixo)
features:                 asian_range_high/low/mid do dia
                          atr_h1_14 = media TR dos 14 H1 fechados antes
                          das 07:00 London (causal)
                          rompimento: high > range_high + buffer*ATR
                          (superior) ou low < range_low - buffer*ATR
                          (inferior), apos 07:00 London
                          confirmacao: primeiro candle em {N, N+1, N+2}
                          que feche DENTRO da faixa
primary_parameters:       buffer = 0.15 x ATR(H1,14)
                          max 2 candles apos o rompimento para confirmar
                          direcao: superior -> SHORT; inferior -> LONG
                          saida inicial (estagio 2): alvo midpoint,
                          stop extremo do rompimento + buffer
allowed_sensitivity:      buffer 0.10 / 0.15 / 0.20 (declarado ANTES;
                          variar um parametro por vez)
entry_rule:               ESTAGIO 1 = previsao condicional: retorno
                          assinado (direcao esperada) em 1/2/4/8 candles
                          apos o fechamento da confirmacao + taxa de
                          alcance do midpoint em 8 candles + retorno ate
                          a borda oposta; SEM trade
exit_rule:                estagio 2 (so se efeito existir): alvo
                          midpoint, stop extremo + buffer, custos
cost_model:               base (2.0/0.5/3.5) + estresse 1.5x / 2.0x (estagio 2)
risk_model:               FixedSizeRiskGate 0.01 (estagio 2)
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado -
                          confirmacao final com --allow-oos + evento)
rejection_criteria:       rejeitar se: efeito depender de um unico
                          subperiodo; funcionar somente em buffer muito
                          especifico (ilha de parametro); nao sobreviver
                          a custos conservadores (estagio 2); retorno
                          assinado medio <= 0 no estagio 1
git_commit:               commit do pre-registro (docs/26 §14)
```

## Subgrupos pre-registrados (estagio 1)

```text
tamanho da faixa:   percentil < 30 (comprimida) vs > 70 (larga)
duracao fora:       confirmacao no proprio candle de rompimento (0)
                    vs 1-2 candles depois
lado:               superior vs inferior
```


---

# 15. Resultado H01 - Estagio 1 (2026-08-12) — REJECTED

## Execucao

- Experimento `research/h01_experiment.py`: faixa asiatica = M15
  com hora Europe/London [00:00, 07:00) (zoneinfo, DST correto);
  ATR(H1,14) dos 14 H1 fechados antes das 07:00 London (Wilder TR,
  causal); rompimento = high > range_high + buffer*ATR (superior)
  ou low < range_low - buffer*ATR (inferior); confirmacao = primeiro
  candle em {N, N+1, N+2} fechando DENTRO da faixa; um evento por
  lado por dia (sem dupla contagem de episodios).
- Dataset: EURUSD M15 2015-01-02..2026-08-10 + H1 processado.
- Estagio 1: retorno assinado h1/2/4/8 apos o fechamento da
  confirmacao (superior -> espera reversao negativa), por ano, por
  lado; taxa de alcance do midpoint em 8 barras.

## Resultados (signed mean %, buffer 0.15, n=3,956 eventos)

| h | signed% | pos% |
|---|---|---|
| 1 | -0.001% | 49.29% |
| 2 | +0.000% | 50.03% |
| 4 | +0.001% | 50.76% |
| 8 | +0.003% | 51.11% |

- Midpoint touch rate (8 barras): 1.00 — o midpoint e SEMPRE tocado
  em 2 horas; metrica nao discrimina.
- Sensibilidade: buffer 0.10 (n=4,074, h8 +0.004%) e 0.20
  (n=3,828, h8 +0.003%) — mesmo padrao, sem ilha de parametro.
- Por ano (h8): oscila entre -0.009% e +0.015% com quatro
  inversoes de sinal (2015 neg; 2017/2019/2020/2024 pos;
  2021-2023 neg) — sem direcao estavel.
- Por lado (h8): upper +0.002%, lower +0.004% — ambos levemente
  POSITIVOS, i.e., o rompimento continua na direcao (oposto da
  reversao esperada pela hipotese).

## Decisao

**H01 REJEITADA (estagio 1)**, conforme criterios pre-registrados
(docs/26 §14):

- retorno assinado medio ~0 em todos os horizontes e buffers, e
  ligeiramente POSITIVO no h8 (continuacao, nao reversao);
- efeito instavel entre subperiodos (4 inversoes de sinal por ano);
- magnitude <= 0.015% por ano (global ~0.004% ~ 0.4 pips) — muito
  abaixo do custo round-trip (3.7 pips); estagio 2 nao aberto por
  ausencia de efeito no estagio 1.

## Proxima hipotese ativa

H02 (prioridade 3, docs/26 §4): continuacao apos handoff
Asia-Londres. Pre-registro obrigatorio antes de qualquer backtest
(protocolo §5).


---

# 16. Registro Imutavel - H02 (primeira versao, pre-backtest)

```text
hypothesis_id:            H02
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
rationale:                o mesmo retorno asiatico pode representar
                          deslocamento eficiente ainda nao saturado
                          (faixa comprimida + fechamento no extremo ->
                          continuacao em Londres) ou movimento ja
                          excessivo (faixa larga -> reversao)
expected_direction:       faixa < p30 e CLV >= 0.80 -> fwd positivo
                          faixa < p30 e CLV <= 0.20 -> fwd negativo
                          faixa > p70 e CLV >= 0.80 -> fwd negativo
                          faixa > p70 e CLV <= 0.20 -> fwd positivo
dataset_version:          EURUSD M15 parquet 2015-01-02..2026-08-10
timeframe:                M15 (evento) — sessao asiatica + abertura Londres
session_definition:       sessao asiatica = M15 com hora Europe/London
                          [00:00, 07:00) (zoneinfo, DST correto);
                          fechamento asiatico = close da ultima barra
                          da sessao; abertura Londres = 07:00 London
features:                 asian_return = close_fim / open_inicio - 1
                          asian_range = high - low da sessao
                          asian_range_percentile = percentil empirico
                          do range vs os 60 dias uteis ANTERIORES
                          (causal; janela movel)
                          close_location_value (CLV) = (close - low) /
                          (high - low) da ultima barra asiatica;
                          high == low -> sem sinal
                          distance_to_high/low = distancia normalizada
                          ao extremo (analise)
                          relative_tick_volume = soma tick_volume da
                          sessao / mediana dos 60 dias anteriores
primary_parameters:       fronteiras de percentil p30/p70 (janela 60)
                          CLV 0.80/0.20
                          fwd: 1/2/4 horas apos 07:00 London
                          (4/8/16 candles M15)
allowed_sensitivity:      fronteiras p25/p35 e p65/p75; CLV 0.75/0.85 e
                          0.15/0.25 (declarado ANTES; variar um por vez)
entry_rule:               ESTAGIO 1 = relacao estatistica: retorno
                          assinado medio por grupo e horizonte (direcao
                          esperada acima); SEM trade
exit_rule:                estagio 2 (so se efeito consistente):
                          regras de trade completas pre-registradas
cost_model:               base (2.0/0.5/3.5) + estresse 1.5x / 2.0x (estagio 2)
risk_model:               FixedSizeRiskGate 0.01 (estagio 2)
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado -
                          confirmacao final com --allow-oos + evento)
rejection_criteria:       rejeitar se a direcao esperada NAO permanecer
                          estavel entre subperiodos (anos), regimes de
                          volatilidade (ATR por ano), fronteiras de
                          percentil e CLV; ou se o retorno assinado
                          medio por grupo for <= 0 no estagio 1
git_commit:               commit do pre-registro (docs/26 §16)
```


---

# 17. Resultado H02 - Estagio 1 (2026-08-12) — REJECTED

## Execucao

- Experimento `research/h02_experiment.py`: sessao asiatica =
  M15 Europe/London [00:00, 07:00) (zoneinfo); asian_return/range;
  percentil empirico do range vs 60 dias uteis anteriores (causal);
  CLV da ultima barra asiatica; 4 grupos mutuamente exclusivos
  (p30/p70 x CLV 0.20/0.80); retorno assinado 1/2/4 horas apos
  07:00 London (a partir do close da ultima barra asiatica).
- Dataset: EURUSD M15 2015-01-02..2026-08-10 (3,363 sessoes).
- Sensibilidade pre-registrada: p25/p35, p65/p75, CLV 0.75/0.85,
  CLV 0.15/0.25 (uma fronteira por vez).

## Resultados (signed mean %, fronteiras base p30/p70 CLV 0.2/0.8)

| grupo | h1 | h2 | h4 | n |
|---|---|---|---|---|
| continuation_up (comprimida + close high) | -0.013% | -0.016% | -0.035% | 168 |
| continuation_down (comprimida + close low) | -0.006% | -0.011% | -0.000% | 185 |
| reversal_down (larga + close high) | -0.007% | -0.003% | +0.011% | 302 |
| reversal_up (larga + close low) | +0.001% | +0.003% | +0.000% | 198 |

Sensibilidade: continuation_up NEGATIVO em todas as variacoes
(-0.005% a -0.038%) — consistente na direcao OPOSTA da hipotese.
reversal_down h4 positivo em todas (+0.007% a +0.023%) mas
negativo em h1/h2. Demais grupos ~0.

## Por ano (h4 signed)

- continuation_up: negativo em 10 de 12 anos (2015 -0.112%,
  2026 -0.115%; unicas excecoes 2016/2017 +0.019%) — consistente,
  porem OPOSTO a hipotese (nao ha continuacao compradora; o
  padrao real e reversao).
- continuation_down: misto (-0.059% a +0.112%), instavel.
- reversal_down: misto (2016 +0.087% vs 2025 -0.045%), instavel.
- reversal_up: misto (-0.067% a +0.050%), instavel.
- Amostras por grupo/ano: 5-31 eventos; magnitudes <= 0.12% —
  na escala ou abaixo do custo.

## Decisao

**H02 REJEITADA (estagio 1)**, conforme criterios pre-registrados
(docs/26 §16):

- a direcao esperada NAO permanece estavel entre subperiodos: 3 de
  4 grupos com sinais mistos por ano;
- continuation_up falha o criterio de retorno assinado medio > 0
  (e negativo em todos os cenarios de fronteira e 10/12 anos);
- reversal_down, unico grupo com sinal esperado no h4, e instavel
  entre horizontes (h1/h2 negativos) e entre anos;
- amostras pequenas e magnitudes <= 0.12% (custo round-trip 3.7
  pips ~ 0.034% com alavancagem; sem efeito economico) — estagio 2
  nao aberto.

## Nota de pesquisa (nao e hipotese nova)

O padrao mais consistente encontrado foi o OPOSTO de H02 no grupo
comprimida+high: reversao apos faixa comprimida com fechamento no
extremo (continuation_up negativo em 10/12 anos). NAO sera elevado
a hipotese: sinal nao pre-registrado, sujeito a multiple testing
(4 grupos x 4 cenarios de fronteira x 3 horizontes).

## Proxima hipotese ativa

H04 (prioridade 3, docs/26 §4): compressao + atividade. Pre-registro
obrigatorio antes de qualquer backtest (protocolo §5).


---

# 18. Registro Imutavel - H04 (primeira versao, pre-backtest)

```text
hypothesis_id:            H04
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
rationale:                expansao isolada pode ser ruido; compressao
                          anterior + range anormal + aumento de atividade
                          + fechamento direcionalmente eficiente = mudanca
                          de estado mais relevante (continuidade)
expected_direction:       LONG quando CLV >= 0.75 no candle de choque
                          SHORT quando CLV <= 0.25
                          continuacao na direcao do fechamento
dataset_version:          EURUSD M15 parquet 2015-01-02..2026-08-10
timeframe:                M15
session_definition:       slots M15 por horario UTC (mesmo padrao H03)
features:                 realized_range_16 = high(max) - low(min) das
                          ultimas 16 barras M15 (4h), avaliado no
                          fechamento da barra atual
                          compression_pct = slot_percentile do
                          realized_range_16 vs 60 slots anteriores do
                          mesmo horario (causal)
                          shock_range_pct = slot_percentile do true_range
                          vs 60 slots anteriores
                          activity_pct = slot_percentile do tick_volume
                          vs 60 slots anteriores
                          CLV = (close - low)/(high - low); high==low ->
                          sem sinal
primary_parameters:       compressao: realized_range_16 abaixo do
                          percentil 25 (mesmo slot, janela 60)
                          choque: true_range acima do percentil 90
                          atividade: tick_volume acima do percentil 80
                          confirmacao: CLV >= 0.75 (LONG) / <= 0.25 (SHORT)
                          sinal no fechamento do candle de choque
allowed_sensitivity:      percentis de compressao p20/p25/p30 e choque
                          p85/p90/p95 (declarado ANTES; variar um por vez)
entry_rule:               ESTAGIO 1 = previsao condicional: retorno
                          assinado (direcao do sinal) em 1/2/4/8 candles
                          a partir do CLOSE do candle de choque; SEM trade
ablation:                 obrigatorio, 4 modelos:
                          A1 = somente compressao
                          A2 = compressao + choque de range
                          A3 = compressao + range + tick volume
                          A4 = completo (compressao + range + TV + CLV)
                          controle: breakout simples (range alto sem
                          compressao, sem TV, sem CLV)
exit_rule:                estagio 2 (so se efeito consistente no A4 e
                          ablation incremental): regras de trade
                          pre-registradas
cost_model:               base (2.0/0.5/3.5) + estresse 1.5x / 2.0x (estagio 2)
risk_model:               FixedSizeRiskGate 0.01 (estagio 2)
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado -
                          confirmacao final com --allow-oos + evento)
rejection_criteria:       rejeitar se: o ganho vier apenas do filtro de
                          horario (checar distribuicao por hora); A4 nao
                          superar o controle de breakout simples; o efeito
                          sumir sob 1.5x custo (estagio 2); depender de
                          poucos eventos extremos (top 1% dos retornos);
                          retorno assinado medio <= 0 no estagio 1
git_commit:               commit do pre-registro (docs/26 §18)
```


---

# 19. Registro Imutavel - H07 (primeira versao, pre-backtest)

```text
hypothesis_id:            H07
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
rationale:                o fim de semana cria descontinuidade real; nem
                          todo gap representa tendencia nova — parte pode
                          ser corrigida na normalizacao da liquidez
expected_direction:       gap positivo (abre acima) -> reversao parcial
                          (retorno negativo); gap negativo -> retorno
                          positivo
dataset_version:          EURUSD M15 parquet 2015-01-02..2026-08-10
                          + H1 processado (ATR)
timeframe:                M15 (primeira barra da semana) + H1 (ATR)
session_definition:       semana = ISO year-week das barras M15 UTC;
                          NAO criar candles de fim de semana: primeira
                          barra realmente disponivel da nova semana e
                          ultima barra realmente disponivel da anterior
features:                 weekly_gap = first_open_new_week -
                          last_close_previous_week
                          normalized_gap = abs(weekly_gap) / ATR(H1,14)
                          (ATR dos 14 H1 fechados antes da primeira
                          barra da nova semana — causal)
primary_parameters:       normalized_gap >= 0.50
                          fwd: 1/4/8/16 horas a partir do first_open
                          reversao: signed = -sign(gap) * fwd
allowed_sensitivity:      thresholds 0.40 / 0.50 / 0.60 (declarado
                          ANTES; variar um por vez)
entry_rule:               ESTAGIO 1 = previsao condicional: retorno
                          assinado + fracao do gap fechado por horizonte;
                          SEM trade. NUNCA assumir fill no fechamento de
                          sexta; usar o primeiro preco disponivel.
exit_rule:                estagio 2 (so se efeito consistente):
                          regras de trade pre-registradas com custos
                          conservadores (gaps atravessam stops)
cost_model:               base (2.0/0.5/3.5) + estresse 1.5x / 2.0x
                          (estagio 2) — spread/slippage conservadores
risk_model:               FixedSizeRiskGate 0.01 (estagio 2)
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado -
                          confirmacao final com --allow-oos + evento)
statistical_limits:       amostra pequena (semanas ~ 500-600): reportar
                          n EXATO por threshold, intervalo de confianca
                          (bootstrap), leave-one-year-out, impacto dos
                          maiores gaps e teste SEM os 5 maiores
rejection_criteria:       rejeitar se: retorno assinado medio <= 0; o
                          efeito desaparecer no leave-one-year-out ou sem
                          os 5 maiores gaps; o retorno medio nao cobrir
                          os custos conservadores (estagio 2)
git_commit:               commit do pre-registro (docs/26 §19)
```


---

# 20. Resultado H04 - Estagio 1 (2026-08-12) — REJECTED

## Execucao

- Experimento `research/h04_experiment.py`: realized_range_16 =
  high-low das ultimas 16 barras M15; percentis por slot (60 slots,
  causais): compressao p25, choque de range p90, atividade p80;
  CLV 0.75/0.25; ablation obrigatorio A1 (compressao), A2 (+range),
  A3 (+TV), A4 (completo + CLV) + controle CTRL (breakout simples
  sem compressao); retorno assinado (direcao do candle) h1/2/4/8.
- Dataset: EURUSD M15 288,223 candles.

## Resultados (signed mean %, h8)

| modelo | h8 signed | n | pos% |
|---|---|---|---|
| A1 compressao | -0.001% | 75,629 | 47.8% |
| A2 + range | -0.000% | 1,825 | 46.0% |
| A3 + atividade | +0.005% | 694 | 47.6% |
| A4 completo | +0.009% | 439 | 49.0% |
| CTRL breakout simples | -0.002% | 32,174 | 47.9% |

- A4 h1 = -0.003% (pior que CTRL h1 -0.002%); pos < 50% em todos
  com media > 0 no A4 = cauda (poucos retornos grandes positivos).
- Por ano (A4 h8): 6 positivos / 6 negativos (2017 -0.036% vs
  2023 +0.060%) — instavel.
- Por hora (A4 h8): n de 6 a 23 por slot, sinais alternando
  (+0.085% 16:00 vs -0.067% 21:00) — ruido, nao efeito de horario.

## Decisao

**H04 REJEITADA (estagio 1)**: A4 nao supera o controle de breakout
simples de forma consistente; efeito dependente de eventos extremos
(pos < 50% com media positiva); ablation sem melhora monotona;
instavel por ano.

---

# 21. Resultado H07 - Estagio 1 (2026-08-12) — REJECTED

## Execucao

- Experimento `research/h07_experiment.py`: gap semanal =
  first_open_new_week - last_close_previous_week (sem criar candles
  de fim de semana); normalized = |gap|/ATR(H1,14) causal >= 0.50;
  retorno a partir do primeiro open disponivel; h1/4/8/16; reversao:
  signed = -sign(gap)*fwd; bootstrap CI 95% (10k); leave-one-year-out;
  sem os 5 maiores gaps.
- Dataset: EURUSD M15 + H1 processado; 301 eventos (threshold 0.50).

## Resultados

| h | signed | pos% | fração do gap fechada |
|---|---|---|---|
| 1 | +0.031% | 66.78% | +14.0% |
| 4 | +0.025% | 56.81% | +10.4% |
| 8 | +0.014% | 54.49% | +2.9% |
| 16 | +0.012% | 48.17% | -6.6% |

- h8 bootstrap CI 95%: [-0.009%, +0.037%] (contem zero).
- Sem os 5 maiores gaps (h8): +0.014% — robusto.
- Leave-one-year-out (h8): +0.009% a +0.019% — o efeito nunca
  desaparece com a remocao de um ano.
- Por ano (h8): positivo em 9 de 12; negativos 2016 (-0.028%),
  2019 (-0.040%, pos 33%), 2025/2026 (-0.006%/-0.011%).

## Decisao

**H07 REJEITADA (estagio 1)**: existe sinal estatistico REAL no h1
(66.78% pos, robusto a leave-one-year-out e sem top-5), mas o edge
bruto (~3.1 pips) NAO cobre o custo round-trip conservador (3.7
pips) e o efeito se dissipa ate o h16 (pos 48%). Falha o criterio
de custo pre-registrado (docs/26 §19). Achado registrado como
candidato a reavaliacao SE custos de execucao menores existirem
(nao elevado: criterio pre-registrado e o custo do baseline).

---

# 22. Fechamento do Programa de Hipotese (2026-08-12)

Todas as 7 hipoteses (H01-H07) executadas no estagio 1 com
pre-registro imutavel. Classificacao final: 7 REFUTADAS / 0
CONFIRMADAS / 0 INCONCLUSIVAS. Base de registros:
`research/hypotheses_log.json`. Relatorio consolidado:
`docs/27_HYPOTHESES_TEST_REPORT.md`.


---

# 23. Reavaliacao H07 com Custos Reais de Execucao (2026-08-12)

## Motivo (docs/27 §5 recomendacao 1-2)

O estagio 1 do H07 foi rejeitado pelo criterio de custo usando o
baseline de 3.7 pips round-trip (docs/21). Esta secao reavalia o
h1 (unico sinal estatistico robusto do programa) com o custo REAL
medido no proprio dataset, e decide se o caso justifica abrir o
estagio 2.

## Metodo (declarado antes da execucao, sem mining)

- `research/cost_measurement.py`: mede a coluna `spread` (pontos MT5;
  EURUSD 5 digitos: 1 ponto = 0.1 pip) do M15, por ano e por hora,
  e especificamente na PRIMEIRA barra de cada semana ISO (ponto de
  entrada do H07).
- Custo round-trip real = spread_entrada + spread_saida +
  2 x slippage (0.5/fill) + comissao (0.7 pips/lote round-trip,
  3.50/lado).
- Aplicado ao retorno assinado h1 ja registrado (docs/26 §21):
  +0.031% ~ 3.11 pips brutos (EURUSD ~1.10).

## Resultados da medicao (EURUSD M15, 288,223 candles)

- Spread geral: media 0.36 pips, mediana 0.20, p90 0.80 — o baseline
  de 2.0 pips e MUITO conservador para o mercado normal.
- Spread no OPEN SEMANAL (primeira barra da semana, n=606): media
  1.48 pips, mediana 1.20, p90 3.25 — ~6x o spread normal.
- Spread na hora 1 UTC (saida +1h): mediana 0.40.

## Custo round-trip real (entrada open semanal + saida +1h)

| cenario | entrada | saida | + slippage/comissao | total | vs edge 3.11 pips |
|---|---|---|---|---|---|
| mediana | 1.20 | 0.40 | +1.7 | 3.30 pips | -0.19 pips |
| media | 1.48 | 0.47 | +1.7 | 3.65 pips | -0.54 pips |
| p90 entrada | 3.25 | 0.80 | +1.7 | 5.75 pips | -2.64 pips |
| baseline docs/21 | 2.00 | 2.00 | +1.7 | 3.70 pips | -0.59 pips |

## Decisao

**H07 permanece REFUTADA** — confirmado com custo REAL, nao apenas
baseline:

- na melhor estimativa (mediana), o edge liquido e -0.19 pips;
- no p90 do spread de entrada, -2.64 pips — o open semanal tem
  cauda de spread que inviabiliza a entrada consistente;
- o fator decisivo e a dispersao do spread no open semanal (p90 =
  3.25 pips), nao o baseline de 2.0.

A recomendacao docs/27 §5 rec. 1-2 esta RESOLVIDA: nao ha caso para
estagio 2. A ferramenta de medicao de custos fica no projeto
(`research/cost_measurement.py` + `research/reports/cost_measurement.json`)
para calibrar futuras hipoteses: o mercado normal EURUSD e barato
(~0.2-0.4 pips), o open semanal e a excecao cara.


---

# 24. Infraestrutura de Eventos Raros (docs/27 §5 recomendacao 3) — 2026-08-12

## Motivo

O H07 validou um framework de estatistica para amostras pequenas
(bootstrap CI, leave-one-year-out, remocao de top-N), mas embutido
no experimento. Esta secao generaliza a infra em modulo reutilizavel
e testado para futuras hipoteses de baixa frequencia.

## Implementacao (TDD, 12 testes novos — suite 1131 passed)

- `research/rare_events.py`:
  - `summarize(samples)` — n exato, media, positive rate, mediana;
  - `bootstrap_ci(samples, n_resamples=10000, seed=42, ci=0.95)` —
    IC percentil bootstrap da media, reprodutivel (seed fixa);
    None se amostra < 10;
  - `leave_one_year_out(by_year, metric=media)` — media do pool apos
    remover cada ano; metric customizavel;
  - `without_largest_n(samples, magnitudes, n=5)` — remove os n
    maiores por |magnitude|, alinhado por indice.
- `research/h07_experiment.py` refatorado para usar o modulo.

## Verificacao de regressao

- Resultados do H07 re-gerados com o modulo: bootstrap CI
  [-0.009%, +0.037%] IDENTICO byte-a-byte; eventos/horizontes
  identicos; by_year e without_top5 com os mesmos valores numericos
  (formato agora via `summarize`: chave `mean` + campo `median`).

## Uso em futuras hipoteses

Hipoteses de baixa frequencia (gaps, sessoes raras, eventos
exogenos) devem reportar: n EXATO, bootstrap CI, leave-one-year-out
e teste sem os maiores eventos — via `research/rare_events.py`.


---

# 25. Custos Calibrados Multi-Simbolo + Reavaliacao da Bateria docs/21 (2026-08-12)

## Motivo (docs/27 §5 recomendacao 2, extendida ao multi-simbolo)

O baseline de custos (spread 2.0 pips para todos os pares) foi
medido como MUITO conservador no EURUSD (mediana real 0.20 pips).
Esta secao calibra o spread real por instrumento e re-roda a bateria
do docs/21 para verificar se alguma conclusao inverte sob custos
medidos (nao assumidos).

## Medicao (research/cost_measurement.py --out cost_measurement_all.json)

| simbolo | spread mediana (pips) | p90 | round-trip real (mediana) |
|---|---|---|---|
| EURUSD | 0.20 | 0.80 | 1.90 |
| USDJPY | 0.30 | 0.90 | 2.00 |
| AUDUSD | 0.50 | 1.60 | 2.20 |
| GBPUSD | 0.50 | 1.40 | 2.20 |
| USDCAD | 0.50 | 1.80 | 2.20 |
| USDCHF | 0.60 | 1.60 | 2.30 |
| NZDUSD | 0.90 | 2.80 | 2.60 |

Round-trip = spread mediana + 2 x slippage 0.5 + comissao 0.7
(slippage/comissao mantidos no nivel do baseline — apenas o
componente medido varia).

## Bug fix no runner (regressao RA-04)

- `--spread-pips` (override) quebrava com NameError:
  `effective_cost_params` era usado em `build_report` mas nunca
  recebido como argumento (introduzido em 7cf7c87; nenhum backtest
  via runner rodou desde entao — as hipoteses usaram experimentos
  proprios).
- Corrigido: parametro adicionado e propagado; 2 testes de regressao
  novos (`tests/test_runner_cost_regression.py`) exercitam o caminho
  completo `run_single` com custos baseline e override.

## Bateria docs/21 re-rodada com spread calibrado (dev 2015-2021)

Todos os 21 backtests (7 pares x 3 estrategias) continuam NEGATIVOS:

| par | TSM baseline -> realcost | EMA | MR |
|---|---|---|---|
| EURUSD | -325.20 -> **-73.74** | -223.15 | -606.77 |
| GBPUSD | -334.17 -> **-113.52** | -262.66 | -833.61 |
| AUDUSD | -657.40 -> **-411.40** | -396.97 | -755.00 |
| NZDUSD | -615.68 -> **-431.87** | -391.73 | -1009.76 |
| USDJPY | -401.21 -> **-187.02** | -226.82 | -769.15 |
| USDCHF | -860.80 -> **-638.57** | -759.64 | -434.86 |
| USDCAD | -534.24 -> **-361.61** | -309.18 | -322.76 |

## Decisao

- **Nenhuma conclusao do docs/21 inverte**: 21/21 negativos sob
  custos reais calibrados. A ausencia de edge nao era artefato do
  baseline conservador — e robusta a custos medidos.
- Melhora media de PnL ~+200 a +500 USD por combo (custo menor),
  insuficiente para tornar qualquer combinacao positiva.
- Registros: `research/reports/realcost_battery.json`,
  `research/reports/cost_measurement_all.json` (gitignored).

## Nota de execucao

O runner agora suporta custos calibrados por instrumento via
`--spread-pips <medido>`; a medicao multi-simbolo fica disponivel
via `python -m research.cost_measurement` (modo padrao = 7 pares).


---

# 26. Abertura do Ciclo 2 de Hipotese (2026-08-12)

## Licoes do ciclo 1 (H01-H07, 7/7 refutadas)

1. **O custo entra no estagio 1**: H07-h1 tinha sinal real (66.8%
   pos) mas morreu no custo. Todo o ciclo 2 avalia valor esperado
   LIQUIDO (retorno assinado - custo efetivo por evento) desde o
   primeiro backtest, com custos calibrados (docs/26 §25).
2. **Timeframes maiores diluem o custo fixo**: o round-trip de
   ~1.9-2.6 pips (calibrado) e grande frente a movimentos M15;
   hipoteses em H1/H4 tem custo relativo menor.
3. **Filtros de execucao podem virar o jogo**: o open semanal e
   caro (p90 3.25 pips) — filtrar por liquidez normal pode reduzir
   o custo de entrada e preservar o sinal.
4. **Sem mining**: cada hipotese tem pre-registro imutavel e
   sensibilidade declarada antes de qualquer backtest.

## Hipotese ativas do ciclo 2

| ID | Hipotese | Racional | Prioridade |
|---|---|---|---|
| H08 | Reversao do gap semanal com filtro de liquidez no open | O sinal h1 do H07 e real; opens com spread baixo tem custo de entrada menor e liquidez normal (reversao mais provavel) | 1 |
| H09 | Reversao apos faixa comprimida + fechamento no extremo | Padrao anti-H02 observado (10/12 anos); agora PRE-REGISTRADO com origem de descoberta declarada e validacao rigida | 2 |
| H10 | Momentum da primeira hora de Londres | Fluxo institucional europeu tende a continuar no dia | 3 |
| H11 | Eficiencia direcional H1 -> proximo H1 | Timeframe maior dilui o custo fixo; DE alta + volume em H1 | 4 |


---

# 27. Registro Imutavel - H08 (primeira versao, pre-backtest)

```text
hypothesis_id:            H08
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
rationale:                o sinal de reversao parcial do gap semanal
                          (H07-h1: +0.031%, 66.78% pos) foi refutado
                          apenas pelo custo do open semanal (mediana
                          1.20, p90 3.25 pips). Opens com spread baixo
                          indicam liquidez normal (sem noticia grande):
                          custo de entrada menor E reversao mais
                          provavel. O filtro de liquidez pode gerar
                          valor esperado LIQUIDO positivo.
expected_direction:       gap positivo + open liquido -> retorno negativo
                          gap negativo + open liquido -> retorno positivo
dataset_version:          EURUSD M15 parquet 2015-01-02..2026-08-10
                          + H1 processado (ATR)
timeframe:                M15 (evento) + H1 (ATR)
session_definition:       semana ISO; primeira barra REAL da semana
                          (sem candles de fim de semana); spread da
                          primeira barra = spread de entrada
features:                 weekly_gap = first_open - last_close_prev
                          normalized_gap = |gap| / ATR(H1,14) causal
                          entry_spread_pips = spread da primeira barra
                          da semana (pontos MT5 / 10)
                          saida em +1h: spread da hora 1 UTC (mediana
                          0.40 pips calibrada)
primary_parameters:       normalized_gap >= 0.50
                          filtro de entrada: entry_spread_pips <= 1.0
                          (sensibilidade declarada: 1.2 / 1.0 / 0.8)
                          custo efetivo = entry_spread + 0.40 (saida)
                          + 1.0 (slippage 2x0.5) + 0.7 (comissao)
allowed_sensitivity:      limiar de spread 1.2 / 1.0 / 0.8 (declarado
                          ANTES; um por vez); threshold do gap
                          0.40/0.50/0.60 permanece como no H07
entry_rule:               ESTAGIO 1 = valor esperado LIQUIDO por
                          evento: net = signed_h1 - custo_efetivo;
                          media do net por grupo de limiar; SEM trade
exit_rule:                estagio 2 (so se net medio > 0 com n >= 50
                          e robusto): regras de trade pre-registradas
cost_model:               custos calibrados por evento (docs/26 §25):
                          entrada = spread medido da barra, saida =
                          0.40 pips, slippage 1.0, comissao 0.7
risk_model:               FixedSizeRiskGate 0.01 (estagio 2)
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado)
rejection_criteria:       rejeitar se net medio <= 0 em qualquer
                          limiar; n < 50 apos o filtro; efeito
                          desaparecer no leave-one-year-out ou sem os
                          5 maiores gaps; net nao robusto ao limiar
                          (1.2/1.0/0.8)
git_commit:               commit do pre-registro (docs/26 §27)
```


---

# 28. Registro Imutavel - H09 (primeira versao, pre-backtest)

```text
hypothesis_id:            H09
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
origem_da_descoberta:     padrao anti-H02 observado em docs/26 §17
                          (continuation_up negativo em 10/12 anos no
                          h4) — NAO elevado naquele ciclo por nao ser
                          pre-registrado. Agora formalizado como
                          hipotese com validacao mais rigorosa.
rationale:                faixa asiatica comprimida com fechamento no
                          extremo = squeeze; squeezes resolvem rapido
                          e tendem a reverter na abertura de Londres
expected_direction:       faixa < p30 e CLV >= 0.80 -> retorno NEGATIVO
                          faixa < p30 e CLV <= 0.20 -> retorno POSITIVO
                          (reversao, OPOSTO do H02)
dataset_version:          EURUSD M15 2015-01-02..2026-08-10
timeframe:                M15
session_definition:       Asia Europe/London [00:00, 07:00) zoneinfo
features:                 asian_range_percentile (60d, causal); CLV da
                          ultima barra asiatica; retorno fwd 1/2/4h
primary_parameters:       p30, CLV 0.80/0.20
allowed_sensitivity:      p25/p35; CLV 0.75/0.85 e 0.15/0.25
entry_rule:               ESTAGIO 1 = net liquido: signed - custo
                          (entrada 07:00 London, saida +1h: custo =
                          spread hora 0 + 0.40 + 1.0 + 0.7 pips)
exit_rule:                estagio 2 (se net > 0 robusto)
cost_model:               calibrado por hora (docs/26 §25)
risk_model:               FixedSizeRiskGate 0.01
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado)
rejection_criteria:       rejeitar se net <= 0; nao estavel no
                          leave-one-year-out; depender de poucos
                          eventos (cauda); falhar em qualquer variacao
                          de fronteira
git_commit:               commit do pre-registro (docs/26 §28)
```


---

# 29. Registro Imutavel - H10 (primeira versao, pre-backtest)

```text
hypothesis_id:            H10
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
rationale:                a primeira hora de Londres concentra o fluxo
                          institucional europeu; retornos dessa janela
                          tendem a continuar no resto do dia (horizonte
                          D1, custo relativo pequeno)
expected_direction:       retorno da janela 07:00-08:00 London > 0 ->
                          retorno do resto do dia > 0 (e vice-versa)
dataset_version:          EURUSD M15 2015-01-02..2026-08-10
timeframe:                M15 (evento) — avaliacao ate o fechamento
                          do dia London
session_definition:       janela 07:00-08:00 Europe/London (zoneinfo);
                          resto do dia = 08:00 London ate 22:00 London
features:                 london_open_return = close 08:00 / open 07:00
                          - 1; fwd = close 22:00 / close 08:00 - 1
primary_parameters:       assinatura: signed = sign(london_open) * fwd
                          sem threshold de entrada (relacao linear)
allowed_sensitivity:      janelas 07:00-08:00 e 08:00-09:00; corte do
                          dia 21:00/22:00 London
entry_rule:               ESTAGIO 1 = correlacao/retorno assinado medio
                          + decil por tamanho do movimento
exit_rule:                estagio 2 (se efeito consistente)
cost_model:               1 trade/dia: custo ~1.9 pips calibrado
risk_model:               FixedSizeRiskGate 0.01
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado)
rejection_criteria:       rejeitar se signed medio <= 0; efeito nao
                          monotono nos decis; instavel por ano
git_commit:               commit do pre-registro (docs/26 §29)
```


---

# 30. Registro Imutavel - H11 (primeira versao, pre-backtest)

```text
hypothesis_id:            H11
version:                  1.0
status:                   SPECIFIED (pre-registrado antes de qualquer backtest)
date:                     2026-08-12
rationale:                em H1 o movimento medio e ~3-5x o do M15 e o
                          custo round-trip e o mesmo (~1.9 pips
                          calibrado) -> custo relativo muito menor;
                          a eficiencia direcional (DE) alta com volume
                          em H1 pode indicar continuacao
expected_direction:       H1 com DE >= 0.70 e TV > mediana do mesmo
                          slot -> proximo H1 na mesma direcao
dataset_version:          EURUSD H1 processado 2015-01-02..2026-08-10
timeframe:                H1
session_definition:       slots H1 por horario UTC
features:                 directional_efficiency (abs(close-open)/
                          (high-low)); tick_volume percentil do slot
                          (60 slots); fwd = proximo H1 close/open - 1
primary_parameters:       DE >= 0.70; TV percentil >= 0.50; signed =
                          sign(candle) * fwd
allowed_sensitivity:      DE 0.60/0.70/0.80; TV p40/p50/p60
entry_rule:               ESTAGIO 1 = net liquido: signed - custo
                          (1.9 pips calibrado)
exit_rule:                estagio 2 (se net > 0 robusto)
cost_model:               calibrado (docs/26 §25), 1.9 pips
risk_model:               FixedSizeRiskGate 0.01
development_period:       2015-01-01 .. 2021-01-01
validation_period:        2021-01-01 .. 2024-01-01
oos_period:               2024-01-01 .. 2027-01-01 (contaminado)
rejection_criteria:       rejeitar se net <= 0; efeito so em um ano;
                          DE nao adicionar vs controle (candle simples)
git_commit:               commit do pre-registro (docs/26 §30)
```


---

# 31. Resultado H08 - Estagio 1 (2026-08-12) — REJECTED

## Execucao

- Experimento `research/h08_experiment.py`: mesmos eventos do H07
  (301 gaps, normalized >= 0.50) com filtro de liquidez na entrada
  (spread da primeira barra da semana <= 1.2 / 1.0 / 0.8 pips) e
  custo efetivo POR EVENTO (spread medido + 0.40 saida + 1.0
  slippage + 0.7 comissao). net = signed_h1 - custo.
- Sensibilidade pre-registrada (docs/26 §27): limiares 1.2/1.0/0.8.

## Resultados (net medio h1)

| limiar | n | net | net pos% | bruto | custo entrada medio | CI 95% |
|---|---|---|---|---|---|---|
| 1.2 | 169 | +0.002% | 50.30% | +0.027% | 0.473 | [-0.020%, +0.022%] |
| 1.0 | 149 | +0.002% | 51.01% | +0.027% | 0.382 | [-0.019%, +0.024%] |
| 0.8 | 134 | +0.001% | 50.75% | +0.025% | 0.319 | [-0.023%, +0.024%] |

- Leave-one-year-out: -0.003% a +0.009% (cruza zero).
- Sem top-5: +0.002% (estavel, mas ~0).
- Por ano: instavel; 2026 fortemente negativo (-0.056%); amostras
  por ano de 1 a 28.

## Decisao

**H08 REJEITADA (estagio 1)** — o filtro de liquidez falhou em criar
valor esperado positivo:

- net medio ~0.2 pips com CI bootstrap contendo ZERO em todos os
  limiares (criterio pre-registrado: net > 0 robusto);
- o filtro barateou a entrada (0.47 -> 0.32 pips) mas REMOVEU sinal:
  o bruto caiu de 0.031% (todos os 301) para 0.025-0.027%
  (filtrados). A reversao do gap concentra-se nos opens CAROS
  (eventos com noticia), nao nos calmos — o oposto do racional;
- instabilidade por ano e cauda (2022: n=2, +0.164%).

Achado de pesquisa: a reversao parcial do gap (H07-h1) esta associada
a eventos de alta volatilidade (opens com spread alto), o que
inviabiliza o filtro de liquidez como mecanismo de reducao de custo
sem perder o sinal.


---

# 32. Resultado H09 - Estagio 1 (2026-08-12) — INCONCLUSIVA

## Execucao

- Experimento `research/h09_experiment.py`: faixa asiatica comprimida
  (percentil < p30, 60d causal) com fechamento no extremo (CLV 0.80/
  0.20); direcao esperada = REVERSAO (oposto do H02); net liquido
  por evento (spread de entrada medido + 0.40 saida + 1.0 + 0.7);
  fwd 1/2/4h; sensibilidade p25/p35 e CLV 0.75/0.85, 0.15/0.25.
- Origem da descoberta declarada (docs/26 §28): padrao anti-H02.

## Resultados (net medio, grupo compressed_close_high)

| variacao | h4 net | n |
|---|---|---|
| base (p30, CLV 0.80) | +0.010% | 168 |
| p25 | +0.012% | 129 |
| p35 | +0.009% | 195 |
| CLV 0.85 | +0.003% | 126 |
| CLV 0.75 | +0.005% | 217 |

- fwd bruto h4 ~ -0.035% (reversao real de ~3.5 pips, consistente com
  o padrao anti-H02 do docs/26 §17); net = +0.003% a +0.012%
  (~0.3-1.2 pips liquidos).
- Leave-one-year-out (h4, base): +0.002% a +0.014% — sempre > 0, mas
  sem 2015 o net cai para +0.002% (2015 concentra ~80% do net).
- Grupo espelho (compressed_close_low): net NEGATIVO em todas as
  variacoes (-0.026% a -0.036%) — fwd ~0, apenas custo. Assimetria
  nao prevista.
- h1/h2 do grupo high: negativos (-0.012%/-0.010%) — o efeito so
  aparece no h4 (timing especifico).

## Decisao

**H09 INCONCLUSIVA no estagio 1** — primeiro sinal do programa com
net positivo em TODAS as variacoes de fronteira (sem ilha de
parametro) e robusto ao leave-one-year-out. Contudo: net marginal
(~0.5-1 pip), concentracao temporal em 2015, efeito apenas no h4 e
assimetria de grupo nao prevista.

NAO sera declarada confirmada (net pequeno e concentrado) nem
refutada (sinal real e consistente). Recomendacao: estagio 2 focado
(trade completo no grupo high h4 com custos reais, alvo midpoint da
faixa, stop alem do extremo) + walk-forward — condicionado a
aceitacao do operador; validar tambem o padrao em H1 (custo relativo
menor, docs/26 §30 H11).


---

# 33. Resultado H10 - Estagio 1 (2026-08-12) — REJECTED

## Execucao

- Experimento `research/h10_experiment.py`: janela 07:00-08:00
  Europe/London (zoneinfo); retorno da janela; fwd = close 22:00
  London / close 08:00 London - 1; signed = sign(janela) * fwd;
  net = signed - custo (spread de entrada medido 0.335 pips medio +
  0.40 saida + 1.0 + 0.7).
- 2.998 dias uteis.

## Resultados

- net medio: **-0.023%** (pos 47.0%) — retorno bruto pos-janela ~0,
  o net negativo e essencialmente o custo.
- Por ano: negativo em 9 de 12 anos (-0.072% a +0.006%).

## Decisao

**H10 REJEITADA** — nao ha momentum da primeira hora de Londres: o
retorno do resto do dia e indiferente ao sinal da janela inicial.


---

# 34. Resultado H11 - Estagio 1 (2026-08-12) — REJECTED

## Execucao

- Experimento `research/h11_experiment.py`: H1 agregado do M15;
  directional_efficiency + slot_percentile do tick_volume (60 slots
  causais); sinal DE >= 0.70 e TV >= p50; signed = direcao do candle
  * fwd (proximo H1); net = signed - 1.9 pips calibrados; controle =
  direcao do candle sem filtro; sensibilidade DE 0.60/0.80 e
  TV p40/p60.
- 72.080 barras H1; filtro n=7.622.

## Resultados (bruto / net)

| modelo | n | bruto | pos% | net |
|---|---|---|---|---|
| DE_TV (base) | 7.622 | -0.002% | 46.6% | -0.021% |
| controle (candle) | 72.079 | -0.001% | 48.1% | -0.020% |
| DE 0.60 | 11.800 | -0.002% | 46.7% | -0.021% |
| DE 0.80 | 3.953 | -0.005% | 45.4% | -0.024% |
| TV p40 | 8.839 | -0.003% | 46.4% | -0.022% |
| TV p60 | 6.376 | -0.002% | 46.5% | -0.021% |

## Decisao

**H11 REJEITADA** — a eficiencia direcional com volume em H1 NAO
adiciona poder preditivo vs o controle (candle simples): o filtro e
levemente PIOR em todas as variacoes. A continuacao H1-a-H1 nao
existe (bruto ~0 e negativo).

---

# 35. Fechamento do Ciclo 2 (2026-08-12)

| ID | Resultado | Resumo |
|---|---|---|
| H08 | REFUTADA | filtro de liquidez removeu sinal (reversao do gap vive nos opens caros) |
| H09 | INCONCLUSIVA | comprimida+high h4: net +0.003% a +0.012% em todas as fronteiras; marginal e concentrado em 2015 |
| H10 | REFUTADA | sem momentum da 1a hora de Londres (net -0.023%) |
| H11 | REFUTADA | DE/TV em H1 nao adiciona vs controle (net ~-0.021%) |

Ciclo 2: 3 refutadas, 1 inconclusiva (H09 — candidata a estagio 2
condicionado ao operador). Base de registros atualizada em
`research/hypotheses_log.json`.


---

# 36. Pre-registro do Estagio 2 do H09 (2026-08-12)

Imutavel. Nenhum backtest do estagio 2 foi executado antes deste
registro. Origem: H09 estagio 1 (secao 32) — grupo
`compressed_close_high`, horizonte h4: unico sinal do programa com
net positivo em todas as variacoes de fronteira.

## Trade completo (fixado antes de rodar)

- **Sinal**: sessao asiatica (London 00:00-07:00) com
  `range_pct < 0.30` (percentil 60d causal) e `clv >= 0.80`
  (fechamento no extremo superior da faixa).
- **Direcao**: SHORT (reversao da compressao).
- **Entrada**: close da ultima barra M15 asiatica (`last_ts`).
- **Alvo (TP)**: midpoint da faixa asiatica = (high + low) / 2.
  Nivel estrutural: retorno ao centro da compressao.
- **Stop (SL)**: high da faixa asiatica + 0.10 x (high - low).
  Buffer declarado contra ruido de mercado; romper o extremo
  invalida a tese de reversao.
- **Horizonte maximo**: 16 barras M15 (4h) — o efeito foi medido no
  h4 no estagio 1. Timeout = saida market no close da 16a barra.
- **Simulacao intrabarra (M15)**: barra de entrada nao participa;
  barras seguintes avaliadas na ordem: (1) gap no open — se
  open >= SL (short), stop no open; se open <= TP, alvo no open;
  (2) SL-first: se high >= SL, saida no SL; senao se low <= TP,
  saida no TP. SL e TP na mesma barra -> SL (pior caso).
- **Custos por trade** (mesmo modelo do estagio 1):
  custo_pips = spread_entrada_medido (ultima barra asiatica) + 0.40
  (spread de saida) + 1.0 (slippage) + 0.7 (comissao).
  net_pnl = (entry - exit) - custo_pips x PIP_SIZE (short).
- **PIP_SIZE** = 0.0001. Dataset: EURUSD M15 completo
  (mesmo do estagio 1; anos 2024-2026 sao OOS contaminado, relatorio
  informativo).

## Criterios de aceitacao (fixados antes de rodar)

1. n >= 50 trades no grupo.
2. net medio por trade > 0 (pips).
3. leave-one-year-out do net medio > 0 (nao depender de 1 ano).
4. mediana dos net anuais > 0 (sem cauda de poucos anos).
5. walk-forward em blocos de 2 anos: >= 60% dos blocos com net > 0.
6. hit rate do TP >= 15% (alvo atingivel).

## Decisoes

- net medio > 0 + mediana anual > 0 + LOYO > 0 + blocos >= 60%:
  **CONFIRMADA no estagio 2** -> proximo passo: validacao OOS
  (lockbox) e, se mantido, candidata a demo (decisao do operador).
- net > 0 mas mediana anual <= 0 ou blocos < 60%: **INCONCLUSIVA**
  (dependencia temporal).
- net <= 0: **REFUTADA**.


---

# 37. Resultado do Estagio 2 do H09 (2026-08-12) — REFUTADA

## Execucao

- `research/h09_stage2.py` (pre-registro na secao 36; simulador com
  7 testes unitarios sinteticos em `tests/test_h09_stage2.py`).
- Trade completo: SHORT na ultima barra asiatica (comprimida p30 +
  CLV 0.80); TP = midpoint da faixa; SL = high + 0.10 x range;
  timeout 16 barras M15 (4h); SL-first intrabarra; custos:
  spread de entrada medido + 0.40 + 1.0 + 0.7 pips.

## Resultados (n = 168 trades)

| metrica | valor |
|---|---|
| net medio | **-0.81 pips** |
| bruto medio | +1.73 pips |
| hit TP | 43.5% |
| stop | 56.5% |
| timeout | 0.0% |
| payoff | 1.03 |
| barras ate saida (media) | 3.8 (~1h) |
| spread entrada medio | 0.335 pips |

- Por ano: positivo em 4 de 12 (2015 +3.05, 2020 +1.10, 2021 +0.14,
  2025 +1.34); negativo em 8 de 12 (2016 -3.84, 2017 -3.04,
  2018 -2.34, 2019 -2.08, 2022 -3.31, 2023 -0.84, 2024 -3.50,
  2026 -1.23).
- Leave-one-year-out e blocos de 2 anos: ver JSON
  `research/reports/h09_stage2.json` (net medio negativo).

## Decisao

**H09 REFUTADA no estagio 2.** O edge bruto REAL do trade completo
(+1.73 pips, hit TP 43.5%, payoff ~1.0) e menor que o custo
calibrado (~2.5 pips por trade). A saida pelo TP midpoint ocorre em
media em ~1h, mas os stops (56.5%) consomem o edge. A concentracao
em 2015 do estagio 1 nao se sustentou: 2015 (+3.05) foi compensado
por anos negativos.

## Programa de hipoteses — status final

12 execucoes registradas (ciclo 1 H01-H07, ciclo 2 H08-H11,
estagio 2 H09): **11 refutadas + 1 inconclusiva (H09 estagio 1,
agora resolvida no estagio 2 como refutada)**.

**Resultado consolidado: 0 CONFIRMADAS / 12 REFUTADAS.**
Nenhuma hipotese do programa produziu valor esperado liquido
positivo sob custos calibrados. O padrao repetido: edge bruto
marginal (0.1-1.7 pips) sistematicamente menor que o custo
round-trip calibrado (1.9-3.7 pips).

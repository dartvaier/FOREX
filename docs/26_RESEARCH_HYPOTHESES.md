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

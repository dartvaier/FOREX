# Integração Conceitual com `ai-hedge-fund` — Roadmap de Alpha Models e Ensemble

> **Status:** proposta arquitetural / próximos passos de pesquisa  
> **Branch analisada:** `feature/backtest-core-models`  
> **FOREX commit de referência:** `1bb37af9a2d5e53acfc62d87d06010bbca451cdc`  
> **Projeto externo analisado:** `virattt/ai-hedge-fund`  
> **ai-hedge-fund commit de referência:** `eff8a7320fcf0b473b135690fa1a5b0d9b022a83` (`v2.2.0`)  
> **Data da análise:** 2026-08-16

---

## 1. Objetivo

Este documento registra quais ideias do projeto externo [`virattt/ai-hedge-fund`](https://github.com/virattt/ai-hedge-fund) podem agregar valor à plataforma FOREX **no estado atual do projeto**, sem substituir componentes que já estão implementados e validados.

A conclusão central é:

> O FOREX já possui o núcleo de backtest, risco, execução, portfólio, auditoria e validação necessário. O maior potencial de reaproveitamento do `ai-hedge-fund` está na camada de **formação e combinação de views/alpha**, e não na infraestrutura de trading.

O objetivo proposto não é portar o `ai-hedge-fund` para dentro do FOREX. O objetivo é adaptar alguns de seus princípios:

- `AlphaModel` como unidade de pesquisa;
- sinal contínuo de convicção em `[-1, +1]`;
- distinção entre **neutralidade** e **abstenção**;
- combinação explícita de múltiplos modelos;
- estratégias declarativas por configuração;
- separação rígida entre opinião de modelo, decisão operacional, risco e execução;
- possibilidade futura de adicionar modelos baseados em LLM sem conceder a eles controle sobre sizing ou execução.

---

## 2. Estado Atual do FOREX

A branch `feature/backtest-core-models` já está muito além da fundação observada na `master` antiga.

O projeto já possui, entre outros:

- `BacktestEngine` determinístico e bar-by-bar;
- `SimulationClock`;
- `BacktestContext` com barreira temporal;
- `HistoricalBarFeed`;
- `Signal`, `Order`, `Fill`, `Position` e `Trade`;
- filas e ledgers auditáveis;
- `CostModel` explícito;
- `Portfolio` e equity tracking;
- `RiskGate` e composição de gates;
- sizing por stop;
- limites de exposição;
- daily loss guard;
- drawdown / kill switch;
- Stop Loss e Take Profit;
- gap-through-stop;
- política worst-case intrabar;
- métricas de performance;
- múltiplas estratégias quantitativas;
- robustez, sweeps, subperíodos, DEV/VAL/OOS e walk-forward;
- camada `execution/` desacoplada;
- `MT5Execution`;
- reconciliação e auditoria de execução;
- readiness para demo/live;
- suporte a múltiplos símbolos e conversão de moedas;
- programa estruturado de pesquisa de hipóteses.

Portanto, a seguinte arquitetura existente deve continuar sendo a espinha dorsal:

```text
Market / Historical Data
        |
        v
 BacktestContext
        |
        v
     Strategy
        |
        v
      Signal
        |
        v
     RiskGate
        |
        v
  RiskDecision
        |
        v
   OrderFactory
        |
        v
      Order
        |
   +----+------------------+
   |                       |
   v                       v
SimulatedExecution     MT5Execution
   |                       |
   +-----------+-----------+
               |
               v
              Fill
               |
               v
           Portfolio
               |
               v
     Ledgers / Performance
```

A proposta deste documento é adicionar uma camada **antes de `Strategy -> Signal`**, preservando o restante.

---

## 3. Diagnóstico Atual do Projeto

A infraestrutura deixou de ser o principal gargalo.

Os resultados documentados em F6/F8 e no programa posterior de hipóteses mostram um padrão recorrente:

```text
edge bruto pequeno ou inexistente
              +
          turnover
              +
   custos explícitos reais
              =
     edge líquido negativo
```

Exemplos observados no projeto incluem:

- Time-Series Momentum apresentando algum sinal bruto em certos recortes, mas não sobrevivendo aos custos;
- Mean Reversion com turnover elevado e forte degradação por custos;
- EMA Trend e outros baselines consistentemente negativos sob custos explícitos;
- hipóteses H01-H07 sem candidato que passasse os critérios pré-registrados;
- H07 apresentando o efeito mais promissor, porém com edge bruto ainda inferior ao custo baseline utilizado.

Isso sugere que o próximo ciclo de engenharia/pesquisa deve investigar menos a criação de novos indicadores isolados e mais:

1. **combinação de sinais independentes**;
2. **gating por regime/contexto**;
3. **redução de turnover**;
4. **abstenção quando o contexto não é favorável**;
5. **seleção condicional de modelos**;
6. **avaliação de contribuição incremental de cada modelo**;
7. **modelos de menor frequência e maior payoff potencial**.

---

## 4. O Que o `ai-hedge-fund` Faz Bem para Este Problema

O `ai-hedge-fund` separa conceitualmente:

```text
MODEL -> SIGNAL/VIEW -> STRATEGY -> PORTFOLIO -> RISK -> EXECUTION
```

O conceito mais útil é o de `AlphaModel`:

```python
predict(...) -> Signal(value in [-1, +1])
```

O modelo não controla tamanho, ordem nem broker. Ele forma apenas uma **view**.

Além disso, o projeto trata tanto modelos quantitativos quanto agentes LLM sob a mesma interface, permitindo que qualquer fonte de visão seja combinada no mesmo pipeline.

Essa separação é diretamente útil ao FOREX.

---

## 5. O Que NÃO Deve Ser Portado

A integração proposta deve ser seletiva.

### 5.1 Backtest Engine

**Não portar.**

O FOREX possui um backtester mais apropriado para Forex intraday, com:

- Signal on Close;
- Next Bar Open execution;
- custos;
- stop/target;
- gaps;
- política intrabar;
- posições;
- trades;
- accounting;
- auditoria.

O `run_cycle()` do `ai-hedge-fund` resolve um problema diferente, mais próximo de rebalanceamento de portfólio.

### 5.2 Portfolio Construction por pesos de ativos

**Não portar diretamente.**

O FOREX dimensiona risco em unidades/lotes e possui `RiskGate`. Não faz sentido substituir isso por normalização de pesos de portfólio do projeto externo.

### 5.3 Risk Engine

**Não substituir.**

O FOREX já possui gates específicos para Forex e conceitos que não existem da mesma forma no `ai-hedge-fund`.

### 5.4 Execution / Broker

**Não substituir.**

`SimulatedExecution`, `ExecutionInterface` e `MT5Execution` já formam uma separação apropriada para o projeto.

### 5.5 Personas de ações

Não portar:

- Buffett;
- Graham;
- Munger;
- Lynch;
- PEAD específico de equities;
- snapshots fundamentalistas de empresas.

São conceitos de outro mercado.

---

## 6. Conceito Principal a Adicionar: `AlphaModel`

A proposta é introduzir um novo contrato independente de `Strategy`.

```python
@runtime_checkable
class AlphaModel(Protocol):

    @property
    def model_id(self) -> str:
        ...

    def predict(
        self,
        context: BacktestContext,
    ) -> AlphaSignal:
        ...
```

Responsabilidade:

> Transformar somente informações causalmente disponíveis no `BacktestContext` em uma view quantitativa ou qualitativa sobre o ativo.

Um `AlphaModel` **não deve**:

- criar `Order`;
- calcular lote final;
- acessar MT5 diretamente;
- consultar dados futuros;
- alterar o relógio;
- aplicar custos;
- alterar o portfolio;
- executar trade;
- decidir limites de risco.

---

## 7. Novo Contrato: `AlphaSignal`

Não é recomendável alterar a semântica atual de `backtest.models.signal.Signal`.

O `Signal` existente representa corretamente uma **intenção operacional**:

```text
ENTER_LONG
ENTER_SHORT
EXIT
HOLD
```

Portanto deve existir um objeto separado:

```python
@dataclass(frozen=True, slots=True)
class AlphaSignal:
    model_id: str
    symbol: str
    timestamp: datetime
    value: float
    confidence: float | None = None
    abstained: bool = False
    reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

### 7.1 `value`

Faixa:

```text
-1.0  bearish forte
 0.0  visão neutra
+1.0  bullish forte
```

Invariante sugerida:

```python
-1.0 <= value <= 1.0
```

### 7.2 `confidence`

Opcional.

Faixa sugerida:

```text
0.0 .. 1.0
```

`value` representa direção/intensidade da visão.

`confidence` representa qualidade/certeza atribuída pelo modelo.

Na primeira implementação, é aceitável **não usar `confidence` no sizing nem no blend**. Pode ser apenas informativo até existir evidência de que adiciona valor.

### 7.3 `abstained`

Este campo é importante.

Há diferença entre:

```text
value = 0.0
```

que significa:

> o modelo avaliou o contexto e concluiu neutralidade;

versus:

```text
abstained = True
```

que significa:

> o modelo não possui uma view válida para este instante.

Exemplos de abstenção:

- modelo de faixa asiática fora da janela relevante;
- warm-up insuficiente;
- dado auxiliar indisponível;
- filtro de regime incompatível;
- modelo LLM falhou ou recebeu snapshot incompleto;
- evento macro não aplicável naquele instante.

Um modelo abstido não deve diluir automaticamente a votação dos demais.

---

## 8. Separação Final de Responsabilidades

A arquitetura proposta fica:

```text
                   BacktestContext
                         |
       +-----------------+------------------+
       |                 |                  |
       v                 v                  v
   AlphaModel A      AlphaModel B       AlphaModel C
       |                 |                  |
       +-----------------+------------------+
                         |
                         v
                    AlphaSignals
                         |
                         v
                    AlphaBlender
                         |
                         v
                  BlendedAlphaView
                         |
                         v
                   EnsembleStrategy
                         |
                         v
                       Signal
                         |
                         v
                      RiskGate
                         |
                         v
                   RiskDecision
                         |
                         v
                       Order
                         |
                         v
                     Execution
```

O ponto crítico é:

> Nada abaixo de `Signal` precisa saber que existe uma camada de Alpha Models.

Essa propriedade reduz o risco de regressão arquitetural.

---

## 9. `AlphaBlender`

O blender combina múltiplas views.

### 9.1 Primeira versão recomendada

Usar média ponderada simples:

```text
blended = sum(weight_i * value_i) / sum(weight_i)
```

ignorando sinais com:

```text
abstained == True
```

### 9.2 Evitar um erro do `ai-hedge-fund`

O `blend_signals()` do projeto externo normaliza convicções cross-sectionalmente para exposição de portfólio. Isso é adequado ao problema que ele tenta resolver, mas não deve ser copiado literalmente para um único par de Forex.

Exemplo indesejado:

```text
EURUSD alpha = +0.03
```

não deve se transformar em:

```text
100% da exposição disponível
```

apenas porque é o único ativo/modelo.

No FOREX, o valor absoluto da convicção deve permanecer significativo.

### 9.3 Threshold mínimo

Adicionar:

```text
min_conviction
```

Exemplo:

```text
abs(blended) < 0.30 -> HOLD
blended >= 0.30     -> candidato LONG
blended <= -0.30    -> candidato SHORT
```

O threshold não deve ser otimizado livremente sem protocolo de pesquisa.

---

## 10. `BlendedAlphaView`

Objeto sugerido:

```python
@dataclass(frozen=True, slots=True)
class BlendedAlphaView:
    symbol: str
    timestamp: datetime
    value: float
    contributors: tuple[AlphaContribution, ...]
    abstained_models: tuple[str, ...]
    metadata: Mapping[str, Any]
```

Isso permite auditoria completa:

```text
EURUSD @ 2026-08-01 12:00 UTC

EMA          +0.62  weight 1.0
TSMOM        +0.41  weight 1.2
BREAKOUT     ABSTAIN
REGIME       +0.30  weight 0.8

BLENDED      +0.43
```

---

## 11. `EnsembleStrategy`

O `EnsembleStrategy` é responsável por converter uma view contínua em um `Signal` operacional existente.

Exemplo conceitual:

```python
class EnsembleStrategy:

    def on_bar(self, context: BacktestContext) -> Signal:
        alpha_signals = [
            model.predict(context)
            for model in self.models
        ]

        view = self.blender.blend(alpha_signals)

        if view.value >= self.enter_long_threshold:
            return ENTER_LONG

        if view.value <= self.enter_short_threshold:
            return ENTER_SHORT

        if self._should_exit(view):
            return EXIT

        return HOLD
```

A Strategy continua sem conhecer:

- posição final aprovada;
- quantidade final;
- spread/slippage final;
- broker;
- execução.

---

## 12. Não Vincular Convicção Diretamente a Lote na Primeira Versão

Uma tentação natural seria:

```text
conviction 0.30 -> 0.1% risco
conviction 0.60 -> 0.5% risco
conviction 0.90 -> 1.0% risco
```

Não implementar isso inicialmente.

Motivos:

1. adiciona uma dimensão extra de otimização;
2. aumenta risco de overfitting;
3. mistura alpha com risk sizing;
4. não existe evidência ainda de que a escala do score esteja calibrada;
5. dificulta comparar ensemble vs baseline.

A primeira versão deve usar o mesmo RiskGate de referência das estratégias atuais.

Assim a pergunta científica fica limpa:

> O ensemble melhora a qualidade/timing dos sinais mantendo o mesmo motor de risco e execução?

---

## 13. Converter Estratégias Atuais em Alpha Models

Não remover as estratégias atuais.

Criar versões Alpha paralelas.

Exemplo:

```text
SimpleEmaTrendStrategy
```

continua existindo para comparação.

Adicionar:

```text
EmaTrendAlphaModel
```

### 13.1 Possível score para EMA

Em vez de gerar score apenas no cruzamento, usar uma função contínua causal, por exemplo:

```text
EMA spread normalizado por ATR
```

Conceitualmente:

```python
raw = (ema_fast - ema_slow) / atr
value = tanh(k * raw)
```

O parâmetro `k` precisa ser pré-registrado/justificado antes de backtest ou mantido simples.

### 13.2 TSMOM Alpha

Possível view:

```text
retorno lookback normalizado por volatilidade
```

convertido de forma limitada para `[-1,+1]`.

### 13.3 Volatility Breakout Alpha

Pode combinar:

- distância do breakout;
- normalização por ATR/range;
- confirmação de fechamento;
- potencial abstenção fora de contexto.

### 13.4 Mean Reversion Alpha

Pode produzir score proporcional à distância normalizada da média, mas preferencialmente só quando um regime compatível estiver ativo.

### 13.5 Regime Alpha / Regime Gate

Duas opções distintas devem ser testadas separadamente:

1. regime como mais um score no blend;
2. regime como **gating**, alterando quais Alpha Models podem votar.

A segunda opção pode ser mais interessante.

---

## 14. Regime como Gating

Uma arquitetura potencial:

```text
                Regime Classifier
                       |
          +------------+-------------+
          |                          |
       TRENDING                    RANGING
          |                          |
   +------+------+              +----+-----+
   |             |              |          |
  EMA          TSMOM        MeanRev     Breakout?
```

Exemplo de política:

```text
TRENDING:
  EMA weight   = 1.0
  TSMOM weight = 1.2
  MeanRev      = abstain/disabled

RANGING:
  EMA weight   = 0.2
  TSMOM weight = 0.2
  MeanRev      = 1.0
```

Isso deve ser tratado como hipótese pré-registrada, não como configuração escolhida depois de olhar resultados.

---

## 15. Estratégias Declarativas em YAML

Outra ideia útil do `ai-hedge-fund` é separar composição de modelos do código.

Estrutura sugerida:

```text
config/
└── strategies/
    ├── ensemble_trend_v1.yaml
    ├── ensemble_regime_v1.yaml
    └── ensemble_low_turnover_v1.yaml
```

Exemplo:

```yaml
name: ensemble-trend-v1
symbol: EURUSD

models:
  - id: ema-trend
    weight: 1.0

  - id: time-series-momentum
    weight: 1.2

  - id: volatility-breakout
    weight: 0.5

blend:
  method: weighted_mean
  min_active_models: 2
  min_conviction: 0.30

signal_policy:
  enter_long: 0.30
  enter_short: -0.30
  exit_long_below: 0.05
  exit_short_above: -0.05
```

### Vantagens

- menos classes duplicadas;
- experimentos reproduzíveis;
- parâmetros explícitos;
- fácil hashing/versionamento;
- auditoria;
- comparação entre configurações;
- futura integração com Experiment Manager.

---

## 16. Novo Ledger de Alpha

Adicionar um ledger específico pode valer a pena:

```text
AlphaLedger
```

Ele deve registrar, para cada ciclo de decisão:

```text
timestamp
symbol
model_id
value
confidence
abstained
reason
metadata
```

Opcionalmente também:

```text
blended_value
strategy_decision
```

Isso facilita responder perguntas importantes:

- qual modelo contribuiu para cada trade?
- quais modelos estavam em desacordo?
- o modelo A adicionou informação ao B?
- trades lucrativos dependem sempre do mesmo modelo?
- existe alpha que só funciona em determinada sessão/regime?
- abstention reduz turnover?

---

## 17. Métricas Novas para Ensemble

Além das métricas financeiras existentes, adicionar métricas de diagnóstico de alpha.

### 17.1 Coverage

```text
% dos bars em que o modelo não abstém
```

### 17.2 Agreement Rate

```text
% de timestamps em que modelos possuem o mesmo sinal direcional
```

### 17.3 Disagreement Rate

Importante para verificar diversificação real de sinais.

### 17.4 Signal Turnover

Mudanças de direção do score / threshold crossing.

### 17.5 Trade Conversion Rate

```text
alpha views -> sinais operacionais -> trades executados
```

### 17.6 Incremental Contribution

Comparar:

```text
A
B
A+B
A+B+C
```

com protocolo de ablation.

### 17.7 Correlation of Alpha Streams

Se dois modelos geram praticamente a mesma série de score, combiná-los pode apenas duplicar o mesmo risco lógico.

---

## 18. Prioridade: Redução de Turnover

Dado o histórico atual do projeto, a primeira Meta-Strategy não deveria ter como objetivo maximizar quantidade de sinais.

Deveria tentar:

```text
menos trades
+
maior seletividade
+
melhor expectativa por trade
```

Hipóteses úteis:

### E01 — Consensus Filter

Entrar somente se pelo menos `N` modelos concordarem na direção.

### E02 — Conviction Threshold

Entrar somente quando o blended alpha exceder uma faixa mínima.

### E03 — Regime Gating

Usar trend models apenas em trend regime e mean-reversion apenas em range regime.

### E04 — Cooldown

Após saída, impedir reentrada por um número pré-definido de barras.

### E05 — Hysteresis

Usar thresholds de entrada e saída diferentes:

```text
entry = +0.40
exit  = +0.05
```

para evitar churn em torno de zero.

### E06 — Minimum Expected Move

Só aceitar sinal quando o movimento esperado normalizado superar um múltiplo do custo estimado.

Esse conceito é especialmente importante devido ao histórico de edges brutos menores que o round-trip.

---

## 19. Cost-Aware Gating sem Vazamento

É legítimo usar uma estimativa causal de custos para decidir se vale operar.

Exemplo:

```text
expected_move_pips > cost_estimate_pips * safety_factor
```

Requisitos:

- `cost_estimate` deve usar informação disponível no instante;
- não usar o custo realizado futuro;
- baseline fixo pode ser usado inicialmente;
- qualquer adaptação dinâmica de spread deve ser causal;
- manter decisão auditável em metadata.

Isso não significa otimizar a estratégia para o backtest. Significa modelar uma restrição econômica real:

> não operar quando o edge estimado não cobre fricção.

---

## 20. Ordem Recomendada de Implementação

### Fase A0 — ADR / contrato

Objetivo:

- registrar decisão arquitetural;
- definir semântica de `AlphaModel`, `AlphaSignal`, abstention e blend;
- congelar a regra de que Alpha Models nunca fazem sizing/execution.

Entregáveis:

```text
alpha/protocol.py
alpha/models.py
ADR em DECISIONS.md
```

### Fase A1 — Core Alpha Models

Implementar apenas contratos e testes.

Arquivos:

```text
alpha/__init__.py
alpha/protocol.py
alpha/models.py
alpha/blender.py
```

Testes mínimos:

- `value` fora de `[-1,+1]` rejeitado;
- timestamp timezone-aware obrigatório;
- metadata imutável;
- abstention validada;
- blender ignora abstidos;
- todos abstidos -> blended abstained;
- zero real não é abstention;
- pesos inválidos rejeitados;
- resultado determinístico.

### Fase A2 — Primeiro Adaptador de Estratégia para Alpha

Começar com **um** modelo.

Sugestão:

```text
TimeSeriesMomentumAlphaModel
```

Motivo:

TSMOM já mostrou algum edge bruto em parte dos testes, apesar de não sobreviver aos custos. Ele é um bom candidato para testar se gating/ensemble consegue reduzir trades ruins.

Comparar:

```text
TimeSeriesMomentumStrategy atual
vs
TimeSeriesMomentumAlphaModel + EnsembleStrategy (1 modelo)
```

Os resultados devem ser funcionalmente explicáveis antes de adicionar outros modelos.

### Fase A3 — `EnsembleStrategy`

Adicionar:

```text
strategy/ensemble.py
```

Primeira versão:

- weighted mean;
- `min_conviction`;
- entry/exit thresholds fixos;
- sem dynamic sizing;
- sem LLM;
- sem regime dynamic weights inicialmente.

### Fase A4 — Alpha Ledger / Diagnostics

Adicionar auditoria de scores e contribuições.

Objetivo:

> entender o ensemble antes de otimizar o ensemble.

### Fase A5 — Segundo e Terceiro Alpha

Sugestão de ordem:

1. `TimeSeriesMomentumAlphaModel`;
2. `EmaTrendAlphaModel`;
3. `RegimeAlphaModel` ou `RegimeGate`.

Evitar adicionar muitos modelos ao mesmo tempo.

### Fase A6 — Experimentos de Ensemble Pré-registrados

Criar um novo documento de hipóteses antes de rodar resultados.

Por exemplo:

```text
E01 Consensus Filter
E02 Regime Gating
E03 Hysteresis
E04 Cost-Aware Minimum Move
```

Cada hipótese deve definir:

- mecanismo;
- parâmetros;
- rationale;
- métricas;
- critérios de aceitação;
- ablations obrigatórias;
- período permitido;
- custo utilizado;
- regra de avanço para VAL/OOS.

### Fase A7 — Configuração Declarativa

Somente depois que o contrato de ensemble estiver estável, adicionar YAML loader.

Isso evita cristalizar cedo demais uma API de configuração.

### Fase A8 — Multi-Symbol Ensemble

Somente depois de comprovar utilidade em um pipeline simples.

Possibilidades:

- aplicar mesmo modelo em 7 majors;
- cross-sectional relative momentum;
- moeda-base aggregation;
- exposição agregada USD/EUR/JPY/GBP;
- limites de risco por moeda, não apenas por par.

Essa fase pode exigir evolução adicional do Portfolio/Risk.

### Fase A9 — LLM/Macro Agents (opcional)

Somente depois de existir infraestrutura point-in-time apropriada para dados macro/notícias.

Não iniciar essa fase apenas porque a interface suporta LLM.

---

## 21. LLM como Alpha Model Futuro

O padrão do `ai-hedge-fund` permite tratar um agente LLM como mais um analista.

No FOREX isso poderia resultar em:

```text
MacroUSDAlpha
MacroEURAlpha
CentralBankAlpha
MacroRegimeAlpha
NewsShockAlpha
```

Um exemplo conceitual:

```text
Fed stance             hawkish
ECB stance             neutral
US CPI surprise        positive
US 2Y yield change     positive
risk sentiment         neutral

             |
             v
      Macro EURUSD Alpha

value       = -0.62
confidence  = 0.78
```

### Regra inegociável

O LLM termina no `AlphaSignal`.

Nunca:

```text
LLM -> BUY 2.0 lots -> MT5
```

Sempre:

```text
LLM
 |
 v
AlphaSignal
 |
 v
EnsembleStrategy
 |
 v
Signal
 |
 v
RiskGate
 |
 v
Order
 |
 v
Execution
```

---

## 22. Requisito Point-in-Time para LLM/Macro

Essa é a principal barreira.

Um backtest histórico de agente macro só é válido se o snapshot histórico reproduzir a informação realmente disponível naquele instante.

Necessário, conforme o tipo de modelo:

- release timestamp original;
- valor inicialmente divulgado;
- consenso conhecido antes do release;
- revisões separadas do valor inicial;
- notícias com timestamp original;
- calendário de eventos;
- decisões de banco central;
- yields observáveis naquele instante;
- headlines sem informação posterior;
- versionamento/cache do prompt e input.

Não basta consultar hoje uma API que retorna séries históricas revisadas.

Sem essa camada, LLM deve ser limitado a:

```text
research exploratório fora de backtest formal
```

ou não ser utilizado.

---

## 23. Prompt Cache e Reprodutibilidade

Caso LLM seja adicionado no futuro, copiar conceitualmente a ideia de cache do `ai-hedge-fund`.

Persistir:

```text
agent_id
model_provider
model_name
system_prompt
user_prompt
input snapshot hash
raw response
parsed response
timestamp
```

Chave lógica baseada em hash do conteúdo.

Objetivos:

- reduzir custo;
- permitir replay;
- auditar mudanças;
- detectar prompt drift;
- impedir chamadas diferentes durante reexecução do mesmo backtest.

Mesmo com cache, o primeiro resultado de um LLM não deve ser tratado como determinístico da mesma forma que um modelo matemático.

---

## 24. Validação de Ensemble

O framework F8 existente deve continuar sendo autoridade.

Toda Meta-Strategy precisa passar por:

```text
DEV
 -> parameter neighborhood
 -> subperiods
 -> cost stress
 -> ablation
 -> VAL
 -> walk-forward quando aplicável
 -> OOS somente após freeze explícito
```

### 24.1 Ablation obrigatória

Para um ensemble A+B+C:

```text
A
B
C
A+B
A+C
B+C
A+B+C
```

Não é obrigatório rodar todas as combinações quando isso elevar excessivamente multiple testing, mas deve existir um plano de ablation pré-definido para demonstrar contribuição incremental.

### 24.2 Não aceitar melhoria apenas por redução de trades

Se um filtro reduz trades e melhora PnL, verificar:

- expectancy por trade;
- profit factor;
- retorno por unidade de turnover;
- estabilidade temporal;
- estabilidade entre pares;
- sensibilidade ao threshold.

### 24.3 Custos

Toda conclusão econômica deve usar custos explícitos.

Zero-cost continua útil apenas como diagnóstico de edge bruto.

---

## 25. CPCV / PBO — Ideia para Avaliação Futura

O `ai-hedge-fund` cita Combinatorial Purged Cross-Validation e Probability of Backtest Overfitting como evolução de validation.

Pode ser interessante estudar conceitos semelhantes no FOREX, especialmente se o número de estratégias/configurações aumentar.

Entretanto:

- não adicionar CPCV apenas por sofisticação;
- garantir purging/embargo compatível com horizonte dos trades;
- avaliar custo computacional;
- manter walk-forward como referência temporal intuitiva;
- PBO só é útil se houver um conjunto coerente de configurações candidatas.

Esta fase é secundária ao Alpha/Ensemble core.

---

## 26. Estrutura de Diretórios Sugerida

```text
FOREX/
|
├── alpha/
│   ├── __init__.py
│   ├── protocol.py
│   ├── models.py
│   ├── blender.py
│   ├── ledger.py
│   │
│   ├── quant/
│   │   ├── __init__.py
│   │   ├── ema_trend.py
│   │   ├── time_series_momentum.py
│   │   ├── volatility_breakout.py
│   │   ├── mean_reversion.py
│   │   └── regime.py
│   │
│   └── llm/                  # futuro / opcional
│       ├── __init__.py
│       ├── protocol.py
│       ├── cache.py
│       ├── macro.py
│       └── news.py
│
├── strategy/
│   ├── ... existentes ...
│   └── ensemble.py
│
├── config/
│   └── strategies/
│       └── ... YAML futuro ...
│
├── backtest/
│   └── ... manter arquitetura atual ...
│
├── execution/
│   └── ... manter arquitetura atual ...
│
└── risk/
    └── ... manter arquitetura atual ...
```

---

## 27. Compatibilidade e Migração

A implementação deve ser **aditiva**.

### Não quebrar

- `Strategy` Protocol existente;
- `Signal` existente;
- `RiskGate` existente;
- `BacktestEngine.run()`;
- `OrderFactory`;
- `SimulatedExecution`;
- ledgers existentes;
- pesquisas baseline.

### Estratégias antigas continuam válidas

```text
SimpleEmaTrendStrategy
VolatilityBreakoutStrategy
TimeSeriesMomentumStrategy
...
```

continuam executáveis.

`EnsembleStrategy` será apenas outra Strategy.

Isso permite comparação direta e reduz risco de regressão.

---

## 28. Testes Mínimos Antes do Primeiro Experimento

### Unit tests

- `AlphaSignal` invariants;
- abstention;
- metadata immutability;
- weighted blending;
- all-abstain;
- neutral vs abstain;
- model weight validation;
- threshold policy;
- deterministic order of contributors;
- same inputs -> same outputs para modelos quant;
- strategy never exposes full DataFrame;
- no future bar access.

### Integration tests

- `BacktestEngine` executa `EnsembleStrategy` sem modificação;
- RiskGate recebe `Signal` normal;
- execution permanece idêntica;
- Alpha layer não acessa broker;
- AlphaLedger timestamps coincidem com BAR_CLOSE;
- next-bar-open continua preservado.

### Regression

Todos os testes atuais precisam permanecer verdes.

---

## 29. Critérios de Sucesso da Primeira Implementação

A implementação de Alpha/Ensemble é considerada tecnicamente bem-sucedida quando:

```text
[ ] contratos AlphaModel/AlphaSignal estáveis
[ ] abstention explicitamente suportado
[ ] blender determinístico
[ ] uma estratégia atual convertida em AlphaModel
[ ] EnsembleStrategy executa no BacktestEngine existente
[ ] RiskGate e Execution não foram alterados por necessidade do ensemble
[ ] Alpha outputs auditáveis
[ ] todos os testes existentes continuam passando
[ ] novos testes de alpha passam
[ ] resultado de um ensemble de 1 modelo é explicável contra baseline
```

O sucesso técnico **não implica edge econômico**.

---

## 30. Critérios de Sucesso Científico

Uma hipótese de ensemble só deve ser considerada promissora se mostrar, antes do OOS:

- melhoria em expectativa líquida;
- custos explícitos cobertos;
- robustez em subperíodos;
- ausência de ilha estreita de parâmetros;
- contribuição incremental explicável;
- turnover menor ou economicamente justificável;
- estabilidade de comportamento;
- resultado não concentrado em poucos outliers;
- validade em VAL;
- protocolo de pesquisa respeitado.

O OOS deve permanecer protegido até freeze formal.

---

## 31. Primeiros Experimentos Recomendados

### Experimento E01 — TSMOM + Conviction Threshold

Objetivo:

> Verificar se a fraqueza do TSMOM atual decorre parcialmente de operar sinais de baixa intensidade.

Comparar:

```text
TSMOM baseline
vs
TSMOM Alpha + threshold
```

Métricas principais:

- trade count;
- gross edge;
- net edge;
- expectancy;
- turnover;
- cost / gross profit;
- estabilidade por subperíodo.

### Experimento E02 — TSMOM + EMA Consensus

Hipótese:

> executar somente quando tendência de curto/médio prazo e momentum concordarem pode eliminar parte dos trades marginais.

Ablation:

```text
TSMOM
EMA
TSMOM + EMA consensus
```

### Experimento E03 — Regime Gating

Hipótese:

> TSMOM/EMA têm melhor qualidade em regime direcional e Mean Reversion em regime lateral.

Não usar regime para recalibrar o passado depois do resultado.

### Experimento E04 — Hysteresis

Hipótese:

> separar entrada e saída por bandas reduz churn sem destruir o edge bruto.

Exemplo conceitual:

```text
enter long >= +0.40
exit long  <= +0.05
```

### Experimento E05 — Cost-aware Filter

Hipótese:

> sinais cujo movimento esperado é inferior à fricção não devem gerar operação.

Usar estimator causal e pré-definido.

---

## 32. O Que Evitar

Evitar nesta fase:

- dezenas de Alpha Models simultaneamente;
- otimização automática de weights;
- Bayesian/Genetic optimization sem hipótese clara;
- weights aprendidos no dataset inteiro;
- dynamic sizing baseado em score antes de calibrar o score;
- LLM usando notícias sem snapshot point-in-time;
- permitir ao LLM criar `Order`;
- alterar RiskGate para acomodar resultado de backtest;
- reabrir OOS repetidamente;
- selecionar ensemble depois de testar centenas de combinações sem correção para multiple testing;
- considerar `confidence` do LLM como probabilidade calibrada sem validação.

---

## 33. Prioridade Recomendada

Ordem sugerida:

```text
1. AlphaSignal + AlphaModel
        |
2. AlphaBlender + abstention
        |
3. TSMOM Alpha
        |
4. EnsembleStrategy com 1 modelo
        |
5. AlphaLedger / diagnostics
        |
6. EMA Alpha
        |
7. Experimento TSMOM + EMA
        |
8. Regime gating
        |
9. Hysteresis / turnover reduction
        |
10. Cost-aware gating
        |
11. Configuração YAML
        |
12. Multi-symbol ensemble
        |
13. LLM/Macro somente com dados point-in-time
```

---

## 34. Decisão Recomendada

A recomendação arquitetural final é:

> **Manter o FOREX como plataforma principal de backtest, risco, execução e validação; utilizar o `ai-hedge-fund` apenas como referência para criar uma nova camada de Alpha Models, blending, abstention e composição declarativa de estratégias.**

Essa abordagem preserva os investimentos já feitos no projeto e ataca o problema que os resultados atuais indicam ser o mais relevante: encontrar combinações de sinais que produzam edge econômico após custos, sem sacrificar rigor temporal e científico.

---

## 35. Próximo PR Sugerido

Escopo propositalmente pequeno:

```text
feat: add alpha model core contracts
```

Arquivos:

```text
alpha/__init__.py
alpha/models.py
alpha/protocol.py
alpha/blender.py

tests/test_alpha_models.py
tests/test_alpha_blender.py
```

Sem ainda:

- converter estratégias;
- alterar BacktestEngine;
- adicionar YAML;
- adicionar LLM;
- alterar RiskGate;
- alterar Execution.

Definition of Done:

```text
[ ] AlphaSignal imutável
[ ] AlphaModel Protocol
[ ] weighted blender
[ ] abstention
[ ] validação rigorosa
[ ] testes unitários
[ ] suite existente verde
```

Depois desse PR, o segundo PR recomendado seria:

```text
feat: add time-series momentum alpha adapter
```

E o terceiro:

```text
feat: add ensemble strategy baseline
```

Essa divisão mantém cada mudança pequena, auditável e reversível.

---

## 36. Referências Técnicas

### FOREX

Principais arquivos relevantes:

```text
backtest/engine.py
backtest/context.py
backtest/strategy.py
backtest/models/signal.py
backtest/risk.py
strategy/
execution/interface.py
execution/mt5_execution.py
docs/14_RISK_MANAGEMENT.md
docs/15_ROBUSTNESS.md
docs/16_EXECUTION_LAYER.md
docs/26_RESEARCH_HYPOTHESES.md
docs/27_hypotheses_test_report.md
```

### ai-hedge-fund

Conceitos analisados principalmente em:

```text
hedge_fund/signals/base.py
hedge_fund/signals/llm_agent.py
hedge_fund/portfolio/construction.py
hedge_fund/risk/limits.py
hedge_fund/pipeline/run_cycle.py
hedge_fund/strategies/*.yaml
```

Repositório:

```text
https://github.com/virattt/ai-hedge-fund
```

Commit de referência desta análise:

```text
eff8a7320fcf0b473b135690fa1a5b0d9b022a83
```

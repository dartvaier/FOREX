# 25 — Post-Audit Hardening Plan

## 1. Objetivo

Este documento registra o plano de correções obrigatórias identificado após a auditoria técnica do estado atual da plataforma em `feature/backtest-core-models`.

O objetivo deste ciclo não é procurar uma nova Strategy nem avançar para capital real.

O objetivo é fortalecer as invariantes de:

```text
Execution Safety
Risk Composition
Multi-Currency Financial Integrity
Live Readiness / Audit Integrity
```

antes de qualquer novo programa de pesquisa ou decisão de live trading.

Este plano deve ser executado **em sequência**.

```text
v0.6.1 Execution Safety Hardening
        ↓
v0.6.2 Risk Composition
        ↓
v0.6.3 Multi-Currency Financial Integrity
        ↓
v0.6.4 Readiness & Audit Integrity
        ↓
novo programa de pesquisa, se desejado
```

---

## 2. Estado de Entrada

Estado observado na auditoria:

```text
F0-F8            completos
F9 Demo          executado e documentado
F10 Readiness    parcialmente implementado
Backtest         determinístico / bar-by-bar
Research         Dev / Val / OOS / Walk-Forward disponíveis
Risk             Fixed / StopBased / Exposure / DailyLoss /
                 Drawdown / KillSwitch
Execution        MT5 adapter + validation + reconciliation /
                 monitoring / audit / comparison
Multi-symbol     7 majors no registry
Currency         quote->USD implementado no Portfolio
```

A auditoria concluiu que a arquitetura geral permanece sólida, porém existem pontos que devem ser corrigidos antes de tratar a plataforma como plenamente hardened para execução.

---

# 3. Regra de Prioridade

Durante este ciclo:

```text
P0 Safety / estado do broker
P1 Integridade financeira
P2 Readiness / documentação
P3 Nova pesquisa
```

Nenhuma nova estratégia deve ter prioridade sobre um P0 ou P1 aberto.

---

# 4. v0.6.1 — Execution Safety Hardening

## Status

```text
DONE (2026-08-12)
```

## Objetivo

Garantir que o adapter MT5 não dependa de mocks incorretos, não envie ordens sem todas as precondições obrigatórias e nunca represente incorretamente uma execução que já ocorreu no broker.

---

## ES-01 — Corrigir cancelamento de ordem MT5

### Problema

O adapter atual usa uma superfície semelhante a:

```python
mt5.order_delete(order_id)
```

O mock dos testes também expõe `order_delete()`, o que permite que a suíte fique verde mesmo que essa operação não corresponda à API real utilizada pelo MetaTrader5 Python package.

### Implementação esperada

Usar a operação oficial de remoção/cancelamento via request apropriado de `order_send()` para pending orders.

A implementação deve:

```text
receber o identificador correto da ordem do broker
montar request de remoção
chamar order_send
traduzir retcode
produzir ExecutionReport auditável
```

### Testes obrigatórios

```text
cancel disabled -> nenhum broker call
cancel request usa action correta
broker aceita cancelamento
broker rejeita cancelamento
retcode desconhecido é preservado no relatório
mock não deve inventar API inexistente
```

### Critério de aceite

```text
[x] cancel usa somente superfície suportada pelo adapter MT5 real
[x] testes reproduzem a API real utilizada
[x] nenhuma regressão nos submits existentes
```

### Commit sugerido

```text
fix(execution): use MT5 order removal request for cancellation
```

---

## ES-02 — Corrigir filling mode

### Problema

A interpretação de `symbol_info().filling_mode` deve respeitar exatamente os valores/flags expostos pelo MT5.

A implementação atual não deve assumir que todo bit disponível mapeia diretamente para `ORDER_FILLING_RETURN`.

### Implementação esperada

Criar uma função explícita e testável para selecionar o filling policy compatível com:

```text
FOK
IOC
RETURN quando permitido pelo execution mode
BoC apenas quando aplicável a tipos de ordem compatíveis
```

Market order não deve receber filling policy incompatível com o símbolo.

### Testes obrigatórios

```text
FOK
IOC
RETURN permitido
BoC não tratado como RETURN
sem filling conhecido
símbolo desconhecido
retcode 10030 regression
```

### Critério de aceite

```text
[x] seleção de filling possui regra documentada
[x] bit/enum do broker não é interpretado por suposição
[x] regression test cobre retcode 10030
```

### Commit sugerido

```text
fix(execution): align MT5 filling policy with broker capabilities
```

---

## ES-03 — Demo e broker preconditions no caminho obrigatório de submit

### Problema

Hoje existem validações independentes para:

```text
trade mode
server
TRADING_ENABLED
kill switch
symbol
quantity
stop
margin
```

mas elas não formam necessariamente um único gate obrigatório imediatamente antes do `order_send()`.

`trading_enabled=True` não deve ser suficiente para alcançar o broker.

### Implementação esperada

Fluxo obrigatório:

```text
submit(order)
  ↓
trading flag
  ↓
account snapshot
  ↓
account mode / environment policy
  ↓
kill switch
  ↓
broker preconditions
  ↓
order validation
  ↓
order_send
```

Para o estágio atual da plataforma:

```text
trade_mode == demo
```

deve ser a política padrão permitida.

Qualquer futura permissão de conta real deve exigir uma política separada e explícita, não apenas `trading_enabled=True`.

### Testes obrigatórios

```text
real account bloqueada
unknown account mode bloqueado
server fora da allowlist bloqueado
kill switch armado bloqueado
TRADING_ENABLED false bloqueado
símbolo fora da allowlist bloqueado
ordem inválida não alcança order_send
ordem válida em demo alcança broker
```

### Critério de aceite

```text
[x] nenhuma chamada mutável ao broker ignora o gate final
[x] conta real não pode executar por acidente
[x] kill switch é checado no caminho de submit
[x] ambiente Demo continua funcionando
```

### Commit sugerido

```text
fix(execution): enforce broker safety preconditions before submit
```

---

## ES-04 — Não transformar Fill real em REJECTED local

### Problema

Uma ordem pode ser executada pelo broker e posteriormente falhar em uma validação local de:

```text
slippage
quantity
latency
outro invariant de fill
```

Depois que o broker executou, o fato econômico não pode ser convertido em "não executado" apenas porque a validação local falhou.

Fluxo proibido:

```text
broker FILLED
  ↓
validation failed
  ↓
platform REJECTED
```

Isso pode produzir posição órfã.

### Implementação esperada

Separar:

```text
broker execution status
```

from:

```text
local validation verdict
```

Uma possibilidade é um modelo equivalente a:

```text
broker_status = FILLED
validation_status = OUTSIDE_TOLERANCE
requires_reconciliation = true
```

O nome exato do modelo pode variar; a invariante não.

### Ação de segurança esperada

Quando um fill real viola tolerância:

```text
preservar FILLED
registrar violation
acionar/recomendar kill switch
reconciliar broker x plataforma
não enviar nova ordem automaticamente
```

### Testes obrigatórios

```text
FILLED dentro da tolerância
FILLED fora da tolerância continua sendo FILLED
violation fica auditável
reconciliation pode detectar estado real
nenhuma duplicação/reenvio automático
```

### Critério de aceite

```text
[x] execução real nunca é apagada pela camada de validação
[x] violation é representável no modelo
[x] estado exige reconciliação antes de continuar
```

### Commit sugerido

```text
fix(execution): preserve broker fills when validation flags violations
```

---

## ES-05 — Pip size por instrumento no Fill Validation

### Problema

Validação de slippage não pode assumir universalmente:

```text
pip_size = 0.0001
```

Exemplo:

```text
EURUSD pip = 0.0001
USDJPY pip = 0.01
```

### Implementação esperada

`validate_fill()` deve receber o pip size real do instrumento ou uma `InstrumentSpecification`/policy equivalente.

### Testes obrigatórios

```text
EURUSD slippage
USDJPY slippage
instrumento 5 digits
instrumento 3 digits
limite exatamente no boundary
```

### Critério de aceite

```text
[x] nenhuma validação multi-symbol usa pip default implícito
```

### Commit sugerido

```text
fix(execution): validate fill slippage with instrument pip size
```

---

## Definition of Done — v0.6.1

```text
[x] ES-01 cancel MT5 corrigido
[x] ES-02 filling mode corrigido
[x] ES-03 broker safety gate obrigatório
[x] ES-04 Fill real preservado em violations
[x] ES-05 pip size multi-symbol
[x] focused tests verdes
[x] execution tests verdes
[x] non-integration suite verde
[x] docs/16 e docs/17 atualizados
[x] CHANGELOG atualizado
```

Gate:

> v0.6.2 só começa depois de v0.6.1 verde.

---

# 5. v0.6.2 — Risk Composition

## Status

```text
DONE (2026-08-12)
```

## Objetivo

Garantir que RiskGates composicionais mantenham seu estado corretamente independentemente da ordem dos wrappers.

---

## RC-01 — Propagação de EquityPoint em wrappers

### Problema

O Engine observa apenas o `risk_gate` externo.

Uma composição como:

```text
KillSwitch
  ↓
Drawdown
  ↓
DailyLoss
  ↓
StopBased
```

pode impedir que gates internos stateful recebam `observe_equity()`.

### Implementação esperada

Formalizar uma capacidade de observação, por exemplo:

```python
class EquityObserver(Protocol):
    def observe_equity(self, point: EquityPoint) -> None:
        ...
```

Wrappers devem propagar a observação para o inner quando aplicável.

### Invariante

A ordem de composição não pode silenciosamente desativar:

```text
DailyLoss
Drawdown
```

### Testes obrigatórios

Composição real:

```text
KillSwitchRiskGate(
  DrawdownRiskGate(
    DailyLossRiskGate(
      StopBasedRiskGate(...)
    )
  )
)
```

Cobrir:

```text
equity chega ao DailyLoss
equity chega ao Drawdown
daily lock funciona
drawdown lock funciona
EXIT continua permitido
kill switch soft continua permitido para EXIT
inner rejection é preservada
```

### Critério de aceite

```text
[x] wrappers stateful recebem equity independentemente da composição
[x] testes usam cadeia real, não apenas gates isolados
```

### Commit sugerido

```text
fix(risk): propagate equity observations through composed gates
```

---

## RC-02 — Política do Kill Switch HARD

### Problema

O modo HARD pode bloquear EXIT.

Isso pode ser útil como freeze operacional em situações específicas, mas não deve ser confundido com o comportamento de emergência padrão de redução de risco.

### Implementação esperada

Documentar explicitamente:

```text
SOFT = emergency risk stop padrão
       bloqueia novas entradas
       permite reduzir/fechar exposição

HARD = operational freeze excepcional
       pode bloquear exits
       exige justificativa/operator action
```

Avaliar renomear a opção para tornar o risco explícito, por exemplo:

```text
freeze_all_orders
```

em vez de apenas `block_exits`.

### Testes obrigatórios

```text
soft permite EXIT
hard bloqueia EXIT somente quando explicitamente configurado
reset é manual
```

### Critério de aceite

```text
[x] default permanece exposure-reducing
[x] hard mode não pode ser ativado implicitamente
[x] docs explicam quando ele pode ser usado
```

---

## Definition of Done — v0.6.2

```text
[x] RC-01 observer propagation
[x] RC-02 kill switch policy documentada
[x] chain regression test
[x] risk tests verdes
[x] engine integration verde
[x] non-integration suite verde
[x] docs/14 atualizado
[x] DECISIONS atualizado se houver mudança arquitetural
[x] CHANGELOG atualizado
```

Gate:

> v0.6.3 só começa depois da cadeia de RiskGate ter regression test explícito.

---

# 6. v0.6.3 — Multi-Currency Financial Integrity

## Status

```text
DONE (2026-08-12)
```

## Objetivo

Garantir que todos os valores monetários usados por Portfolio, Risk, Trade audit e research estejam na mesma account currency.

A correção atual de quote->USD no Portfolio é necessária, mas não é suficiente para toda a stack.

---

## MC-01 — StopBasedRiskGate em account currency

### Problema

Hoje o sizing conceitual usa:

```text
risk_amount = account equity em USD
risk_per_lot = stop distance × contract size
```

Para quote currency diferente de USD, `risk_per_lot` nasce em moeda de cotação.

Exemplo:

```text
USDJPY
risk_amount -> USD
risk_per_lot -> JPY
```

Esses valores não podem ser divididos diretamente.

### Implementação esperada

Converter o risco por lote para account currency usando taxa causal disponível no instante da decisão.

### Testes obrigatórios

```text
EURUSD sizing regression
USDJPY sizing manual
USDCHF sizing manual
USDCAD sizing manual
volume step depois da conversão
```

### Critério de aceite

```text
[x] risk_amount e risk_per_lot usam a mesma moeda
```

### Commit sugerido

```text
fix(risk): size positions in account currency
```

---

## MC-02 — ExposureLimitRiskGate em account currency

### Problema

`max_notional` deve possuir semântica monetária explícita.

Não deve existir ambiguidade entre:

```text
base notional
quote notional
account-currency exposure
```

### Implementação esperada

Definir uma única política para `max_notional` e refletir o nome/documentação no código.

Se o limite representar account currency, fazer a conversão necessária antes da comparação.

### Testes obrigatórios

```text
EURUSD
USDJPY
USDCHF
USDCAD
boundary exato
```

---

## MC-03 — TradeFactory spread/slippage em account currency

### Problema

`TradeFactory` transforma price distance em valor monetário.

Para pares com quote != account currency, o resultado precisa ser convertido antes de entrar no ledger.

Caso contrário, campos como:

```text
spread_cost
slippage_cost
total_cost_paid
```

podem misturar JPY/CHF/CAD com comissão em USD.

### Implementação esperada

Converter os custos auditados com taxa causal apropriada do trade.

O PnL não deve ter custos subtraídos duas vezes.

### Testes obrigatórios

```text
EURUSD cost audit regression
USDJPY spread/slippage em USD
commission permanece USD
total_cost_paid usa uma única moeda
net_pnl não sofre double count
```

### Critério de aceite

```text
[x] todo campo monetário do Trade é account-currency consistente
```

---

## MC-04 — Corrigir classificação USD-base / USD-quote nos testes

### Problema

Testes existentes agrupam pares como USDCHF/USDCAD junto a pares USD-quote em algumas verificações.

Classificação correta:

```text
USD-quote:
EURUSD
GBPUSD
AUDUSD
NZDUSD

USD-base:
USDJPY
USDCHF
USDCAD
```

### Critério de aceite

```text
[x] testes usam estrutura monetária correta do instrumento
```

---

## MC-05 — Reexecutar matriz afetada

Após as correções:

```text
USDJPY
USDCHF
USDCAD
```

precisam ter os baselines relevantes rerodados para confirmar que conclusões documentadas continuam válidas.

Não consultar novo OOS.

Prioridade:

```text
DEV regression
```

### Critério de aceite

```text
[x] resultados rerodados
[x] diferenças explicadas
[x] docs/21 e docs/22 atualizados
[x] nenhuma conclusão antiga mantida sem reconferência
```

### Commit sugerido

```text
fix(backtest): make multi-currency accounting consistent end to end
```

---

## Definition of Done — v0.6.3

```text
[x] StopBased account-currency safe
[x] Exposure semantics explícita
[x] Trade costs em account currency
[x] testes de USD-base corrigidos
[x] USDJPY/USDCHF/USDCAD rerodados em DEV
[x] currency tests verdes
[x] risk tests verdes
[x] research regression verde
[x] non-integration suite verde
[x] docs/21-22 atualizados
[x] CHANGELOG atualizado
```

Gate:

> v0.6.4 só começa depois de todos os valores financeiros relevantes terem unidade explícita.

---

# 7. v0.6.4 — Readiness & Audit Integrity

## Status

```text
DONE (2026-08-12)
```

## Objetivo

Fazer com que a classificação de readiness represente garantias realmente verificadas pelo código e sincronizar a documentação com o estado real.

---

## RA-01 — Risk per trade realmente validado

### Problema

`RiskLimitConfig` possui `risk_per_trade_pct`, mas a avaliação agregada de readiness não deve afirmar que esse limite foi verificado se ele não participa da decisão.

### Implementação esperada

Adicionar entrada explícita de risco atual da ordem/trade ou remover a afirmação de que esse item é validado até que a informação exista.

### Critério de aceite

```text
[x] risk_per_trade_pct participa efetivamente da review
```

---

## RA-02 — Separar Exposure de Leverage

### Problema

Exposure e leverage não devem ser duas labels para exatamente a mesma expressão sem semântica adicional.

### Implementação esperada

Definir:

```text
exposure
leverage
```

com significado financeiro explícito.

Exemplo possível:

```text
exposure = gross account-currency notional / equity
leverage = broker/account leverage or gross notional / equity
```

Se ambos permanecerem matematicamente iguais, manter apenas uma policy ou justificar limites diferentes sem redundância enganosa.

### Critério de aceite

```text
[x] duas métricas diferentes têm semântica diferente
OU
[x] uma delas é removida
```

---

## RA-03 — Padronizar unidades percentuais

### Problema

Existem componentes usando convenções diferentes:

```text
0.10 = 10%
```

versus:

```text
10.0 = 10%
```

Isso é perigoso em configuração de risco.

### Política recomendada

Padronizar frações:

```text
0.10  = 10%
0.03  = 3%
0.005 = 0.5%
```

Preferir nomes como:

```text
*_fraction
```

quando possível.

Se uma API pública existente não puder ser alterada imediatamente, adicionar nomes/unidades explícitos e testes de boundary.

### Testes obrigatórios

```text
0.10 -> 10%
0.01 -> 1%
limite exato
config inválida > 1 quando fração
```

---

## RA-04 — Zero-cost report coerente

### Problema

Um report com `cost_mode=zero` não deve apresentar análise de round-trip baseada nos parâmetros explícitos de custo como se esses custos tivessem sido pagos.

### Implementação esperada

Para zero-cost:

```text
effective spread = 0
effective slippage = 0
effective commission = 0
round_trip_cost_money = 0
round_trip_cost_pips = 0
```

Os custos baseline podem ser registrados separadamente apenas como referência, nunca como custo efetivamente aplicado.

### Critério de aceite

```text
[x] zero-cost report não contém custo efetivo não-zero
```

---

## RA-05 — OOS wording / lockbox integrity

### Problema

O período 2024-2026 já foi consultado uma vez.

Ele pode continuar proibido para tuning, mas não deve ser descrito como novamente "unseen".

### Terminologia recomendada

```text
LEGACY OOS / previously observed holdout
```

Para pesquisas futuras:

```text
DEV
VALIDATION
LEGACY OOS (já observado)
NEW HOLDOUT (realmente não observado)
```

### Critério de aceite

```text
[x] docs não afirmam que um OOS já visto voltou a ser unseen
[x] futuras hipóteses distinguem legacy OOS de novo holdout
```

---

## RA-06 — Sincronizar documentação de estado

Arquivos mínimos:

```text
AGENTS.md
README.md
DECISIONS.md
CHANGELOG.md
docs/11_ROADMAP.md
docs/14_RISK_MANAGEMENT.md
docs/16_EXECUTION_LAYER.md
docs/17_LIVE_READINESS.md
```

Corrigir estados antigos como:

```text
READ ONLY absoluto
IMPLEMENTATION PENDING já implementado
Backtest futuro já existente
F10 pronta quando ainda há hardening pendente
```

Estado recomendado após este ciclo:

```text
Research/Backtest           ENABLED
Demo execution capability   IMPLEMENTED / guarded
Default mutable execution   DISABLED
Live capital execution      NOT AUTHORIZED
```

### Critério de aceite

```text
[x] documentação não contradiz testes/código
[x] DECISIONS deixa de marcar features implementadas como FUTURE
[x] README reflete estado real
[x] AGENTS mantém guardrails atuais
```

---

## RA-07 — CI visível para commits

### Objetivo

A suíte local é extensa, mas o repositório deve conseguir mostrar evidência remota mínima para commits/PRs.

### Implementação sugerida

GitHub Actions para:

```text
python setup
install dependencies
pytest -m "not integration" -q
```

Testes que exigem MT5 continuam fora do CI padrão.

### Critério de aceite

```text
[x] commit/PR exibe check remoto da suíte non-integration
```

---

## Definition of Done — v0.6.4

```text
[x] risk per trade verificado
[x] exposure/leverage semanticamente corretos
[x] unidades percentuais padronizadas
[x] zero-cost report coerente
[x] legacy OOS documentado corretamente
[x] documentação sincronizada
[x] CI non-integration disponível
[x] readiness tests verdes
[x] full non-integration suite verde
```

---

# 8. Ordem Obrigatória de Implementação

A sequência operacional recomendada é:

```text
01 ES-01 cancel MT5
02 ES-02 filling mode
03 ES-03 mandatory broker safety gate
04 ES-04 preserve real Fill on validation violation
05 ES-05 instrument pip size

06 RC-01 equity observer propagation
07 RC-02 kill switch hard-mode policy

08 MC-01 StopBased currency conversion
09 MC-02 Exposure semantics
10 MC-03 TradeFactory monetary conversion
11 MC-04 currency classification tests
12 MC-05 rerun affected DEV matrix

13 RA-01 risk-per-trade readiness
14 RA-02 exposure vs leverage
15 RA-03 percentage units
16 RA-04 zero-cost report
17 RA-05 OOS terminology
18 RA-06 docs synchronization
19 RA-07 CI
```

Não pular um bloco apenas porque a suíte atual está verde.

Os itens existem justamente porque alguns problemas podem estar mascarados por mocks ou ausência de testes de integração arquitetural.

---

# 9. Processo para Cada Item

Todo item deve seguir:

```text
1. reproduzir o problema
2. escrever regression test que falha
3. confirmar a causa
4. fazer a menor correção correta
5. focused tests
6. related tests
7. non-integration suite
8. revisar diff
9. documentar decisão relevante
10. commit pequeno
```

Não acumular vários P0 em um único commit grande quando puderem ser auditados separadamente.

---

# 10. Regras Durante o Hardening

## Não fazer

```text
nova busca de parâmetros
nova consulta OOS para melhorar Strategy
ativação de conta real
aumento de lote Demo para validar código
refactor amplo sem regression test
alterar mocks para apenas fazer testes passarem
```

## Permitido

```text
fixtures sintéticas
fake MT5 fiel à API usada
smoke read-only
Demo mínima somente quando necessária e explicitamente autorizada
rerun DEV para regression financeira
```

---

# 11. Critério para Retomar Pesquisa de Edge

Um novo programa de pesquisa só deve ser aberto após:

```text
[x] v0.6.1
[x] v0.6.2
[x] v0.6.3
[x] v0.6.4
```

E deve ser estruturalmente novo.

Não reabrir simplesmente:

```text
EMA
TSM
Mean Reversion
```

com mais parâmetros.

Possíveis direções futuras, apenas como agenda de pesquisa:

```text
cross-sectional relative strength entre majors
carry com dados reais de juros/swap
session/regime hypotheses com custo variável
portfolio-level multi-symbol research
feature research pré-registrado
ML/HMM somente como projeto separado
```

Nenhuma dessas ideias é considerada edge até passar pelo pipeline de validação.

---

# 12. Nova Terminologia para o Estado da Pesquisa

Em vez de:

```text
BUSCA DE EDGE ENCERRADA
```

preferir:

```text
PROGRAMA DE PESQUISA DOS BASELINES ATUAIS ENCERRADO
```

Isso significa que as especificações atuais foram rejeitadas.

Não significa que foi demonstrada inexistência de edge em Forex como mercado.

---

# 13. Estado de Live Durante o Hardening

Até o Definition of Done deste documento:

```text
Research                 PERMITIDO
Backtest                 PERMITIDO
Read-only MT5            PERMITIDO
Demo execution           SOMENTE quando explicitamente necessário/autorizado
Real-money execution     NÃO AUTORIZADO
```

O simples fato de:

```python
MT5Execution(trading_enabled=True)
```

existir no código não constitui autorização para capital real.

---

# 14. Critério de Fechamento do Hardening

O ciclo será considerado concluído quando:

```text
[ ] todos os P0 corrigidos
[ ] todos os P1 corrigidos
[ ] RiskGate composto validado por regression test
[ ] monetary units consistentes para USD-base e USD-quote
[ ] readiness representa checks reais
[ ] documentação sincronizada
[ ] non-integration suite verde
[ ] CI remoto verde
[ ] nenhuma execução real necessária para comprovar os itens
```

Depois disso o projeto pode decidir entre:

```text
A) permanecer research/demo platform
B) abrir um novo programa de pesquisa
C) desenvolver portfolio-level multi-symbol risk
D) continuar hardening operacional
```

Nenhuma dessas opções implica automaticamente live trading.

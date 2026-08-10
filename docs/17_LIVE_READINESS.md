# Live Readiness (F10)

## 1. Objetivo

Este documento registra a fase:

```text
F10 - Live Readiness
```

Status:

```text
IN PROGRESS - review programatica implementada
```

F10 nao significa comecar a operar capital real (roadmap §89). Significa
avaliar, de forma auditavel, se a infraestrutura esta pronta para essa
decisao — e o §93 permite que o projeto permaneca indefinidamente como
research/backtest/demo platform.

## 2. Review programatica

`readiness/review.py` codifica o checklist de pre-requisitos (§90) e as
dimensoes da review (§91). A avaliacao combina:

```text
evidencia programatica real (modulos importaveis no momento)
flags de decisao do operador (ativacao demo, validacao demo, etc.)
```

Uso:

```powershell
python -c "from readiness import ReadinessState, evaluate_readiness; \
r = evaluate_readiness(ReadinessState(backtest_done=True, oos_done=True, \
cost_stress_done=True, risk_engine_done=True, ops_procedures_documented=True)); \
print('READY:', r.ready); [print(i.category, i.item_id, i.satisfied) for i in r.items]"
```

### Estado atual (2026-08-10)

| Categoria | Item | Status | Evidencia |
|---|---|---|---|
| validation | backtest | OK | F5-F6, 995 testes |
| validation | oos | OK | lockbox consultado (docs/15) |
| validation | cost_stress | OK | 1.5x/2.0x (docs/15) |
| risk | risk_engine | OK | F7 (sizing + limites) |
| risk | kill_switch | OK | backtest.risk importavel |
| execution | adapter | OK | execution.mt5_execution importavel |
| execution | order_validation | OK | module presente |
| execution | fill_validation | OK | module presente |
| execution | reconciliation | OK | module presente |
| execution | broker_validation | OK | module presente |
| execution | monitoring | OK | module presente |
| execution | audit_log | OK | module presente |
| execution | demo_validation | PENDENTE | depende da ativacao demo |
| operations | trading_flag | PENDENTE | TRADING_ENABLED=false (decisao do operador) |
| operations | ops_procedures | OK | este documento (§6) |

## 3. Risk Limits

`readiness/risk_limits.py` — dimensoes §91 como funcoes puras:

```text
risk_amount(balance, risk_pct)                  capital em risco por trade
stop_distance_pips(entry, stop, pip_size)       distancia do stop em pips
position_size_for_risk(risk_amount, stop, pip)  lote para risco alvo
evaluate_risk_limits(balance, equity, daily_loss,
                     drawdown, exposure, config) -> violacoes
```

Limites default (configuraveis):

```text
risk_per_trade_pct    = 1.0%
max_daily_loss_pct    = 3.0%
max_drawdown_pct      = 10.0%
max_leverage          = 20x
max_exposure_pct      = 50% do equity
```

## 4. Safety

`readiness/safety.py` — deteccao pura para as procedures:

```text
duplicate_order_ids(ids)          ids duplicados (protecao anti-duplicata)
connection_breach_count(beats)    heartbeats falhos consecutivos no final
order_count_per_symbol(orders)    turnover por simbolo
```

## 5. Limites de decisao (capital real)

Qualquer alocacao real (§92) e decisao separada do operador. O saldo
virtual da conta demo nao define risco ou tamanho de operacao real.

## 6. Operational Procedures (documentadas)

Procedimentos minimos antes e durante qualquer operacao (demo ou real):

```text
PRE-OPERACAO
  1. validar ambiente demo (validate_environment: trade mode, servidor, margem)
  2. validar pre-condicoes (TRADING_ENABLED, kill switch desarmado, symbolo, lote)
  3. conferir risk limits (evaluate_risk_limits) com limites do dia
  4. revisar readiness review: nenhum item pendente relevante

DURANTE OPERACAO
  5. reconciliar posicoes a cada ciclo (reconcile_positions)
  6. monitorar metricas (latencia, slippage, rejection rate)
  7. auditar todos os eventos (audit log JSONL)
  8. comparar expected vs observed (execution comparison)

FALHA DE CONEXAO
  9. detectar breach (connection_breach_count > 0)
  10. parar novos envios ate reconexao confirmada (ping())
  11. reconciliar apos reconexao antes de retomar

ORDEM DUPLICADA
  12. detectar via duplicate_order_ids
  13. cancelar a duplicada; registrar no audit log

KILL SWITCH
  14. armar ante qualquer anomalia (risco, dados incorretos, broker estranho)
  15. so desarmar apos reconciliacao e revisao manual
```

## 7. Conclusao da fase (parcial)

A review programatica esta implementada e o estado atual e: **toda a
engenharia presente; pendentes apenas os itens que dependem da decisao
explicita de ativacao demo** (`demo_validation` e `trading_flag`). F10
so sera COMPLETE apos o periodo de validacao demo (F9) concluido e a
revisao final.

## 8. CLI de readiness

```powershell
python -m readiness
python -m readiness --backtest-done --oos-done --cost-stress-done ^
    --risk-engine-done --ops-documented
python -m readiness --demo-validation-done --trading-enabled ^
    --balance 10000 --daily-loss 50 --drawdown-pct 0.02 ^
    --exposure-notional 2000
```

Exit code: `0` quando READY, `1` caso contrario (scriptavel). Flags
booleanas refletem as decisoes do operador; a disponibilidade dos modulos
e sempre verificada ao vivo.

## 9. Procedimento de ativacao demo (proxima etapa)

A ativacao demo e a decisao explicita que fecha F9 e desbloqueia os dois
itens pendentes do F10. Sequencia prevista:

```text
1. [operador] MetaTrader 5 aberto com conta demo logada
2. smoke read-only: MT5Execution().ping() + fetch_account()
3. MT5Execution().validate_environment() -> trade mode demo, servidor, margem
4. instanciar MT5Execution(trading_enabled=True) — ativacao explicita
5. periodo de validacao: ordens minimas (fixed_quantity 0.01), kill switch
   armado como default, reconciliacao a cada ciclo
6. metricas reais: audit log JSONL + monitoring + comparison_summary
7. avaliar expected vs observed; decidir continuar/pausar
```

`TRADING_ENABLED=false` no .env permanece ate o passo 4; o guard
`trading_enabled` e o ponto unico de liberacao.

### Evento de ativacao — smoke read-only (2026-08-10 19:14 UTC-3)

```text
ping: True (terminal conectado)
conta: balance 100000.00 USD | equity 100000.00 | margin_free 100000.00
trade_mode: demo | posicoes abertas: 0
validate_environment: valid=True (demo + margem >= 100.00)
```

Bug real encontrado e corrigido no smoke: `positions_get(symbol=None)` era
rejeitado pelo MT5 (Invalid symbol argument) — o adapter agora chama
`positions_get()` sem argumento quando nao ha filtro (commit `34e2845`).

### Evento de ativacao — ordem de teste (2026-08-10 19:21 UTC-3)

```text
open  EURUSD BUY  0.01 @ 1.15431 (SL 1.15231) -> FILLED (ticket 57912767267)
      position check: 1 posicao, reconciliacao CONSISTENT
close EURUSD SELL 0.01                       -> FILLED (ticket 57912767298)
      descoberta: conta HEDGING (SELL abriu posicao nova em vez de fechar)
close_position(por ticket) -> FILLED x2, posicoes finais: 0
metricas: latencia 233 ms | slippage 0.0 pips | custo total 0.01 USD virtual
```

Descobertas de engenharia corrigidas no adapter (commit `8ec51c2`):

```text
1. retcode 10030 (Unsupported filling mode): tipo de preenchimento agora
   e derivado de symbol_info().filling_mode (FOK/IOC/RETURN)
2. conta hedging: fechamento por ticket (position=int) via close_position()
3. positions_get() sem argumento quando nao ha filtro
```

### Evento de validacao demo (2026-08-10 19:25 UTC-3)

```text
5/5 round-trips EURUSD 0.01 (BUY + close por ticket)
comparisons: 5 (within 5, outside 0) | within_rate: 100%
avg latency: 231 ms | max latency: 233 ms
avg slippage: 0.00 pips | rejeicoes: 0 | reconciliacao OK em todos
posicoes finais: 0 | custo total: 0.01 USD virtual
```

DoD F9 completo (roadmap §88): F9 = COMPLETE. A amostra de execucao
real (10 ordens no total, incluindo o teste de ativacao) mostra
execucao saudavel: latencia ~230 ms, slippage zero, spread minimo.

Nota: validamos EXECUCAO. Nenhuma estrategia do baseline tem edge
com custos (F8/OOS) — o projeto permanece research/demo platform
(roadmap §93) ate existir uma hipotese que passe na validacao.
---

## 10. Live Readiness Review (roadmap §91)

Revisao formal das dez dimensoes exigidas ANTES de qualquer capital
real. Estado: **infraestrutura pronta e verificada em demo**; decisao
de capital real permanece sob o operador (§92 — nunca automatica).

```text
1. risco por trade      max 0.5% (demo 100k -> 500 USD) | risk_limits.py
2. risco diario         max 2.0% (-> 2000 USD) | RiskLimitConfig
3. drawdown maximo      kill switch em -10% equity | KillSwitchRiskGate
4. alavancagem          max 1:5; lotes 0.01-0.1 | OrderValidationConfig
5. exposicao            1 par (EURUSD), 1 posicao por vez | allowed_symbols
6. falhas de conexao    reconectar com backoff; abortar se > 3 falhas
                        | safety.connection_breach_count
7. ordens duplicadas    dedup por order_id antes do send
                        | safety.duplicate_order_ids
8. broker downtime      retry limitado; rejeicao logada; nunca re-enviar
                        cega (audit trail JSONL)
9. dados incorretos     validacao de tick (preco>0, spread>=0) e de
                        fill (slippage vs tolerancia) | fill_validation
10. recovery procedures reconciliacao pos-trade + fechamento por
                        ticket (hedging) + posicoes orfas auditaveis
```

Evidencia coletada em demo (2026-08-10): 10 ordens executadas,
100% fills dentro da tolerancia, latencia ~230 ms, slippage 0.00,
reconciliacao CONSISTENT em todos os ciclos, posicoes finais 0.
A infraestrutura satisfaz as dez dimensoes; a revisao final com
valores de capital real so se aplica se o operador decidir avancar.

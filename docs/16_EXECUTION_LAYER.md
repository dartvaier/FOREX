# Execution Layer (F9)

## 1. Objetivo

Este documento registra a camada de execucao da fase:

```text
F9 - Demo Execution
```

Status:

```text
IN PROGRESS - engineering core (sem ativacao)
```

O fluxo alvo (roadmap §82):

```text
MarketData
    ↓
Strategy
    ↓
Risk
    ↓
MT5Execution
    ↓
MetaTrader 5 Demo
```

Regra de ouro (AGENTS.md §10, roadmap §81): o sistema permanece
`TRADING_ENABLED=false` ate a Execution Layer estar pronta E
explicitamente habilitada para Demo. Nenhuma chamada a `mt5.order_send()`
e executada neste estado.

## 2. Componentes (roadmap §83)

| Componente | Estado | Onde |
|---|---|---|
| Execution Interface | IMPLEMENTED | `execution/interface.py` |
| Order Validation | IMPLEMENTED | `execution/order_validation.py` |
| Fill Validation | IMPLEMENTED | `execution/fill_validation.py` |
| Position Reconciliation | IMPLEMENTED | `execution/reconciliation.py` |
| Broker State | IMPLEMENTED | `execution/interface.py` (BrokerAccountState, BrokerPosition) |
| MT5Execution | IMPLEMENTED (adapter) | `execution/mt5_execution.py` |
| Logs | IMPLEMENTED | `execution/audit_log.py` |
| Monitoring | IMPLEMENTED | `execution/monitoring.py` |
| Broker/Demo Validation | IMPLEMENTED | `execution/broker_validation.py` |
| Execution Comparison | IMPLEMENTED | `execution/comparison.py` |
| Kill Switch | IMPLEMENTED (F7) | `backtest/risk.py` (KillSwitchRiskGate) |

O pacote `execution/` **nao depende de MetaTrader**: tudo e puro e
testavel sem broker (`pytest -m "not integration"`).

## 3. Execution Interface

Contrato do adapter de broker:

```python
class ExecutionInterface(ABC):
    def submit(self, order: Order) -> ExecutionReport: ...
    def cancel(self, order_id: str) -> ExecutionReport: ...
    def fetch_account(self) -> BrokerAccountState: ...
    def fetch_positions(self, symbol=None) -> tuple[BrokerPosition, ...]: ...
    def ping(self) -> bool: ...
    def close(self) -> None: ...
```

Tipos de estado (frozen dataclasses com validacao):

```text
BrokerPosition     identificador, symbol, side, quantity, entry_price, open_time
BrokerAccountState balance, equity, margin_free, currency, positions
ExecutionReport    order_id, status, message, broker_order_id, fill
```

Regras de integridade:

```text
ExecutionReport FILLED exige fill; fill so em FILLED (impossivel estado invalido)
BrokerPosition: quantity > 0, entry_price > 0
BrokerAccountState: balance/equity/margin_free >= 0
```

## 4. Order Validation

`validate_order(order, account, config)` — pura, antes do broker:

```text
simbolo na allowlist (se configurada)
quantity > 0, dentro de [min_quantity, max_quantity]
stop_loss/take_profit positivos e diferentes entre si
margem estimada (quantity * margin_per_lot) <= margin_free
require_stop_loss opcional; sem SL gera warning por padrao
```

Retorna `OrderValidationResult(valid, errors, warnings)` coletando TODAS
as violacoes. Nao levanta excecao para ordem invalida.

## 5. Fill Validation

`validate_fill(order, fill, max_slippage_pips, pip_size)` — pura:

```text
fill.order_id == order.order_id
fill.quantity == order.quantity (execucao integral)
execution_price > 0
fill_time >= order.created_at (causalidade, sem look-ahead)
|execution_price - reference_price| <= max_slippage_pips * pip_size
componentes financeiros nao negativos
```

## 6. Position Reconciliation

`reconcile_positions(expected, actual)` — compara ledger interno vs broker:

```text
missing_positions    esperadas que o broker nao reporta
unexpected_positions posicoes do broker nao esperadas
quantity_mismatches  mesma posicao com quantidade diferente
consistent           nenhuma divergencia
```

`reconcile_balance(expected, actual, tolerance)` — saldo dentro de
tolerancia (default 0.01 USD).

## 7. MT5Execution (adapter)

`execution/mt5_execution.py` implementa `ExecutionInterface` via API MT5:

```text
submit(order)          -> valida (Order Validation), envia TRADE_ACTION_DEAL,
                          traduz retcode em ExecutionReport (FILLED/REJECTED)
cancel(order_id)       -> order_delete
fetch_account()        -> account_info -> BrokerAccountState (+ posicoes)
fetch_positions()      -> positions_get -> tuple[BrokerPosition]
ping() / close()       -> terminal_info().connected / shutdown()
```

Guard de seguranca materializado no codigo:

```text
trading_enabled=False (default)
  submit/cancel -> ExecutionNotEnabledError (AGENTS.md §10)
  fetch_*/ping  -> permitidos (monitoramento nao altera estado do broker)
trading_enabled=True  -> decisao explicita de ativacao Demo, separada
```

Import lazy do MetaTrader5: sem o pacote instalado o adapter falha com
mensagem clara, sem quebrar o import do pacote `execution/`. Testes usam
um fake do modulo MT5 — nenhuma chamada real ao broker.

## 8. Logs / Monitoring / Broker Validation

`execution/audit_log.py` — trilha de auditoria JSONL:

```text
AuditEvent(event_id, timestamp UTC, event_type, payload)
AuditLogger(path).log(event)  -> append de 1 JSON por linha
eventos: ORDER_SUBMITTED, ORDER_REJECTED, FILLED, RECONCILIATION, ...
```

`execution/monitoring.py` — metricas da Demo (roadmap §87):

```text
ExecutionMetrics (imutavel): total/filled/rejected/cancelled
  rejection_rate, avg/max latency (signal->fill), avg/max slippage
update_metrics(metrics, report, order) -> nova instancia (fold)
```

`execution/broker_validation.py` — pre-condicoes (roadmap §84):

```text
validate_demo_environment(account, config, server) -> DemoValidationResult
  trade_mode demo obrigatorio, allowlist de servidor, margem minima
validate_broker_preconditions(...) -> ultima linha antes do envio
  TRADING_ENABLED, kill switch, symbolo, quantity, SL obrigatorio
MT5Execution.validate_environment() -> gate de ativacao Demo (leitura)
```

`BrokerAccountState` ganhou `trade_mode` (demo/contest/real), preenchido
pelo adapter a partir de `account_info().trade_mode`.

## 9. Execution Comparison

`execution/comparison.py` — compara expected vs observed (roadmap §86-87):

```text
ExpectedExecution(order_id, symbol, side, quantity, expected_price,
                  signal_time, expected_spread, expected_commission)
ObservedExecution(order_id, fill_time, actual_price, spread, commission)

compare_executions(expected, observed, max_price_delta_pips,
                   max_latency_seconds) -> ExecutionComparison
  price_delta_pips | latency_seconds | spread/commission deltas
  verdict: WITHIN_TOLERANCE | OUTSIDE_TOLERANCE (issues listadas)

comparison_summary(comparisons) -> within_rate, avg price delta,
  avg/max latency (agregado do periodo de validacao Demo)
```

## 10. Estado da ativacao

```text
TRADING_ENABLED=false   <- inalterado
mt5.order_send()        <- nunca executado (guard testado)
```

**Engenharia F9 completa.** Falta apenas a decisao de ativacao:

```text
Demo activation          -> exige autorizacao explicita; TRADING_ENABLED so muda ai
Periódo de validacao Demo -> rodar demo real, coletar metricas e comparar
  (comparison_summary) — ultimo item do DoD F9
```

## Hardening v0.6.1 — Execution Safety (docs/25, 2026-08-12)

- **ES-01**: cancelamento de pending order via
  `order_send(TRADE_ACTION_REMOVE)` com o ticket do broker —
  `mt5.order_delete()` não existe na API real.
- **ES-02**: enums de filling alinhados à API real (FOK=0, IOC=1,
  RETURN=2); seleção por bitmask de `symbol_info().filling_mode`;
  regression do retcode 10030.
- **ES-03**: caminho obrigatório de submit/cancel/close valida
  política de conta (`allowed_trade_modes=("demo",)` — conta real
  bloqueada por padrão) e kill switch antes de qualquer mutação.
- **ES-04**: fill executado pelo broker nunca é rebaixado a
  REJECTED por validação local — slippage fora da tolerância produz
  `validation_status=OUTSIDE_TOLERANCE` e
  `requires_reconciliation=True`.
- **ES-05**: `validate_fill` exige o pip size real do instrumento
  (EURUSD 0.0001, USDJPY 0.01); sem default implícito.

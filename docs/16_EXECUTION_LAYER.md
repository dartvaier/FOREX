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
| MT5Execution | PLANNED | proximo bloco (adapter MT5) |
| Logs / Monitoring | PLANNED | proximo bloco |
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

## 7. Estado da ativacao

```text
TRADING_ENABLED=false   <- inalterado
mt5.order_send()        <- nunca executado
```

Proximos blocos F9 (somente engenharia, ativacao separada):

```text
MT5Execution adapter  -> implementa ExecutionInterface via API MT5 (sem ativar)
Logs / Monitoring     -> auditoria estruturada de ordens/fills/reconciliacao
Demo activation       -> exige autorizacao explicita; TRADING_ENABLED so muda ai
```

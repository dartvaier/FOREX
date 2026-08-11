# 22 — Conversão de Moeda (quote → USD) no Backtest

Status: **CONCLUÍDO** — resolve a limitação declarada em docs/20 §2.4
e docs/21 §2. O PnL (realizado e não realizado) e o custo round-trip
agora são convertidos para a moeda da conta (USD) de forma causal.

---

## 1. Problema

Para pares com moeda de cotação ≠ USD (USDJPY, USDCHF, USDCAD), o
backtest calculava PnL em moeda de cotação (ex: JPY) e somava com a
comissão em USD **sem conversão**. Sintoma empírico (docs/21): USDJPY
dev TSM reportava retorno −334% e drawdown de 40% — valores
monetários inúteis para decisão.

## 2. Solução (causal)

`InstrumentSpecification` ganha `base_currency`/`quote_currency`
(defaults "USD"/"USD" — compatibilidade total com o comportamento
histórico) e o método:

```python
quote_to_account_rate(price) -> float
# USD-quote pairs: 1.0
# USD-base pairs  (USDJPY, USDCHF, USDCAD): 1.0 / price
# crosses: ValueError (triangular conversion not implemented)
```

Aplicação:

- **PnL realizado** (`Portfolio._calculate_pnl`): multiplicado pela
  taxa no **preço de saída** (fill.execution_price) — disponível no
  instante, sem look-ahead.
- **PnL não realizado** (`mark_to_market`): taxa no **preço de mark**
  corrente.
- **Custo round-trip** (`round_trip_cost_money`/`money_to_pips`):
  a perna spread/slippage (moeda de cotação) é convertida com a taxa
  derivada do preço médio de entrada dos trades realizados; a
  comissão já é USD.

Consequência nos invariantes:

```text
round-trip em pips (spread+slippage): 3.0 pips em TODOS os pares
round-trip total em pips: 3.70 (USD-quote) | 3.78 (USDJPY @ ~142)
  (a comissão custa mais pips em pares de pip barato)
```

## 3. Resultados USDJPY corrigidos (dev 2015-2021, explicit)

| estratégia | trades | net (antes) | net (depois) | max_dd (depois) |
|---|---|---|---|---|
| TSM | 1401 | -33461.07 | **-401.21** | 4.04% |
| EMA | 1394 | -37672.58 | **-440.36** | 4.42% |
| MR | 3410 | -115691.70 | **-1291.99** | 12.99% |

Leitura: com a conversão, o USDJPY se alinha aos demais pares —
**todos negativos**; a conclusão de docs/21 (nenhum par com edge sob
custos) permanece, agora com a matriz monetária íntegra.

## 4. Validação

- 8 testes novos (`tests/test_currency_conversion.py`): taxa por
  estrutura de par, validação de códigos, PnL realizado USDJPY/EURUSD,
  custo round-trip com taxa, invariante de pips USD-quote.
- Suíte completa: **1057 passed, 0 failed**.
- Nenhuma mudança para pares USD-quote (rate = 1.0 → regressão
  intacta).

## 5. Escopo futuro

- Crosses (EURGBP etc.): conversão triangular — fase posterior (§104
  "crosses").
- Moeda de conta ≠ USD: o fator fixo é 1.0 para quote USD; conta em
  outra moeda exigiria parametrização (fora de escopo).

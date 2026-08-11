# 20 — Multiple Symbols (§104) + Multi-Timeframe Runtime (§106)

Status: §106 **DONE** (auditoria); §104 **IN PROGRESS** (infra
entregue, coleta dos pares em andamento).

---

## 1. §106 — Multi-Timeframe Runtime: auditoria (DONE)

A sincronização runtime M15/H1/H4 **já está implementada no
BacktestEngine** — o roadmap §106 foi escrito antes da fase F5:

- `BacktestContextBuilder._higher_timeframe_bars` sincroniza por
  **timestamp** (close-times dos H1/H4 + `bisect_right`), nunca por
  índice: os candles H1/H4 só ficam disponíveis após o próprio
  fechamento (invariante de causalidade multi-timeframe).
- `higher_timeframe_bar_limits` limita a janela exposta (eficiência).
- Evidência: `tests/test_backtest_multitimeframe.py` (5 testes —
  "only after close", "filters incomplete bars", "engine passes
  higher timeframes to strategy").
- Consumers reais: `strategy/multi_timeframe_momentum.py` (H4+H1+M15)
  e o filtro RF-01 (`regime_filter=h4_vol_high`, H4).
- O runner carrega H1/H4 por símbolo
  (`load_higher_timeframe_dataframes`).

Nenhuma mudança necessária. Roadmap §106 → DONE.

## 2. §104 — Multiple Symbols: infra entregue

### 2.1 Instrument registry (7 majors)

`research/runner.py INSTRUMENT_REGISTRY`:

```text
EURUSD/GBPUSD/USDCHF/AUDUSD/USDCAD/NZDUSD:
    digits 5, point 1e-5, pip 1e-4, contract 100k, tick_value 1.0
USDJPY:
    digits 3, point 1e-3, pip 1e-2, contract 100k, tick_value 100.0
```

USDJPY é o caso crítico (digits 3 / pip 0.01) — teste dedicado
(`tests/test_multi_symbol.py`).

### 2.2 Pipeline de dados parametrizado

- `collect_history.py --symbol <par>` (default EURUSD preserva uso
  atual)
- `build_timeframes.py --symbol <par>` (gera H1/H4 do M15 bruto)

### 2.3 Prova de conceito: GBPUSD

```text
M15: 288,337 candles (2015-01-01 -> 2026-08-10)
H1:  72,109 (72,051 completos) | H4: 18,052 (17,941 completos)
Backtest PoC (TSM 96/0.001, explicit, dev 2015-2021):
    net -334.17 | ret -3.34% | round trip 3.70 pips (invariante ok)
```

O invariante de custo (3.70 pips round-trip) é idêntico entre os 6
pares USD-quote (teste dedicado).

### 2.4 Conversão de moeda — RESOLVIDA (docs/22)

A conversão quote→USD foi implementada (docs/22): PnL realizado
e não realizado usam a taxa do próprio par no preço disponível
(causal); o custo round-trip converte a perna em moeda de cotação.
USDJPY dev TSM corrigido: -33461 → -401 USD (dd 40% → 4%).
Invariante: round-trip 3.70 pips (USD-quote) / 3.78 (USDJPY).
Crosses (conversão triangular) continuam fora de escopo.

## 3. Próximos passos (§104)

1. Coletar os 5 pares restantes (USDJPY, USDCHF, AUDUSD, USDCAD,
   NZDUSD) via `collect_history.py --symbol` + `build_timeframes.py`.
2. Rodar os 3 baselines × 7 pares (dev/val, explicit) — o mesmo
   protocolo F8 por par.
3. Decidir portfolio multi-symbol (soma de PnL, correlações) — fase
   posterior, fora do escopo atual.

## 4. Artefatos

- Commit `a3d9d03`: registry + collect/build --symbol + 6 testes
  (`tests/test_multi_symbol.py`)
- Dados: `data/raw/GBPUSD/M15.parquet`, `data/processed/GBPUSD/{H1,H4}.parquet`
  (gitignored)
- Relatório PoC: `research/reports/TIME-SERIES-MOMENTUM_M15_explicit_ms-poc-gbpusd.json`

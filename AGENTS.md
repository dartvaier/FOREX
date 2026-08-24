# AGENTS.md — FOREX Algorithmic Trading Research Platform

Repository-specific agent instructions. This file defines how any agent working on this
repository must behave: what to preserve, what to never break, and how to make decisions.

---

## 1. Primeira Regra: Descubra o Estado Real

Nunca presuma que README, roadmap ou documentação representam o estado atual.
No início de cada sessão:

```powershell
git status --short --branch
git log --oneline -5
```

Hierarquia de fontes de verdade quando houver conflito:

1. Testes automatizados atuais
2. Código atual
3. `DECISIONS.md`
4. Documentação da fase atual
5. `CHANGELOG.md`

---

## 2. Invariantes Que Não Podem Ser Quebradas

### UTC

Todo timestamp interno deve ser `timezone-aware` e em UTC. Conversões para
`Europe/London`, `America/New_York` etc. só quando necessárias para uma hipótese
específica, e nunca com offset fixo (DST importa).

### No Look-Ahead

É proibido usar dados que não estariam disponíveis no instante da decisão simulada.
Isso inclui: candle corrente, close/high/low futuro, H1/H4 ainda não fechados,
labels futuros como features, sincronização por índice entre timeframes.

### Candles Fechados

Strategy só pode usar candles cujo fechamento já ocorreu. No MT5, `bar 0` (barra atual)
é sempre excluída. Existe teste automatizado específico para isso.

### Multi-Timeframe Causal

Sincronize por timestamp, nunca por índice:

```python
# ERRADO
M15.iloc[i], H1.iloc[i], H4.iloc[i]

# CERTO: via BacktestContext.timeframe_bars com disponibilidade temporal
```

H1 e H4 só ficam disponíveis depois do próprio fechamento.

### Gaps

Não fabrique candles inexistentes. Nunca use `ffill()` para esconder gaps de mercado.
A próxima barra usada pelo Engine é a próxima barra realmente disponível.

### Custos Explícitos

O baseline de pesquisa assume:

```text
spread_pips = 2.0
slippage_pips = 0.5
commission_per_lot_per_side = 3.50
```

Nunca considere uma estratégia promissora apenas em zero-cost.
Zero-cost serve para diagnóstico de edge bruto e engenharia.

---

## 3. Arquitetura: Separação de Responsabilidades

```
Strategy → Signal → RiskGate → RiskDecision → Order → Execution → Fill → Portfolio → Trade
```

- **Strategy**: interpreta mercado, produz Signal, informa stop técnico. NÃO envia ordens, NÃO calcula lote, NÃO acessa dados futuros.
- **RiskGate**: aprova/rejeita exposição, faz position sizing, aplica limites.
- **Execution**: transforma ordens aprovadas em fills simulados.
- **CostModel**: spread, slippage, commission — independente da Strategy.
- **Portfolio**: posição, cash, PnL, equity.
- **Performance**: métricas, drawdown, estatísticas.

`Signal != Order != Fill`. Um sinal válido pode ser rejeitado pelo RiskGate. Isso é
comportamento esperado.

---

## 4. Research Runner

Prefira sempre o runner existente para experimentos reproduzíveis:

```powershell
python -m research.runner --strategy ema_trend
python -m research.runner --strategy time_series_momentum --cost explicit
python -m research.runner --strategy ema_trend --date-from 2015-01-01 --date-to 2020-12-31
python -m research.runner --strategy time_series_momentum --param lookback=192
```

Comparação de relatórios:

```powershell
python -m research.summarize
python -m research.summarize --csv
```

Não crie scripts de backtest isolados se o experimento couber no runner.

---

## 5. Disciplina Contra Parameter Mining

É proibido:

```text
rodar milhares de combinações → selecionar a mais lucrativa → chamar isso de Strategy
```

Se houver busca de parâmetros legítima:

- Defina o espaço antes de ver resultados.
- Preserve validation/OOS.
- Registre todos os experimentos.
- Avalie regiões de estabilidade, não apenas o máximo.
- Uma "ilha de parâmetro" (ex: `lookback=47` funciona mas 44-50 não) é suspeita.

---

## 6. Processo para Nova Estratégia

```text
Hipótese → Testes sintéticos → Zero-Cost → Explicit-Cost
→ Análise dos trades → Sensibilidade local → Cost Stress
→ Validação temporal → Out-of-Sample (lockbox)
```

Antes de rodar, escreva: hipótese, racional, regras de entrada/saída, parâmetros pré-definidos,
critérios de aceitação e rejeição. Nunca defina o critério depois de ver o resultado.

---

## 7. Adicionando Nova Strategy

1. Implementar em `strategy/` seguindo o contrato `on_bar(context) -> Signal`
2. Testes unitários com fixtures sintéticas (3-10 candles)
3. Adicionar ao registry do research runner
4. Rodar zero-cost → explicit-cost → relatório

---

## 8. Testes

- Para lógica financeira crítica, use datasets artificiais onde o resultado possa ser
  calculado manualmente (3, 5, 10 candles).
- Teste separadamente: regra, integração, resultado histórico.
- TDD para bugs: reproduza o teste falhando → corrija → verifique que passa → regressão.
- Teste de regressão é contrato: se muda um resultado esperado, determine se é bug fix
  legítimo ou mudança intencional de modelo.

```powershell
pytest -m "not integration" -q   # engenharia sem MT5
pytest tests/ -q                  # suíte completa
```

---

## 9. Git Workflow

- Não trabalhe diretamente em `master`.
- Branches com nomes claros: `feature/risk-drawdown-guard`, `fix/backtest-xyz`.
- Commits pequenos e auditáveis: `feat(risk): add equity drawdown guard`.
- Nunca execute sem autorização: `reset --hard`, `clean -fd`, force push, rebase destrutivo,
  merge em master.
- Antes de commit: verifique `git status`, `git diff --stat`, `git diff`. Confira: sem
  segredos, sem datasets enormes, sem reports temporários indevidos.

---

## 10. Proibição de Execução Real

Nunca execute:

```python
mt5.order_send()
```

sem que a fase de Execution/Demo tenha sido explicitamente autorizada.

```env
TRADING_ENABLED=false
```

nunca deve ser alterado silenciosamente. O estado atual do projeto é **READ ONLY** —
pesquisa e backtest. Execução exigirá: backtest → OOS → risk validation → demo →
monitoramento.

---

## 11. Nunca Otimize Win Rate Isoladamente

Analise sempre: Win Rate, Payoff, Expectancy, Profit Factor, Drawdown, Trade Count.
Uma estratégia com 90% de acerto ainda pode perder dinheiro. Turnover é uma variável
crítica — sinais com edge pequeno podem ser destruídos por custos quando a frequência
é alta.

---

## 12. Resultados Excelentes Devem Ser Auditados

Quanto melhor o backtest parecer, maior o rigor. Verifique: look-ahead, data leakage,
same-close execution, H1/H4 future access, custos, SL/TP ambiguity, gap handling,
position sizing, duplicação de PnL, spread contado incorretamente, amostra,
concentração dos lucros.

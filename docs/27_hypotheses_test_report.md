# 27. Relatório Consolidado do Programa de Hipóteses (H01–H07)

> **Data**: 2026-08-12 · **Responsável**: Engenheiro (agente de pesquisa) ·
> **Branch**: `feature/backtest-core-models` · **Programa**: docs/26 §1–§22

Este relatório consolida a execução completa do programa de hipóteses do
projeto FOREX Algorithmic Trading Research Platform. Todas as 7 hipóteses
foram testadas no **estágio 1** (previsão condicional, sem trade), cada uma
com **registro imutável pré-registrado** antes de qualquer backtest
(protocolo docs/26 §5), seguindo a disciplina de `AGENTS.md` (sem parameter
mining, sem look-ahead, custos explícitos).

---

## 1. Inventário das Hipóteses (status inicial, prioridade, critérios)

| ID | Hipótese | Prioridade | Status inicial | Critérios de aceitação (pré-registrados) |
|---|---|---|---|---|
| H03 | Surpresa de volatilidade intradiária | 1 | ACTIVE | Retorno condicional significativo e estável por ano; sobreviver a 1.5× custo |
| H05 | Reversão após choque ineficiente (DE baixa) | 2 | ACTIVE | DE adicionar poder vs controles; estável; sobreviver a custos |
| H06 | Continuação após choque eficiente (DE alta + CLV) | 2 | ACTIVE | DE adicionar poder vs controles; estável; sobreviver a custos |
| H01 | Falso rompimento da faixa asiática | 3 | ACTIVE | Signed médio > 0; estável; sem ilha de parâmetro; sobreviver a custos |
| H02 | Handoff Ásia–Londres condicionado ao formato | 3 | ACTIVE | Direção estável entre subperíodos/fronteiras; signed médio > 0 por grupo |
| H04 | Compressão + choque de preço/atividade | 3 | ACTIVE | A4 superar breakout simples; ablation incremental; sem efeito só de horário; sem cauda |
| H07 | Reversão parcial do gap semanal | 4 | PROPOSED / LOW SAMPLE | Signed > 0; robusto a leave-one-year-out e sem top-5; cobrir custos |

**Fonte**: docs/26 §1–§4 (especificações) + registros imutáveis §10, §12, §14, §16, §18, §19.

---

## 2. Plano de Teste (fechado antes da execução)

| Item | Definição |
|---|---|
| Casos | 7 hipóteses × estágio 1 (previsão condicional) + ablations/sensibilidades pré-declaradas |
| Ambiente | EURUSD M15 `data/raw/EURUSD/M15.parquet` (288.223 candles, 2015-01-02..2026-08-10) + H1 processado para ATR |
| Dataset version | parquet timezone-aware UTC; sessões com timezones reais (zoneinfo), nunca offset fixo |
| Responsável | Engenheiro (agente) — execução automática com protocolo de pre-registro |
| Cronograma | Executado em 2026-08-12 (programa aberto e fechado no mesmo dia, 4 sessões de trabalho) |
| Métricas | Retorno assinado médio, positive rate, n de eventos, decomposição por ano, sensibilidade de parâmetros, bootstrap CI (H07) |
| Critérios de sucesso | Estágio 1 com efeito consistente **e** cobertura de custos → estágio 2; caso contrário REJECTED |

**Períodos formais** (docs/26 §9): DEV 2015-2021 / VAL 2021-2024 / OOS
2024-2027. OOS declarado **contaminado** (consultado uma vez em 2026-08-10);
nenhuma hipótese atingiu o estágio que exigiria walk-forward/OOS.

---

## 3. Resultados por Hipótese (log de execução resumido)

| ID | Data | Etapas executadas | n de eventos | Métrica-chave (h8 salvo indicação) | Classificação |
|---|---|---|---|---|---|
| H03 | 2026-08-12 | volatility_surprise (mediana por slot, 60 slots) → janelas 40/60/80 × h1/2/4/8 × ano × hora | 288.223 (base) | 0.000% overall; −0.011%…+0.012% por ano; highlight 00:00 UTC +0.018% (~1,98 pips < 3,7 pips) | **REFUTADA** |
| H05 | 2026-08-12 | directional_efficiency + slot_percentile → matriz 6 células × p85/90/95 × h1/2/4/8 | 2.999 | +0.003% (≈0); 3 inversões de sinal por ano | **REFUTADA** |
| H06 | 2026-08-12 | idem H05 + confirmação CLV ≥ 0,90 / ≤ 0,10 | 3.296 | **−0.004%** (negativo, pos 44–48%) | **REFUTADA** |
| H01 | 2026-08-12 | faixa Ásia Europe/London (zoneinfo) + ATR(H1,14) causal → buffer 0,10/0,15/0,20 → confirmação {N,N+1,N+2} → 1 evento/lado/dia | 3.956 (b0.15) | +0.003% (levemente **positivo** = continuação, não reversão); 4 inversões/ano; midpoint touch 1,00 | **REFUTADA** |
| H02 | 2026-08-12 | percentil range 60d + CLV → 4 grupos (p30/p70 × CLV 0,2/0,8) → fwd 1/2/4h → sensibilidade p25–75 / CLV 0,15–0,85 | 3.363 sessões | continuation_up **−0.035%** (todas as variações e 10/12 anos); demais grupos instáveis | **REFUTADA** |
| H04 | 2026-08-12 | realized_range_16 p25 + TR p90 + TV p80 + CLV → ablation A1/A2/A3/A4 + CTRL breakout | 439 (A4) | A4 +0.009% (pos 49,0%) vs CTRL −0.002%; h1 A4 pior que CTRL; 6 pos/6 neg por ano | **REFUTADA** |
| H07 | 2026-08-12 | gap semanal (sem criar candles de fim de semana) → normalized ≥ 0,50 → fwd 1/4/8/16h → bootstrap, leave-one-year-out, sem top-5 | 301 | h1 **+0.031% (pos 66,8%)**; h8 CI [−0.009%, +0.037%]; sem top-5 +0.014%; **~3,1 pips < 3,7 pips custo** | **REFUTADA** |

**Evidências completas**: docs/26 §10–§22 (registros imutáveis e resultados);
`research/hypotheses_log.json` (base de registros); relatórios JSON em
`research/reports/` (gitignored, auditáveis localmente):
`h03_experiment{,_lb40,_lb80}.json`, `h0506_experiment{,_p85,_p95}.json`,
`h01_experiment{,_b010,_b020}.json`, `h02_experiment.json`,
`h02_exp_{p25_p35,p65_p75,clv_75_85,clv_15_25}.json`,
`h04_experiment.json`, `h07_experiment.json`.

---

## 4. Classificação Final

| Classificação | Contagem | Hipóteses |
|---|---|---|
| Confirmada | 0 | — |
| Refutada | **7** | H03, H05, H06, H01, H02, H04, H07 |
| Inconclusiva | 0 | — |

### Justificativas consolidadas

1. **H03** — retorno condicional ≈ 0 em todas as janelas; único destaque
   (00:00 UTC) não cobre custo e carrega risco de multiple testing
   (24 slots inspecionados).
2. **H05** — a eficiência direcional não discrimina: controles com DE alta
   têm o mesmo padrão das células-alvo; sinal ≈ 0 com 3 inversões por ano.
3. **H06** — efeito **negativo** (oposto da hipótese) em todos os horizontes
   e variações de fronteira.
4. **H01** — retorno ≈ 0 e levemente **positivo** (continuação, não a
   reversão esperada); instável entre subperíodos; midpoint sempre tocado
   em 8 barras (não discrimina).
5. **H02** — o único grupo consistente (faixa comprimida + close no high)
   é negativo — o **oposto** da continuação compradora prevista; padrão
   anti-H02 não elevado a hipótese nova (não pré-registrado, multiple
   testing).
6. **H04** — o modelo completo não supera o controle de breakout simples
   de forma consistente; positive rate < 50% com média > 0 indica
   dependência de eventos extremos (cauda).
7. **H07** — sinal estatístico real no h1 (66,8% positive rate; robusto a
   leave-one-year-out e à remoção dos 5 maiores gaps), **mas** o edge bruto
   (~3,1 pips) não cobre o custo round-trip conservador (3,7 pips) e se
   dissipa até o h16 — falha o critério de custo pré-registrado.

---

## 5. Recomendações de Próximos Passos

1. **Reavaliar H07 sob custos de execução reais** (prioridade alta, baixo
   custo): o h1 do gap semanal é o único efeito estatístico robusto do
   programa. Se o custo efetivo de um par EURUSD com execução otimizada
   (spread reduzido, sem slippage no open da semana) for < 3,1 pips, o
   caso merece estágio 2 formal (com custos medidos, não assumidos).
2. **Medir custos reais de execução** (pré-requisito do item 1): a
   referência de 3,7 pips é o baseline do projeto (docs/21); a decisão
   real de capital (§92) continua exclusiva do operador.
3. **Infraestrutura de eventos raros**: H07 mostrou que o framework
   bootstrap + leave-one-year-out + remoção de top-N funciona bem para
   amostras pequenas; estender essa infra para futuras hipóteses de baixa
   frequência.
4. **Novo ciclo de hipóteses (fora do escopo deste programa)**: as
   features reutilizáveis construídas (volatility_surprise,
   directional_efficiency, slot_percentile, detector de sessão asiática,
   ATR causal, ablation framework) reduzem o custo de testar novas
   hipóteses; qualquer nova hipótese exige novo pre-registro (docs/26 §5).
5. **Nenhuma hipótese avança para walk-forward/OOS** — não há edge que
   justifique o custo de validação formal; o OOS contaminado permanece
   intocado.

---

## 6. Anexos e Acesso

- Base de registros rastreável: `research/hypotheses_log.json` (inventário,
  log, métricas, classificação, evidências por hipótese).
- Registros imutáveis e resultados: `docs/26_RESEARCH_HYPOTHESES.md`
  (§10–§22).
- Código de experimentos: `research/h0{1,2,3,4,5_6,7}_experiment.py` +
  `research/features.py` (features reutilizáveis, testadas).
- Suíte de testes: **1119 passed** (inclui 19 testes de features de
  pesquisa).
- Relatórios JSON auditáveis: `research/reports/` (gitignored).
- Commits: `b615243` (H03), `0b5fd6a` (H05/H06), `99971d0` (H01),
  `4b8c3ec` (H02), commit de fechamento (H04 + H07 + docs/27 + log).

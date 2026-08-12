# 29. Revisão de Literatura — Conclusões Consolidadas

> Arquivo vivo de conclusões das literaturas analisadas, para revisão
> futura. Cada literatura analisada adiciona uma seção; cada ciclo de
> hipóteses derivado dela referencia o resultado no
> `docs/26_RESEARCH_HYPOTHESES.md` e em `research/hypotheses_log.json`.
> Hierarquia de verdade: testes > código > DECISIONS.md > docs > README.

---

# Literatura 1 — "Evidence-Based Technical Analysis" (David R. Aronson, 2007)

**Status: ANALISADA (2026-08-12).** Fonte: PDF fornecido pelo operador
(`.openclaw-attachments/20260812-183428-...`). Extração de texto:
`.openclaw/tmp/aronson/`.

## 1.1 Conclusões metodológicas (incorporadas ao funil)

1. **Data-mining bias é o erro nº 1 de backtests de regras.**
   O case study do livro: 6.402 regras no S&P 500 (1980-2005) —
   **nenhuma estatisticamente significativa** após correção (a melhor
   regra: p = 0.8164; a distribuição nula do "melhor de 6.402" estava
   centrada em ~11% ao ano, não em zero). Com teste ingênuo, ~320
   regras (5%, exatamente o esperado por acaso) pareceriam
   significativas. Lição: **selecionar o melhor de N sem corrigir é
   fabricar fool's gold**.
2. **White's Reality Check (WRC)**: bootstrap da distribuição do
   máximo de N regras sob H0 (todas com retorno esperado zero,
   retornos centrados). p = fração da distribuição ≥ média observada
   da melhor regra. Corrige o viés de seleção do melhor de N.
3. **Monte Carlo Permutation (MCP, Masters)**: embaralha o pareamento
   outputs × retornos de mercado usando o MESMO embaralhamento para
   todas as regras (preserva correlação entre regras).
4. **Fatores que ampliam o bias**: (a) nº de regras testadas; (b)
   poucas observações por regra (1.000 meses reduzem o bias do
   best-of-1.024 de 84% para <12%); (c) correlação baixa entre
   regras; (d) variabilidade de qualidade entre regras.
5. **Detrending = benchmarking por position bias** (apêndice, com
   prova): centrar os retornos elimina o viés de posição long/short
   em mercado com drift.
6. **Regras complexas > simples** (Hsu-Kuan, 39.832 regras, 4
   índices): 82% das significativas eram combinações
   (voting/fractional position); nenhuma regra simples foi
   significativa no S&P 500 (mas houve em NASDAQ/Russell 2000 —
   mercados menos eficientes).

**Implementado:** `research/data_mining_tests.py` (WRC + MCP) com 9
testes em `tests/test_data_mining_tests.py`. Registro: docs/26 §42.
**Padrão do funil a partir de agora:** qualquer resultado que envolva
seleção (pares, parâmetros, variações) é avaliado com WRC/MCP além
dos critérios pré-registrados.

## 1.2 Conclusões de conteúdo (teorias de movimento não-aleatório)

Teorias do cap. 7 que geram hipóteses testáveis:

1. **Liquidity premium (Cooper)**: comprar ~2 semanas de queda com
   volume DECLINANTE → retorno acima da média na semana seguinte
   (44.95% vs 17.91% benchmark em ações, walk-forward 1978-1993).
   Racional: compensação por prover liquidez a vendedores distressed.
2. **Regras complexas (Hsu-Kuan)**: combinar regras simples via
   voting/fractional position captura sinergia inexistente nas partes.
3. **Hedge risk premium (MLM)**: trend following em commodities
   futures = compensação por transferência de risco de hedgers
   (MLM index, MA12 mensal em 25 mercados, Sharpe ~0.60 vs ~0.05 em
   ações). Kestner: Sharpe 0.604 futures vs 0.046 stocks.
4. **Underreaction/overreaction (BSV/DHS/HS)**: momentum após
   surpresa, reversão após streaks — base teórica de H05/H06/H11
   (refutadas).

## 1.3 O que testamos e o resultado (ciclo 3, docs/26 §43-§44)

| Hipótese | Teoria | Resultado | Veredito |
|---|---|---|---|
| H12 | Liquidity premium (Cooper em FX) | net +0.104% (n=315), CI contém zero, LOYO>0 | **INCONCLUSIVA** |
| H13 | Regras complexas voting (8 regras) | net −0.00005%/barra (n=279k) | **REFUTADA** |
| H14 | Hedge risk premium (MLM semanal) | net −0.085%, CI negativo significativo | **REFUTADA** |

**Interpretação:** as teorias de não-aleatoriedade do Aronson não se
materializam em edge líquido no EURUSD spot com custos de varejo. O
EURUSD comportou-se como o S&P 500 do case study (líquido,
eficiente), não como NASDAQ/Russell ou commodities.

## 1.4 Re-auditoria H07-MP com WRC (docs/26 §42)

O estágio 1 do H07-MP (melhor de 6/7 pares) sobrevive ao WRC:
p = 0.0002 (7 pares) / 0.0004 (6 pares). **Não era artefato de
seleção** — a refutação do estágio 2 (custo do open semanal +
timeouts) permanece válida. A disciplina do funil foi validada
retroativamente.

## 1.5 O que NÃO testamos (candidatos para revisão futura)

- H12 em estágio 2 (trade completo) — não elevado por edge marginal
  (~0.1%/evento, mesmo perfil do H09 que foi refutado no stage-2).
- Liquidity premium nos outros pares (especialmente NZDUSD/USDCAD,
  onde a liquidez é menor e o fenômeno Cooper seria mais provável —
  analogia NASDAQ vs S&P).
- Regras complexas em mercados menos eficientes (pares exóticos —
  sem dados no momento).
- Trend following semanal em commodities-like (sem dados).

---

# Pendências de literatura (próximas análises)

Ordem sugerida (com racional):

1. **Ernest Chan — Algorithmic Trading: Winning Strategies and Their
   Rationale**: fonte direta de hipóteses testáveis com racional
   econômico e código. É o próximo mais acionável para o ciclo 4.
2. **Marcos López de Prado — Advances in Financial ML**: métricas de
   robustez (deflated Sharpe, PBO, purged k-fold) — fortalece a
   validação do funil, especialmente para múltiplos testes.
3. **Larry Harris — Trading and Exchanges (Market Microstructure)**:
   o "porquê" do custo comer o edge (quem paga spread, por que o
   open semanal é caro) — pode gerar hipóteses sobre onde/quando o
   custo é estruturalmente baixo.
4. **Kathy Lien — Currency Trading and Intermarket Analysis**:
   racionais de sessão e intermercado (Asia/Londres/NY) para
   hipóteses de horário/correlação.

Qualquer literatura nova segue o pipeline: extração → síntese →
hipóteses com racional → **pré-registro imutável (docs/26)** → funil
com custos calibrados + WRC → classificação nos critérios fixados.

---

# Lições transversais para revisão futura (18 execuções, 3 ciclos)

1. **Padrão consolidado**: edge bruto marginal (0.1-3.7 pips/evento)
   < custo round-trip calibrado (1.9-7.9 pips) em todos os horizontes
   testados (M15, H1, D1, W1) e em todos os pares (7).
2. **O assassino é o custo, não a ausência de sinal**: H07-MP e H09
   tinham edge bruto real e estatisticamente robusto (WRC p=0.0004);
   ambos morreram no estágio 2 quando o trade completo pagou o custo
   real (open semanal 4.5-6.2 pips; round-trip 1.9-2.6 pips).
3. **O único caminho que a evidência não refutou**: custos
   institucionais (ECN/API, spread de frações de pip). Se o custo
   cair de 2-8 pips para <0.5 pip, os sinais com edge bruto real
   (H07-MP AUDUSD/NZDUSD, H09) poderiam virar líquidos. Requer dados
   de custo institucional — não disponíveis no dataset atual.
4. **Mercados líquidos majors não pagam edge a regras simples ou
   combinadas** (confirmado por Aronson no S&P e por nós no EURUSD).
5. **Disciplina preservada**: 0 confirmadas / 17 refutadas / 1
   inconclusiva; nenhum critério redefinido após ver resultados;
   pré-registro sempre imutável antes de rodar; OOS 2024-2027
   contaminado tratado como informativo apenas.

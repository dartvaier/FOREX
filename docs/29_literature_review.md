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


---

# Literatura 2 — "Winning Algorithmic Trading Strategies" (Thomas West)

**Status: ANALISADA (2026-08-12).** Fonte: EPUB fornecido pelo
operador. Extração: `.openclaw/tmp/west/` (40 capítulos).

## 2.1 O que é o livro

Guia prático de TradingView/PineScript: construção de sistemas
(Filtro -> Trigger -> Saídas -> Risk Management), 15 estrategias
concretas (5 de bands/envelopes, 5 de osciladores de momentum,
5 de trend-following) e automatização em plataformas crypto
(Pionex, 3Commas, Capitalize.ai). Exemplos com profit factors
altos reportados do Strategy Tester (ex: Bollinger+RSI PF > 4.0;
BT-SAR EMA Squeeze PF 2.98, 91% win, BTC/USD 1H).

## 2.2 Conclusoes

1. **Representa o "outro lado" que o Aronson critica**: backtests do
   TradingView sem custos realistas, sem correcao de data-mining,
   sem OOS, sem registro de trials. Profit factors 2-4 em backtests
   de plataforma sao exatamente o tipo de claim que nosso funil
   refuta (18/18 execucoes: edge bruto < custo calibrado). O proprio
   livro admite PF > 3.0 "e raro em estrategias honestas e nao
   overfit" — sem dizer quantos backtests rodou para achar esses.
2. **Ideias concretas ja cobertas pelo nosso funil**: squeeze ->
   breakout (testado como H04 range compression e H09 compressed
   range, ambos refutados); multi-timeframe filter (engine MTF do
   runner, 21/21 negativos); osciladores com threshold (H13 RSI14,
   refutado).
3. **Variaveis NAO testadas (anotadas para revisao futura)**:
   - *Oscillator re-entry*: entrar quando o oscilador cruza DE VOLTA
     para fora da zona extrema (RSI sobe acima de 30 apos tocar
     <30), nao ao entrar na zona — refinamento de timing do mean
     reversion.
   - *Momentum divergence* (regular/hidden com pivots) — dificil de
     automatizar, mas definivel com pivots de 2 barras.
   - *Squeeze + EMA200 filter + SAR flip* (estilo BT-SAR) em FX.
4. **Vies de universo**: o livro e majoritariamente crypto/BTC;
   nossos dados sao FX majors (mais liquidos, mais eficientes).
   Nada no livro sugere edge que sobreviva a custos calibrados no
   varejo FX; as 3 variacoes acima entram apenas como candidatas
   menores ao ciclo 4, com pre-registro.

---

# Literatura 3 — "Advances in Financial Machine Learning" (Marcos López de Prado, 2018)

**Status: ANALISADA (2026-08-12).** Fonte: EPUB fornecido pelo
operador. Extração: `.openclaw/tmp/afml/` (7 arquivos, cap. 1-22).

## 3.1 Conclusoes metodologicas (como o AFML confirma e estende nosso funil)

1. **"Backtest nao e ferramenta de pesquisa"** (cap. 11): o backtest
   serve para DESCARTAR modelos ruins, nunca para melhora-los.
   "Nunca backteste ate o modelo estar totalmente especificado. Se o
   backtest falhar, comece de novo." — nosso pre-registro imutavel e
   a operacionalizacao exata disso (18/18 sem redefinicao pos-hoc).
2. **Sete pecados (Luo et al. 2014)**: survivorship, look-ahead,
   storytelling, data mining/snooping, transaction costs, outliers,
   shorting. Nosso funil os evita: OOS lockbox (look-ahead),
   custos calibrados medidos (transaction costs), WRC + registro de
   trials (data mining), LOYO/blocos (outliers), sem shorting de
   cash em pares nao cobertos.
3. **"Mesmo um backtest impecavel provavelmente esta errado"**
   (cap. 11.3): especialista = milhares de backtests = selecao.
   "A cada teste novo no mesmo dataset, a probabilidade de falso
   positivo muda" — por isso o hypotheses_log registra TODAS as
   execucoes (Terceira Lei do Backtesting, cap. 14.7.3).
4. **Deflated Sharpe Ratio (DSR)** (cap. 14.7.3): SR* = expectativa
   do maximo de N trials sob H0:SR=0 — cresce com N e com a variancia
   entre trials. Aplicacao ao funil: se reportarmos Sharpe (runner,
   futuros resultados), o DSR deflaciona pelo numero de trials — o
   equivalente em Sharpe ao WRC que ja usamos em net mean.
5. **Combinatorial Purged Cross-Validation (CPCV)** (cap. 12.4):
   o walk-forward testa UM caminho historico (facil de overfit; o
   proprio livro mostra que walk-backward inconsistente indica
   overfit). CPCV deriva a distribuicao de Sharpe de MUITOS caminhos
   com purging/embargo. Upgrade natural do funil SE migrarmos para
   modelos com parametros aprendidos (ML).
6. **Meta-labeling / triple-barrier** (cap. 3): rotular com
   barreiras TP/SL + treinar classificador para decidir TAMANHO da
   aposta em sinais ja existentes — aplicavel se um dia tivermos um
   sinal com edge bruto real (H07-MP/H09 tinham; nenhum sobreviveu
   ao custo no stage-2).

## 3.2 O que isso muda no nosso funil (decisao)

- **Nada muda nas 18 execucoes ja registradas** — todas passam nos
  criterios do AFML (pre-especificacao, custos, trials registrados).
- **Incorporacoes a partir de agora** (DECISIONS.md):
  a) PSR/DSR como metrica complementar quando Sharpe for reportado;
  b) CPCV (com purging) para qualquer backtest com otimizacao de
     parametros aprendidos — proibido walk-forward com re-ajuste
     repetido;
  c) manter a regra: "backtest descarta, nao melhora" — reforco do
     pre-registro.
- **Roteiro condicional**: AFML so se aplica plenamente se o projeto
  avancar para ML (ex.: meta-labeling sobre um sinal com edge bruto
  real via custos institucionais). Sem sinal com edge, ML e
  premature.

## 3.3 Conclusao transversal das 3 literaturas

Aronson (metodo) + West (contra-exemplo popular) + Lopez de Prado
(rigor estatistico) convergem no mesmo ponto: **em mercados
liquidos, backtests sem custos calibrados e sem correcao de
multiples testes produzem fool's gold**; edge real exige (a) racional
economico, (b) pre-registro, (c) custos reais, (d) correcao de
selecao. Nosso funil ja implementa (a)-(d). As proximas literaturas
da fila (Harris: microestrutura — por que o custo come o edge;
Lien: sessoes/intermercado) seguem o mesmo pipeline.


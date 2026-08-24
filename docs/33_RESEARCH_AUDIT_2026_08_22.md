# 33 — Auditoria de Pesquisa e Backtests — 2026-08-22

## Conclusão

Nenhuma estratégia auditada está pronta para demo ou execução real.

O principal problema não é falta de complexidade. Nos sinais intradiários, o
edge bruto por trade é menor que a fricção; nas estratégias de horizonte maior,
o edge não se replica entre pares ou fora do development. O melhor candidato
temporário, o ensemble de regime em GBPUSD, foi positivo no development e
negativo na validation.

## Correções de validade

1. H07 ordenava semanas ISO como texto (`W10` antes de `W9`) e podia fabricar
   gaps entre semanas não consecutivas. A agrupação agora preserva ordem
   cronológica e usa rótulos com zero à esquerda.
2. O ATR H1 aceitava uma barra pelo horário de abertura, antes do fechamento.
   A disponibilidade agora é `time + 1h <= decision_time`.
3. H07 usava pip size `0.0001` em USDJPY. O valor correto `0.01` agora é
   resolvido por símbolo.
4. O critério LOYO verificava o resultado total, não cada exclusão anual. Agora
   todas as exclusões precisam permanecer positivas.
5. O research runner conhecia o instrumento USDJPY, mas não passava seu pip
   size a estratégias com parâmetro `pip_size`. O default agora é injetado pelo
   registry, preservando overrides explícitos.

## Auditoria causal

O numerical leak check executou prefix replay e mutação forte do futuro em:

- H03 `volatility_surprise`;
- H03 `slot_percentile`;
- M15 para H1;
- M15 para H4;
- H07 `detect_gaps` corrigido.

Resultado: 5/5 casos e 346/346 linhas passaram, sem warning ou falha. Isso é
evidência forte de causalidade para os casos cobertos, não prova formal para
todo o sistema.

## H07 com Bid/Ask real

Execução direta nos CSVs JForex:

- long entra em Ask e sai em Bid;
- short entra em Bid e sai em Ask;
- slippage + comissão: 1.7 pips por round-trip;
- nenhum spread fixo adicional, pois os lados já incorporam o spread;
- H1 construído causalmente;
- pequenas inconsistências OHLC de arredondamento, no máximo 0.30 pip, foram
  normalizadas e contadas; defeitos maiores continuam rejeitados.

| Par | Trades | Edge bruto Bid | Drag Bid/Ask | Líquido médio | Passa |
|---|---:|---:|---:|---:|---:|
| AUDUSD | 265 | +6.04 pips | 5.64 pips | -1.30 pips | não |
| EURUSD | 203 | +6.26 pips | 3.23 pips | +1.33 pips | sim, apenas critérios simples |
| GBPUSD | 229 | +9.45 pips | 10.53 pips | -2.78 pips | não |
| NZDUSD | 290 | +6.36 pips | 9.39 pips | -4.73 pips | não |
| USDCAD | 202 | +6.60 pips | 10.26 pips | -5.36 pips | não |
| USDCHF | 257 | +6.05 pips | 15.23 pips | -10.88 pips | não |
| USDJPY | 260 | +7.24 pips | 6.79 pips | -1.25 pips | não |

O EURUSD sobrevivente não passa pelo filtro estatístico conservador:

- Sharpe anual: 0.382;
- PSR contra zero: 0.9003, abaixo de 0.95;
- DSR: 0.0 com 18 e 425 trials declarados;
- MinTRL: 996 observações para apenas 607 semanas;
- PBO calculado com somente sete colunas é exploratório e não deve ser usado
  isoladamente como aprovação.

Conclusão: H07 permanece rejeitada como estratégia negociável.

## Ensembles

Os 16 commits remotos de alpha/ensemble/multi-symbol foram integrados por
fast-forward, sem conflito com as alterações locais. A configuração declarativa
foi executada nos sete pares de 2015 a 2026.

- seis pares foram negativos até em zero-cost;
- USDJPY: +5.19% zero-cost e -2.95% explicit-cost;
- nenhum par ficou positivo com custo explícito.

No development 2015–2020, foram testadas as variantes pré-existentes:

- hysteresis: 0/7 positivos líquidos;
- cost-aware: 0/7 positivos líquidos;
- regime: GBPUSD foi o único positivo, +2.82%, PF 1.13, DD 2.16%.

A configuração GBPUSD/regime foi congelada e executada em validation
2021–2023:

- zero-cost: +0.86%, PF 1.09;
- explicit-cost: -0.44%, PF 0.96, 350 trades.

Conclusão: família rejeitada; lockbox não consultado.

## H1/H4

EMA e time-series momentum, com defaults existentes, foram executados em H1 e
H4 nos sete pares durante development. Entre 28 combinações de família/par,
somente EMA-H4/USDCHF foi líquido positivo (+0.24%), sem replicação. A família
não avançou para validation.

## H15 — momentum cross-sectional mensal

H15 foi pré-registrada antes da execução. O portfólio normaliza todos os pares
como moeda estrangeira contra USD, compra as duas vencedoras, vende as duas
perdedoras e rebalanceia mensalmente. Lookbacks fixos: 1, 3, 6 e 12 meses.

| Lookback | Bruto anual | Líquido anual | Sharpe | Anos positivos |
|---:|---:|---:|---:|---:|
| 1m | -0.62% | -0.93% | -0.22 | 3/6 |
| 3m | -2.53% | -2.73% | -0.71 | 0/6 |
| 6m | -2.86% | -3.03% | -0.82 | 0/6 |
| 12m | -1.81% | -1.93% | -0.50 | 0/5 |

Conclusão: rejeitada no development; validation não consultada.

## H16 — carry cross-sectional mensal

H16 foi pré-registrada e usou taxas mensais OECD/FRED de call money com lag
causal completo. O snapshot validado contém 120 meses, oito moedas e zero
ausências. A configuração primária top/bottom 2 produziu +0,85% bruto e +0,83%
líquido ao ano, Sharpe 0,23 e drawdown máximo de -6,32% em 71 meses.

O retorno veio do accrual de juros (+1,19% anual aproximado), parcialmente
consumido pelo spot (-0,34%). As sensibilidades top/bottom 1 e 3 também foram
positivas, mas o gate obrigatório de Sharpe > 0,50 falhou. O leak check passou
138/138 testes; DSR 0,5903 e MinTRL 587,9 meses reforçaram a rejeição.

Conclusão: rejeitada no development; validation e lockbox não consultadas.
Detalhes em `docs/35_H16_CROSS_SECTIONAL_CARRY_RESULT.md`.

## Próxima linha recomendada

O projeto esgotou grande parte das regras derivadas apenas de OHLC/tick volume
nos sete majors. A próxima expansão deve adicionar uma fonte de informação
economicamente distinta, não mais filtros do mesmo preço:

1. dados históricos executáveis de forward points ou swaps, para substituir o
   proxy de call money rejeitado em H16;
2. fator de value cambial, idealmente com PPP/REER;
3. somente depois, blend de carry + value + momentum em portfolio;
4. aumentar o universo de moedas apenas com Bid/Ask e regras de tradabilidade
   explícitas.

A literatura de currency momentum usa retornos excedentes com forwards e
universos bem maiores; o spot-only de sete majors é uma aproximação limitada.

## Verificação

Suíte completa após as mudanças:

```text
1390 passed
```

O projeto continua `READ ONLY` para pesquisa/backtest. Nenhuma chamada de
execução real foi realizada e `TRADING_ENABLED` não foi alterado.

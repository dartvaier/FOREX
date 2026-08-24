# 37 — Resultado da Coleta Pública para Value Cambial

Status: `DATA_READY_FOR_SPECIFICATION` — a base pública permite especificar a
hipótese H17, mas nenhum sinal, parâmetro ou backtest foi aprovado por este
resultado.

## Conclusão

O painel macroeconômico público está suficientemente completo para iniciar a
especificação de um fator de value cambial. As 20 moedas do universo têm REER
mensal e câmbio de referência BIS completos nos 384 meses entre janeiro de
1994 e dezembro de 2025.

Isso ainda não prova edge nem retorno líquido. A base não contém Bid/Ask,
forward points ou swaps históricos específicos da corretora e os indicadores
anuais não são vintages point-in-time.

## Snapshot auditável

- coleta UTC: `2026-08-22T14:25:11.404150+00:00`;
- manifesto: `data/external/value/public_snapshot/manifest.json`;
- fontes: BIS EER, BIS USD exchange rates, World Bank Indicators API e OECD;
- arquivos brutos e normalizados têm SHA256 verificado no carregamento;
- gaps permanecem como ausências, sem `ffill`, interpolação ou backfill.

## Cobertura congelada: 1994–2025

| Painel | Moedas completas | Observações esperadas por moeda |
|---|---:|---:|
| BIS REER mensal | 20/20 | 384 meses |
| BIS USD mensal | 20/20 | 384 meses |
| World Bank PPP anual | 19/20 | 32 anos |
| World Bank câmbio oficial anual | 19/20 | 32 anos |
| OECD PPP anual | 18/20 | 32 anos |

No World Bank, EUR não está disponível como agregado da área do euro. Na OECD,
EUR e SGD têm 31 anos na janela. Não será feito preenchimento artificial.

World Bank e OECD têm 720 observações PPP sobrepostas. A diferença relativa
absoluta mediana é zero, o percentil 95 é aproximadamente `0,00004%` e a maior
diferença é `3,51%`. A fonte primária deverá ser escolhida antes de observar
retornos, sem combinar as duas para melhorar resultado.

## Causalidade numérica

O REER do mês `t` foi deslocado para disponibilidade em `t+2`. O teste executou
prefix replay e mutação forte do futuro para cada uma das 20 moedas.

| Unidade | PASS | WARN | FAIL | ERROR |
|---|---:|---:|---:|---:|
| Casos por moeda | 20 | 0 | 0 | 0 |
| Checkpoints/modos | 760 | 0 | 0 | 0 |

O resultado mostra que alterar observações futuras não muda a história já
disponível pelo painel mensal. A limitação é importante: o teste valida o
transformador mensal de REER, não valida ainda uma estratégia, execução,
custos, PPP anual ou backtest H17.

## Diagnóstico das séries de REER

Foram produzidos relatórios pela API da skill `time-series-analysis`, usando
384 meses e janelas de 120, 240 e 384 meses. No diagnóstico da janela integral:

- 8 moedas foram classificadas como tendência forte/não estacionária;
- 8 como tendência fraca ou contrária;
- 3 apresentaram sinais conflitantes;
- 1, KRW, apresentou tendência com evidência de estacionariedade;
- 16/20 séries apresentaram caudas grossas; apenas DKK, NZD, SEK e USD ficaram
  próximas da distribuição normal nesse diagnóstico;
- somente KRW teve ADF e KPSS conjuntamente compatíveis com estacionariedade
  ao nível de 5%.

Portanto, o nível bruto de REER não deve ser tratado como um sinal diretamente
negociável. A próxima especificação deve estudar desvio relativo, ranking
cross-sectional e normalização robusta, com controle explícito de caudas e de
regimes. Estes diagnósticos escolhem uma direção de pesquisa; não escolhem uma
janela ótima e não constituem evidência de rentabilidade.

## O que ainda falta para validar retorno líquido

1. Bid/Ask histórico ou ticks dos instrumentos realmente negociáveis.
2. Forward points de prazo fixo, preferencialmente 1 mês, ou futuros cambiais
   com regras de rolagem auditáveis.
3. Histórico de `swap_long`, `swap_short`, dia de triplo swap e alterações de
   contrato da corretora que seria usada.
4. Vintages ou datas de publicação verificáveis para PPP anual; na ausência,
   deverá ser usada uma defasagem conservadora pré-registrada.
5. Confirmação de quais moedas exóticas estavam disponíveis e com qual tamanho
   mínimo de lote ao longo do período.

## Próxima decisão de pesquisa

Antes de rodar qualquer backtest H17, congelar em documento separado: fórmula
do value, fonte primária, janela, universo negociável, frequência de rebalance,
regra de publicação, custos, critérios de aceitação/rejeição e divisões
train/validation/OOS. A lockbox permanece intocada.

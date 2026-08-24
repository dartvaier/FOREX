# 38 — Coleta de Bid/Ask e Swaps da Corretora

Status: `FP_MARKETS_DEMO_CONNECTED / COLLECTION_VALIDATED`

## Conclusão

O projeto possui um coletor MT5 somente leitura capaz de exportar ticks Bid/Ask
em blocos, registrar os termos atuais de swap e gerar um manifesto com SHA256.
A conta `FPMarketsSC-Demo`, Raw e em USD foi conectada e validada em 22 de
agosto de 2026. Isto permite pesquisa do feed e dos custos divulgados pela
corretora, mas ainda não autoriza execução real.

## Ensaio concluído

- símbolo: `EURUSD`;
- janela: `2026-08-21 23:00:00Z` até `2026-08-22 00:00:00Z`;
- ticks: `7.393`;
- quotes válidos: `7.393`;
- quotes inválidos: `0`;
- armazenamento: Parquet com timestamps UTC;
- servidor: `MetaQuotes-Demo`;
- modo da conta: demo;
- nenhuma ordem foi enviada.

O ensaio original em `MetaQuotes-Demo` foi substituído como fonte-alvo. No
primeiro ensaio FP Markets foram encontrados todos os 19 instrumentos de H17 no
perfil Raw, com sufixo `.r`. Uma hora ativa produziu 73.539 ticks em 17/19
símbolos. `USDBRL.r` exigirá uma janela compatível com seu horário de cotação;
`USDTRY.r` apresentou último tick em 18 de agosto de 2026 e está suspenso da
pesquisa até nova auditoria.

O snapshot registrou `swap_mode`, `swap_long`, `swap_short`, dia de triplo
swap, tamanho do contrato, moedas do contrato e limites de lote. Esses valores
representam somente a especificação observada naquele instante.

## Como coletar na corretora correta

1. Abrir o MT5 e entrar na conta `FPMarketsSC-Demo`. Uma conta demo é suficiente
   para pesquisar quotes e especificações, mas execução e slippage podem ser
   diferentes de uma conta real.
2. Exibir no Market Watch os símbolos exatos, incluindo prefixos ou sufixos da
   corretora.
3. Confirmar que o cabeçalho `server` no manifesto corresponde à corretora.
4. Fazer primeiro um snapshot de swaps:

```powershell
python collect_broker_data.py --profile fpmarkets_raw_h17
```

5. Coletar ticks em janelas pequenas. Exemplo de um dia UTC:

```powershell
python collect_broker_data.py `
  --symbols EURUSD.r GBPUSD.r `
  --date-from 2026-08-20T00:00:00Z `
  --date-to 2026-08-21T00:00:00Z `
  --chunk-hours 6
```

Os arquivos são gravados em `data/external/broker/mt5/`, fora do Git. Cada
execução cria uma pasta imutável com `manifest.json`, `swap_terms.json` e os
Parquets de ticks.

## Profundidade observada

Consultas pontuais de um minuto em `EURUSD.r` encontraram ticks a partir de
`2025-01-02`. As mesmas consultas não encontraram ticks em 2024 ou antes. Isso
indica uma janela de aproximadamente 20 meses no servidor atual, suficiente
para calibrar custos recentes e testar regimes, mas insuficiente para substituir
o histórico de preços 2015–2021 ou validar sozinho um edge estrutural.

## Coleta operacional de 30 dias

A primeira coleta operacional foi concluída para os 17 símbolos com histórico
funcional, de `2026-07-23T00:00:00Z` até `2026-08-22T00:00:00Z`:

| Métrica | Resultado |
|---|---:|
| Símbolos | 17 |
| Arquivos diários | 510 |
| Ticks Bid/Ask | 28.395.208 |
| Quotes inválidos | 0 |
| Tamanho Parquet | 642.080.873 bytes |
| Arquivos sem ticks | 137 |

Os arquivos vazios são esperados principalmente nos oito dias de fim de semana
da janela. Dezesseis símbolos tiveram oito arquivos vazios; `USDKRW.r` teve
nove, indicando uma ausência adicional de sessão que deve permanecer explícita.
Nenhum gap foi preenchido.

O snapshot está em:

```text
data/external/broker/mt5/20260822T152810319039Z/manifest.json
```

Todos os SHA256, arquivos e contagens de linhas foram verificados após o
download.

## Captura recorrente de swaps

A automação `FP Markets — snapshot diário de swaps` está ativa no Codex em dias
úteis às 22:15 no horário local. Ela aceita somente `FPMarketsSC-Demo` com
`trade_mode=0`, executa o perfil `fpmarkets_raw_h17` e verifica o manifesto.
O terminal MT5 precisa permanecer instalado, aberto e conectado quando a rotina
for executada. Falha de conexão deve ser reportada; a rotina nunca envia ordens.

## Limite do MT5 para swaps históricos

`symbol_info()` expõe a especificação corrente. A API Python não oferece uma
série histórica das alterações de `swap_long` e `swap_short`. O histórico de
deals pode mostrar o swap cumulativo efetivamente pago ao fechar posições da
própria conta, mas isso serve para reconciliação e não reconstrói a tabela
diária de swap para todos os símbolos e lados.

Por isso, os termos devem ser capturados diariamente daqui em diante. Para o
passado, é necessário solicitar à corretora um arquivo ou extrato contratual.

## Solicitação exata à corretora

Solicitar, para cada símbolo e cada dia em UTC ou com timezone declarado:

```text
date, symbol, swap_mode, swap_long, swap_short,
rollover_cutoff_timezone, triple_swap_day,
long_daily_multiplier, short_daily_multiplier,
contract_size, point, account_currency
```

Também pedir a fórmula usada em cada `swap_mode`, datas de mudança de contrato,
feriados com multiplicadores especiais e confirmação se os dados são os mesmos
para conta demo e real.

## Critério de suficiência

- Bid/Ask: idealmente todo o período de backtest; mínimo aceitável para uma
  primeira calibração de custo é cobrir regimes normais, estresse, aberturas,
  fechamento semanal e rollover.
- Swap: histórico diário real da corretora é o alvo. Se não existir, usar
  forward points como benchmark econômico e limitar qualquer validação de swap
  específico ao período iniciado pelos snapshots diários.
- Nunca aplicar o swap observado hoje retroativamente a anos anteriores.

# 36 — Contrato de Dados para Pesquisa de Value Cambial

Status: `SPECIFIED` — contrato criado antes da coleta, normalização e inspeção
dos resultados de cobertura. Este documento não autoriza backtest de H17.

## Objetivo

Construir uma base pública, auditável e causalmente explícita para uma futura
hipótese de value cambial. A coleta não define ranking, pesos, janela de value
ou critério de aceitação; essas escolhas exigirão um pré-registro separado.

## Universo de coleta

```text
AUD, BRL, CAD, CHF, CZK, DKK, EUR, GBP, HUF, JPY,
KRW, MXN, NOK, NZD, PLN, SEK, SGD, TRY, USD, ZAR
```

Inclusão na base não significa tradabilidade. Uma moeda só poderá entrar em um
backtest quando houver spot e custo executável para o período correspondente.

## Fontes congeladas

1. BIS Effective Exchange Rates, bulk CSV flat:
   - frequência mensal;
   - REER real;
   - cesta ampla;
   - índice 2020 = 100.
2. BIS US Dollar Exchange Rates, bulk CSV flat:
   - frequência mensal;
   - média das observações do período;
   - unidades de moeda local por USD.
3. World Bank Indicators API:
   - `PA.NUS.PPP`, PPP do PIB;
   - `PA.NUS.FCRF`, câmbio oficial médio em moeda local por USD;
   - price level derivável de forma transparente como `PPP / câmbio`.
4. OECD Annual Purchasing Power Parities and Exchange Rates:
   - frequência anual;
   - transação `PPP_B1GQ`;
   - unidade moeda nacional por USD internacional.

## Auditoria e arquivos

Cada download registra URL, horário UTC, SHA256, tamanho e nome local. Cada
arquivo normalizado registra SHA256, linhas, moedas, primeira/última data e
ausências. O loader recusa arquivo alterado ou mapeamento inesperado.

Arquivos brutos e derivados ficam em `data/external/value/public_snapshot/` e
não entram no Git. Código, testes e relatório de cobertura permanecem no
repositório.

## Disponibilidade causal

- REER mensal: a observação do mês `t` só entra no painel de disponibilidade
  em `t+2`, regra conservadora equivalente a usar `t-2` no mês de decisão.
- Nenhum gap mensal é preenchido; uma ausência continua ausente.
- PPP World Bank/OECD é anual, revisável e não é vintage point-in-time. A
  coleta preserva o ano observado, mas não inventa `available_at` histórico.
  Um futuro fator PPP deverá congelar uma política de publicação antes do
  backtest ou obter vintages verificáveis.
- Todos os timestamps derivados são timezone-aware em UTC.

## Restrições

- não consultar retornos de validation/lockbox nesta fase;
- não escolher moedas pela cobertura depois de observar performance;
- não usar dados BIS/World Bank/OECD como substitutos de Bid/Ask ou forward;
- não fazer `ffill`, interpolação ou backfill;
- não executar ordens nem alterar `TRADING_ENABLED`.

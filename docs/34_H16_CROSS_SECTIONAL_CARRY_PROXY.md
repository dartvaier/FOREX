# 34 — H16: Carry Cross-Sectional Mensal com Taxas de Curto Prazo

Status: `REJECTED_IN_DEVELOPMENT` — pré-registro criado antes do download e do
primeiro backtest; resultado documentado em
`docs/35_H16_CROSS_SECTIONAL_CARRY_RESULT.md`.

## Hipótese

Uma carteira mensal comprada nas duas moedas com maior diferencial de juros de
curto prazo contra USD e vendida nas duas com menor diferencial deve produzir
retorno spot + accrual de carry positivo após custos.

H16 é um **proxy de carry**, não um backtest de forward negociável. O dado
ideal seria o forward point executável ou o swap histórico do broker. A taxa
interbancária permite testar a direção econômica e o accrual aproximado sem
inventar carry estático.

Referências:

- Burnside, Eichenbaum e Rebelo (2011), *Carry Trade and Momentum in Currency
  Markets*, NBER 16942: https://doi.org/10.3386/w16942
- Lustig, Roussanov e Verdelhan (2011), *Common Risk Factors in Currency
  Markets*: https://doi.org/10.1093/rfs/hhq136

## Fonte de dados congelada

Séries mensais OECD Main Economic Indicators, distribuídas pelo FRED:

| Moeda | Série FRED |
|---|---|
| AUD | `IRSTCI01AUM156N` |
| CAD | `IRSTCI01CAM156N` |
| CHF | `IRSTCI01CHM156N` |
| EUR | `IRSTCI01EZM156N` |
| GBP | `IRSTCI01GBM156N` |
| JPY | `IRSTCI01JPM156N` |
| NZD | `IRSTCI01NZM156N` |
| USD | `IRSTCI01USM156N` |

Medida: taxa interbancária de call money/imediata (prazo inferior a 24 horas),
percentual anual, não ajustada sazonalmente, frequência mensal.

Cada download deve registrar URL, horário UTC, SHA256, primeira/última data,
número de observações e ausências. Backtests leem somente o snapshot local; não
acessam a rede.

### Emenda pré-execução — 2026-08-22

O pré-registro inicial especificava as oito séries OECD/FRED de taxa
interbancária de 3 meses (`IR3TIB01...`). A inspeção do snapshot, antes de
qualquer backtest, encontrou uma observação ausente na série USD em 2020-04.
Como o protocolo proíbe `ffill`, interpolação ou omissão silenciosa, esse
conjunto foi considerado estruturalmente incompleto para a janela de pesquisa.

Para não misturar maturidades entre moedas, as oito séries foram substituídas
uniformemente pela família OECD/FRED `IRSTCI01...`, de call money/imediata. As
regras de sinal, lag, carteira, custos, partições e aceitação permaneceram
inalteradas. O snapshot original de 3 meses foi preservado como trilha de
auditoria e nenhum resultado de H16 havia sido calculado no momento desta
emenda.

## Disponibilidade causal

A observação mensal é uma média do mês e não está disponível no início desse
mesmo mês. Para o holding do mês `t`, o sinal usa exclusivamente a observação
de `t-2`:

```text
fim de t-1: decisão
taxa mais recente permitida: t-2
holding: t
```

Essa defasagem completa de um mês após o fim da observação é conservadora para
publicação. Não haverá `ffill` sobre uma ausência: qualquer mês sem as oito
moedas falha explicitamente.

O snapshot atual do FRED pode conter revisões históricas. A defasagem elimina
look-ahead de calendário, mas não transforma o arquivo em vintage point-in-time.
Essa limitação deve permanecer no relatório.

## Universo e orientação

Pares fixos:

```text
AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY
```

Diferencial por moeda estrangeira:

```text
rate_foreign - rate_USD
```

O retorno spot é normalizado como valor da moeda estrangeira em USD:

- `XXXUSD`: preço direto;
- `USDXXX`: inverso do preço.

## Portfólio congelado

- rebalanceamento mensal;
- long nas duas moedas com maior diferencial;
- short nas duas com menor diferencial;
- peso `+0.25` por long e `-0.25` por short;
- exposição bruta `1.0`, líquida `0.0`;
- três moedas intermediárias sem posição;
- empates resolvidos alfabeticamente;
- posição inalterada não paga novo turnover.

Retorno mensal por moeda:

```text
spot_return + (rate_foreign - rate_USD) / 100 / 12
```

O portfólio soma esse retorno multiplicado pelo peso. O accrual é um proxy
linear e não inclui convenções específicas de calendário, mark-up do broker ou
roll triplo.

## Custos

- baseline: 3.7 pips por round-trip completo;
- custo cobrado pela variação absoluta dos pesos, metade em cada lado;
- pip size específico por instrumento;
- liquidação final incluída;
- stress pré-definido: `1.5x`.

## Partições

```text
development: 2015-01-01 até 2021-01-01
validation:  2021-01-01 até 2024-01-01
lockbox:     2024-01-01 em diante
```

O lockbox não será consultado nesta etapa.

## Sensibilidade pré-definida

Sem escolher o melhor resultado depois do teste:

- primário: top/bottom 2;
- sensibilidade concentrada: top/bottom 1;
- sensibilidade diversificada: top/bottom 3.

## Critérios para avançar

H16 só avança para validation se, no development:

1. configuração primária tiver retorno anualizado líquido `> 0`;
2. Sharpe anualizado primário `> 0.50`;
3. primário permanecer positivo sob custo `1.5x`;
4. pelo menos 4 anos civis forem positivos;
5. nenhum ano representar mais de 50% da soma dos anos positivos;
6. top/bottom 1 e top/bottom 3 também tiverem retorno líquido positivo.

Se todos passarem, somente top/bottom 2 será executado uma vez em validation.
Retorno líquido ou Sharpe `<= 0` em validation rejeita a hipótese.

## Restrições

- nenhuma alteração de parâmetro após ver development;
- não consultar lockbox para salvar a hipótese;
- não chamar o resultado de forward carry;
- nenhuma execução demo ou real;
- não alterar `TRADING_ENABLED`.

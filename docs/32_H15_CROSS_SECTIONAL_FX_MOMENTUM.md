# 32 — H15: Momentum Cross-Sectional Mensal de Moedas

Status: `SPECIFIED` — pré-registro criado antes da primeira execução histórica.

## Hipótese

Entre os sete majors disponíveis, moedas com maior retorno recente contra o
dólar tendem a superar, no mês seguinte, moedas com menor retorno recente. Um
portfólio comprado nas duas vencedoras e vendido nas duas perdedoras deve ter
turnover suficientemente baixo para sobreviver aos custos explícitos.

Esta é uma aproximação **spot-only**. A literatura original usa retornos
excedentes com forwards; portanto, um resultado negativo não refuta o prêmio
acadêmico de moeda, apenas sua implementação possível com os dados deste
projeto.

Referências de origem da hipótese:

- Menkhoff, Sarno, Schmeling e Schrimpf (2012), *Currency Momentum
  Strategies*, JFE, DOI: https://doi.org/10.1016/j.jfineco.2012.06.009
- Burnside, Eichenbaum e Rebelo (2011), *Carry Trade and Momentum in Currency
  Markets*, NBER 16942: https://doi.org/10.3386/w16942

## Universo e normalização

Universo fixo:

```text
AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY
```

Todos os preços serão convertidos para “valor da moeda estrangeira em USD”:

- pares `XXXUSD`: usar o preço diretamente;
- pares `USDXXX`: usar o inverso do preço.

Isso impede que a orientação do ticker inverta artificialmente vencedores e
perdedores.

## Regras congeladas

- Dados: H4 fechado, com disponibilidade em `time + 4h`.
- Frequência de decisão: mensal.
- Formação: retornos de 1, 3, 6 e 12 meses, definidos antes dos resultados.
- Holding: um mês, com rebalanceamento no fechamento mensal disponível.
- Long: duas moedas de maior retorno de formação.
- Short: duas moedas de menor retorno de formação.
- Peso: `+0.25` por long e `-0.25` por short; exposição bruta total `1.0` e
  exposição líquida `0.0`.
- Empates: ordem alfabética estável, apenas para determinismo.
- Sem posição nas três moedas intermediárias.
- Uma posição mantida de um mês para o seguinte não paga novo giro.

## Custos

Baseline: `3.7 pips` por round-trip completo. O backtest cobra metade desse
custo em cada variação de peso, usando o pip size correto do instrumento e o
preço conhecido no instante do rebalanceamento. Também cobra a liquidação final.

Stress pré-definido: `1.5x` o baseline.

## Partições temporais

```text
development: 2015-01-01 até 2021-01-01
validation:  2021-01-01 até 2024-01-01
lockbox:     2024-01-01 em diante
```

O lockbox não será consultado nesta etapa.

## Critérios de avanço

H15 só avança para validation se, no development:

1. retorno anualizado líquido for positivo em pelo menos 3 dos 4 lookbacks;
2. o lookback primário de 6 meses tiver Sharpe anualizado líquido `> 0.50`;
3. o lookback de 6 meses permanecer positivo sob custo `1.5x`;
4. pelo menos 4 anos civis tiverem retorno líquido positivo;
5. nenhum único ano responder por mais de 50% do lucro líquido positivo total.

Se avançar, a configuração primária de 6 meses será executada uma única vez em
validation, sem alteração. O resultado será rejeitado se retorno líquido ou
Sharpe forem `<= 0`.

## Limitações conhecidas

- apenas sete moedas desenvolvidas, enquanto os estudos usam universos maiores;
- ausência de forwards, diferencial de juros e swap realizado;
- apenas cerca de seis anos no development após o warm-up de 12 meses;
- custos fixos conservadores, não Bid/Ask mensal por evento;
- não representa autorização para execução real.

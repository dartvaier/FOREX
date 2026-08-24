# 35 — Resultado H16: Carry Cross-Sectional Mensal

## Conclusão

H16 foi **rejeitada no development**. O carry econômico apareceu, mas foi
fraco demais para o critério estatístico pré-registrado. Validation
2021–2023 e lockbox 2024+ não foram consultados.

## Dados e emenda pré-execução

O snapshot original de taxas interbancárias de três meses tinha uma ausência
na série USD em 2020-04. Nenhum backtest havia sido executado. Em vez de
preencher ou misturar maturidades, as oito moedas foram substituídas
uniformemente pelas séries OECD/FRED mensais de call money/imediatas
`IRSTCI01...`.

O snapshot final contém 120 meses completos entre 2014-01 e 2023-12, oito
moedas e zero ausências. Cada arquivo é validado por SHA256. As taxas atuais do
FRED não são vintages point-in-time; esta limitação permanece.

## Resultado de development

Janela efetivamente observável: 2015-02 a 2020-12, 71 retornos mensais. Janeiro
de 2015 não pôde ser incluído porque a base spot começa em janeiro e o primeiro
holding exige o fechamento de dezembro de 2014 para formação.

| Carteira | Bruto anual | Líquido anual | Sharpe | DD máximo | Stress 1,5x |
|---|---:|---:|---:|---:|---:|
| top/bottom 1 | +1,85% | +1,82% | 0,40 | -7,05% | +1,81% |
| top/bottom 2 (primária) | +0,85% | +0,83% | 0,23 | -6,32% | +0,82% |
| top/bottom 3 | +0,21% | +0,21% | 0,07 | -6,81% | +0,20% |

Na configuração primária, a decomposição anualizada aproximada foi:

- retorno spot: -0,34%;
- accrual do diferencial de juros: +1,19%;
- bruto combinado: +0,85%;
- líquido após custos: +0,83%.

Isso mostra que o fator de carry existiu na direção esperada, mas a depreciação
spot consumiu parte relevante do prêmio e a volatilidade deixou o Sharpe baixo.

## Gate pré-registrado

| Critério | Resultado |
|---|---|
| líquido primário > 0 | passa |
| Sharpe primário > 0,50 | **falha (0,23)** |
| positivo a custo 1,5x | passa |
| pelo menos 4 anos positivos | passa (4/6) |
| concentração anual <= 50% | passa (40,99%) |
| top/bottom 1 e 3 positivos | passa |

Como um dos critérios obrigatórios falhou, a regra congelada impediu a abertura
da validation.

## Auditoria causal

O numerical leak check cobriu as três configurações com 23 checkpoints por
case, concentrados no lag mensal, viradas de ano, pontos proporcionais e fim da
amostra. Foram executados prefix replay e mutação extrema de preços e taxas
futuras.

| status | cases | testes |
|---|---:|---:|
| PASS | 3 | 138 |
| WARN | 0 | 0 |
| FAIL | 0 | 0 |
| ERROR | 0 | 0 |

O PASS significa que estes testes numéricos não encontraram dependência do
futuro; não é prova formal de ausência de todo tipo de vazamento. O custo/net do
último ponto de cada prefixo foi excluído da comparação porque a liquidação na
fronteira artificial é deliberadamente diferente.

## Overfitting e tamanho de amostra

A configuração primária foi avaliada com as três variações pré-declaradas:

- Sharpe anual observado: 0,2345;
- PSR contra zero: 0,7150;
- DSR: 0,5903, abaixo do gate 0,95;
- Sharpe após Bonferroni: 0,00;
- MinTRL: 587,9 meses, contra 71 observados;
- PBO: 0,409, apenas diagnóstico exploratório porque três configurações são
  insuficientes para um PBO confiável.

Mesmo sem o gate pré-registrado de Sharpe, a evidência estatística não permite
tratar o retorno como edge confiável.

## Artefatos

- pré-registro: `docs/34_H16_CROSS_SECTIONAL_CARRY_PROXY.md`;
- dados: `research/carry_data.py`;
- backtest: `research/cross_sectional_carry.py`;
- causalidade: `research/h16_leak_check_adapter.py`;
- resultado: `research/reports/h16_cross_sectional_carry_dev.{json,csv}`;
- leak check: `research/reports/h16_leak_check_dev/`;
- overfit: `research/reports/h16_overfit_dev/overfit_report.json`.

## Decisão

H16 permanece útil como evidência de que carry é uma fonte de informação
economicamente distinta e superior ao momentum spot testado em H15. Porém, o
proxy de call money em sete majors não oferece retorno ajustado ao risco
suficiente. Não ajustar ranking, lag ou número de moedas após este resultado.

Próxima pesquisa recomendada: dados históricos executáveis de forward
points/swaps ou um fator cambial de value (REER/PPP), com novo pré-registro.

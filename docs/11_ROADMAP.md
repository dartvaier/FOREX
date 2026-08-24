# Roadmap

## Estado oficial

Este é o roadmap versionado da plataforma **FOREX Algorithmic Trading Research
Platform**. Ele descreve o estado integrado do repositório e a ordem autorizada
de avanço; não registra resultados científicos que ainda não existem.

| Marco | Escopo | Estado |
| --- | --- | --- |
| F0–F4 | Metodologia, ambiente e dados | ✅ Concluído |
| F5 | Quantitative Research Core | ✅ Concluído |
| F6.1–F6.7 | Research Automation & Agent Tool Layer | ✅ Concluído |
| F6.8a–F6.8e | Proposal Quality / catálogo e validação | ✅ F6.8e concluído; acceptance ainda pendente |
| F7 | Paper & Demo Trading | ⬜ Não iniciado |
| F8 | Monitoring & Operations | ⬜ Não iniciado |
| F9 | Live-readiness Gate | ⬜ Não iniciado |

Os detalhes de implementação de F5 estão em `docs/12_F5_DOMAIN_MODELS.md`
até `docs/26_F5_STRATEGY_REGISTRY.md`. O registro auditável de F6 e das PRs
integradas está em `docs/42_F6_AUDIT_STATUS.md`.

## F5 — Quantitative Research Core

F5 está concluído. A camada quantitativa fornece o fluxo determinístico de
pesquisa e validação: modelos de domínio, contexto temporal, portfólio e
custos, execução simulada, métricas, experimentos, sensibilidade,
walk-forward, Strategy Gate e registry auditável.

Os resultados de uma estratégia não são inferidos a partir da conclusão de
F5. Em especial, este roadmap não afirma resultado de holdout, edge, aprovação
de Strategy Gate ou aptidão para negociação.

## F6 — Research Automation & Agent Tool Layer

F6.1–F6.7 estão concluídos. A camada expõe somente operações tipadas e
auditáveis para pesquisa; o agente não é uma camada de execução ou de
autoridade quantitativa.

F6.8 foi evoluído até **F6.8e — Catalog Closure Validation**, concluído e
integrado. O catálogo atual é deliberadamente fechado: somente
`EMA_CROSSOVER` declarativo, para EURUSD/H1, com `fast_period` e
`slow_period` inteiros positivos e fixos por `StrategySpec` e por Experimento.
ATR, RSI, MACD, Bollinger e períodos/adaptações dynamic, adaptive,
volatility-adjusted ou regime-dependent falham fechados.

### Estado de acceptance de F6.8

**F6.8 Proposal Quality Acceptance não está concluído.** O critério pendente
é um único proposal-only válido que resulte em proposal `ACCEPTED` e seja
depois `HUMAN APPROVED`. Até que ambos ocorram, nenhuma proposal autoriza
freeze, Experiment, Sensitivity, Walk-Forward, Strategy Gate, Assessment ou
ControlledResearchLoop.

A última tentativa de canary F6.8e terminou em `CONNECTION_REFUSED` porque o
Ollama estava indisponível. Ela não gerou proposal, não executou validação, não
criou pacote para revisão humana e não autorizou pesquisa. Esse evento é uma
falha de infraestrutura do provider, não um resultado científico nem uma
aceitação/rejeição de proposal.

O estado de autorização permanece:

```text
research_authorization = NOT_AUTHORIZED
```

## Guardrails imutáveis

Os itens abaixo são limites arquiteturais, não preferências do agente:

- O LLM nunca chama `order_send` e não tem acesso a MT5.
- O LLM nunca altera métricas calculadas, `GateStatus`, holdout ou evidência
  congelada.
- `Signal != Order`: uma estratégia expressa intenção; não cria uma ordem.
- O Risk Engine determinístico possui a autoridade final para aprovar ou
  rejeitar uma ordem.
- Não há look-ahead: estratégias usam barras fechadas; o sinal no close é
  executado no open da próxima barra real.
- Gaps são preservados, nunca preenchidos artificialmente.
- Fingerprints, idempotência, ordem de protocolo e trilha de auditoria são
  obrigatórios para artefatos e transições de pesquisa.
- O agente não tem shell, filesystem arbitrário, código arbitrário, MT5 ou
  acesso direto a runners quantitativos.

Qualquer tentativa de violar esses limites falha fechada. O agente pode propor
ou interpretar dentro do contrato; validators, serviços quantitativos,
orquestrador, registry, evidência e Gate continuam autoritativos.

## Próxima sequência autorizável

A ordem é estrita e não deve ser encurtada:

```text
1. Restaurar o provider Ollama e concluir a acceptance humana de F6.8
   com um proposal-only válido: ACCEPTED + HUMAN APPROVED.

2. Executar exatamente um ciclo congelado:
   Registration
     → Experiment
     → Sensitivity
     → Walk-Forward
     → Strategy Gate
     → Assessment
     → STOP

3. Somente depois desse ciclo: F7 Paper & Demo Trading.

4. Depois: F8 Monitoring & Operations.

5. Por último: F9 Live-readiness Gate.
```

O ciclo do item 2 depende de aprovação humana explícita e preserva seus
fingerprints, critérios e evidência congelados. Nenhuma repetição para buscar
um resultado diferente, alteração pós-hoc de parâmetros, consulta antecipada
ao holdout ou avanço automático é permitido.

## Regra de progresso

Uma fase só pode avançar quando os seus critérios estiverem satisfeitos e o
estado resultante for reproduzível, auditável e explicitamente autorizado. A
conclusão técnica de F5 ou F6.8e não substitui acceptance humana, validação
quantitativa nem o Live-readiness Gate.

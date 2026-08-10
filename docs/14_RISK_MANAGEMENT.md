# Risk Management

## 1. Objetivo

Este documento registra a fase:

```text
F7 - Risk Management
```

O objetivo da F7 e separar:

```text
decisao de mercado
```

de:

```text
decisao de exposicao financeira
```

Uma Strategy pode indicar direcao, racional e stop tecnico.

O tamanho final da posicao pertence ao RiskGate.

---

## 2. Estado Atual

Status:

```text
IN PROGRESS
```

Primeiro bloco implementado:

```text
RiskGate protocol

RiskDecision

VolumeRules

FixedSizeRiskGate

StopBasedRiskGate

ExposureLimitRiskGate
```

---

## 3. RiskGate

Contrato:

```text
Signal
  ->
RiskGate.evaluate(signal)
  ->
RiskDecision
```

O resultado pode ser:

```text
approved=True
```

ou:

```text
approved=False
```

Sinais rejeitados pelo risco nao geram Order.

---

## 4. FixedSizeRiskGate

Mantem o baseline historico usado nas pesquisas F6.

Entrada:

```text
fixed_quantity
```

Validacoes:

```text
quantity > 0

quantity >= volume_min

quantity <= volume_max

quantity respeita volume_step
```

---

## 5. StopBasedRiskGate

Calcula o tamanho da posicao a partir de:

```text
account_equity

risk_fraction

entry_price

stop_loss

contract_size
```

Metadata obrigatoria para entradas:

```text
entry_price

stop_loss
```

Formula:

```text
risk_amount = account_equity * risk_fraction

risk_per_lot = abs(entry_price - stop_loss) * contract_size

raw_quantity = risk_amount / risk_per_lot
```

Depois disso o volume e normalizado para baixo respeitando:

```text
volume_step
```

e validado contra:

```text
volume_min

volume_max
```

---

## 6. Rejeicoes Auditaveis

## 6. ExposureLimitRiskGate

Envolve outro RiskGate:

```text
inner RiskGate
  ->
ExposureLimitRiskGate
```

Limites suportados:

```text
max_quantity

max_notional
```

O limite nocional usa:

```text
entry_price * contract_size * quantity
```

Por isso `max_notional` exige:

```text
entry_price
```

na metadata do Signal.

Sinais `HOLD` e `EXIT` passam sem checagem de exposicao nova porque nao
aumentam posicao.

---

## 7. Rejeicoes Auditaveis

O RiskGate rejeita entradas quando:

```text
entry_price ausente

stop_loss ausente

stop_loss do long nao esta abaixo do entry_price

stop_loss do short nao esta acima do entry_price

volume calculado fica abaixo de volume_min

quantity excede max_quantity

notional excede max_notional
```

Essas rejeicoes retornam:

```text
RiskDecision(approved=False)
```

com motivo em:

```text
reason
```

---

## 8. Limites Ainda Pendentes

Implementado:

```text
max exposure
```

Ainda nao implementado:

```text

daily loss guard

maximum drawdown guard

kill switch

portfolio-level risk

multi-symbol risk
```

Esses itens continuam como proximos blocos da F7.

---

## 9. Testes

Coberto por testes:

```text
RiskDecision validation

FixedSizeRiskGate

VolumeRules

StopBasedRiskGate long/short

ExposureLimitRiskGate

missing entry_price

missing stop_loss

invalid stop side

volume_step normalization

max_quantity cap

max_notional cap

engine integration
```

---

## 10. Proximo Passo

Avancar para:

```text
Daily loss guard
```

Objetivo:

```text
impedir novas entradas quando a perda diaria realizada ou simulada
atingir o limite configurado
```

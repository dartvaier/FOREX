from collections import defaultdict
from datetime import datetime
import math
from numbers import Real

from alpha.ledger import AlphaLedgerRecord


def alpha_direction(
    value: float,
    *,
    neutral_threshold: float = 0.0,
) -> int:
    """
    Convert a continuous alpha value into a coarse direction.

    Returns:

    - +1 for bullish
    - -1 for bearish
    -  0 for neutral
    """

    _validate_threshold(
        neutral_threshold
    )

    if value > neutral_threshold:
        return 1

    if value < -neutral_threshold:
        return -1

    return 0


def coverage_rate(
    records: tuple[AlphaLedgerRecord, ...],
    *,
    model_id: str | None = None,
    symbol: str | None = None,
) -> float:
    """
    Fraction of alpha records that did not abstain.
    """

    selected = _select_records(
        records,
        model_id=model_id,
        symbol=symbol,
    )

    if not selected:
        return 0.0

    active = sum(
        1
        for record in selected
        if not record.abstained
    )

    return active / len(selected)


def agreement_rate(
    records: tuple[AlphaLedgerRecord, ...],
    *,
    neutral_threshold: float = 0.0,
    min_active_models: int = 2,
) -> float:
    """
    Fraction of comparable timestamps where active models agree.

    Abstained records do not participate. Neutral active records
    are treated as a real direction (0), not as abstention.
    """

    groups = _comparable_direction_groups(
        records,
        neutral_threshold=neutral_threshold,
        min_active_models=min_active_models,
    )

    if not groups:
        return 0.0

    agreeing = sum(
        1
        for directions in groups
        if len(set(directions)) == 1
    )

    return agreeing / len(groups)


def disagreement_rate(
    records: tuple[AlphaLedgerRecord, ...],
    *,
    neutral_threshold: float = 0.0,
    min_active_models: int = 2,
) -> float:
    """
    Fraction of comparable timestamps where active models differ.
    """

    groups = _comparable_direction_groups(
        records,
        neutral_threshold=neutral_threshold,
        min_active_models=min_active_models,
    )

    if not groups:
        return 0.0

    disagreeing = sum(
        1
        for directions in groups
        if len(set(directions)) > 1
    )

    return disagreeing / len(groups)


def signal_turnover_rate(
    records: tuple[AlphaLedgerRecord, ...],
    *,
    model_id: str | None = None,
    symbol: str | None = None,
    neutral_threshold: float = 0.0,
) -> float:
    """
    Fraction of consecutive active alpha records whose direction
    changed.

    Abstained records are skipped. Neutral active records count as
    direction 0.
    """

    selected = tuple(
        record
        for record in _select_records(
            records,
            model_id=model_id,
            symbol=symbol,
        )
        if not record.abstained
    )

    if len(selected) < 2:
        return 0.0

    ordered = tuple(
        sorted(
            selected,
            key=lambda record: (
                record.symbol,
                record.model_id,
                record.timestamp,
            ),
        )
    )

    transitions = 0
    changes = 0

    previous_key: tuple[str, str] | None = None
    previous_direction: int | None = None

    for record in ordered:
        key = (
            record.symbol,
            record.model_id,
        )
        direction = alpha_direction(
            record.value,
            neutral_threshold=neutral_threshold,
        )

        if previous_key == key and previous_direction is not None:
            transitions += 1

            if direction != previous_direction:
                changes += 1

        previous_key = key
        previous_direction = direction

    if transitions == 0:
        return 0.0

    return changes / transitions


def _comparable_direction_groups(
    records: tuple[AlphaLedgerRecord, ...],
    *,
    neutral_threshold: float,
    min_active_models: int,
) -> tuple[tuple[int, ...], ...]:
    _validate_threshold(
        neutral_threshold
    )

    if (
        not isinstance(min_active_models, int)
        or isinstance(min_active_models, bool)
        or min_active_models < 2
    ):
        raise ValueError(
            "min_active_models must be an integer >= 2"
        )

    _validate_records(records)

    grouped: dict[
        tuple[str, datetime],
        list[AlphaLedgerRecord],
    ] = defaultdict(list)

    for record in records:
        grouped[
            (
                record.symbol,
                record.timestamp,
            )
        ].append(record)

    direction_groups = []

    for group in grouped.values():
        active = tuple(
            record
            for record in group
            if not record.abstained
        )

        if len(active) < min_active_models:
            continue

        direction_groups.append(
            tuple(
                alpha_direction(
                    record.value,
                    neutral_threshold=neutral_threshold,
                )
                for record in active
            )
        )

    return tuple(direction_groups)


def _select_records(
    records: tuple[AlphaLedgerRecord, ...],
    *,
    model_id: str | None,
    symbol: str | None,
) -> tuple[AlphaLedgerRecord, ...]:
    _validate_records(records)

    if (
        model_id is not None
        and (
            not isinstance(model_id, str)
            or not model_id.strip()
        )
    ):
        raise ValueError(
            "model_id must be a non-empty string or None"
        )

    if (
        symbol is not None
        and (
            not isinstance(symbol, str)
            or not symbol.strip()
        )
    ):
        raise ValueError(
            "symbol must be a non-empty string or None"
        )

    return tuple(
        record
        for record in records
        if (
            model_id is None
            or record.model_id == model_id
        )
        and (
            symbol is None
            or record.symbol == symbol
        )
    )


def _validate_records(
    records: tuple[AlphaLedgerRecord, ...],
) -> None:
    if not isinstance(records, tuple):
        raise TypeError(
            "records must be a tuple"
        )

    if not all(
        isinstance(record, AlphaLedgerRecord)
        for record in records
    ):
        raise TypeError(
            "records must contain only AlphaLedgerRecord objects"
        )


def _validate_threshold(
    value: float,
) -> None:
    if (
        not isinstance(value, Real)
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0.0
        or value > 1.0
    ):
        raise ValueError(
            "neutral_threshold must be a number in [0.0, 1.0]"
        )

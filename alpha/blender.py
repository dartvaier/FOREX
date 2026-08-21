import math
from types import MappingProxyType
from typing import Mapping

from alpha.models import (
    AlphaContribution,
    AlphaSignal,
    BlendedAlphaView,
)


class WeightedAlphaBlender:
    """
    Deterministic weighted-mean blender for AlphaSignal objects.

    Abstained signals are audited but do not dilute active views.
    Neutral active signals, value == 0.0 and abstained == False,
    still contribute to the denominator.
    """

    def __init__(
        self,
        weights: Mapping[str, float],
    ) -> None:
        if not isinstance(weights, Mapping):
            raise TypeError(
                "weights must be a mapping"
            )

        if not weights:
            raise ValueError(
                "weights must not be empty"
            )

        normalized = {}

        for model_id, weight in weights.items():
            if not isinstance(model_id, str) or not model_id.strip():
                raise ValueError(
                    "weight model_id must be a non-empty string"
                )

            if (
                not isinstance(weight, (int, float))
                or isinstance(weight, bool)
                or not math.isfinite(weight)
                or weight <= 0
            ):
                raise ValueError(
                    "weights must be finite positive numbers"
                )

            normalized[model_id] = float(weight)

        self._weights = MappingProxyType(normalized)

    @property
    def weights(
        self,
    ) -> Mapping[str, float]:
        return self._weights

    def blend(
        self,
        signals: tuple[AlphaSignal, ...],
    ) -> BlendedAlphaView:
        if not isinstance(signals, tuple):
            raise TypeError(
                "signals must be a tuple"
            )

        if not signals:
            raise ValueError(
                "signals must not be empty"
            )

        if not all(
            isinstance(signal, AlphaSignal)
            for signal in signals
        ):
            raise TypeError(
                "signals must contain only AlphaSignal objects"
            )

        symbol = signals[0].symbol
        timestamp = signals[0].timestamp
        seen_model_ids = set()

        for signal in signals:
            if signal.symbol != symbol:
                raise ValueError(
                    "all alpha signals must have the same symbol"
                )

            if signal.timestamp != timestamp:
                raise ValueError(
                    "all alpha signals must have the same timestamp"
                )

            if signal.model_id in seen_model_ids:
                raise ValueError(
                    "alpha signals must have unique model_id values"
                )

            if signal.model_id not in self._weights:
                raise ValueError(
                    f"missing weight for model_id: {signal.model_id}"
                )

            seen_model_ids.add(signal.model_id)

        ordered_signals = tuple(
            sorted(
                signals,
                key=lambda signal: signal.model_id,
            )
        )

        abstained_models = tuple(
            signal.model_id
            for signal in ordered_signals
            if signal.abstained
        )

        active_signals = tuple(
            signal
            for signal in ordered_signals
            if not signal.abstained
        )

        if not active_signals:
            return BlendedAlphaView(
                symbol=symbol,
                timestamp=timestamp,
                value=0.0,
                contributors=(),
                abstained_models=abstained_models,
                abstained=True,
                metadata={
                    "method": "weighted_mean",
                    "active_model_count": 0,
                    "total_model_count": len(signals),
                },
            )

        contributors = tuple(
            AlphaContribution(
                model_id=signal.model_id,
                value=signal.value,
                weight=self._weights[signal.model_id],
                confidence=signal.confidence,
            )
            for signal in active_signals
        )

        total_weight = sum(
            contributor.weight
            for contributor in contributors
        )

        blended_value = sum(
            contributor.weight * contributor.value
            for contributor in contributors
        ) / total_weight

        return BlendedAlphaView(
            symbol=symbol,
            timestamp=timestamp,
            value=blended_value,
            contributors=contributors,
            abstained_models=abstained_models,
            abstained=False,
            metadata={
                "method": "weighted_mean",
                "active_model_count": len(active_signals),
                "total_model_count": len(signals),
            },
        )

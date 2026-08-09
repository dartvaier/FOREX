from backtest.models.signal import Signal


class SignalLedger:
    """
    Ordered ledger of Signals produced by Strategy.

    Responsibilities:

    - preserve insertion order;
    - expose immutable Signal snapshots;
    - reject duplicate signal IDs;
    - reject chronological regression.

    Signal processing and strategy logic do not belong here.
    """

    def __init__(self) -> None:
        self._signals: list[Signal] = []
        self._signal_ids: set[str] = set()

    @property
    def signals(self) -> tuple[Signal, ...]:
        return tuple(self._signals)

    @property
    def count(self) -> int:
        return len(self._signals)

    @property
    def is_empty(self) -> bool:
        return not self._signals

    @property
    def last_signal(self) -> Signal | None:
        if not self._signals:
            return None

        return self._signals[-1]

    def append(
        self,
        signal: Signal,
    ) -> None:
        if not isinstance(signal, Signal):
            raise TypeError(
                "signal must be a Signal"
            )

        if signal.signal_id in self._signal_ids:
            raise ValueError(
                "duplicate signal_id"
            )

        if self._signals:
            previous = self._signals[-1]

            if signal.timestamp < previous.timestamp:
                raise ValueError(
                    "Signal timestamp cannot move backward"
                )

        self._signals.append(signal)
        self._signal_ids.add(signal.signal_id)

    def get(
        self,
        signal_id: str,
    ) -> Signal | None:
        if (
            not isinstance(signal_id, str)
            or not signal_id.strip()
        ):
            raise ValueError(
                "signal_id must be a non-empty string"
            )

        for signal in self._signals:
            if signal.signal_id == signal_id:
                return signal

        return None

    def __len__(self) -> int:
        return len(self._signals)

    def __iter__(self):
        return iter(self.signals)
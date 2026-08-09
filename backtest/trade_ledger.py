from backtest.models.trade import Trade


class TradeLedger:
    """
    Ordered ledger of completed Trades.

    Responsibilities:

    - preserve insertion order;
    - expose immutable Trade snapshots;
    - reject duplicate trade IDs;
    - reject more than one Trade for the same Position;
    - reject chronological regression.

    Performance metrics do not belong here.
    """

    def __init__(self) -> None:
        self._trades: list[Trade] = []
        self._trade_ids: set[str] = set()
        self._position_ids: set[str] = set()

    @property
    def trades(self) -> tuple[Trade, ...]:
        return tuple(self._trades)

    @property
    def count(self) -> int:
        return len(self._trades)

    @property
    def is_empty(self) -> bool:
        return not self._trades

    @property
    def last_trade(self) -> Trade | None:
        if not self._trades:
            return None

        return self._trades[-1]

    def append(
        self,
        trade: Trade,
    ) -> None:
        if not isinstance(trade, Trade):
            raise TypeError(
                "trade must be a Trade"
            )

        if trade.trade_id in self._trade_ids:
            raise ValueError(
                "duplicate trade_id"
            )

        if trade.position_id in self._position_ids:
            raise ValueError(
                "Position already has a Trade"
            )

        if self._trades:
            previous = self._trades[-1]

            if trade.exit_time < previous.exit_time:
                raise ValueError(
                    "Trade exit_time cannot move backward"
                )

        self._trades.append(trade)
        self._trade_ids.add(trade.trade_id)
        self._position_ids.add(trade.position_id)

    def get(
        self,
        trade_id: str,
    ) -> Trade | None:
        if (
            not isinstance(trade_id, str)
            or not trade_id.strip()
        ):
            raise ValueError(
                "trade_id must be a non-empty string"
            )

        for trade in self._trades:
            if trade.trade_id == trade_id:
                return trade

        return None

    def __len__(self) -> int:
        return len(self._trades)

    def __iter__(self):
        return iter(self.trades)
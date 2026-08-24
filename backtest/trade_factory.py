from backtest.holding_period import calculate_bars_held
from backtest.models.enums import SimulationPhase
from backtest.models.instrument import InstrumentSpecification
from backtest.models.trade import Trade
from backtest.portfolio import PositionCloseResult


class TradeFactory:
    """
    Builds an immutable Trade ledger record from a completed
    Position lifecycle.

    Spread and slippage stored by Fill / Portfolio are price
    distances. Here they are converted into monetary audit
    values in ACCOUNT currency (USD):

        price_distance
        * contract_size
        * quantity
        * quote_to_account_rate(price)

    Entry-side costs use the causal rate at the entry price;
    exit-side costs use the causal rate at the exit price
    (docs/25 MC-03). For USD-quote pairs the rate is 1.0, so
    historical behavior is preserved.

    They are NOT subtracted again from net_pnl because their
    effect is already embedded in execution prices.
    """

    def __init__(
        self,
        instrument: InstrumentSpecification,
    ) -> None:
        if not isinstance(
            instrument,
            InstrumentSpecification,
        ):
            raise TypeError(
                "instrument must be an "
                "InstrumentSpecification"
            )

        self._instrument = instrument

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._instrument

    def create(
        self,
        close_result: PositionCloseResult,
        *,
        bars_held: int,
    ) -> Trade:
        if not isinstance(
            close_result,
            PositionCloseResult,
        ):
            raise TypeError(
                "close_result must be a PositionCloseResult"
            )

        if (
            not isinstance(bars_held, int)
            or isinstance(bars_held, bool)
            or bars_held < 0
        ):
            raise ValueError(
                "bars_held must be a non-negative integer"
            )

        position = close_result.position

        if position.symbol != self._instrument.symbol:
            raise ValueError(
                "Position symbol does not match instrument"
            )

        strategy_id = position.metadata.get(
            "strategy_id"
        )

        if (
            not isinstance(strategy_id, str)
            or not strategy_id.strip()
        ):
            raise ValueError(
                "Position must contain a valid strategy_id"
            )

        quantity = position.quantity

        entry_rate = self._instrument.quote_to_account_rate(
            position.entry_price
        )

        exit_rate = self._instrument.quote_to_account_rate(
            close_result.exit_price
        )

        spread_cost = self._price_distance_to_money(
            close_result.entry_spread_impact,
            quantity=quantity,
            rate=entry_rate,
        ) + self._price_distance_to_money(
            close_result.exit_spread_impact,
            quantity=quantity,
            rate=exit_rate,
        )

        slippage_cost = self._price_distance_to_money(
            close_result.entry_slippage,
            quantity=quantity,
            rate=entry_rate,
        ) + self._price_distance_to_money(
            close_result.exit_slippage,
            quantity=quantity,
            rate=exit_rate,
        )

        return Trade(
            trade_id=(
                f"TRADE-{position.position_id}"
            ),
            position_id=position.position_id,
            strategy_id=strategy_id,
            symbol=position.symbol,
            side=position.side,
            entry_fill_id=position.entry_fill_id,
            exit_fill_id=close_result.exit_fill_id,
            entry_time=position.entry_time,
            exit_time=close_result.exit_time,
            entry_price=position.entry_price,
            exit_price=close_result.exit_price,
            quantity=quantity,
            gross_pnl=close_result.gross_pnl,
            net_pnl=close_result.net_pnl,
            spread_cost=spread_cost,
            slippage_cost=slippage_cost,
            commission=close_result.commission,
            swap=0.0,
            bars_held=bars_held,
            exit_reason=close_result.exit_reason,
            metadata={
                "entry_order_id": (
                    position.metadata.get(
                        "entry_order_id"
                    )
                ),
                "exit_order_id": (
                    close_result.exit_order_id
                ),
            },
        )

    def create_from_bar_indexes(
        self,
        close_result: PositionCloseResult,
        *,
        entry_bar_index: int,
        exit_bar_index: int,
        exit_phase: SimulationPhase,
    ) -> Trade:
        """
        Build a Trade using observed simulation bar indexes.

        bars_held is derived from the event sequence rather than
        elapsed wall-clock time, so historical gaps do not create
        fictitious bars.
        """

        bars_held = calculate_bars_held(
            entry_bar_index=entry_bar_index,
            exit_bar_index=exit_bar_index,
            exit_phase=exit_phase,
        )

        return self.create(
            close_result,
            bars_held=bars_held,
        )

    def _price_distance_to_money(
        self,
        distance: float,
        *,
        quantity: float,
        rate: float = 1.0,
    ) -> float:
        return (
            distance
            * self._instrument.contract_size
            * quantity
            * rate
        )
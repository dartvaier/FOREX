from __future__ import annotations

import MetaTrader5 as mt5


class MT5Client:

    def __init__(self):
        self.connected = False

    def connect(self) -> None:
        if self.connected:
            return

        if not mt5.initialize():
            raise RuntimeError(
                f"Falha ao conectar ao MetaTrader 5: "
                f"{mt5.last_error()}"
            )

        terminal = mt5.terminal_info()

        if terminal is None or not terminal.connected:
            mt5.shutdown()

            raise RuntimeError(
                "MetaTrader 5 inicializado, "
                "mas terminal não está conectado."
            )

        self.connected = True

    def disconnect(self) -> None:
        if self.connected:
            mt5.shutdown()
            self.connected = False

    def account_info(self):
        self._ensure_connected()

        account = mt5.account_info()

        if account is None:
            raise RuntimeError(
                f"Erro ao consultar conta: {mt5.last_error()}"
            )

        return account

    def symbol_info(self, symbol: str):
        self._ensure_connected()

        info = mt5.symbol_info(symbol)

        if info is None:
            raise ValueError(
                f"Símbolo não encontrado: {symbol}"
            )

        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(
                    f"Não foi possível habilitar {symbol}: "
                    f"{mt5.last_error()}"
                )

            info = mt5.symbol_info(symbol)

        return info

    def current_tick(self, symbol: str):
        self._ensure_connected()

        self.symbol_info(symbol)

        tick = mt5.symbol_info_tick(symbol)

        if tick is None:
            raise RuntimeError(
                f"Erro ao obter tick de {symbol}: "
                f"{mt5.last_error()}"
            )

        return tick

    def current_bar(
        self,
        symbol: str,
        timeframe
    ):
        self._ensure_connected()

        self.symbol_info(symbol)

        rates = mt5.copy_rates_from_pos(
            symbol,
            timeframe,
            0,
            1
        )

        if rates is None or len(rates) == 0:
            raise RuntimeError(
                f"Erro ao obter barra atual de {symbol}: "
                f"{mt5.last_error()}"
            )

        return rates[0]

    def rates(
        self,
        symbol: str,
        timeframe,
        start_pos: int,
        count: int
    ):
        self._ensure_connected()

        self.symbol_info(symbol)

        rates = mt5.copy_rates_from_pos(
            symbol,
            timeframe,
            start_pos,
            count
        )

        if rates is None:
            raise RuntimeError(
                f"Erro ao obter candles de {symbol}: "
                f"{mt5.last_error()}"
            )

        return rates

    def _ensure_connected(self) -> None:
        if not self.connected:
            raise RuntimeError(
                "MT5Client não está conectado."
            )

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        
    def rates_range(
        self,
        symbol: str,
        timeframe,
        date_from,
        date_to
    ):
        self._ensure_connected()
        self.symbol_info(symbol)

        if date_from.tzinfo is None:
            raise ValueError(
                "date_from precisa possuir timezone."
            )

        if date_to.tzinfo is None:
            raise ValueError(
                "date_to precisa possuir timezone."
            )

        if date_from >= date_to:
            raise ValueError(
                "date_from precisa ser anterior a date_to."
            )

        timestamp_from = int(date_from.timestamp())
        timestamp_to = int(date_to.timestamp())

        rates = mt5.copy_rates_range(
            symbol,
            timeframe,
            timestamp_from,
            timestamp_to
        )

        if rates is None:
            raise RuntimeError(
                f"Erro ao obter histórico de {symbol}: "
                f"{mt5.last_error()}"
            )

        return rates

    def ticks_range(
        self,
        symbol: str,
        date_from,
        date_to,
        flags,
    ):
        """Return broker ticks for a timezone-aware half-open request window."""

        self._ensure_connected()
        self.symbol_info(symbol)

        if date_from.tzinfo is None:
            raise ValueError("date_from precisa possuir timezone.")
        if date_to.tzinfo is None:
            raise ValueError("date_to precisa possuir timezone.")
        if date_from >= date_to:
            raise ValueError("date_from precisa ser anterior a date_to.")

        ticks = mt5.copy_ticks_range(
            symbol,
            int(date_from.timestamp()),
            int(date_to.timestamp()),
            flags,
        )
        if ticks is None:
            raise RuntimeError(
                f"Erro ao obter ticks de {symbol}: {mt5.last_error()}"
            )
        return ticks

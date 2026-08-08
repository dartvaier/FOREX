from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5
import pandas as pd


SYMBOL = "EURUSD"


def main():
    print("=" * 70)
    print("FOREX BOT - VALIDACAO DE MARKET DATA")
    print("=" * 70)

    if not mt5.initialize():
        print("[ERRO] Falha ao inicializar MT5:", mt5.last_error())
        return

    try:
        symbol = mt5.symbol_info(SYMBOL)

        if symbol is None:
            print(f"[ERRO] {SYMBOL} não encontrado.")
            return

        # =====================================================
        # INFORMAÇÕES DO SÍMBOLO
        # =====================================================

        point = symbol.point

        # Para a maioria dos pares de Forex:
        # 5 digits -> 1 pip = 10 points
        # 3 digits -> 1 pip = 10 points
        pip_size = point * 10 if symbol.digits in (3, 5) else point

        print("\n--- SYMBOL SPEC ---")
        print("Symbol:", SYMBOL)
        print("Digits:", symbol.digits)
        print("Point:", point)
        print("Pip size:", pip_size)
        print("Contract size:", symbol.trade_contract_size)
        print("Min volume:", symbol.volume_min)
        print("Max volume:", symbol.volume_max)
        print("Volume step:", symbol.volume_step)

        # =====================================================
        # ÚLTIMO TICK
        # =====================================================

        tick = mt5.symbol_info_tick(SYMBOL)

        if tick is None:
            print("[ERRO] Tick indisponível.")
            return

        tick_time = datetime.fromtimestamp(
            tick.time,
            tz=timezone.utc
        )

        spread_price = tick.ask - tick.bid
        spread_points = spread_price / point
        spread_pips = spread_price / pip_size

        print("\n--- ULTIMO TICK ---")
        print("Timestamp UTC:", tick_time)
        print("Bid:", tick.bid)
        print("Ask:", tick.ask)
        print("Spread price:", spread_price)
        print("Spread points:", round(spread_points, 2))
        print("Spread pips:", round(spread_pips, 3))

        # =====================================================
        # CANDLES
        # =====================================================

        rates = mt5.copy_rates_from_pos(
            SYMBOL,
            mt5.TIMEFRAME_M15,
            0,
            10
        )

        if rates is None:
            print("[ERRO] Candles indisponíveis:", mt5.last_error())
            return

        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s",
            utc=True
        )

        print("\n--- ULTIMAS 10 BARRAS ---")

        print(
            df[
                [
                    "time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "tick_volume",
                    "spread",
                ]
            ].to_string(index=False)
        )

        # =====================================================
        # IDENTIFICAR BAR 0 E BAR 1
        # =====================================================

        print("\n--- BAR POSITION ---")

        print("Barra mais recente:")
        print(df.iloc[-1][["time", "open", "close"]])

        print("\nBarra anterior:")
        print(df.iloc[-2][["time", "open", "close"]])

        # =====================================================
        # TICKS HISTÓRICOS
        # =====================================================

        utc_to = datetime.now(timezone.utc)
        utc_from = utc_to - timedelta(hours=6)

        ticks = mt5.copy_ticks_range(
            SYMBOL,
            utc_from,
            utc_to,
            mt5.COPY_TICKS_ALL
        )

        if ticks is None:
            print(
                "\n[ERRO] Não foi possível recuperar ticks:",
                mt5.last_error()
            )

        elif len(ticks) == 0:
            print("\n[AVISO] Nenhum tick encontrado nas últimas 6 horas.")

        else:
            ticks_df = pd.DataFrame(ticks)

            ticks_df["time"] = pd.to_datetime(
                ticks_df["time_msc"],
                unit="ms",
                utc=True
            )

            ticks_df["spread_price"] = (
                ticks_df["ask"] - ticks_df["bid"]
            )

            ticks_df["spread_points"] = (
                ticks_df["spread_price"] / point
            )

            ticks_df["spread_pips"] = (
                ticks_df["spread_price"] / pip_size
            )

            print("\n--- ULTIMOS 10 TICKS ---")

            print(
                ticks_df[
                    [
                        "time",
                        "bid",
                        "ask",
                        "spread_points",
                        "spread_pips",
                    ]
                ]
                .tail(10)
                .to_string(index=False)
            )

            print("\n--- SPREAD NOS TICKS ---")

            print(
                ticks_df["spread_pips"]
                .describe()
            )

        # =====================================================
        # RESULTADO
        # =====================================================

        print("\n" + "=" * 70)
        print("[SUCESSO] MARKET DATA VALIDADO.")
        print("Nenhuma ordem foi enviada.")
        print("=" * 70)

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
import MetaTrader5 as mt5
import pandas as pd


SYMBOL = "EURUSD"


def main():
    print("=" * 60)
    print("FOREX BOT - TESTE DE CONEXAO MT5")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Inicializar conexão com o terminal
    # ---------------------------------------------------------
    if not mt5.initialize():
        print("\n[ERRO] Não foi possível conectar ao MetaTrader 5.")
        print("Detalhes:", mt5.last_error())
        return

    print("\n[OK] Conexão com MetaTrader 5 estabelecida.")
    print(f"[INFO] Pacote MetaTrader5: {mt5.__version__}")

    try:
        # -----------------------------------------------------
        # 2. Informações do terminal
        # -----------------------------------------------------
        terminal = mt5.terminal_info()

        if terminal is None:
            print("[ERRO] Não foi possível obter informações do terminal.")
            print(mt5.last_error())
            return

        print("\n--- TERMINAL ---")
        print("Nome:", terminal.name)
        print("Empresa:", terminal.company)
        print("Conectado:", terminal.connected)

        # -----------------------------------------------------
        # 3. Informações da conta
        # -----------------------------------------------------
        account = mt5.account_info()

        if account is None:
            print("[ERRO] Não foi possível obter informações da conta.")
            print(mt5.last_error())
            return

        print("\n--- CONTA ---")
        print("Login:", account.login)
        print("Servidor:", account.server)
        print("Moeda:", account.currency)
        print("Saldo:", account.balance)
        print("Equity:", account.equity)
        print("Alavancagem:", account.leverage)

        # -----------------------------------------------------
        # 4. Verificar EURUSD
        # -----------------------------------------------------
        symbol = mt5.symbol_info(SYMBOL)

        if symbol is None:
            print(f"\n[ERRO] Símbolo {SYMBOL} não encontrado.")
            return

        if not symbol.visible:
            print(f"\n[INFO] {SYMBOL} não está visível. Tentando habilitar...")

            if not mt5.symbol_select(SYMBOL, True):
                print(f"[ERRO] Não foi possível habilitar {SYMBOL}.")
                print(mt5.last_error())
                return

        print("\n--- SIMBOLO ---")
        print("Símbolo:", SYMBOL)
        print("Digits:", symbol.digits)
        print("Point:", symbol.point)
        print("Volume mínimo:", symbol.volume_min)
        print("Volume máximo:", symbol.volume_max)
        print("Volume step:", symbol.volume_step)
        print("Contract size:", symbol.trade_contract_size)

        # -----------------------------------------------------
        # 5. Bid / Ask
        # -----------------------------------------------------
        tick = mt5.symbol_info_tick(SYMBOL)

        if tick is None:
            print("[ERRO] Não foi possível obter o último tick.")
            print(mt5.last_error())
            return

        spread_price = tick.ask - tick.bid
        spread_points = spread_price / symbol.point

        print("\n--- TICK ATUAL ---")
        print("Bid:", tick.bid)
        print("Ask:", tick.ask)
        print("Spread em preço:", spread_price)
        print("Spread em points:", spread_points)

        # -----------------------------------------------------
        # 6. Buscar candles
        # -----------------------------------------------------
        rates = mt5.copy_rates_from_pos(
            SYMBOL,
            mt5.TIMEFRAME_M15,
            0,
            10
        )

        if rates is None:
            print("[ERRO] Não foi possível obter candles.")
            print(mt5.last_error())
            return

        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s",
            utc=True
        )

        print("\n--- ÚLTIMOS 10 CANDLES M15 ---")
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

        print("\n" + "=" * 60)
        print("[SUCESSO] Teste concluído.")
        print("Nenhuma ordem foi enviada.")
        print("=" * 60)

    finally:
        mt5.shutdown()
        print("\n[INFO] Conexão com MT5 encerrada.")


if __name__ == "__main__":
    main()
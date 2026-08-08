import MetaTrader5 as mt5

from broker.mt5_client import MT5Client
from data.market_data import MarketData


SYMBOL = "EURUSD"


def main():

    with MT5Client() as client:

        market = MarketData(client)

        quote = market.get_current_quote(SYMBOL)

        print("\n--- QUOTE ---")

        for key, value in quote.items():
            print(f"{key}: {value}")

        bars = market.get_closed_bars(
            symbol=SYMBOL,
            timeframe=mt5.TIMEFRAME_M15,
            count=10
        )

        print("\n--- CLOSED BARS ---")
        print(bars.to_string(index=False))


if __name__ == "__main__":
    main()
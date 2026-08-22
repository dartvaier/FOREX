from backtest.models import InstrumentSpecification


EURUSD_INSTRUMENT = {
    "symbol": "EURUSD",
    "digits": 5,
    "point": 0.00001,
    "pip_size": 0.00010,
    "contract_size": 100000,
    "volume_min": 0.01,
    "volume_max": 500.0,
    "volume_step": 0.01,
    "tick_size": 0.00001,
    "tick_value": 1.0,
}


INSTRUMENT_REGISTRY = {
    "EURUSD": {
        "symbol": "EURUSD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "USD",
        "quote_currency": "USD",
    },
    "GBPUSD": {
        "symbol": "GBPUSD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "GBP",
        "quote_currency": "USD",
    },
    "USDJPY": {
        "symbol": "USDJPY",
        "digits": 3,
        "point": 0.001,
        "pip_size": 0.01,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.001,
        "tick_value": 100.0,
        "base_currency": "USD",
        "quote_currency": "JPY",
    },
    "USDCHF": {
        "symbol": "USDCHF",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "USD",
        "quote_currency": "CHF",
    },
    "AUDUSD": {
        "symbol": "AUDUSD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "AUD",
        "quote_currency": "USD",
    },
    "USDCAD": {
        "symbol": "USDCAD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "USD",
        "quote_currency": "CAD",
    },
    "NZDUSD": {
        "symbol": "NZDUSD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "NZD",
        "quote_currency": "USD",
    },
}


MAJOR_SYMBOLS = tuple(INSTRUMENT_REGISTRY)


def instrument_specification(
    symbol: str,
) -> InstrumentSpecification:
    if symbol not in INSTRUMENT_REGISTRY:
        raise KeyError(symbol)

    return InstrumentSpecification(
        **INSTRUMENT_REGISTRY[symbol]
    )

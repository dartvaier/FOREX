from collect_broker_data import BROKER_PROFILES, FP_MARKETS_RAW_H17_SYMBOLS


def test_fpmarkets_raw_h17_profile_has_one_pair_for_each_non_usd_currency():
    assert BROKER_PROFILES["fpmarkets_raw_h17"] == FP_MARKETS_RAW_H17_SYMBOLS
    assert len(FP_MARKETS_RAW_H17_SYMBOLS) == 19
    assert len(set(FP_MARKETS_RAW_H17_SYMBOLS)) == 19
    assert all(symbol.endswith(".r") for symbol in FP_MARKETS_RAW_H17_SYMBOLS)
    assert "EURUSD.r" in FP_MARKETS_RAW_H17_SYMBOLS
    assert "USDBRL.r" in FP_MARKETS_RAW_H17_SYMBOLS

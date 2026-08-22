import json
from pathlib import Path

import pytest

from research.multi_symbol import (
    DEFAULT_CONFIG_PATH,
    assert_datasets_available,
    available_symbols,
    cost_modes,
    dataset_preflight_message,
    extract_summary_row,
    missing_dataset_paths,
    parse_symbols,
    run_multi_symbol,
    summary_stem,
    symbol_tag,
    write_summary_files,
)


BASE_COSTS = {
    "spread_pips": 2.0,
    "slippage_pips": 0.5,
    "commission_per_lot_per_side": 3.50,
}


def minimal_report(
    *,
    symbol: str,
    cost: str,
    tag: str,
    net_profit: float = -12.345,
) -> dict:
    return {
        "config": {
            "symbol": symbol,
            "strategy_id": "DECLARATIVE",
            "timeframe": "M15",
            "cost_model": cost,
            "cost_multiplier": 1.0,
            "tag": tag,
            "date_from": "2015-01-01T00:00:00+00:00",
            "date_to": "2021-01-01T00:00:00+00:00",
        },
        "performance": {
            "trades": 10,
            "net_profit": net_profit,
            "total_return_pct": -0.123456,
            "max_drawdown_pct": 1.23456,
            "win_rate": 45.678,
            "profit_factor": 0.987654321,
            "expectancy": -1.23456,
        },
        "cost_analysis": {
            "round_trip_cost_pips": 3.7000001,
        },
    }


def test_parse_symbols_from_raw_csv():
    assert parse_symbols("eurusd, USDJPY") == (
        "EURUSD",
        "USDJPY",
    )


def test_parse_symbols_from_declarative_config():
    symbols = parse_symbols(
        None,
        config_path=DEFAULT_CONFIG_PATH,
    )

    assert symbols == (
        "AUDUSD",
        "EURUSD",
        "GBPUSD",
        "NZDUSD",
        "USDCAD",
        "USDCHF",
        "USDJPY",
    )


def test_parse_symbols_rejects_duplicates_and_unknowns():
    with pytest.raises(ValueError, match="duplicates"):
        parse_symbols("EURUSD,EURUSD")

    with pytest.raises(ValueError, match="unknown symbols"):
        parse_symbols("EURGBP")


def test_cost_modes():
    assert cost_modes("zero") == ("zero",)
    assert cost_modes("explicit") == ("explicit",)
    assert cost_modes("both") == ("zero", "explicit")

    with pytest.raises(ValueError, match="cost"):
        cost_modes("bad")


def test_symbol_tag_adds_symbol_suffix():
    assert symbol_tag(None, "EURUSD") == "eurusd"
    assert symbol_tag("dev", "USDJPY") == "dev-usdjpy"


def test_dataset_preflight_reports_missing_datasets(monkeypatch, tmp_path):
    def fake_dataset_path(symbol, timeframe):
        return tmp_path / symbol / f"{timeframe}.parquet"

    monkeypatch.setattr(
        "research.multi_symbol.dataset_path",
        fake_dataset_path,
    )

    missing = missing_dataset_paths(
        ("EURUSD", "USDJPY"),
        timeframe="M15",
    )

    assert set(missing) == {"EURUSD", "USDJPY"}
    assert "collect_history.py --symbol <SYMBOL>" in (
        dataset_preflight_message(missing)
    )

    with pytest.raises(FileNotFoundError, match="missing datasets"):
        assert_datasets_available(
            ("EURUSD", "USDJPY"),
            timeframe="M15",
        )


def test_available_symbols_filters_missing_datasets(
    monkeypatch,
    tmp_path,
):
    available = tmp_path / "EURUSD" / "M15.parquet"
    available.parent.mkdir(
        parents=True,
    )
    available.write_text(
        "placeholder",
        encoding="utf-8",
    )

    def fake_dataset_path(symbol, timeframe):
        return tmp_path / symbol / f"{timeframe}.parquet"

    monkeypatch.setattr(
        "research.multi_symbol.dataset_path",
        fake_dataset_path,
    )

    assert available_symbols(
        ("EURUSD", "USDJPY"),
        timeframe="M15",
    ) == ("EURUSD",)


def test_extract_summary_row_rounds_values(tmp_path):
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps(
            minimal_report(
                symbol="EURUSD",
                cost="explicit",
                tag="dev-eurusd",
            )
        ),
        encoding="utf-8",
    )

    row = extract_summary_row(path)

    assert row["symbol"] == "EURUSD"
    assert row["net_profit"] == -12.35
    assert row["return_pct"] == -0.1235
    assert row["profit_factor"] == 0.987654
    assert row["round_trip_cost_pips"] == 3.7
    assert row["report_path"] == str(path)


def test_write_summary_files_writes_json_and_csv(tmp_path):
    rows = [
        {
            "symbol": "EURUSD",
            "strategy": "DECLARATIVE",
            "tf": "M15",
            "cost": "explicit",
            "cost_multiplier": 1.0,
            "tag": "dev-eurusd",
            "from": "2015-01-01",
            "to": "2021-01-01",
            "trades": 10,
            "net_profit": -1.0,
            "return_pct": -0.01,
            "max_dd_pct": 0.1,
            "win_rate": 40.0,
            "profit_factor": 0.9,
            "expectancy": -0.1,
            "round_trip_cost_pips": 3.7,
            "report_path": "report.json",
        }
    ]

    json_path, csv_path = write_summary_files(
        rows,
        out_dir=tmp_path,
        stem="summary",
    )

    payload = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "multi-symbol-summary/0.1.0"
    assert payload["rows"] == rows
    assert csv_path.read_text(encoding="utf-8").startswith(
        "symbol,strategy,tf"
    )


def test_run_multi_symbol_calls_runner_for_each_symbol_and_mode(
    monkeypatch,
    tmp_path,
):
    for symbol in ("EURUSD", "USDJPY"):
        path = tmp_path / "data" / symbol / "M15.parquet"
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            "placeholder",
            encoding="utf-8",
        )

    def fake_dataset_path(symbol, timeframe):
        return tmp_path / "data" / symbol / f"{timeframe}.parquet"

    monkeypatch.setattr(
        "research.multi_symbol.dataset_path",
        fake_dataset_path,
    )

    calls = []

    def fake_run_single(**kwargs) -> Path:
        calls.append(kwargs)
        path = (
            tmp_path
            / f"{kwargs['symbol']}_{kwargs['cost_mode']}.json"
        )
        path.write_text(
            json.dumps(
                minimal_report(
                    symbol=kwargs["symbol"],
                    cost=kwargs["cost_mode"],
                    tag=kwargs["tag"],
                    net_profit=-1.0
                    if kwargs["symbol"] == "EURUSD"
                    else -2.0,
                )
            ),
            encoding="utf-8",
        )
        return path

    rows = run_multi_symbol(
        symbols=("EURUSD", "USDJPY"),
        strategy_key="declarative_ensemble",
        strategy_params={
            "config_path": DEFAULT_CONFIG_PATH,
        },
        timeframe="M15",
        date_from="2015-01-01",
        date_to="2021-01-01",
        initial_capital=10000.0,
        fixed_quantity=0.01,
        cost="both",
        cost_params=BASE_COSTS,
        cost_multiplier=1.0,
        out_dir=tmp_path,
        tag="dev",
        write_equity=False,
        run_single_fn=fake_run_single,
    )

    assert [
        (
            call["symbol"],
            call["cost_mode"],
            call["tag"],
        )
        for call in calls
    ] == [
        ("EURUSD", "zero", "dev-eurusd"),
        ("EURUSD", "explicit", "dev-eurusd"),
        ("USDJPY", "zero", "dev-usdjpy"),
        ("USDJPY", "explicit", "dev-usdjpy"),
    ]
    assert len(rows) == 4
    assert {
        row["symbol"]
        for row in rows
    } == {"EURUSD", "USDJPY"}


def test_run_multi_symbol_skip_missing_runs_available_symbol(
    monkeypatch,
    tmp_path,
):
    available = tmp_path / "data" / "EURUSD" / "M15.parquet"
    available.parent.mkdir(
        parents=True,
    )
    available.write_text(
        "placeholder",
        encoding="utf-8",
    )

    def fake_dataset_path(symbol, timeframe):
        return tmp_path / "data" / symbol / f"{timeframe}.parquet"

    monkeypatch.setattr(
        "research.multi_symbol.dataset_path",
        fake_dataset_path,
    )

    calls = []

    def fake_run_single(**kwargs) -> Path:
        calls.append(kwargs["symbol"])
        path = tmp_path / f"{kwargs['symbol']}.json"
        path.write_text(
            json.dumps(
                minimal_report(
                    symbol=kwargs["symbol"],
                    cost=kwargs["cost_mode"],
                    tag=kwargs["tag"],
                )
            ),
            encoding="utf-8",
        )
        return path

    rows = run_multi_symbol(
        symbols=("EURUSD", "USDJPY"),
        strategy_key="declarative_ensemble",
        strategy_params={
            "config_path": DEFAULT_CONFIG_PATH,
        },
        timeframe="M15",
        date_from=None,
        date_to=None,
        initial_capital=10000.0,
        fixed_quantity=0.01,
        cost="explicit",
        cost_params=BASE_COSTS,
        cost_multiplier=1.0,
        out_dir=tmp_path,
        tag=None,
        write_equity=False,
        skip_missing=True,
        run_single_fn=fake_run_single,
    )

    assert calls == ["EURUSD"]
    assert [
        row["symbol"]
        for row in rows
    ] == ["EURUSD"]


def test_summary_stem_includes_optional_tag():
    assert summary_stem(
        strategy_key="declarative_ensemble",
        timeframe="M15",
        cost="explicit",
        tag=None,
    ) == "multi_symbol_declarative_ensemble_M15_explicit"
    assert summary_stem(
        strategy_key="declarative_ensemble",
        timeframe="M15",
        cost="explicit",
        tag="dev",
    ) == "multi_symbol_declarative_ensemble_M15_explicit_dev"

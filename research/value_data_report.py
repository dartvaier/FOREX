"""Coverage and consistency report for the public currency-value snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.value_data import (
    VALUE_UNIVERSE,
    derive_price_level,
    lag_monthly_panel,
    load_value_snapshot,
)


MONTHLY_FROM = pd.Timestamp("1994-01-01", tz="UTC")
MONTHLY_TO = pd.Timestamp("2026-01-01", tz="UTC")
ANNUAL_FROM = pd.Timestamp("1994-01-01", tz="UTC")
ANNUAL_TO = pd.Timestamp("2026-01-01", tz="UTC")


def _window(panel: pd.DataFrame, date_from: pd.Timestamp, date_to: pd.Timestamp) -> pd.DataFrame:
    return panel.loc[(panel.index >= date_from) & (panel.index < date_to)].copy()


def _coverage(
    panel: pd.DataFrame,
    *,
    date_from: pd.Timestamp,
    date_to: pd.Timestamp,
    frequency: str,
) -> dict:
    expected_index = pd.date_range(date_from, date_to, freq=frequency, inclusive="left")
    window = _window(panel, date_from, date_to).reindex(expected_index)
    return {
        currency: {
            "observations": int(window[currency].notna().sum()),
            "missing": int(window[currency].isna().sum()),
            "date_from": str(window[currency].first_valid_index()),
            "date_to": str(window[currency].last_valid_index()),
        }
        for currency in VALUE_UNIVERSE
    }


def build_value_data_report(manifest_path: Path) -> tuple[dict, pd.DataFrame]:
    panels = load_value_snapshot(manifest_path)
    reer = panels["bis_reer_monthly"]
    usd_rates = panels["bis_usd_monthly"]
    wb_ppp = panels["world_bank_ppp_annual"]
    wb_fx = panels["world_bank_exchange_rate_annual"]
    oecd_ppp = panels["oecd_ppp_annual"]
    causal_reer = lag_monthly_panel(reer, lag_months=2)
    wb_price_level = derive_price_level(wb_ppp, wb_fx)

    coverage = {
        "bis_reer_monthly": _coverage(
            reer, date_from=MONTHLY_FROM, date_to=MONTHLY_TO, frequency="MS"
        ),
        "bis_usd_monthly": _coverage(
            usd_rates, date_from=MONTHLY_FROM, date_to=MONTHLY_TO, frequency="MS"
        ),
        "world_bank_ppp_annual": _coverage(
            wb_ppp, date_from=ANNUAL_FROM, date_to=ANNUAL_TO, frequency="YS"
        ),
        "world_bank_exchange_rate_annual": _coverage(
            wb_fx, date_from=ANNUAL_FROM, date_to=ANNUAL_TO, frequency="YS"
        ),
        "oecd_ppp_annual": _coverage(
            oecd_ppp, date_from=ANNUAL_FROM, date_to=ANNUAL_TO, frequency="YS"
        ),
    }

    common = wb_ppp.index.intersection(oecd_ppp.index)
    wb_common = wb_ppp.loc[common]
    oecd_common = oecd_ppp.loc[common]
    valid = wb_common.notna() & oecd_common.notna() & (oecd_common != 0)
    relative_difference = ((wb_common - oecd_common).abs() / oecd_common.abs()).where(valid)
    differences = relative_difference.stack().astype(float)

    rows = []
    for currency in VALUE_UNIVERSE:
        row = {"currency": currency}
        for dataset, values in coverage.items():
            row[f"{dataset}_observations"] = values[currency]["observations"]
            row[f"{dataset}_missing"] = values[currency]["missing"]
            row[f"{dataset}_date_from"] = values[currency]["date_from"]
            row[f"{dataset}_date_to"] = values[currency]["date_to"]
        row["wb_price_level_observations"] = int(
            wb_price_level[currency].notna().sum()
        )
        rows.append(row)
    coverage_frame = pd.DataFrame(rows)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {
        "snapshot_manifest": str(manifest_path),
        "retrieved_at": manifest["retrieved_at"],
        "universe_size": len(VALUE_UNIVERSE),
        "universe": list(VALUE_UNIVERSE),
        "point_in_time": False,
        "monthly_window": {
            "date_from": str(MONTHLY_FROM),
            "date_to_exclusive": str(MONTHLY_TO),
            "expected_months": int(len(pd.date_range(MONTHLY_FROM, periods=384, freq="MS"))),
        },
        "annual_window": {
            "date_from": str(ANNUAL_FROM),
            "date_to_exclusive": str(ANNUAL_TO),
            "expected_years": 32,
        },
        "complete_currencies": {
            dataset: [
                currency
                for currency, values in dataset_coverage.items()
                if values["missing"] == 0
            ]
            for dataset, dataset_coverage in coverage.items()
        },
        "bis_reer_causal": {
            "lag_months": 2,
            "rows": int(len(causal_reer)),
            "date_from": str(causal_reer.index.min()),
            "date_to": str(causal_reer.index.max()),
            "missing_values": int(causal_reer.isna().sum().sum()),
        },
        "world_bank_price_level": {
            "formula": "PA.NUS.PPP / PA.NUS.FCRF",
            "observations": int(wb_price_level.notna().sum().sum()),
            "currencies_present": [
                currency
                for currency in VALUE_UNIVERSE
                if wb_price_level[currency].notna().any()
            ],
        },
        "world_bank_vs_oecd_ppp": {
            "overlapping_observations": int(len(differences)),
            "median_absolute_relative_difference": (
                float(differences.median()) if len(differences) else None
            ),
            "p95_absolute_relative_difference": (
                float(differences.quantile(0.95)) if len(differences) else None
            ),
            "max_absolute_relative_difference": (
                float(differences.max()) if len(differences) else None
            ),
        },
        "ready_for_factor_specification": bool(
            len(report_complete := [
                currency
                for currency, values in coverage["bis_reer_monthly"].items()
                if values["missing"] == 0
            ])
            >= 12
        ),
        "complete_reer_currency_count": len(report_complete),
        "limitations": [
            "current snapshots are revised data, not point-in-time vintages",
            "BIS USD rates are reference averages without bid/ask",
            "annual PPP publication availability is not assigned",
            "macro coverage does not prove instrument tradability",
        ],
    }
    return report, coverage_frame


def render_markdown(report: dict, coverage: pd.DataFrame) -> str:
    complete = report["complete_currencies"]
    agreement = report["world_bank_vs_oecd_ppp"]
    lines = [
        "# H17 — Relatório de Cobertura dos Dados Públicos de Value",
        "",
        "## Conclusão",
        "",
        (
            f"A coleta pública é suficiente para especificar uma hipótese de value: "
            f"{report['complete_reer_currency_count']}/{report['universe_size']} moedas "
            "têm REER mensal completo entre 1994 e 2025. Ainda não é suficiente "
            "para afirmar tradabilidade ou retorno líquido, pois Bid/Ask, forwards e "
            "swaps históricos não estão nestas fontes."
        ),
        "",
        "## Cobertura por fonte",
        "",
        "| Fonte | Moedas completas na janela | Total |",
        "|---|---:|---:|",
    ]
    for dataset in (
        "bis_reer_monthly",
        "bis_usd_monthly",
        "world_bank_ppp_annual",
        "world_bank_exchange_rate_annual",
        "oecd_ppp_annual",
    ):
        lines.append(
            f"| {dataset} | {len(complete[dataset])} | {report['universe_size']} |"
        )
    lines.extend(
        [
            "",
            "## Consistência PPP",
            "",
            (
                f"World Bank e OECD têm {agreement['overlapping_observations']} "
                "observações sobrepostas. A diferença relativa absoluta mediana é "
                f"{agreement['median_absolute_relative_difference']:.2%} e o percentil "
                f"95 é {agreement['p95_absolute_relative_difference']:.4%}; a maior "
                f"diferença observada é {agreement['max_absolute_relative_difference']:.2%}."
            ),
            "",
            "Diferenças não serão reconciliadas por média ou preenchimento. A futura "
            "especificação deverá escolher uma fonte primária antes de ver retornos.",
            "",
            "## Disponibilidade causal",
            "",
            (
                "O painel REER causal contém as mesmas observações, deslocadas dois "
                "meses para a frente. Nenhuma linha intermediária é criada e nenhuma "
                "ausência é preenchida. PPP anual permanece sem `available_at` porque "
                "os snapshots atuais não são vintages históricos."
            ),
            "",
            "## Cobertura por moeda",
            "",
            "| Moeda | REER meses | Spot ref. meses | OECD PPP anos | WB PPP anos |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in coverage.to_dict(orient="records"):
        lines.append(
            f"| {row['currency']} | {row['bis_reer_monthly_observations']} | "
            f"{row['bis_usd_monthly_observations']} | "
            f"{row['oecd_ppp_annual_observations']} | "
            f"{row['world_bank_ppp_annual_observations']} |"
        )
    lines.extend(
        [
            "",
            "## Limitações",
            "",
            "- Os snapshots atuais são dados revisados, não vintages point-in-time.",
            "- As taxas BIS são médias de referência, sem Bid/Ask.",
            "- PPP anual ainda não possui uma data histórica de publicação atribuída.",
            "- Cobertura macroeconômica não comprova que o instrumento era negociável.",
            "",
            "Este relatório avalia dados, não gera sinal ou recomendação de trade.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/external/value/public_snapshot/manifest.json"),
    )
    parser.add_argument("--out-dir", type=Path, default=Path("research/reports"))
    args = parser.parse_args()
    report, coverage = build_value_data_report(args.manifest)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "h17_value_data_coverage.json"
    csv_path = args.out_dir / "h17_value_data_coverage.csv"
    md_path = args.out_dir / "h17_value_data_coverage.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    coverage.to_csv(csv_path, index=False)
    md_path.write_text(render_markdown(report, coverage), encoding="utf-8")
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

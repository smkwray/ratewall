from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

from ratewall.databook.holder_scenario_results import (
    HOLDER_SCENARIO_RESULT_FIELDS,
    holder_scenario_readout_markdown,
    holder_scenario_result_rows_from_directory,
    write_holder_scenario_outputs,
)


def test_holder_scenario_rows_capture_tdc_mechanism_and_fixed_denominator(
    tmp_path: Path,
) -> None:
    _write_suite(tmp_path)

    rows = holder_scenario_result_rows_from_directory(tmp_path)

    assert len(rows) == 3
    assert {field for row in rows for field in row} == set(
        HOLDER_SCENARIO_RESULT_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    reserve = by_scenario["tdcsim_holder_source_reserve_user_absorption_v1"]
    assert reserve["scenario_label"] == "Banks+Foreign absorb more from Private"
    assert reserve["delta_ratewall_ratio_vs_baseline"] == "0.28"
    assert reserve["delta_tdc_current_demand_support_bil"] == "45"
    assert reserve["denominator_change_allowed"] == "false_no_rate_change"
    assert reserve["new_issuance_preference_banks_share"] == "0.2"
    assert reserve["new_issuance_preference_foreign_share"] == "0.5"
    assert reserve["new_issuance_preference_private_share"] == "0.3"
    assert reserve["new_issuance_preference_banks_plus_foreign_share"] == "0.7"
    assert reserve["final_stock_date"] == "2027-09-30"
    assert reserve["final_total_stock_banks_plus_foreign_share"] == "0.7"
    assert reserve["mmf_deposit_pass_through"] == "0.97"
    assert reserve["canonical_ratio_entry"] == "false"


def test_holder_scenario_outputs_write_csv_png_and_readout(tmp_path: Path) -> None:
    _write_suite(tmp_path)
    rows = holder_scenario_result_rows_from_directory(tmp_path)

    outputs = write_holder_scenario_outputs(tmp_path / "out", rows=rows)

    assert outputs["csv"].read_text(encoding="utf-8").startswith(
        "holder_scenario_result_row_id,"
    )
    readout = holder_scenario_readout_markdown(rows)
    assert outputs["readout_md"].read_text(encoding="utf-8") == readout
    assert "The RateWall movement comes through TDCSim's TDC cashflow channel" in readout
    for key in ("png_delta_rw", "png_tdc_components", "png_holder_shares"):
        assert outputs[key].read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def _write_suite(root: Path) -> None:
    _write_csv(
        root / "ratewall_tdcsim_cbo_scenario_effect.csv",
        [
            _effect_row("cbo_baseline_noop_v1", "0.22", "0", "0", "0"),
            _effect_row(
                "tdcsim_holder_source_current_mix_v1",
                "0.31",
                "0.09",
                "14",
                "11",
            ),
            _effect_row(
                "tdcsim_holder_source_reserve_user_absorption_v1",
                "0.50",
                "0.28",
                "45",
                "36",
            ),
            _effect_row(
                "tdcsim_holder_source_domestic_nonbank_absorption_v1",
                "0.30",
                "0.08",
                "13",
                "10",
            ),
        ],
    )
    _write_csv(
        root / "ratewall_tdcsim_cbo_fiscal_year_ratio_input.csv",
        [
            _ratio_row("cbo_baseline_noop_v1"),
            _ratio_row("tdcsim_holder_source_current_mix_v1"),
            _ratio_row("tdcsim_holder_source_reserve_user_absorption_v1"),
            _ratio_row("tdcsim_holder_source_domestic_nonbank_absorption_v1"),
        ],
    )
    scenarios = root / "scenarios"
    scenarios.mkdir()
    _write_scenario(
        scenarios / "current.json",
        "tdcsim_holder_source_current_mix_v1",
        "Source-backed current holder mix",
        {"Banks": 0.1, "Foreign": 0.4, "Private": 0.5},
    )
    _write_scenario(
        scenarios / "reserve.json",
        "tdcsim_holder_source_reserve_user_absorption_v1",
        "Source-backed reserve-user absorption holder mix",
        {"Banks": 0.2, "Foreign": 0.5, "Private": 0.3},
    )
    _write_scenario(
        scenarios / "private.json",
        "tdcsim_holder_source_domestic_nonbank_absorption_v1",
        "Source-backed domestic-nonbank absorption holder mix",
        {"Banks": 0.15, "Foreign": 0.35, "Private": 0.5},
    )
    _write_holder_stocks(
        root,
        "26_current",
        "tdcsim_holder_source_current_mix_v1",
        {"Banks": 10, "Foreign": 40, "Private": 45, "CB": 5},
    )
    _write_holder_stocks(
        root,
        "27_reserve",
        "tdcsim_holder_source_reserve_user_absorption_v1",
        {"Banks": 20, "Foreign": 50, "Private": 25, "CB": 5},
    )
    _write_holder_stocks(
        root,
        "28_private",
        "tdcsim_holder_source_domestic_nonbank_absorption_v1",
        {"Banks": 15, "Foreign": 35, "Private": 45, "CB": 5},
    )


def _effect_row(
    scenario_id: str,
    rw: str,
    delta_rw: str,
    delta_tdc: str,
    delta_total: str,
) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "fiscal_year": "2027",
        "level_ratewall_ratio": rw,
        "delta_ratewall_ratio_vs_baseline": delta_rw,
        "total_current_demand_support_bil": "50",
        "delta_total_current_demand_support_bil": delta_total,
        "tdc_current_demand_support_bil": "30",
        "delta_tdc_current_demand_support_bil": delta_tdc,
        "direct_treasury_current_demand_support_bil": "2",
        "delta_direct_treasury_current_demand_support_bil": "-1",
        "bank_treasury_current_demand_support_bil": "1",
        "delta_bank_treasury_current_demand_support_bil": "0.1",
        "frozen_denominator_bil": "126",
    }


def _ratio_row(scenario_id: str) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "fiscal_year": "2027",
        "mmf_deposit_pass_through": "0.97",
        "source_status": "pass_tdcsim_cbo_contract_materialized",
    }


def _write_scenario(
    path: Path,
    scenario_id: str,
    title: str,
    shares: dict[str, float],
) -> None:
    path.write_text(
        json.dumps(
            {
                "scenario_id": scenario_id,
                "title": title,
                "overrides": {
                    "holder_preferences": {
                        "rows": [
                            {"security_type": "bills", "shares": shares},
                            {"security_type": "notes", "shares": shares},
                        ]
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def _write_holder_stocks(
    root: Path,
    run: str,
    scenario_id: str,
    final_amounts: dict[str, int],
) -> None:
    output = root / "runs" / run / "outputs"
    output.mkdir(parents=True)
    path = output / "tdcsim_holder_stocks.csv.gz"
    rows = []
    for date, amounts in (
        ("2026-06-21", {"Banks": 1, "Foreign": 1, "Private": 1, "CB": 1}),
        ("2027-09-30", final_amounts),
    ):
        for holder, amount in amounts.items():
            rows.append(
                {
                    "scenario_id": scenario_id,
                    "date": date,
                    "holder_sector": holder,
                    "debt_held_bil": str(amount),
                }
            )
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["scenario_id", "date", "holder_sector", "debt_held_bil"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

from __future__ import annotations

import csv
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from ratewall.rwtam.assembly import (
    _sector_columns,
    _with_rw_ratio_degenerate,
    parameter_manifest_rows,
    sfc_balance_sheet_tables,
    sfc_transaction_flow_tables,
)
from ratewall.rwtam.v1 import _load_pack, build_v1, write_v1_outputs


PACK_DIR = Path("configs/rwtam/packs")


@lru_cache(maxsize=1)
def _default_v1():
    return build_v1(PACK_DIR)


def test_sfc_balance_sheet_matrix_zero_sums_from_opening_stocks() -> None:
    pack = _load_pack(PACK_DIR)
    rows, checks, lineage = sfc_balance_sheet_tables(pack, _sector_columns())

    base_rows = [row for row in rows if row["band"] == "base"]
    assert sum(int(row["opening_stock_source_rows"]) for row in base_rows) == 79
    assert {row["status"] for row in checks} == {"pass"}
    assert all(Decimal(row["row_sum_bil"]) == 0 for row in rows)
    assert any(
        Decimal(row["unallocated_line_mapping_residual"]) != 0 for row in rows
    )
    assert lineage
    assert all("avoid double counting" in row["lineage_note"] for row in lineage)


def test_sfc_transaction_flow_matrix_zero_sums_and_ties_to_rollup() -> None:
    rows, checks = sfc_transaction_flow_tables(_default_v1(), _sector_columns())

    assert {row["status"] for row in checks} == {"pass"}
    assert all(
        Decimal(row["row_sum_bil"]) == 0
        for row in rows
        if row["adding_up_status"] == "pass"
    )
    assert any(
        row["flow_row_id"] == "memo_phase6_elasticity_layers_not_in_flow_ledger"
        and row["adding_up_status"] == "memo"
        for row in rows
    )
    assert {
        "TFM_ROLLUP_N_TIEOUT",
        "TFM_ROLLUP_D_TIEOUT",
        "TFM_ROLLUP_NET_TIEOUT",
    }.issubset({row["check_id"] for row in checks})


def test_three_bin_manifest_full_coverage_and_flagged_subset() -> None:
    rows, summary = parameter_manifest_rows(PACK_DIR, _default_v1())
    parameter_rows = [row for row in rows if row["record_type"] == "parameter_row"]

    assert len(parameter_rows) == summary["parameter_count"]
    assert {row["three_bin"] for row in parameter_rows} == {
        "directly_observed",
        "literature_calibrated",
        "scenario_or_owner_assumption",
    }
    assert [
        row
        for row in rows
        if row["record_type"] == "coverage_check"
        and row["pack"] == "unbinned_rows"
        and row["status"] == "pass"
    ]
    assert [
        row
        for row in rows
        if row["record_type"] == "subset_check"
        and row["pack"] == "flagged_assumptions_missing_from_assumption_bin"
        and row["count"] == "0"
        and row["status"] == "pass"
    ]


def test_rw_ratio_degenerate_emits_only_for_scenario_rollups(tmp_path: Path) -> None:
    result = _default_v1()
    default_paths = write_v1_outputs(result, tmp_path / "var/rwtam/v1")
    scenario_paths = write_v1_outputs(
        result,
        tmp_path / "var/rwtam/scenarios/probe",
    )

    with default_paths["out_ratewall_rollup"].open(encoding="utf-8", newline="") as handle:
        assert "rw_ratio_degenerate" not in (csv.DictReader(handle).fieldnames or [])
    with scenario_paths["out_ratewall_rollup"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert "rw_ratio_degenerate" in rows[0]
    headline = [
        row
        for row in rows
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]
    assert headline["rw_ratio_degenerate"] == "false"

    probe = _with_rw_ratio_degenerate(
        [
            {
                "period_type": "annual",
                "period": "2026",
                "band": "base",
                "ricardian_offset": "0",
                "D_bil": "211.1247661743165232622429402",
                "RW_ratio": "0.0505300748588156",
            },
            {
                "period_type": "annual",
                "period": "2035",
                "band": "high",
                "ricardian_offset": "0",
                "D_bil": "0.7",
                "RW_ratio": "7.8",
            },
        ]
    )
    assert probe[1]["rw_ratio_degenerate"] == "true"

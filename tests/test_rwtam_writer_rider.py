from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from ratewall.rwtam.writer_rider import (
    build_conversion_tornado_rows,
    build_parallel_curve_comparator_rows,
    build_writer_rider_outputs,
)
from ratewall.rwtam.v1 import build_v1


PACK_DIR = Path("configs/rwtam/packs")


@lru_cache(maxsize=1)
def _conversion_rows() -> list[dict[str, str]]:
    return build_conversion_tornado_rows(PACK_DIR)


@lru_cache(maxsize=1)
def _parallel_rows() -> list[dict[str, str]]:
    return build_parallel_curve_comparator_rows(PACK_DIR)


def test_conversion_tornado_moves_one_cell_and_keeps_default_frozen() -> None:
    rows = _conversion_rows()
    base = build_v1(PACK_DIR, include_impulse_beta_comparator=False).rows(
        "out_ratewall_rollup"
    )
    default = [
        row
        for row in rows
        if row["run_id"] == "base_default"
        and row["period_type"] == "annual"
        and row["period"] == "2026"
    ][0]
    base_default = [
        row
        for row in base
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]
    assert default["RW_ratio"] == base_default["RW_ratio"]

    retiree_high = [
        row
        for row in rows
        if row["run_id"] == "hh_retiree_fixed_income_saver__high"
        and row["period_type"] == "annual"
    ][0]
    assert Decimal(retiree_high["delta_RW_vs_base"]) != 0
    assert retiree_high["dominant_side"] == "N"
    assert retiree_high["scenario_role"] == "scenario_only;sensitivity_readout"


def test_conversion_tornado_envelope_bounds_single_cell_rows() -> None:
    rows = [row for row in _conversion_rows() if row["row_type"] == "run"]
    for period_type in ("annual", "cumulative_120_month"):
        singles = [
            Decimal(row["RW_ratio"])
            for row in rows
            if row["run_type"] == "single_cell" and row["period_type"] == period_type
        ]
        envelope = {
            row["coefficient_variant"]: Decimal(row["RW_ratio"])
            for row in rows
            if row["run_type"] == "conversion_only_envelope"
            and row["period_type"] == period_type
        }
        assert envelope["low"] < min(singles)
        assert envelope["high"] > max(singles)


def test_parallel_curve_comparator_zeroes_tp_and_preserves_bill_side_n() -> None:
    rows = _parallel_rows()
    annual_tp_off = [
        row
        for row in rows
        if row["row_type"] == "summary"
        and row["scenario_id"] == "parallel_tp_off"
        and row["period_type"] == "annual"
    ][0]
    assert annual_tp_off["label"] == "comparator_only"
    assert Decimal(annual_tp_off["gap_RW"]) != 0
    assert Decimal(annual_tp_off["gap_D_bil"]) != 0

    bill_rows = [
        row
        for row in rows
        if row["row_type"] == "bill_tp_invariant"
        and row["instrument_family"] == "treasury_bills"
    ]
    assert bill_rows
    assert all(row["headline_N_bil"] == row["tp_off_N_bil"] for row in bill_rows)
    assert all(row["headline_D_bil"] == row["tp_off_D_bil"] for row in bill_rows)
    assert {row["gap_N_bil"] for row in bill_rows} == {"0"}
    assert {row["label"] for row in bill_rows} == {
        "comparator_only;bill_side_tp_invariant"
    }


def test_writer_rider_outputs_are_scenario_only(tmp_path: Path) -> None:
    paths = build_writer_rider_outputs(
        PACK_DIR,
        output_dir=tmp_path / "var/rwtam/scenarios/writer_rider",
        report_path=tmp_path / "do/rwtam_writer_rider_report_20260705.md",
    )
    assert paths["out_conversion_tornado"].exists()
    assert paths["out_parallel_curve_comparator"].exists()
    assert paths["report"].exists()
    assert "scenarios/writer_rider" in paths["out_conversion_tornado"].as_posix()

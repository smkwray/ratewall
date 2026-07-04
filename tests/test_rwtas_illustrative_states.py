from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from ratewall.rwtas.data_upgrades import settlement_class_invariant_rows
from ratewall.rwtas.illustrative_states import (
    DECADE_LABEL,
    EMERGENCE_CAPTION_NOTE,
    FIAT_LABEL,
    SHAPE_ONLY_CAPTION_NOTE,
    build_illustrative_states,
    write_illustrative_state_outputs,
)


PACK_DIR = Path("configs/rwtas/packs")


def test_illustrative_states_emit_required_tables_and_labels(tmp_path: Path) -> None:
    result = build_illustrative_states(PACK_DIR, output_root=tmp_path)

    emergence = result.rows("out_decade_emergence_series")
    channel = result.rows("out_channel_existence")
    japan = result.rows("out_japan_comparison")
    fiscal = result.rows("out_pure_fiscal_two_engines")
    spectrum = result.rows("out_grand_spectrum")
    inputs = result.rows("out_illustrative_state_inputs")
    lineage = result.rows("out_lineage")
    old_vs_new = result.rows("out_decade_emergence_old_vs_new")
    bank_perimeter = result.rows("out_historical_bank_perimeter")
    settlement_map = result.rows("out_settlement_class_map")

    assert [row["state_id"] for row in emergence] == [
        "historical_1965",
        "historical_1985",
        "historical_2005",
        "calibrated_US_2026_default",
    ]
    assert all(row["claim_grade_label"] == DECADE_LABEL for row in emergence[:3])
    assert all(Decimal(row["RW_ratio"]) >= 0 for row in emergence)

    assert not [row for row in inputs if row["grade"] == "C"]
    assert any(
        row["state_id"] == "historical_1985"
        and row["input_item"] == "bill_share"
        and "28.247752685492127" in row["source_value_verbatim"]
        and row["grade"] == "A"
        for row in inputs
    )
    assert any(
        row["state_id"] == "historical_2005"
        and row["input_item"] == "foreign_holder_share"
        and "43.212094737786494" in row["source_value_verbatim"]
        for row in inputs
    )
    assert {row["state_id"] for row in old_vs_new} == {"historical_1965", "historical_1985", "historical_2005"}
    assert any(Decimal(row["delta_RW_ratio"]) != 0 for row in old_vs_new)

    assert any(
        row["state_id"] == "historical_1965"
        and row["channel_id"] == "deposit_pass_through"
        and row["structurally_present"] == "false"
        for row in channel
    )
    assert any(
        row["state_id"] == "historical_1985"
        and row["channel_id"] == "deposit_pass_through"
        and row["structurally_present"] == "partial"
        for row in channel
    )

    assert japan == [
        {
            "comparison_id": "not_debt_gdp_japan_vs_us",
            "state_id": "stylized_japan",
            "RW_ratio": japan[0]["RW_ratio"],
            "US_default_RW_ratio": japan[0]["US_default_RW_ratio"],
            "debt_gdp_ratio": "250",
            "US_debt_gdp_ratio": "100",
            "interpretation": "holder_composition_and_pass_through_gate_wall_not_debt_scale",
            "claim_grade_label": FIAT_LABEL,
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        }
    ]
    assert Decimal(japan[0]["RW_ratio"]) < Decimal(japan[0]["US_default_RW_ratio"])

    assert {row["state_id"] for row in fiscal} == {
        "pure_fiscal_reg_q",
        "pure_fiscal_today_betas",
        "italy_early_1990s_note",
    }
    zero = next(row for row in fiscal if row["state_id"] == "pure_fiscal_reg_q")
    today = next(row for row in fiscal if row["state_id"] == "pure_fiscal_today_betas")
    assert Decimal(zero["RW_ratio"]) > 0
    assert Decimal(today["RW_ratio"]) >= Decimal(zero["RW_ratio"])

    assert {"textbook_limit_fiat_state", "hypothetical_ratio_one_illustration"}.issubset(
        {row["state_id"] for row in spectrum}
    )
    endpoint_rows = [
        row
        for row in spectrum
        if row["state_id"] in {"textbook_limit_fiat_state", "hypothetical_ratio_one_illustration"}
    ]
    assert all("cited_not_rebuilt" in row["claim_grade_label"] for row in endpoint_rows)
    assert any("out_slr_spectrum.csv" in row["source_file"] for row in lineage)
    assert any(
        row["bank_perimeter"] == "banks_incl_credit_unions"
        and row["settlement_class"] == "mode_B_confirmed"
        and row["recommended_for_absorption"] == "true"
        for row in bank_perimeter
    )
    assert next(row for row in settlement_map if row["holder"] == "other_residual")[
        "share_of_l210_total"
    ] == "0"
    assert not any(row["holder"] == "assertion" for row in settlement_map)
    assert {row["status"] for row in result.rows("out_settlement_class_invariant")} == {"pass"}
    mutated = [dict(row) for row in settlement_map]
    mutated[0]["share_of_l210_total"] = "0"
    assert any(
        row["check_id"] == "settlement_class_map_share_sum" and row["status"] == "fail"
        for row in settlement_class_invariant_rows(PACK_DIR, mutated)
    )
    assert {row["caption_note"] for row in emergence} == {EMERGENCE_CAPTION_NOTE}
    assert {row["caption_note"] for row in japan} == {SHAPE_ONLY_CAPTION_NOTE}
    assert {row["caption_note"] for row in fiscal} == {SHAPE_ONLY_CAPTION_NOTE}
    assert any(SHAPE_ONLY_CAPTION_NOTE == row["caption_note"] for row in spectrum)


def test_illustrative_state_outputs_write_csvs(tmp_path: Path) -> None:
    result = build_illustrative_states(PACK_DIR, output_root=tmp_path / "build")
    paths = write_illustrative_state_outputs(result, tmp_path / "written")

    assert paths["out_grand_spectrum"].exists()
    assert paths["out_settlement_class_map"].exists()
    assert paths["out_settlement_class_invariant"].exists()
    with paths["out_grand_spectrum"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert any(row["state_id"] == "stylized_japan" for row in rows)

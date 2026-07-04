from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from ratewall.rwtas.allocation_layer import (
    ALLOCATION_CAPTION_NOTE,
    PARAMETER_BANDS,
    build_allocation_layer,
    validate_allocation_overlap_rows,
    write_allocation_layer_outputs,
)
from ratewall.rwtas.v1 import build_v1


PACK_DIR = Path("configs/rwtas/packs")


@lru_cache(maxsize=1)
def _allocation_result():
    return build_allocation_layer(PACK_DIR)


def test_allocation_layer_wires_evidence_bands_and_excludes_buyback() -> None:
    result = _allocation_result()
    rows = result.rows("out_allocation_layer_diagnostic")
    parameters = {row.get("parameter_id"): row for row in rows if row.get("row_type") == "parameter"}

    assert parameters["household_rotation_elasticity"]["low"] == "0.04"
    assert parameters["household_rotation_elasticity"]["base"] == "0.09"
    assert parameters["household_rotation_elasticity"]["high"] == "0.16"
    assert parameters["household_rotation_elasticity"]["grade"] == "D+"
    assert parameters["stock_reallocation_share"]["grade"] == "D"
    assert parameters["hurdle_passthrough"]["base"] == "0.25"
    assert parameters["hurdle_passthrough"]["claim_grade_label"] == "B"
    assert parameters["corporate_financial_allocation_share"]["high"] == "0.45"
    assert PARAMETER_BANDS["hurdle_passthrough"]["grade"] == "B"

    excluded = [row for row in rows if row.get("parameter_id") == "buyback_equity_supply_leg"][0]
    assert excluded["row_type"] == "excluded_with_evidence"
    assert "profit/cash-driven" in excluded["disposition"]

    capex_excluded = [
        row
        for row in rows
        if row.get("row_type") == "excluded_overlap_with_6B_user_cost"
        and row.get("rule") == "corporate_capex_allocation_drag"
    ]
    assert {row["dose_mode"] for row in capex_excluded} == {"persistent_level", "transient_12m"}
    assert all(row["delta_D_bil"] == "0" for row in capex_excluded)
    assert all(row["include_flag"] == "0" for row in capex_excluded)


def test_allocation_layer_emits_required_pairs_and_scenario_labels(tmp_path: Path) -> None:
    result = build_allocation_layer(PACK_DIR, output_root=tmp_path / "build")
    pairs = result.rows("out_allocation_on_off")

    assert {row["dose_mode"] for row in pairs} == {"persistent_level", "transient_12m"}
    assert all(Decimal(row["delta_D_bil"]) < 0 for row in pairs)
    assert all(abs(Decimal(row["delta_RW"])) < Decimal("0.003") for row in pairs)
    assert any(row.get("row_type") == "financialization_interaction" for row in result.rows("out_allocation_layer_diagnostic"))
    assert {
        row["input_basis_label"] for row in result.rows("out_allocation_layer_diagnostic")
    } == {"scenario_only", "grade_A_exact_pull"}
    assert all(
        row["claim_grade_label"] in {"assumption_directional_support", "B", "allocation_evidence_exact_pull"}
        for row in result.rows("out_allocation_layer_diagnostic")
    )
    exact_pulls = result.rows("out_allocation_exact_pulls")
    assert any(
        row["row_type"] == "grade_A_exact_pull"
        and row["parameter_id"] == "ncb_net_equity_issuance_2025"
        and row["base"] == "-304066"
        for row in exact_pulls
    )
    assert any(
        row["row_type"] == "overlap_resolution"
        and row["overlap_key"] == "mmf_overlap_resolution|z1_household_share|2021_2025"
        for row in exact_pulls
    )
    assert {
        row["caption_note"]
        for rows in result.tables.values()
        for row in rows
    } == {ALLOCATION_CAPTION_NOTE}

    paths = write_allocation_layer_outputs(result, tmp_path / "out")
    assert paths["out_allocation_layer_diagnostic"].name == "out_allocation_layer_diagnostic.csv"
    assert paths["out_allocation_layer_diagnostic"].exists()
    assert paths["out_allocation_exact_pulls"].exists()


def test_allocation_attribution_reconciles_on_vs_off_with_explicit_residuals() -> None:
    result = _allocation_result()
    pairs = {row["dose_mode"]: row for row in result.rows("out_allocation_on_off")}
    attribution = result.rows("out_allocation_attribution")

    for dose_mode, pair in pairs.items():
        rows = [
            row
            for row in attribution
            if row["dose_mode"] == dose_mode and row.get("include_in_reconciliation") == "1"
        ]
        assert {row["rule"] for row in rows} == {
            "household_and_corporate_financial_claim_yield",
            "rotation_side_d_recomposition",
            "interaction_residual",
        }
        assert sum(Decimal(row["delta_N_bil"]) for row in rows) == Decimal(pair["delta_N_bil"])
        assert sum(Decimal(row["delta_D_bil"]) for row in rows) == Decimal(pair["delta_D_bil"])
        recomposition = [row for row in rows if row["rule"] == "rotation_side_d_recomposition"][0]
        assert Decimal(recomposition["delta_D_bil"]).quantize(Decimal("0.001")) == Decimal("-0.709")
        residual = [row for row in rows if row["rule"] == "interaction_residual"][0]
        assert Decimal(residual["delta_N_bil"]) == 0
        assert Decimal(residual["delta_D_bil"]) == 0


def test_allocation_overlap_probes_fail_on_double_count_injections() -> None:
    rows = [
        {
            "overlap_type": "user_cost_vs_allocation_capex",
            "overlap_key": "firm|2026|base",
            "include_flag": "1",
        }
    ]
    assert validate_allocation_overlap_rows(rows) == []
    assert validate_allocation_overlap_rows(rows + [dict(rows[0])])

    result = _allocation_result()
    probes = {row["check_id"]: row for row in result.rows("out_allocation_overlap_probe")}
    assert probes["actual_rows_distinct"]["status"] == "pass"
    assert probes["user_cost_double_count_injection_fails"]["status"] == "pass"
    assert probes["actual_flow_duplicate_injection_fails"]["status"] == "pass"


def test_allocation_off_keeps_default_headline_byte_stable() -> None:
    before = build_v1(PACK_DIR).rows("out_ratewall_rollup")
    _ = _allocation_result()
    after = build_v1(PACK_DIR).rows("out_ratewall_rollup")

    assert before == after

from __future__ import annotations

import pytest
import csv
from decimal import Decimal
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
ARTIFACTS = {
    "replication": "ratewall_residualized_ffr_literature_replication_audit.csv",
    "lp_results": "ratewall_residualized_ffr_literature_lp_results.csv",
    "fwl": "ratewall_residualized_ffr_fwl_diagnostics.csv",
    "bridge": "ratewall_residualized_ffr_private_demand_bridge.csv",
    "normalization": "ratewall_residualized_ffr_normalization_bridge.csv",
}


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_residualized_ffr_bridge_materializes_real_review_only_results() -> None:
    replication_rows = _rows(ARTIFACTS["replication"])
    lp_rows = _rows(ARTIFACTS["lp_results"])
    fwl_rows = _rows(ARTIFACTS["fwl"])
    bridge_rows = _rows(ARTIFACTS["bridge"])
    normalization_rows = _rows(ARTIFACTS["normalization"])

    h8_gdp_replication = next(
        row for row in replication_rows if row["outcome_id"] == "log_real_gdp" and row["horizon_q"] == "8"
    )
    assert h8_gdp_replication["replication_status"] == (
        "pass_paper_gdp_replication_within_tolerance"
    )
    assert Decimal(h8_gdp_replication["local_replication_response_pct"]) < Decimal("0")
    assert Decimal(h8_gdp_replication["absolute_difference_pct"]) <= Decimal(
        h8_gdp_replication["replication_tolerance_pct"]
    )

    h8_fspdp = next(
        row
        for row in lp_rows
        if row["outcome_id"] == "log_real_fspdp" and row["horizon_q"] == "8"
    )
    assert h8_fspdp["lp_result_status"] == "pass_private_demand_adaptation_estimated"
    assert Decimal(h8_fspdp["response_value"]) < Decimal("0")

    h8_fspdp_pp_gdp = next(
        row
        for row in lp_rows
        if row["outcome_id"] == "fspdp_gdp_share_contribution"
        and row["horizon_q"] == "8"
    )
    assert h8_fspdp_pp_gdp["lp_result_status"] == (
        "pass_private_demand_adaptation_estimated"
    )
    assert Decimal(h8_fspdp_pp_gdp["response_value"]) < Decimal("0")

    h8_pfi = next(
        row
        for row in lp_rows
        if row["outcome_id"] == "log_real_private_fixed_investment"
        and row["horizon_q"] == "8"
    )
    assert h8_pfi["lp_result_status"] == "blocked_local_component_series_unavailable"

    assert {row["diagnostic_status"] for row in fwl_rows} == {
        "pass_fwl_audit_materialized"
    }
    fwl_equivalence = next(
        row for row in fwl_rows if row["diagnostic_item"] == "fwl_equivalence"
    )
    assert Decimal(fwl_equivalence["beta_abs_diff"]) <= Decimal("0.000000001")

    h8_bridge = next(
        row
        for row in bridge_rows
        if row["outcome_id"] == "fspdp_gdp_share_contribution"
        and row["horizon_q"] == "8"
        and row["target_role"] == "ratewall_denominator_target"
    )
    assert h8_bridge["bridge_status"] == "pass_fspdp_outcome_adapted"

    summary_row = next(
        row
        for row in normalization_rows
        if row["normalization_target_id"] == "exact_100bp_year_cumulative_policy_path_summary"
    )
    assert summary_row["normalization_status"] == (
        "pass_bridge_normalization_100bp_year"
    )
    assert Decimal(summary_row["first_year_area_bps_year"]) > Decimal("90")
    assert Decimal(summary_row["mapped_h8_fspdp_d_y_per_100bp_year"]) > Decimal(
        "0"
    )
    assert summary_row["normalization_formula"] == (
        "D_Y_per_100bp_year = D_Y_native * (100 / first_year_area_bps_year)"
    )

    year1_window = next(
        row
        for row in normalization_rows
        if row["annual_window_id"] == "year1_h4_endpoint_proxy"
    )
    year2_window = next(
        row
        for row in normalization_rows
        if row["annual_window_id"] == "year2_h8_minus_h4_increment_proxy"
    )
    year3_window = next(
        row
        for row in normalization_rows
        if row["annual_window_id"] == "year3_h12_minus_h8_increment_proxy"
    )
    assert year1_window["normalization_status"] == (
        "pass_review_only_annual_flow_window_materialized"
    )
    assert Decimal(year1_window["mapped_window_d_y_per_100bp_year"]) > Decimal("0")
    assert Decimal(year2_window["mapped_window_d_y_per_100bp_year"]) > Decimal("0")
    assert Decimal(year3_window["mapped_window_d_y_per_100bp_year"]) < Decimal("0")

    year1_bridge = next(
        row
        for row in bridge_rows
        if row["target_role"] == "annual_flow_window_translation"
        and row["annual_window_id"] == "year1_h4_endpoint_proxy"
    )
    assert year1_bridge["bridge_status"] == (
        "pass_review_only_annual_flow_window_materialized"
    )
    assert Decimal(year1_bridge["bridge_response_value"]) < Decimal("0")


def test_residualized_ffr_bridge_keeps_forbidden_switches_false() -> None:
    for artifact in ARTIFACTS.values():
        for row in _rows(artifact):
            assert row["canonical_ratio_entry"] == "false"
            assert row["enters_main_ratio"] == "false"
            assert row["evidence_mode_enabled"] == "false"
            for field in FORBIDDEN_SWITCH_FIELDS:
                assert row[field] == "false"

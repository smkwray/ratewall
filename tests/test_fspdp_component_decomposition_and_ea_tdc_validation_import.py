import pytest
import csv
from collections import Counter
from pathlib import Path




pytestmark = pytest.mark.full_surface

FSPDP_BRIDGE = (
    "outputs/tables/ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv"
)
FSPDP_SOURCE_MANIFEST = (
    "outputs/tables/ratewall_conventional_drag_fspdp_component_source_manifest.csv"
)
FSPDP_SHARE_PANEL = (
    "outputs/tables/ratewall_conventional_drag_fspdp_component_share_panel.csv"
)
EA_TDC_IMPORT = (
    "outputs/tables/ratewall_tdc_ea_tdc_pass_through_regime_validation_import.csv"
)

FORBIDDEN_SWITCH_FIELDS = [
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]


def _rows(path: str) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_fspdp_component_decomposition_bridge_row_grain_and_requirements() -> None:
    rows = _rows(FSPDP_BRIDGE)

    assert len(rows) == 63
    assert len({row["decomposition_bridge_row_id"] for row in rows}) == 63
    assert {row["target_outcome_id"] for row in rows} == {"fspdp_gdp_share"}
    assert {row["target_horizon_quarters"] for row in rows} == {"4", "8", "12"}
    assert Counter(row["decomposition_component_id"] for row in rows) == {
        "pce_durable_goods": 9,
        "pce_nondurable_goods": 9,
        "pce_services": 9,
        "private_residential_fixed_investment": 9,
        "private_nonresidential_structures": 9,
        "private_equipment": 9,
        "private_intellectual_property_products": 9,
    }
    assert {
        row["source_acquisition_status"] for row in rows
    } == {"pass_source_snapshot_materialized_review_only"}
    assert all(row["source_snapshot_sha256"] for row in rows)
    assert all(row["source_record_count"] for row in rows)
    assert all(row["mean_nominal_share_of_gdp"] for row in rows)
    assert all(row["latest_nominal_share_of_gdp"] for row in rows)


def test_fspdp_component_decomposition_bridge_mir_joins_are_review_only() -> None:
    rows = _rows(FSPDP_BRIDGE)
    direct_rows = [
        row
        for row in rows
        if row["decomposition_component_id"]
        in {"pce_durable_goods", "pce_nondurable_goods"}
    ]
    proxy_rows = [
        row
        for row in rows
        if row["decomposition_component_id"] == "private_residential_fixed_investment"
    ]
    missing_rows = [
        row
        for row in rows
        if row["decomposition_component_id"]
        in {
            "pce_services",
            "private_nonresidential_structures",
            "private_equipment",
            "private_intellectual_property_products",
        }
    ]

    assert all(row["mir_join_status"].startswith("pass_") for row in direct_rows)
    assert all(
        len(row["mir_component_aggregation_review_row_ids"].split(";")) == 2
        for row in direct_rows
    )
    assert all(
        row["proxy_bridge_status"] == "not_applicable_direct_pce_component_series"
        for row in direct_rows
    )
    assert all(row["mir_join_status"].startswith("pass_") for row in proxy_rows)
    assert all(
        len(row["mir_component_aggregation_review_row_ids"].split(";")) == 4
        for row in proxy_rows
    )
    assert all(
        len(row["mir_component_source_variant_review_row_ids"].split(";")) == 8
        for row in proxy_rows
    )
    assert all(
        row["proxy_bridge_status"].startswith(
            "blocked_missing_reviewed_houst_permit"
        )
        for row in proxy_rows
    )
    assert all(row["mir_join_status"].startswith("blocked_no_interpreted") for row in missing_rows)


def test_fspdp_component_decomposition_bridge_fail_closed() -> None:
    rows = _rows(FSPDP_BRIDGE)

    assert all(row["candidate_bps_year_exposure"] == "" for row in rows)
    assert all(row["candidate_gdp_share_drag_per_100bp_year"] == "" for row in rows)
    assert all(row["candidate_ci_lower"] == "" for row in rows)
    assert all(row["candidate_ci_upper"] == "" for row in rows)
    assert {
        row["research_parameterization_admission_status"] for row in rows
    } == {"blocked_fspdp_component_decomposition_bridge_not_denominator_calibration"}
    assert all(
        all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
        for row in rows
    )


def test_fspdp_component_source_manifest_and_share_panel_are_source_backed() -> None:
    manifest_rows = _rows(FSPDP_SOURCE_MANIFEST)
    panel_rows = _rows(FSPDP_SHARE_PANEL)

    assert len(manifest_rows) == 8
    assert {row["source_family"] for row in manifest_rows} == {
        "DB.nomics mirror of BEA NIPA"
    }
    assert all(row["raw_source_sha256"] for row in manifest_rows)
    assert all(row["source_snapshot_sha256"] for row in manifest_rows)
    assert {
        row["component_id"]
        for row in panel_rows
    } == {
        "pce_durable_goods",
        "pce_nondurable_goods",
        "pce_services",
        "private_residential_fixed_investment",
        "private_nonresidential_structures",
        "private_equipment",
        "private_intellectual_property_products",
    }
    assert all(row["nominal_share_of_gdp"] for row in panel_rows)
    assert all(row["nominal_share_of_parent"] for row in panel_rows)
    assert {row["candidate_bps_year_exposure"] for row in panel_rows} == {""}
    assert {
        row["candidate_gdp_share_drag_per_100bp_year"]
        for row in manifest_rows + panel_rows
    } == {""}
    assert all(
        all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
        for row in manifest_rows + panel_rows
    )


def test_ea_tdc_regime_validation_import_is_hashed_and_not_runtime_selector() -> None:
    rows = _rows(EA_TDC_IMPORT)

    assert len(rows) == 15
    assert len({row["regime_validation_import_row_id"] for row in rows}) == 15
    assert {row["contract_row_count"] for row in rows} == {"15"}
    assert {row["validation_row_count"] for row in rows} == {"30"}
    assert {row["classifier_row_count"] for row in rows} == {"11"}
    assert {row["estimates_row_count"] for row in rows} == {"23"}
    assert all(row["contract_artifact_sha256"] for row in rows)
    assert all(row["validation_artifact_sha256"] for row in rows)
    assert {row["ratewall_runtime_selector_allowed"] for row in rows} == {"false"}
    assert {row["ratewall_scenario_default_allowed"] for row in rows} == {"false"}
    assert {row["candidate_pass_through_runtime_value"] for row in rows} == {""}
    assert all(row["admission_status"].startswith("blocked_") for row in rows)
    assert all(
        all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
        for row in rows
    )


def test_fspdp_and_ea_tdc_import_ledger_and_audit_invariant() -> None:
    ledger_rows = _rows("outputs/tables/ratewall_assumption_source_backing_ledger.csv")
    backend_audit_rows = _rows(
        "outputs/tables/ratewall_backend_invariant_guardrail_audit.csv"
    )
    source_audit_rows = _rows(
        "outputs/tables/ratewall_assumption_source_backing_invariant_audit.csv"
    )

    expected = {
        "conventional_drag_fspdp_component_decomposition_bridge": (
            "ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv",
            len(_rows(FSPDP_BRIDGE)),
            "fspdp_component_decomposition_bridge_not_denominator_calibration",
        ),
        "tdc_ea_tdc_pass_through_regime_validation_import": (
            "ratewall_tdc_ea_tdc_pass_through_regime_validation_import.csv",
            len(_rows(EA_TDC_IMPORT)),
            "ea_tdc_regime_validation_import_not_runtime_selector",
        ),
    }
    for family, (artifact, expected_count, claim_boundary) in expected.items():
        family_rows = [row for row in ledger_rows if row["assumption_family"] == family]
        assert len(family_rows) == expected_count
        assert {row["artifact_or_surface"] for row in family_rows} == {artifact}
        assert {row["source_backing_class"] for row in family_rows} == {
            "blocked_or_diagnostic_only"
        }
        assert {row["claim_boundary"] for row in family_rows} == {claim_boundary}
        assert all(row["enters_canonical_ratio"] == "false" for row in family_rows)

    source_manifest_ledger_rows = [
        row
        for row in ledger_rows
        if row["assumption_family"]
        == "conventional_drag_fspdp_component_source_manifest"
    ]
    share_panel_ledger_rows = [
        row
        for row in ledger_rows
        if row["assumption_family"] == "conventional_drag_fspdp_component_share_panel"
    ]
    assert len(source_manifest_ledger_rows) == len(_rows(FSPDP_SOURCE_MANIFEST))
    assert len(share_panel_ledger_rows) == len(_rows(FSPDP_SHARE_PANEL))
    assert {
        row["source_backing_class"]
        for row in source_manifest_ledger_rows + share_panel_ledger_rows
    } == {"official_source_value"}

    for audit_item in {
        "conventional_drag_fspdp_component_decomposition_bridge_fail_closed",
        "tdc_ea_tdc_pass_through_regime_validation_import_fail_closed",
        "fspdp_component_decomposition_source_panel_no_drag",
    }:
        assert {
            row["audit_status"]
            for row in backend_audit_rows
            if row["audit_item"] == audit_item
        } == {"pass"}
    for audit_item in {
        "conventional_drag_fspdp_component_decomposition_bridge_fail_closed",
        "tdc_ea_tdc_pass_through_regime_validation_import_fail_closed",
        "fspdp_component_source_panel_no_drag",
    }:
        assert {
            row["audit_status"]
            for row in source_audit_rows
            if row["audit_item"] == audit_item
        } == {"pass"}

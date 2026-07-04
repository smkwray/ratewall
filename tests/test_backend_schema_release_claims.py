from __future__ import annotations

import pytest
import csv
import json
import zipfile
from pathlib import Path




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
SOURCE_ARCHIVE = Path("outputs/release/ratewall_release_23_0_source_archive.zip")
SOURCE_SPECIFIC_CURRENT_DEMAND_BLOCKERS = (
    "ratewall_final_recipient_current_demand_bridge_attempt.csv",
    "blocked_no_admissible_source_backed_final_recipient_current_demand_bridge",
    "exact next source fields live in that bridge-attempt artifact",
    "blocked_no_recipient_current_demand_bridge",
    "no_source_backed_mapping_from_tdcest_gross_interest_cashflow_to_"
    "final_recipient_current_demand",
    "blocked_bank_iorb_timing_matrix_requires_behavior_bridge",
)
CENTRAL_TDC_GUARDRAIL_TERMS = (
    "ru_flow_tier2_tdc_core_object",
    "central TDC-family scenario object",
    "route/final-recipient gaps",
    "not TDC exclusion or quarantine gates",
    "DU-flow is not a prerequisite",
)
JOINT_WALL_PROBABILITY_BOUNDARY_TERMS = (
    "ratewall_joint_wall_probability_summary.csv",
    "conditional_named_grid_share_not_empirical_or_posterior_probability",
    "object-family wall-hit shares stay separate",
    "empirical probability",
    "posterior probability",
    "canonical RW_Y",
    "Evidence Mode",
    "prior updates remain blocked",
)
DENOMINATOR_EVIDENCE_UPGRADE_BOUNDARY_TERMS = (
    "ratewall_denominator_evidence_upgrade_priority_queue.csv",
    "ratewall_denominator_evidence_upgrade_tier1_workplan.csv",
    "ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv",
    "denominator_evidence_upgrade_queue_nonpromotional_source_acquisition_only",
    "blocked denominator source-design work",
    "unresolved evidence actions",
    "denominator prior narrowing",
    "split-denominator promotion",
    "Evidence Mode",
    "canonical ratio entry",
)
NONCANONICAL_CURRENT_DEMAND_ACTIVE_OUTPUT_TERMS = (
    "ratewall_noncanonical_current_demand_support_ratio_consumer.csv",
    "ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv",
    "active_output_noncanonical_current_demand_consumer_review_only",
    "active_output_noncanonical_current_demand_endpoint_review_only",
    "pass_review_only_noncanonical_consumer_indexed",
    "pass_review_only_endpoint_decision_indexed",
    "pass_shared_dual_lane_contract_sufficient_review_only_endpoint",
    "pass_no_further_consumer_hardening_required_review_only",
    "current_demand_admission",
    "Evidence_Mode",
)
TDC_ARITHMETIC_SURFACES = {
    "outputs/tables/ratewall_forecast_holder_tdc_consistency_bridge.csv",
    "outputs/tables/ratewall_historical_assumption_mode_tdc_wall_ratio_path.csv",
    "outputs/tables/ratewall_historical_tdc_wall_ratio_path.csv",
    "outputs/tables/ratewall_paper_tdc_dynamic_contribution.csv",
    "outputs/tables/ratewall_tdc_claim_boundary_audit.csv",
    "outputs/tables/ratewall_tdc_deposit_credit_decomposition.csv",
    "outputs/tables/ratewall_tdc_double_count_guardrail.csv",
    "outputs/tables/ratewall_tdc_net_ratewall_effect.csv",
    "outputs/tables/ratewall_tdc_materialization_semantic_summary.csv",
    "outputs/tables/ratewall_tdc_ru_financing_deposit_impulse.csv",
}
TDC_ARITHMETIC_ARCHIVE_TERMS = (
    "tdc_credit_supply_beta_overlap_safeguard_assumption_mode_no_double_count_not_source_gate_promotion",
    "blocked_default_replace_not_stack",
    "tdc_deposit_support_uses_tdcsim_projected_tdc_change_ex_interest_overlap",
    "historical_assumption_mode_tdc_wall_ratio_path_not_evidence_mode",
    "paper_tdc_dynamic_contribution_assumption_mode_decomposition_only",
    "tdc_to_total_deposits_net_materialization_coefficient",
    "tdc_materialization_semantic_summary_not_empirical_threshold_or_deposit_pricing_claim",
)


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _header(name: str) -> list[str]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


def test_backend_surface_schema_contract_rejects_duplicate_fields() -> None:
    rows = _rows("ratewall_backend_surface_schema_contract.csv")
    assert rows
    assert {row["schema_contract_status"] for row in rows} == {"pass"}
    assert {row["pandas_suffix_pattern_detected"] for row in rows} == {"false"}
    assert {row["prompt_numeric_source_block_status"] for row in rows} == {"pass"}

    frontier_header = _header(
        "ratewall_conventional_drag_research_parameterization_source_frontier.csv"
    )
    assert frontier_header.count("current_demand_mapping_status") == 1
    assert frontier_header.count("gdp_share_conversion_status") == 1

    frontier_contract_rows = [
        row
        for row in rows
        if row["artifact_name"]
        == "ratewall_conventional_drag_research_parameterization_source_frontier.csv"
    ]
    assert frontier_contract_rows
    assert {
        row["duplicate_header_count"]
        for row in frontier_contract_rows
        if row["field_name"]
        in {"current_demand_mapping_status", "gdp_share_conversion_status"}
    } == {"1"}


def test_artifact_claim_boundary_manifest_classifies_release_layers() -> None:
    rows = _rows("ratewall_backend_artifact_claim_boundary_manifest.csv")
    assert rows
    assert {row["artifact_claim_boundary_status"] for row in rows} == {"pass"}
    assert {row["prompt_numeric_source_block_status"] for row in rows} == {"pass"}
    assert not [
        row
        for row in rows
        if row["review_only_artifact_status"]
        == "fail_review_only_artifact_in_empirical_estimates_layer"
    ]

    by_artifact = {row["artifact_name"]: row for row in rows}
    for artifact in {
        "ratewall_backend_surface_schema_contract.csv",
        "ratewall_backend_artifact_claim_boundary_manifest.csv",
        "ratewall_release_archive_reproducibility_audit.csv",
        "ratewall_tdcest_z1_domestic_nonbank_sector_context.csv",
        "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv",
        "ratewall_policy_path_bps_year_protocol_closure.csv",
        "ratewall_tdc_deposit_pass_through_trigger_validation_preflight.csv",
    }:
        assert by_artifact[artifact]["release_layer"]
        assert by_artifact[artifact]["claim_boundary_status"].startswith("pass")

    z1_context = by_artifact[
        "ratewall_tdcest_z1_domestic_nonbank_sector_context.csv"
    ]
    assert z1_context["release_layer"] == "tdc_deposit_channel"
    assert z1_context["empirical_claim_enabled"] == "false"
    assert z1_context["pricing_output_enabled"] == "false"
    assert z1_context["holder_allocation_enabled"] == "false"

    dn_route_proxy = by_artifact[
        "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv"
    ]
    assert dn_route_proxy["release_layer"] == "assumption_mode"
    assert dn_route_proxy["empirical_claim_enabled"] == "false"
    assert dn_route_proxy["pricing_output_enabled"] == "false"
    assert dn_route_proxy["holder_allocation_enabled"] == "false"


def test_release_archive_reproducibility_audit_covers_new_surfaces() -> None:
    rows = _rows("ratewall_release_archive_reproducibility_audit.csv")
    assert rows
    required_paths = {
        "outputs/tables/ratewall_backend_surface_schema_contract.csv",
        "outputs/tables/ratewall_backend_artifact_claim_boundary_manifest.csv",
        "outputs/tables/ratewall_release_archive_reproducibility_audit.csv",
    }
    by_path = {row["artifact_path"]: row for row in rows}
    assert required_paths <= set(by_path)
    self_referential_audit_path = (
        "outputs/tables/ratewall_release_archive_reproducibility_audit.csv"
    )
    for path in required_paths:
        row = by_path[path]
        assert row["archive_included"] == "true"
        assert row["release_manifest_listed"] == "true"
        if path == self_referential_audit_path:
            assert row["sha256"]
            assert row["archive_reproducibility_status"] == "pass"
        else:
            assert row["sha256"]
            assert row["archive_reproducibility_status"] == "pass"

    with SOURCE_ARCHIVE.open("rb"):
        pass
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
    assert required_paths <= names


def test_release_archive_preserves_source_specific_current_demand_blockers() -> None:
    archived_summary_surfaces = {
        "outputs/tables/ratewall_final_recipient_current_demand_bridge_attempt.csv",
        "outputs/tables/ratewall_backend_model_readiness_gate.csv",
        "outputs/tables/ratewall_backend_completion_verdict.csv",
        "outputs/tables/ratewall_publication_claim_decision.csv",
    }
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
        assert archived_summary_surfaces <= names
        archived_text = "\n".join(
            archive.read(path).decode("utf-8")
            for path in sorted(archived_summary_surfaces)
        )

    for blocker in SOURCE_SPECIFIC_CURRENT_DEMAND_BLOCKERS:
        assert blocker in archived_text

    rows = _rows("ratewall_final_recipient_current_demand_bridge_attempt.csv")
    assert len(rows) == 11
    assert {row["bridge_materialization_status"] for row in rows} == {
        "blocked_no_admissible_source_backed_final_recipient_current_demand_bridge"
    }
    assert all(row["exact_next_required_field_set"] for row in rows)


def test_release_archive_preserves_central_ru_flow_tdc_guardrail() -> None:
    archived_tdc_guardrail_surfaces = {
        "outputs/tables/ratewall_tdc_equation_variant_registry.csv",
        "outputs/tables/ratewall_backend_model_readiness_gate.csv",
        "outputs/tables/ratewall_backend_completion_verdict.csv",
        "outputs/tables/ratewall_publication_claim_decision.csv",
    }
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
        assert archived_tdc_guardrail_surfaces <= names
        archived_text = "\n".join(
            archive.read(path).decode("utf-8")
            for path in sorted(archived_tdc_guardrail_surfaces)
        )

    for term in CENTRAL_TDC_GUARDRAIL_TERMS:
        assert term in archived_text


def test_release_archive_preserves_joint_probability_boundary() -> None:
    archived_joint_probability_surfaces = {
        "outputs/tables/ratewall_joint_wall_probability_summary.csv",
        "outputs/tables/ratewall_active_output_index.csv",
        "outputs/tables/ratewall_backend_model_readiness_gate.csv",
        "outputs/tables/ratewall_backend_completion_verdict.csv",
        "outputs/tables/ratewall_publication_claim_decision.csv",
    }
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
        assert archived_joint_probability_surfaces <= names
        archived_text = "\n".join(
            archive.read(path).decode("utf-8")
            for path in sorted(archived_joint_probability_surfaces)
        )

    for term in JOINT_WALL_PROBABILITY_BOUNDARY_TERMS:
        assert term in archived_text


def test_release_archive_preserves_denominator_evidence_upgrade_boundary() -> None:
    archived_denominator_upgrade_surfaces = {
        "outputs/tables/ratewall_denominator_evidence_upgrade_priority_queue.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_tier1_workplan.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv",
        "outputs/tables/ratewall_backend_model_readiness_gate.csv",
        "outputs/tables/ratewall_backend_completion_verdict.csv",
        "outputs/tables/ratewall_publication_claim_decision.csv",
    }
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
        assert archived_denominator_upgrade_surfaces <= names
        archived_text = "\n".join(
            archive.read(path).decode("utf-8")
            for path in sorted(archived_denominator_upgrade_surfaces)
        )

    for term in DENOMINATOR_EVIDENCE_UPGRADE_BOUNDARY_TERMS:
        assert term in archived_text


def test_release_archive_preserves_noncanonical_current_demand_active_output_boundary() -> None:
    archived_noncanonical_current_demand_surfaces = {
        "outputs/tables/ratewall_active_output_index.csv",
        "outputs/tables/ratewall_noncanonical_current_demand_support_ratio_consumer.csv",
        (
            "outputs/tables/"
            "ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv"
        ),
    }
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
        assert archived_noncanonical_current_demand_surfaces <= names
        archived_text = "\n".join(
            archive.read(path).decode("utf-8")
            for path in sorted(archived_noncanonical_current_demand_surfaces)
        )

    for term in NONCANONICAL_CURRENT_DEMAND_ACTIVE_OUTPUT_TERMS:
        assert term in archived_text


def test_release_manifest_and_archive_preserve_tdc_arithmetic_surfaces() -> None:
    manifest = json.loads(
        (OUTPUT_TABLES / "ratewall_release_manifest.json").read_text(encoding="utf-8")
    )
    listed = set().union(*(set(layer) for layer in manifest["artifact_layers"].values()))
    assert TDC_ARITHMETIC_SURFACES <= listed

    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
        assert TDC_ARITHMETIC_SURFACES <= names
        archived_text = "\n".join(
            archive.read(path).decode("utf-8")
            for path in sorted(TDC_ARITHMETIC_SURFACES)
        )

    for term in TDC_ARITHMETIC_ARCHIVE_TERMS:
        assert term in archived_text


def test_backend_schema_surfaces_are_ledgered_and_invariant_checked() -> None:
    ledger_rows = _rows("ratewall_assumption_source_backing_ledger.csv")
    families = {
        "backend_surface_schema_contract",
        "backend_artifact_claim_boundary_manifest",
        "release_archive_reproducibility_audit",
    }
    ledgered = [row for row in ledger_rows if row["assumption_family"] in families]
    assert ledgered
    assert {row["source_backing_class"] for row in ledgered} == {
        "blocked_or_diagnostic_only"
    }
    assert {row["enters_canonical_ratio"] for row in ledgered} == {"false"}
    assert {row["prior_narrowing_allowed"] for row in ledgered} == {"false"}
    assert {row["pricing_output_enabled"] for row in ledgered} == {"false"}
    assert {row["holder_allocation_enabled"] for row in ledgered} == {"false"}
    assert {row["raw_rate_shock_enabled"] for row in ledgered} == {"false"}

    source_backing = {
        row["audit_item"]: row
        for row in _rows("ratewall_assumption_source_backing_invariant_audit.csv")
    }
    assert source_backing[
        "backend_schema_release_anti_overclaim_surfaces_fail_closed"
    ]["audit_status"] == "pass"

    backend = {
        row["audit_item"]: row
        for row in _rows("ratewall_backend_invariant_guardrail_audit.csv")
    }
    for audit_item in {
        "backend_expansion_context_surfaces_nonpromotional",
        "context_surface_no_main_ratio_audit_complete",
    }:
        assert backend[audit_item]["audit_status"] == "pass"


def test_release_manifest_lists_schema_anti_overclaim_surfaces() -> None:
    manifest = json.loads(
        (OUTPUT_TABLES / "ratewall_release_manifest.json").read_text(encoding="utf-8")
    )
    backend_layer = set(manifest["artifact_layers"]["backend_expansion_context_design"])
    assert {
        "outputs/tables/ratewall_backend_surface_schema_contract.csv",
        "outputs/tables/ratewall_backend_artifact_claim_boundary_manifest.csv",
        "outputs/tables/ratewall_release_archive_reproducibility_audit.csv",
    } <= backend_layer


def test_release_manifest_lists_denominator_bridge_surfaces() -> None:
    manifest = json.loads(
        (OUTPUT_TABLES / "ratewall_release_manifest.json").read_text(encoding="utf-8")
    )
    backend_layer = set(manifest["artifact_layers"]["backend_expansion_context_design"])
    assert {
        "outputs/tables/ratewall_denominator_methodology_registry.csv",
        "outputs/tables/ratewall_annual_flow_denominator_anchor_registry.csv",
        "outputs/tables/ratewall_annual_support_denominator_compatibility_registry.csv",
        "outputs/tables/ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv",
        "outputs/tables/ratewall_scenario_denominator_anchor_lineage.csv",
        "outputs/tables/ratewall_scenario_denominator_stack_comparison.csv",
        "outputs/tables/ratewall_denominator_scale_conflict_adjudication.csv",
        "outputs/tables/ratewall_denominator_scale_conflict_followup_decision.csv",
        "outputs/tables/ratewall_noncanonical_current_demand_source_timing_contract.csv",
        "outputs/tables/ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv",
        "outputs/tables/ratewall_residualized_ffr_literature_replication_audit.csv",
        "outputs/tables/ratewall_residualized_ffr_literature_lp_results.csv",
        "outputs/tables/ratewall_residualized_ffr_fwl_diagnostics.csv",
        "outputs/tables/ratewall_residualized_ffr_private_demand_bridge.csv",
        "outputs/tables/ratewall_residualized_ffr_normalization_bridge.csv",
    } <= backend_layer


def test_release_manifest_and_archive_list_tdcest_route_context_surfaces() -> None:
    manifest = json.loads(
        (OUTPUT_TABLES / "ratewall_release_manifest.json").read_text(encoding="utf-8")
    )
    tdc_layer = set(manifest["artifact_layers"]["tdc_deposit_channel"])
    expected = {
        "outputs/tables/ratewall_tdcest_monetary_route_bridge.csv",
        "outputs/tables/ratewall_tdcest_mmf_route_split_context.csv",
        "outputs/tables/ratewall_tdcest_z1_domestic_nonbank_sector_context.csv",
    }
    assert expected <= tdc_layer

    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
    assert expected <= names


def test_release_manifest_and_archive_list_treasury_route_proxy_sidecar() -> None:
    manifest = json.loads(
        (OUTPUT_TABLES / "ratewall_release_manifest.json").read_text(encoding="utf-8")
    )
    assumption_layer = set(manifest["artifact_layers"]["assumption_mode"])
    expected = (
        "outputs/tables/"
        "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv"
    )
    assert expected in assumption_layer

    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
    assert expected in names


def test_release_archive_lists_runtime_support_offset_reviewer_reports() -> None:
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
    assert "outputs/reports/ratewall_runtime_annual_flow_support_offset_reviewer_packet.md" in names
    assert "outputs/reports/ratewall_runtime_annual_flow_support_offset_limitations.md" in names

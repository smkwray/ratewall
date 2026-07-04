from __future__ import annotations

import csv
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUTS = Path("outputs/tables")
EXPECTED_FORECAST_COMPONENTS = {
    "domestic_nonbank_interest_support",
    "bank_retained_margin_support",
    "tdc_deposit_current_demand_support",
}


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _scenario_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row["forecast_year"],
        row["mpc_scenario"],
        row["maturity_scenario"],
        row["holder_scenario"],
    )


def _component_surface_key(row: dict[str, str]) -> tuple[str, str]:
    return (row["forecast_path_ratio_scenario_registry_row_id"], row["component_id"])


def _assert_one_component_surface_row_per_scenario(
    rows: list[dict[str, str]],
    scenario_ids: set[str],
) -> None:
    rows_by_scenario_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_scenario_id[row["forecast_path_ratio_scenario_registry_row_id"]].append(row)

    assert set(rows_by_scenario_id) == scenario_ids
    for scenario_rows in rows_by_scenario_id.values():
        assert {row["component_id"] for row in scenario_rows} == EXPECTED_FORECAST_COMPONENTS


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def _assert_contiguous_rank(rows: list[dict[str, str]], field: str) -> None:
    assert sorted(int(row[field]) for row in rows) == list(range(1, len(rows) + 1))


def _assert_mapping_rows_link_bridge_basis(
    mapping_rows: list[dict[str, str]],
    bridge_basis_rows: list[dict[str, str]],
    *,
    allowed_unlinked_mapping_ids: set[str],
) -> None:
    basis_by_id = {
        row["forecast_evidence_bridge_basis_row_id"]: row
        for row in bridge_basis_rows
    }
    linked_mapping_rows = [
        row
        for row in mapping_rows
        if row["forecast_evidence_bridge_basis_row_id"]
    ]
    unlinked_mapping_rows = [
        row
        for row in mapping_rows
        if not row["forecast_evidence_bridge_basis_row_id"]
    ]

    assert {
        row["forecast_evidence_bridge_basis_row_id"] for row in linked_mapping_rows
    } == set(basis_by_id)
    assert {row["mapping_id"] for row in unlinked_mapping_rows} == (
        allowed_unlinked_mapping_ids
    )
    for row in unlinked_mapping_rows:
        assert row["mapping_role"] == "public_context_exclusion_statement"
        assert row["eligible_statement_now"]
        assert row["blocked_statement_now"]

    for row in linked_mapping_rows:
        basis_row = basis_by_id[row["forecast_evidence_bridge_basis_row_id"]]
        assert row["component_id"] == basis_row["component_id"]
        assert (
            row["forecast_evidence_bridge_row_id"]
            == basis_row["forecast_evidence_bridge_row_id"]
        )
        for gate_field in (
            "linked_design_gate_id",
            "linked_gate_id",
            "linked_restricted_data_gate_id",
            "linked_restricted_protocol_gate_id",
        ):
            assert row[gate_field] == basis_row[gate_field]


def _assert_admission_rows_link_mapping_basis(
    candidate_rows: list[dict[str, str]],
    mapping_rows: list[dict[str, str]],
) -> None:
    mapping_by_id = {
        row["forecast_evidence_mapping_basis_row_id"]: row for row in mapping_rows
    }

    assert {row["linked_mapping_basis_row_id"] for row in candidate_rows} == set(
        mapping_by_id
    )
    for row in candidate_rows:
        mapping_row = mapping_by_id[row["linked_mapping_basis_row_id"]]
        assert row["candidate_id"] == mapping_row["mapping_id"]
        assert row["candidate_role"] == mapping_row["mapping_role"]
        assert row["component_id"] == mapping_row["component_id"]
        assert (
            row["linked_bridge_basis_row_id"]
            == mapping_row["forecast_evidence_bridge_basis_row_id"]
        )
        assert row["linked_bridge_row_id"] == mapping_row["forecast_evidence_bridge_row_id"]
        for gate_field in (
            "linked_design_gate_id",
            "linked_gate_id",
            "linked_restricted_data_gate_id",
            "linked_restricted_protocol_gate_id",
        ):
            assert row[gate_field] == mapping_row[gate_field]


def _assert_bridge_pass_review_rows_link_admission_candidates(
    review_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
) -> None:
    candidate_by_id = {
        row["forecast_evidence_admission_candidate_row_id"]: row
        for row in candidate_rows
    }

    assert {row["linked_admission_candidate_row_id"] for row in review_rows} == set(
        candidate_by_id
    )
    for row in review_rows:
        candidate_row = candidate_by_id[row["linked_admission_candidate_row_id"]]
        assert row["review_id"] == candidate_row["candidate_id"]
        assert row["review_role"] == candidate_row["candidate_role"]
        assert row["component_id"] == candidate_row["component_id"]
        for linked_field in (
            "linked_mapping_basis_row_id",
            "linked_bridge_basis_row_id",
            "linked_bridge_row_id",
            "linked_design_gate_id",
            "linked_gate_id",
            "linked_restricted_data_gate_id",
            "linked_restricted_protocol_gate_id",
        ):
            assert row[linked_field] == candidate_row[linked_field]


def test_forecast_path_ratio_scenario_registry_materializes_explicit_axes() -> None:
    rows = _rows("ratewall_forecast_path_ratio_scenario_registry.csv")
    forecast_rows = _rows("ratewall_forecast_incremental_path_ratio.csv")
    _assert_fail_closed(rows)

    assert {_scenario_key(row) for row in rows} == {
        _scenario_key(row) for row in forecast_rows
    }
    assert {row["forecast_incremental_path_ratio_row_id"] for row in rows} == {
        row["forecast_incremental_path_ratio_row_id"] for row in forecast_rows
    }
    assert {row["forecast_year"] for row in rows} == {
        row["forecast_year"] for row in forecast_rows
    }
    assert {row["channel_conversion_profile_id"] for row in rows} == {
        "conservative",
        "base",
        "demand_active",
    }
    assert {row["legacy_mpc_scenario_alias"] for row in rows} == {
        "low_mpc_5pct",
        "base_mpc_10pct",
        "high_mpc_20pct",
    }
    assert {row["mpc_scenario"] for row in rows} == {
        "low_mpc_5pct",
        "base_mpc_10pct",
        "high_mpc_20pct",
    }
    assert {row["maturity_scenario"] for row in rows} == {
        "lower_wam_faster_repricing",
        "current_wam_cbo_rate_path",
        "higher_wam_slower_repricing",
    }
    assert {row["holder_scenario"] for row in rows} == {
        "current_holder_distribution",
        "shift_to_domestic_nonbanks",
        "shift_to_banks_foreigners",
    }
    assert {row["current_demand_conversion_value"] for row in rows} == {
        "0.05",
        "0.10",
        "0.20",
    }
    assert {row["tdc_ex_overlap_current_demand_share"] for row in rows} == {
        "0.03",
        "0.07",
        "0.12",
    }
    assert {
        row["tdc_deposit_balance_current_demand_conversion_assumption"]
        for row in rows
    } == {
        "0.03",
        "0.07",
        "0.12",
    }
    assert {row["current_demand_conversion_role"] for row in rows} == {
        "channel_specific_conversion_profile_with_tdc_deposit_balance_conversion"
    }
    assert {row["tdc_path_role"] for row in rows} == {
        "tdcsim_contract_annual_tdc_full_where_mapped"
    }
    assert {row["bank_retained_margin_direct_demand_share"] for row in rows} == {
        "0.00",
        "0.01",
        "0.02",
    }
    assert {row["deposit_pass_through_materialization_status"] for row in rows} == {
        "not_separately_materialized_in_forecast_bridge"
    }

    counts_by_year = Counter(row["forecast_year"] for row in rows)
    expected_rows_per_year = (
        len({row["mpc_scenario"] for row in rows})
        * len({row["maturity_scenario"] for row in rows})
        * len({row["holder_scenario"] for row in rows})
    )
    assert set(counts_by_year.values()) == {expected_rows_per_year}


def test_forecast_path_ratio_decomposition_reconciles_direct_components() -> None:
    registry_rows = _rows("ratewall_forecast_path_ratio_scenario_registry.csv")
    decomposition_rows = _rows("ratewall_forecast_path_ratio_decomposition.csv")
    _assert_fail_closed(decomposition_rows)

    assert {row["component_id"] for row in decomposition_rows} == EXPECTED_FORECAST_COMPONENTS
    assert len(decomposition_rows) == len(registry_rows) * len(EXPECTED_FORECAST_COMPONENTS)

    registry_by_id = {
        row["forecast_incremental_path_ratio_row_id"]: row for row in registry_rows
    }
    rows_by_ratio_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in decomposition_rows:
        rows_by_ratio_id[row["forecast_incremental_path_ratio_row_id"]].append(row)

    assert set(rows_by_ratio_id) == set(registry_by_id)
    for ratio_row_id, rows in rows_by_ratio_id.items():
        assert {row["component_id"] for row in rows} == EXPECTED_FORECAST_COMPONENTS
        assert {row["component_rank_by_abs_value"] for row in rows} == {"1", "2", "3"}
        component_sum = sum(Decimal(row["component_value_bil"]) for row in rows)
        assert (
            abs(component_sum - Decimal(registry_by_id[ratio_row_id]["numerator_total_bil"]))
            <= Decimal("1e-24")
        )
    assert any(row["source_status"] == "dominant_component" for row in decomposition_rows)
    assert {row["component_assumption_parameter_name"] for row in decomposition_rows} == {
        "treasury_recipient_current_demand_share",
        "tdc_deposit_balance_current_demand_conversion_assumption",
        "bank_retained_margin_direct_demand_share",
    }


def test_forecast_path_ratio_sensitivity_and_frontier_linkage_are_deterministic() -> None:
    sensitivity_rows = _rows("ratewall_forecast_path_ratio_sensitivity_summary.csv")
    frontier_rows = _rows("ratewall_forecast_path_ratio_scenario_frontier.csv")
    yearly_frontier_rows = _rows("ratewall_forecast_incremental_path_ratio_frontier_summary.csv")
    registry_rows = _rows("ratewall_forecast_path_ratio_scenario_registry.csv")

    _assert_fail_closed(sensitivity_rows)
    _assert_fail_closed(frontier_rows)

    forecast_years = {row["forecast_year"] for row in registry_rows}
    expected_axis_value_counts = {
        "channel_conversion_profile_id": len(
            {row["channel_conversion_profile_id"] for row in registry_rows}
        ),
        "maturity_scenario": len(
            {row["maturity_scenario"] for row in registry_rows}
        ),
        "holder_scenario": len({row["holder_scenario"] for row in registry_rows}),
    }
    assert len(sensitivity_rows) == sum(
        len(forecast_years) * value_count
        for value_count in expected_axis_value_counts.values()
    )
    assert Counter(row["scenario_axis"] for row in sensitivity_rows) == {
        axis: len(forecast_years) * value_count
        for axis, value_count in expected_axis_value_counts.items()
    }

    zero_delta_rows = [
        row
        for row in sensitivity_rows
        if row["reference_scenario_registry_row_id"]
        == row["matched_scenario_registry_row_id"]
    ]
    assert {
        (row["forecast_year"], row["scenario_axis"]) for row in zero_delta_rows
    } == {
        (forecast_year, scenario_axis)
        for forecast_year in forecast_years
        for scenario_axis in expected_axis_value_counts
    }
    assert {Decimal(row["delta_ratio_vs_reference"]) for row in zero_delta_rows} == {
        Decimal("0")
    }

    registry_ids = {
        row["forecast_path_ratio_scenario_registry_row_id"] for row in registry_rows
    }
    assert {
        row["forecast_path_ratio_scenario_registry_row_id"] for row in frontier_rows
    } == registry_ids

    rows_by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in frontier_rows:
        rows_by_year[row["forecast_year"]].append(row)
    assert set(rows_by_year) == forecast_years
    expected_rows_per_year = len(registry_rows) // len(forecast_years)
    assert set(len(rows) for rows in rows_by_year.values()) == {expected_rows_per_year}
    for rows in rows_by_year.values():
        ranks = sorted(int(row["frontier_rank_within_year"]) for row in rows)
        assert ranks == list(range(1, len(rows) + 1))

    top1_by_year = {
        row["forecast_year"]: row
        for row in frontier_rows
        if row["frontier_tier"] == "closest_to_wall_top1"
    }
    assert set(top1_by_year) == forecast_years
    yearly_max_by_year = {
        row["forecast_year"]: row["maximum_row_id"] for row in yearly_frontier_rows
    }
    for year, frontier_row in top1_by_year.items():
        assert (
            frontier_row["forecast_incremental_path_ratio_row_id"]
            == yearly_max_by_year[year]
        )


def test_2d_wall_phase_diagram_uses_existing_calibrated_handles_only() -> None:
    rows = _rows("ratewall_2d_wall_phase_diagram.csv")
    _assert_fail_closed(rows)

    assert len(rows) == 9
    assert {row["base_assumption_set"] for row in rows} == {
        "literature_calibrated_base"
    }
    assert {row["base_horizon"] for row in rows} == {"1y"}
    assert {row["surface_id"] for row in rows} == {
        "debt_state_x_recipient_conversion_wall_phase"
    }
    assert {row["debt_state_source_assumption_set"] for row in rows} == {
        "literature_calibrated_low",
        "literature_calibrated_base",
        "literature_calibrated_high",
    }
    assert {row["recipient_conversion_source_assumption_set"] for row in rows} == {
        "literature_calibrated_low",
        "literature_calibrated_base",
        "literature_calibrated_high",
    }
    assert {Decimal(row["public_debt_stock_scale"]) for row in rows} == {
        Decimal("1.0"),
        Decimal("1.08"),
        Decimal("1.2"),
    }
    assert {Decimal(row["treasury_interest_demand_share"]) for row in rows} == {
        Decimal("0.05"),
        Decimal("0.12"),
        Decimal("0.25"),
    }
    assert {Decimal(row["iorb_recipient_demand_share"]) for row in rows} == {
        Decimal("0.0"),
        Decimal("0.03"),
        Decimal("0.1"),
    }
    assert {Decimal(row["on_rrp_recipient_demand_share"]) for row in rows} == {
        Decimal("0.02"),
        Decimal("0.06"),
        Decimal("0.12"),
    }
    _assert_contiguous_rank(rows, "grid_rank_by_ratio")
    for row in rows:
        ratio = Decimal(row["ratewall_ratio"])
        assert Decimal(row["iso_wall_denominator_multiplier_to_hit"]) == ratio
        assert row["hit_region_classification"] == (
            "wall_hit_region" if ratio >= Decimal("1") else "below_wall_region"
        )
        assert row["allowed_use"] == "two_dimensional_wall_phase_diagram_figure_source"
        assert row["source_status"] == (
            "pass_existing_calibrated_handles_only_no_new_parameters"
        )
        assert "new_channel_activation" in row["blocked_use"]
        assert row["claim_boundary"].endswith("not_empirical")


def test_forecast_numerator_boundary_registry_preserves_component_boundaries() -> None:
    registry_rows = _rows("ratewall_forecast_path_ratio_scenario_registry.csv")
    boundary_rows = _rows("ratewall_forecast_path_ratio_numerator_boundary_registry.csv")
    _assert_fail_closed(boundary_rows)

    registry_ids = {
        row["forecast_incremental_path_ratio_row_id"] for row in registry_rows
    }
    rows_by_ratio_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in boundary_rows:
        rows_by_ratio_id[row["forecast_incremental_path_ratio_row_id"]].append(row)

    assert set(rows_by_ratio_id) == registry_ids
    for rows in rows_by_ratio_id.values():
        assert {row["component_id"] for row in rows} == EXPECTED_FORECAST_COMPONENTS
    assert Counter(row["component_id"] for row in boundary_rows) == {
        component_id: len(registry_ids) for component_id in EXPECTED_FORECAST_COMPONENTS
    }

    bank_rows = [
        row for row in boundary_rows if row["component_id"] == "bank_retained_margin_support"
    ]
    assert {
        row["bank_margin_vs_depositor_boundary"] for row in bank_rows
    } == {"bank_retained_margin_support_not_depositor_cashflow"}
    assert {
        row["recipient_leakage_boundary_status"] for row in bank_rows
    } == {"bank_margin_proxy_kept_separate_from_depositor_cashflow"}

    tdc_rows = [
        row
        for row in boundary_rows
        if row["component_id"] == "tdc_deposit_current_demand_support"
    ]
    assert {
        row["deposit_pass_through_materialization_status"] for row in tdc_rows
    } == {"not_separately_materialized_in_forecast_bridge"}
    assert {row["tdc_overlap_identity_status"] for row in tdc_rows} == {
        "pass_ex_direct_interest_overlap_conversion_materialized"
    }
    assert all(
        "direct_interest_double_count_without_reconciliation"
        in row["blocked_interpretation"]
        for row in tdc_rows
    )


def test_forecast_interpretation_registry_distinguishes_context_from_conversion() -> None:
    boundary_rows = _rows("ratewall_forecast_path_ratio_numerator_boundary_registry.csv")
    interpretation_rows = _rows("ratewall_forecast_path_ratio_interpretation_registry.csv")
    _assert_fail_closed(interpretation_rows)

    boundary_ids = {
        row["forecast_path_ratio_numerator_boundary_row_id"] for row in boundary_rows
    }
    scenario_ids = {
        row["forecast_path_ratio_scenario_registry_row_id"] for row in boundary_rows
    }
    assert {
        row["forecast_path_ratio_numerator_boundary_row_id"] for row in interpretation_rows
    } == boundary_ids
    assert {_component_surface_key(row) for row in interpretation_rows} == {
        _component_surface_key(row) for row in boundary_rows
    }
    _assert_one_component_surface_row_per_scenario(interpretation_rows, scenario_ids)
    assert Counter(row["component_id"] for row in interpretation_rows) == {
        component_id: len(scenario_ids) for component_id in EXPECTED_FORECAST_COMPONENTS
    }

    treasury_rows = [
        row
        for row in interpretation_rows
        if row["component_id"] == "domestic_nonbank_interest_support"
    ]
    assert {
        row["source_backed_context_status"] for row in treasury_rows
    } == {
        "source_backed_holder_context_with_bucket_repricing_context_not_demand_conversion"
    }
    assert {row["linked_recipient_leakage_design_gate_id"] for row in treasury_rows} == {
        "recipient_leakage::treasury_interest"
    }
    assert {row["exact_blocker"] for row in treasury_rows} == {
        "blocked_context_only_not_demand_conversion"
    }

    bank_rows = [
        row
        for row in interpretation_rows
        if row["component_id"] == "bank_retained_margin_support"
    ]
    assert all(
        "ratewall_deposit_pricing_pass_through_context.csv"
        in row["source_context_artifacts"]
        for row in bank_rows
    )
    assert {
        row["assumption_conversion_status"] for row in bank_rows
    } == {
        "assumption_only_bank_margin_proxy_current_demand_share_preserved"
    }
    assert {row["exact_blocker"] for row in bank_rows} == {
        "blocked_context_only_not_demand_conversion"
    }

    tdc_rows = [
        row
        for row in interpretation_rows
        if row["component_id"] == "tdc_deposit_current_demand_support"
    ]
    assert {
        row["deposit_pass_through_materialization_status"] for row in tdc_rows
    } == {"not_separately_materialized_in_forecast_bridge"}
    assert {row["assumption_parameter_name"] for row in tdc_rows} == {
        "tdc_deposit_balance_current_demand_conversion"
    }
    assert {row["exact_blocker"] for row in tdc_rows} == {
        "deposit_balance_conversion_assumption_mode_and_noncanonical_beta"
    }


def test_forecast_recipient_leakage_registry_preserves_component_specific_blockers() -> None:
    interpretation_rows = _rows("ratewall_forecast_path_ratio_interpretation_registry.csv")
    leakage_rows = _rows("ratewall_forecast_path_ratio_recipient_leakage_registry.csv")
    _assert_fail_closed(leakage_rows)

    interpretation_ids = {
        row["forecast_path_ratio_interpretation_row_id"] for row in interpretation_rows
    }
    boundary_ids = {
        row["forecast_path_ratio_numerator_boundary_row_id"]
        for row in interpretation_rows
    }
    scenario_ids = {
        row["forecast_path_ratio_scenario_registry_row_id"] for row in interpretation_rows
    }
    assert {
        row["forecast_path_ratio_interpretation_row_id"] for row in leakage_rows
    } == interpretation_ids
    assert {
        row["forecast_path_ratio_numerator_boundary_row_id"] for row in leakage_rows
    } == boundary_ids
    assert {_component_surface_key(row) for row in leakage_rows} == {
        _component_surface_key(row) for row in interpretation_rows
    }
    _assert_one_component_surface_row_per_scenario(leakage_rows, scenario_ids)
    assert Counter(row["component_id"] for row in leakage_rows) == {
        component_id: len(scenario_ids) for component_id in EXPECTED_FORECAST_COMPONENTS
    }

    treasury_rows = [
        row
        for row in leakage_rows
        if row["component_id"] == "domestic_nonbank_interest_support"
    ]
    assert {row["forecast_recipient_leakage_status"] for row in treasury_rows} == {
        "source_backed_treasury_context_recipient_bridge_still_missing"
    }
    assert {row["can_narrow_demand_conversion_prior"] for row in treasury_rows} == {
        "false"
    }
    assert {
        row["timing_lag_requirement"] for row in treasury_rows
    } == {"required_before_prior_narrowing"}

    bank_rows = [
        row
        for row in leakage_rows
        if row["component_id"] == "bank_retained_margin_support"
    ]
    assert {row["forecast_recipient_leakage_status"] for row in bank_rows} == {
        "source_backed_bank_context_behavior_bridge_still_missing"
    }
    assert {
        row["demand_conversion_evidence_status"] for row in bank_rows
    } == {"blocked_no_bank_behavior_to_current_demand_conversion_bridge"}
    assert all(
        "bank behavior/pass-through bridge" in row["exact_blocker"] for row in bank_rows
    )

    tdc_rows = [
        row
        for row in leakage_rows
        if row["component_id"] == "tdc_deposit_current_demand_support"
    ]
    assert {row["forecast_recipient_leakage_status"] for row in tdc_rows} == {
        "internal_overlap_only_not_external_recipient_leakage_bridge"
    }
    assert {row["can_narrow_demand_conversion_prior"] for row in tdc_rows} == {
        "false"
    }


def test_forecast_source_specific_interpretation_registry_preserves_component_targets() -> None:
    leakage_rows = _rows("ratewall_forecast_path_ratio_recipient_leakage_registry.csv")
    rows = _rows("ratewall_forecast_path_ratio_source_specific_interpretation_registry.csv")
    _assert_fail_closed(rows)

    interpretation_ids = {
        row["forecast_path_ratio_interpretation_row_id"] for row in leakage_rows
    }
    leakage_ids = {
        row["forecast_path_ratio_recipient_leakage_row_id"] for row in leakage_rows
    }
    scenario_ids = {
        row["forecast_path_ratio_scenario_registry_row_id"] for row in leakage_rows
    }
    assert {
        row["forecast_path_ratio_interpretation_row_id"] for row in rows
    } == interpretation_ids
    assert {
        row["forecast_path_ratio_recipient_leakage_row_id"] for row in rows
    } == leakage_ids
    assert {_component_surface_key(row) for row in rows} == {
        _component_surface_key(row) for row in leakage_rows
    }
    _assert_one_component_surface_row_per_scenario(rows, scenario_ids)
    assert Counter(row["component_id"] for row in rows) == {
        component_id: len(scenario_ids) for component_id in EXPECTED_FORECAST_COMPONENTS
    }

    treasury_rows = [
        row
        for row in rows
        if row["component_id"] == "domestic_nonbank_interest_support"
    ]
    assert {row["source_specific_context_family"] for row in treasury_rows} == {
        "treasury_holder_tic_mmf_context"
    }
    assert {
        row["source_specific_interpretation_tightening_status"] for row in treasury_rows
    } == {"context_rich_but_domestic_recipient_spending_bridge_missing"}

    bank_rows = [
        row for row in rows if row["component_id"] == "bank_retained_margin_support"
    ]
    assert {row["source_specific_context_family"] for row in bank_rows} == {
        "bank_reserve_income_deposit_pricing_behavior_context"
    }
    assert {
        row["source_specific_interpretation_tightening_status"] for row in bank_rows
    } == {
        "reserve_and_deposit_pricing_context_available_but_bank_behavior_bridge_missing"
    }

    tdc_rows = [
        row
        for row in rows
        if row["component_id"] == "tdc_deposit_current_demand_support"
    ]
    assert {row["source_specific_context_family"] for row in tdc_rows} == {
        "tdc_ex_direct_interest_overlap_contract_context_only"
    }
    assert {
        row["source_specific_interpretation_tightening_status"] for row in tdc_rows
    } == {
        "tdc_ex_direct_interest_overlap_context_stable_no_current_proxy_reconciliation_target"
    }


def test_forecast_evidence_dependency_and_targeting_surfaces_prioritize_frontier_gaps() -> None:
    dependency_rows = _rows("ratewall_forecast_path_ratio_evidence_dependency_matrix.csv")
    targeting_rows = _rows("ratewall_forecast_path_ratio_evidence_targeting_registry.csv")
    work_queue_rows = _rows("ratewall_forecast_path_ratio_evidence_work_queue.csv")
    base_frontier_rows = _rows("ratewall_forecast_path_ratio_scenario_frontier.csv")
    pass_through_frontier_rows = _rows(
        "ratewall_forecast_path_ratio_pass_through_scenario_frontier.csv"
    )
    source_specific_rows = _rows(
        "ratewall_forecast_path_ratio_source_specific_interpretation_registry.csv"
    )
    _assert_fail_closed(dependency_rows)
    _assert_fail_closed(targeting_rows)
    _assert_fail_closed(work_queue_rows)

    base_top1_rows = [
        row for row in base_frontier_rows if row["frontier_tier"] == "closest_to_wall_top1"
    ]
    pass_through_top1_rows = [
        row
        for row in pass_through_frontier_rows
        if row["frontier_tier"] == "closest_to_wall_top1"
    ]
    dependency_by_frontier_id = {
        row["linked_frontier_row_id"]: row for row in dependency_rows
    }
    assert set(dependency_by_frontier_id) == {
        row["forecast_path_ratio_scenario_frontier_row_id"] for row in base_top1_rows
    } | {
        row["forecast_pass_through_scenario_frontier_row_id"]
        for row in pass_through_top1_rows
    }
    assert Counter(row["frontier_family"] for row in dependency_rows) == {
        "base_frontier_top1": len(base_top1_rows),
        "pass_through_frontier_top1": len(pass_through_top1_rows),
    }

    source_specific_by_id = {
        row["forecast_path_ratio_source_specific_interpretation_row_id"]: row
        for row in source_specific_rows
    }
    for row in dependency_rows:
        source_specific = source_specific_by_id[
            row["forecast_path_ratio_source_specific_interpretation_row_id"]
        ]
        assert row["dominant_direct_component_id"] == source_specific["component_id"]
        assert (
            row["forecast_path_ratio_recipient_leakage_row_id"]
            == source_specific["forecast_path_ratio_recipient_leakage_row_id"]
        )
        assert (
            row["source_specific_interpretation_tightening_status"]
            == source_specific["source_specific_interpretation_tightening_status"]
        )

    first_forecast_year = min(row["forecast_year"] for row in dependency_rows)
    base_first_year = next(
        row
        for row in dependency_rows
        if row["forecast_year"] == first_forecast_year
        and row["frontier_family"] == "base_frontier_top1"
    )
    assert (
        base_first_year["dominant_direct_component_id"]
        == "tdc_deposit_current_demand_support"
    )
    assert (
        base_first_year["source_specific_interpretation_tightening_status"]
        == "tdc_ex_direct_interest_overlap_context_stable_no_current_proxy_reconciliation_target"
    )
    pass_first_year = next(
        row
        for row in dependency_rows
        if row["forecast_year"] == first_forecast_year
        and row["frontier_family"] == "pass_through_frontier_top1"
    )
    assert pass_first_year["pass_through_scenario"]
    assert pass_first_year["forecast_pass_through_scenario_registry_row_id"]

    dependencies_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in dependency_rows:
        dependencies_by_component[row["dominant_direct_component_id"]].append(row)
    assert set(dependencies_by_component) <= EXPECTED_FORECAST_COMPONENTS
    assert {row["component_id"] for row in targeting_rows} == EXPECTED_FORECAST_COMPONENTS
    targeting_by_component = {row["component_id"]: row for row in targeting_rows}
    for component_id, targeting_row in targeting_by_component.items():
        component_dependency_rows = dependencies_by_component.get(component_id, [])
        base_rows = [
            row
            for row in component_dependency_rows
            if row["frontier_family"] == "base_frontier_top1"
        ]
        pass_through_rows = [
            row
            for row in component_dependency_rows
            if row["frontier_family"] == "pass_through_frontier_top1"
        ]
        dependency_years = sorted(
            {row["forecast_year"] for row in component_dependency_rows}
        )
        assert targeting_row["base_frontier_dependency_year_count"] == str(
            len({row["forecast_year"] for row in base_rows})
        )
        assert targeting_row["pass_through_frontier_dependency_year_count"] == str(
            len({row["forecast_year"] for row in pass_through_rows})
        )
        assert targeting_row["total_frontier_dependency_row_count"] == str(
            len(component_dependency_rows)
        )
        assert targeting_row["frontier_dependency_years"] == ";".join(dependency_years)

    treasury_target = next(
        row
        for row in targeting_rows
        if row["component_id"] == "domestic_nonbank_interest_support"
    )
    assert treasury_target["dependency_actionability_status"] == (
        "frontier_binding_source_upgrade_target"
    )
    bank_target = next(
        row for row in targeting_rows if row["component_id"] == "bank_retained_margin_support"
    )
    assert bank_target["dependency_actionability_status"] == (
        "not_current_frontier_but_still_forecast_relevant"
    )
    tdc_target = next(
        row
        for row in targeting_rows
        if row["component_id"] == "tdc_deposit_current_demand_support"
    )
    assert tdc_target["dependency_actionability_status"] == "boundary_maintenance_only"

    targeting_ids = {
        row["forecast_path_ratio_evidence_targeting_row_id"] for row in targeting_rows
    }
    assert {
        row["forecast_path_ratio_evidence_targeting_row_id"] for row in work_queue_rows
    } == targeting_ids
    assert {row["component_id"] for row in work_queue_rows} == set(targeting_by_component)
    assert sorted(int(row["queue_rank"]) for row in work_queue_rows) == list(
        range(1, len(work_queue_rows) + 1)
    )
    assert work_queue_rows[0]["component_id"] == "domestic_nonbank_interest_support"
    assert work_queue_rows[-1]["component_id"] == "tdc_deposit_current_demand_support"


def test_forecast_bridge_packets_preserve_treasury_first_bank_second_evidence_targets() -> None:
    treasury_rows = _rows("ratewall_forecast_treasury_recipient_bridge_packet.csv")
    treasury_source_target_rows = _rows(
        "ratewall_forecast_treasury_recipient_source_targeting_matrix.csv"
    )
    bank_rows = _rows("ratewall_forecast_bank_behavior_bridge_packet.csv")
    targeting_rows = _rows("ratewall_forecast_path_ratio_evidence_targeting_registry.csv")
    work_queue_rows = _rows("ratewall_forecast_path_ratio_evidence_work_queue.csv")
    _assert_fail_closed(treasury_rows)
    _assert_fail_closed(treasury_source_target_rows)
    _assert_fail_closed(bank_rows)

    targeting_by_component = {row["component_id"]: row for row in targeting_rows}
    work_queue_by_component = {row["component_id"]: row for row in work_queue_rows}
    treasury_targeting = targeting_by_component["domestic_nonbank_interest_support"]
    treasury_work_queue = work_queue_by_component["domestic_nonbank_interest_support"]
    bank_targeting = targeting_by_component["bank_retained_margin_support"]
    bank_work_queue = work_queue_by_component["bank_retained_margin_support"]
    treasury_packet_by_id = {
        row["forecast_evidence_bridge_packet_row_id"]: row for row in treasury_rows
    }
    assert {
        row["forecast_path_ratio_evidence_targeting_row_id"] for row in treasury_rows
    } == {treasury_targeting["forecast_path_ratio_evidence_targeting_row_id"]}
    assert {
        row["forecast_path_ratio_evidence_work_queue_row_id"] for row in treasury_rows
    } == {treasury_work_queue["forecast_path_ratio_evidence_work_queue_row_id"]}
    assert {
        row["linked_bridge_packet_row_id"] for row in treasury_source_target_rows
    } <= set(treasury_packet_by_id)
    for row in treasury_source_target_rows:
        linked_packet = treasury_packet_by_id[row["linked_bridge_packet_row_id"]]
        assert row["linked_packet_step_id"] == linked_packet["packet_step_id"]
        assert row["source_row_origin"] == linked_packet["source_row_origin"]
    assert Counter(row["source_row_origin"] for row in treasury_rows) == Counter(
        row["source_row_origin"] for row in treasury_source_target_rows
    )
    assert sorted(int(row["source_target_rank"]) for row in treasury_source_target_rows) == list(
        range(1, len(treasury_source_target_rows) + 1)
    )
    assert sorted({int(row["packet_step_rank"]) for row in treasury_rows}) == list(
        range(1, max(int(row["packet_step_rank"]) for row in treasury_rows) + 1)
    )

    assert {
        row["forecast_path_ratio_evidence_targeting_row_id"] for row in bank_rows
    } == {bank_targeting["forecast_path_ratio_evidence_targeting_row_id"]}
    assert {
        row["forecast_path_ratio_evidence_work_queue_row_id"] for row in bank_rows
    } == {bank_work_queue["forecast_path_ratio_evidence_work_queue_row_id"]}
    assert sorted(int(row["packet_step_rank"]) for row in bank_rows) == list(
        range(1, len(bank_rows) + 1)
    )
    assert {row["source_row_origin"] for row in bank_rows} == {
        "evidence_targeting_summary",
        "interest_recipient_evidence_gap",
        "recipient_leakage_design_gate",
    }

    treasury_summary = treasury_rows[0]
    assert treasury_summary["packet_family"] == "treasury_recipient_bridge_packet"
    assert treasury_summary["component_id"] == "domestic_nonbank_interest_support"
    assert treasury_summary["current_frontier_binding_status"] == (
        "frontier_binding_source_upgrade_target"
    )
    assert treasury_summary["next_backend_action"] == (
        "build_treasury_beneficial_owner_and_domestic_recipient_bridge_packet"
    )
    assert (
        treasury_summary["frontier_dependency_years"]
        == treasury_targeting["frontier_dependency_years"]
    )
    foreign_context_row = next(
        row
        for row in treasury_rows
        if row["packet_step_id"] == "foreign_holder_leakage_context"
    )
    assert (
        foreign_context_row["bridge_packet_status"]
        == "context_only_source_gate_row_preserved"
    )
    assert "domestic/foreign" in foreign_context_row[
        "evidence_needed_before_prior_narrowing"
    ]
    design_gate_row = next(
        row
        for row in treasury_rows
        if row["source_row_origin"] == "recipient_leakage_design_gate"
    )
    assert design_gate_row["bridge_packet_status"] == (
        "design_gate_fail_closed_requirement_preserved"
    )
    assert design_gate_row["source_status"] == (
        "recipient_leakage_design_gate_context_only"
    )
    assert {
        row["source_target_id"] for row in treasury_source_target_rows
    } >= {
        "tdcest_interest_outlay_cashflow_basis",
        "z1_domestic_private_holder_context",
        "tic_foreign_leakage_context",
        "mmf_treasury_and_repo_portfolio_context",
        "tdcsim_private_bucket_funding_route_gap",
    }
    tdcest_target = next(
        row
        for row in treasury_source_target_rows
        if row["source_target_id"] == "tdcest_interest_outlay_cashflow_basis"
    )
    assert tdcest_target["next_backend_action"] == (
        "use_tdcest_interest_outlays_as_gross_cashflow_basis_for_best_proxy"
    )
    z1_target = next(
        row
        for row in treasury_source_target_rows
        if row["source_target_id"] == "z1_domestic_private_holder_context"
    )
    assert (
        "ratewall_tdcest_z1_domestic_nonbank_sector_context.csv"
        in z1_target["source_artifact"]
    )
    assert "Z.1 sector-route context" in z1_target["what_it_can_resolve"]
    mmf_target = next(
        row
        for row in treasury_source_target_rows
        if row["source_target_id"] == "mmf_treasury_and_repo_portfolio_context"
    )
    assert "ratewall_tdcest_mmf_route_split_context.csv" in mmf_target[
        "source_artifact"
    ]
    tdcsim_gap = next(
        row
        for row in treasury_source_target_rows
        if row["source_target_id"] == "tdcsim_private_bucket_funding_route_gap"
    )
    assert tdcsim_gap["current_evidence_status"] == (
        "blocked_missing_explicit_non_deposit_funded_domestic_nonbank_bucket"
    )
    assert "ratewall_tdcest_monetary_route_bridge.csv" in tdcsim_gap[
        "source_artifact"
    ]
    assert "route-context evidence" in tdcsim_gap["what_it_can_resolve"]
    assert tdcsim_gap["next_backend_action"] == (
        "use_linked_tdcest_route_context_to_keep_private_bucket_split_"
        "quantified_but_fail_closed_until_source_backed_tdcsim_bucket_"
        "mapping_exists"
    )
    assert "welfare_incidence_claims" in tdcsim_gap["blocked_use"]

    bank_summary = bank_rows[0]
    assert bank_summary["packet_family"] == "bank_behavior_bridge_packet"
    assert bank_summary["component_id"] == "bank_retained_margin_support"
    assert bank_summary["current_frontier_binding_status"] == (
        "not_current_frontier_but_still_forecast_relevant"
    )
    assert bank_summary["next_backend_action"] == (
        "build_bank_retention_distribution_credit_supply_bridge_packet"
    )
    evidence_gap_row = next(
        row
        for row in bank_rows
        if row["source_row_origin"] == "interest_recipient_evidence_gap"
    )
    assert (
        evidence_gap_row["missing_evidence_family"]
        == "context_available_but_no_component_specific_demand_conversion_bridge"
    )
    design_gate_row = next(
        row
        for row in bank_rows
        if row["source_row_origin"] == "recipient_leakage_design_gate"
    )
    assert "bank behavior/pass-through bridge" in design_gate_row["exact_blocker"]


def test_forecast_stage_bridges_remain_fail_closed_and_link_to_basis_rows() -> None:
    treasury_packet_rows = _rows("ratewall_forecast_treasury_recipient_bridge_packet.csv")
    treasury_source_target_rows = _rows(
        "ratewall_forecast_treasury_recipient_source_targeting_matrix.csv"
    )
    treasury_rows = _rows(
        "ratewall_forecast_treasury_beneficial_owner_recipient_bridge.csv"
    )
    treasury_best_proxy_rows = _rows(
        "ratewall_forecast_treasury_recipient_best_proxy_basis.csv"
    )
    treasury_best_proxy_review_rows = _rows(
        "ratewall_forecast_treasury_recipient_best_proxy_admission_review.csv"
    )
    treasury_best_proxy_calculation_rows = _rows(
        "ratewall_forecast_treasury_recipient_best_proxy_calculation_scaffold.csv"
    )
    treasury_best_proxy_gate_rows = _rows(
        "ratewall_forecast_treasury_recipient_best_proxy_gate_review.csv"
    )
    treasury_current_demand_contract_rows = _rows(
        "ratewall_forecast_treasury_recipient_current_demand_evidence_contract.csv"
    )
    bank_packet_rows = _rows("ratewall_forecast_bank_behavior_bridge_packet.csv")
    bank_rows = _rows("ratewall_forecast_bank_behavior_distribution_bridge.csv")
    bank_current_demand_contract_rows = _rows(
        "ratewall_forecast_bank_behavior_current_demand_evidence_contract.csv"
    )
    _assert_fail_closed(treasury_rows)
    _assert_fail_closed(treasury_best_proxy_rows)
    _assert_fail_closed(treasury_best_proxy_review_rows)
    _assert_fail_closed(treasury_best_proxy_calculation_rows)
    _assert_fail_closed(treasury_best_proxy_gate_rows)
    _assert_fail_closed(treasury_current_demand_contract_rows)
    _assert_fail_closed(bank_rows)
    _assert_fail_closed(bank_current_demand_contract_rows)

    treasury_packet_ids = {
        row["forecast_evidence_bridge_packet_row_id"] for row in treasury_packet_rows
    }
    treasury_source_target_ids = {
        row["forecast_treasury_recipient_source_targeting_row_id"]
        for row in treasury_source_target_rows
    }
    treasury_bridge_by_id = {
        row["forecast_evidence_bridge_row_id"]: row for row in treasury_rows
    }
    assert {
        row["forecast_evidence_bridge_packet_row_id"] for row in treasury_rows
    } <= treasury_packet_ids
    assert sorted(int(row["bridge_stage_rank"]) for row in treasury_rows) == list(
        range(1, len(treasury_rows) + 1)
    )

    for row in treasury_best_proxy_rows:
        bridge_row = treasury_bridge_by_id[row["linked_bridge_row_id"]]
        assert row["linked_source_targeting_row_id"] in treasury_source_target_ids
        assert row["linked_bridge_stage_id"] == bridge_row["bridge_stage_id"]
    assert sorted(int(row["proxy_step_rank"]) for row in treasury_best_proxy_rows) == list(
        range(1, len(treasury_best_proxy_rows) + 1)
    )

    best_proxy_by_id = {
        row["forecast_treasury_recipient_best_proxy_basis_row_id"]: row
        for row in treasury_best_proxy_rows
    }
    assert {
        row["linked_best_proxy_basis_row_id"]
        for row in treasury_best_proxy_review_rows
    } == set(best_proxy_by_id)
    for row in treasury_best_proxy_review_rows:
        best_proxy_row = best_proxy_by_id[row["linked_best_proxy_basis_row_id"]]
        assert row["linked_source_targeting_row_id"] == best_proxy_row[
            "linked_source_targeting_row_id"
        ]
        assert row["linked_bridge_row_id"] == best_proxy_row["linked_bridge_row_id"]
        assert row["linked_bridge_stage_id"] == best_proxy_row["linked_bridge_stage_id"]
    assert sorted(
        int(row["review_rank"]) for row in treasury_best_proxy_review_rows
    ) == list(range(1, len(treasury_best_proxy_review_rows) + 1))

    review_by_id = {
        row["forecast_treasury_recipient_best_proxy_admission_review_row_id"]: row
        for row in treasury_best_proxy_review_rows
    }
    assert {
        row["linked_admission_review_row_id"]
        for row in treasury_best_proxy_calculation_rows
    } == set(review_by_id)
    for row in treasury_best_proxy_calculation_rows:
        review_row = review_by_id[row["linked_admission_review_row_id"]]
        assert row["linked_bridge_row_id"] == review_row["linked_bridge_row_id"]
        assert row["linked_bridge_stage_id"] == review_row["linked_bridge_stage_id"]
    assert sorted(
        int(row["calculation_step_rank"])
        for row in treasury_best_proxy_calculation_rows
    ) == list(range(1, len(treasury_best_proxy_calculation_rows) + 1))

    calculation_by_id = {
        row["forecast_treasury_recipient_best_proxy_calculation_scaffold_row_id"]: row
        for row in treasury_best_proxy_calculation_rows
    }
    assert {
        row["linked_calculation_scaffold_row_id"]
        for row in treasury_best_proxy_gate_rows
    } == set(calculation_by_id)
    for row in treasury_best_proxy_gate_rows:
        calculation_row = calculation_by_id[row["linked_calculation_scaffold_row_id"]]
        assert row["linked_admission_review_row_id"] == calculation_row[
            "linked_admission_review_row_id"
        ]
        assert row["linked_bridge_row_id"] == calculation_row["linked_bridge_row_id"]
        assert row["linked_bridge_stage_id"] == calculation_row["linked_bridge_stage_id"]
        assert row["gate_review_id"] == calculation_row["calculation_step_id"]
    assert sorted(
        int(row["gate_review_rank"]) for row in treasury_best_proxy_gate_rows
    ) == list(range(1, len(treasury_best_proxy_gate_rows) + 1))

    gate_by_id = {
        row["forecast_treasury_recipient_best_proxy_gate_review_row_id"]: row
        for row in treasury_best_proxy_gate_rows
    }
    assert {
        row["linked_gate_review_row_id"] for row in treasury_current_demand_contract_rows
    } == set(gate_by_id)
    for row in treasury_current_demand_contract_rows:
        gate_row = gate_by_id[row["linked_gate_review_row_id"]]
        assert row["linked_calculation_scaffold_row_id"] == gate_row[
            "linked_calculation_scaffold_row_id"
        ]
        assert row["linked_bridge_row_id"] == gate_row["linked_bridge_row_id"]
        assert row["linked_bridge_packet_row_id"] in treasury_packet_ids
    assert sorted(
        int(row["contract_rank"]) for row in treasury_current_demand_contract_rows
    ) == list(range(1, len(treasury_current_demand_contract_rows) + 1))

    bank_packet_ids = {
        row["forecast_evidence_bridge_packet_row_id"] for row in bank_packet_rows
    }
    bank_bridge_by_id = {
        row["forecast_evidence_bridge_row_id"]: row for row in bank_rows
    }
    assert {
        row["forecast_evidence_bridge_packet_row_id"] for row in bank_rows
    } <= bank_packet_ids
    assert sorted(int(row["bridge_stage_rank"]) for row in bank_rows) == list(
        range(1, len(bank_rows) + 1)
    )
    assert {
        row["linked_bank_bridge_row_id"] for row in bank_current_demand_contract_rows
    } == {
        bridge_id
        for bridge_id, row in bank_bridge_by_id.items()
        if row["bridge_stage_id"] != "bridge_summary"
    }
    for row in bank_current_demand_contract_rows:
        bridge_row = bank_bridge_by_id[row["linked_bank_bridge_row_id"]]
        assert row["linked_bridge_packet_row_id"] in bank_packet_ids
        assert row["linked_bridge_stage_id"] == bridge_row["bridge_stage_id"]
    assert sorted(
        int(row["contract_rank"]) for row in bank_current_demand_contract_rows
    ) == list(range(1, len(bank_current_demand_contract_rows) + 1))

    treasury_basis = next(
        row for row in treasury_rows if row["bridge_stage_id"] == "gross_cashflow_basis"
    )
    assert treasury_basis["bridge_family"] == (
        "treasury_beneficial_owner_recipient_bridge"
    )
    assert treasury_basis["current_assumption_share"] == "0.12"
    assert treasury_basis["gross_cashflow_bil"] == "149.5040974002044000"
    assert treasury_basis["bridge_stage_status"] == (
        "assumption_mode_basis_preserved_until_bridge_passes"
    )

    treasury_design_gate = next(
        row for row in treasury_rows if row["bridge_stage_id"] == "design_gate_closeout"
    )
    assert treasury_design_gate["linked_design_gate_id"] == (
        "recipient_leakage::treasury_interest"
    )
    assert treasury_design_gate["bridge_stage_status"] == "fail_closed_design_gate"
    best_proxy_cashflow = next(
        row
        for row in treasury_best_proxy_rows
        if row["proxy_step_id"] == "tdcest_gross_interest_cashflow_basis"
    )
    assert best_proxy_cashflow["proxy_formula_role"] == (
        "gross_treasury_interest_cashflow_bil"
    )
    assert best_proxy_cashflow["current_best_proxy_status"] == (
        "basis_usable_for_noncanonical_best_proxy"
    )
    assert best_proxy_cashflow["linked_bridge_stage_id"] == "gross_cashflow_basis"
    z1_best_proxy = next(
        row
        for row in treasury_best_proxy_rows
        if row["proxy_step_id"] == "z1_domestic_private_holder_stock_context"
    )
    assert (
        "ratewall_tdcest_z1_domestic_nonbank_sector_context.csv"
        in z1_best_proxy["current_public_artifacts"]
    )
    mmf_best_proxy = next(
        row
        for row in treasury_best_proxy_rows
        if row["proxy_step_id"] == "mmf_portfolio_intermediation_context"
    )
    assert "ratewall_tdcest_mmf_route_split_context.csv" in mmf_best_proxy[
        "current_public_artifacts"
    ]
    tdcsim_proxy_gap = next(
        row
        for row in treasury_best_proxy_rows
        if row["proxy_step_id"] == "tdcsim_private_bucket_funding_route_gap"
    )
    assert tdcsim_proxy_gap["current_best_proxy_status"] == (
        "contract_gap_documented_not_usable_for_proxy_math"
    )
    assert "deposit_funding_route_claims" in tdcsim_proxy_gap["blocked_proxy_use"]
    cashflow_review = next(
        row
        for row in treasury_best_proxy_review_rows
        if row["review_step_id"] == "tdcest_gross_interest_cashflow_basis"
    )
    assert cashflow_review["current_best_proxy_admission_status"] == (
        "admitted_as_noncanonical_best_proxy_cashflow_basis_only"
    )
    assert cashflow_review["calculation_scaffold_status"] == (
        "can_feed_future_noncanonical_calculation_scaffold"
    )
    assert cashflow_review["prior_narrowing_status"] == (
        "blocked_until_recipient_current_demand_bridge_passes"
    )
    tdcsim_gap_review = next(
        row
        for row in treasury_best_proxy_review_rows
        if row["review_step_id"] == "tdcsim_private_bucket_funding_route_gap"
    )
    assert tdcsim_gap_review["current_best_proxy_admission_status"] == (
        "not_admitted_missing_contract_bucket_or_route"
    )
    assert tdcsim_gap_review["calculation_scaffold_status"] == (
        "calculation_scaffold_blocked_by_tdcsim_contract_gap"
    )
    assert "welfare_incidence_claims" in tdcsim_gap_review["blocked_use"]
    calculation_cashflow = next(
        row
        for row in treasury_best_proxy_calculation_rows
        if row["calculation_step_id"] == "gross_tdcest_interest_outlay_input"
    )
    assert calculation_cashflow["preliminary_amount_bil"] == "149.5040974002044000"
    assert calculation_cashflow["calculation_scaffold_status"] == (
        "scaffold_amount_available_noncanonical"
    )
    conversion_gate = next(
        row
        for row in treasury_best_proxy_calculation_rows
        if row["calculation_step_id"] == "recipient_current_demand_conversion_gate"
    )
    assert conversion_gate["preliminary_amount_bil"] == ""
    assert conversion_gate["calculation_scaffold_status"] == (
        "calculation_amount_blocked_until_bridge_pass_review"
    )
    tdcsim_calculation_gap = next(
        row
        for row in treasury_best_proxy_calculation_rows
        if row["calculation_step_id"] == "tdcsim_private_bucket_route_gap"
    )
    assert tdcsim_calculation_gap["calculation_scaffold_status"] == (
        "calculation_amount_blocked_by_tdcsim_route_gap"
    )
    cashflow_gate = next(
        row
        for row in treasury_best_proxy_gate_rows
        if row["gate_review_id"] == "gross_tdcest_interest_outlay_input"
    )
    assert cashflow_gate["bridge_pass_status"] == (
        "pass_cashflow_basis_only_noncanonical"
    )
    assert cashflow_gate["current_demand_gate_status"] == (
        "fail_current_demand_conversion_gate"
    )
    conversion_gate_review = next(
        row
        for row in treasury_best_proxy_gate_rows
        if row["gate_review_id"] == "recipient_current_demand_conversion_gate"
    )
    assert conversion_gate_review["bridge_pass_status"] == (
        "fail_bridge_pass_current_demand_gate_missing"
    )
    assert conversion_gate_review["prior_narrowing_status"] == (
        "blocked_no_prior_narrowing_or_canonical_promotion"
    )
    treasury_cashflow_contract = next(
        row
        for row in treasury_current_demand_contract_rows
        if row["evidence_contract_id"] == "tdcest_gross_cashflow_basis_contract"
    )
    assert treasury_cashflow_contract["linked_gate_review_row_id"] == cashflow_gate[
        "forecast_treasury_recipient_best_proxy_gate_review_row_id"
    ]
    assert treasury_cashflow_contract["current_basis_status"] == (
        "source_backed_cashflow_basis_available"
    )
    assert treasury_cashflow_contract["current_demand_evidence_status"] == (
        "blocked_no_recipient_current_demand_bridge"
    )
    assert treasury_cashflow_contract["current_contract_outcome"] == (
        "fail_closed_cashflow_basis_only"
    )
    assert treasury_cashflow_contract["current_public_basis_artifacts"] == (
        "ratewall_interest_recipient_leakage_evidence_gap.csv;"
        "ratewall_interest_recipient_leakage_bridge.csv"
    )
    assert treasury_cashflow_contract["current_public_basis_trace_status"] == (
        "pass_current_public_basis_trace_available"
    )
    assert treasury_cashflow_contract["current_public_basis_amount_bil"] == (
        "149.5040974002044000"
    )
    assert treasury_cashflow_contract["current_public_basis_value_status"] == (
        "pass_source_backed_cashflow_amount_available"
    )
    assert treasury_cashflow_contract["required_unit_of_observation"] == (
        "recipient_route_quarter_or_year"
    )
    assert "institutional_retention_share" in treasury_cashflow_contract[
        "required_schema_fields"
    ]
    assert treasury_cashflow_contract["missing_bridge_scope"] == (
        "no_source_backed_mapping_from_tdcest_gross_interest_cashflow_to_final_recipient_current_demand"
    )
    assert (
        "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv"
        in treasury_cashflow_contract["best_available_proxy_artifacts"]
    )
    assert treasury_cashflow_contract["best_available_proxy_status"] == (
        "proxy_available_noncanonical_cashflow_and_route_context_only"
    )
    assert "interest_weighted_holder_denominator" in treasury_cashflow_contract[
        "assumption_or_missing_fields_blocking_admission"
    ]
    assert treasury_cashflow_contract["next_acquisition_target"] == (
        "source_backed_interest_weighted_final_recipient_bridge_for_treasury_interest_cashflows"
    )
    assert treasury_cashflow_contract["source_acquisition_execution_status"] == (
        "executed_public_sec_nmfp_mspd_cusip_overlap_path_context_only_no_current_demand_admission"
    )
    assert treasury_cashflow_contract["strongest_source_owned_candidate"] == (
        "sec_nmfp_mspd_cusip_overlap_intermediary_coverage_gate_not_final_recipient_denominator"
    )
    assert "matched_cusip_count=93" in treasury_cashflow_contract[
        "strongest_candidate_latest_values"
    ]
    assert "matched_principal_bil=6086.8251714" in treasury_cashflow_contract[
        "strongest_candidate_latest_values"
    ]
    assert treasury_cashflow_contract["strongest_candidate_admission_status"] == (
        "not_admitted_non_final_cusip_overlap_requires_final_owner_mapping_tax_mpc_and_current_demand_timing"
    )
    assert "replace_not_stack" in treasury_cashflow_contract[
        "nonadditivity_guardrail"
    ]
    assert "canonical_rw_y" in treasury_cashflow_contract["blocked_use"]
    treasury_z1_contract = next(
        row
        for row in treasury_current_demand_contract_rows
        if row["evidence_contract_id"] == "domestic_private_recipient_share_contract"
    )
    assert "ratewall_tdcest_z1_domestic_nonbank_sector_context.csv" in (
        treasury_z1_contract["current_public_basis_artifacts"]
    )
    assert treasury_z1_contract["current_public_basis_value_status"] == (
        "context_scaffold_available_noncanonical"
    )
    assert "final_recipient_class" in treasury_z1_contract["required_schema_fields"]
    assert treasury_z1_contract["best_available_proxy_status"] == (
        "proxy_available_sector_context_not_final_recipient_split"
    )
    assert treasury_z1_contract["next_acquisition_target"] == (
        "source_backed_interest_weighted_holder_denominator_by_domestic_private_route"
    )
    assert treasury_z1_contract["source_acquisition_execution_status"] == (
        "executed_public_sec_nmfp_mspd_cusip_overlap_path_context_only_no_current_demand_admission"
    )
    treasury_conversion_contract = next(
        row
        for row in treasury_current_demand_contract_rows
        if row["evidence_contract_id"] == (
            "recipient_current_demand_conversion_contract"
        )
    )
    assert treasury_conversion_contract["current_contract_outcome"] == (
        "fail_closed_current_demand_gate"
    )
    assert (
        "material_recipient_current_demand_bridge"
        in treasury_conversion_contract["admissible_evidence_required"]
    )
    assert treasury_conversion_contract["strongest_source_owned_candidate"] == (
        "holder_allocation_gate_final_owner_mapping_readiness_blocked"
    )
    assert "status=blocked_not_enabled" in treasury_conversion_contract[
        "strongest_candidate_latest_values"
    ]
    treasury_mmf_contract = next(
        row
        for row in treasury_current_demand_contract_rows
        if row["evidence_contract_id"] == "mmf_intermediation_route_contract"
    )
    assert "ratewall_tdcest_mmf_route_split_context.csv" in (
        treasury_mmf_contract["current_public_basis_artifacts"]
    )
    assert "on_rrp_reserve_user_like_route" in treasury_mmf_contract[
        "required_schema_fields"
    ]
    assert treasury_mmf_contract["best_available_proxy_status"] == (
        "proxy_available_mmf_portfolio_context_not_final_investor_bridge"
    )
    assert "final_investor_class" in treasury_mmf_contract[
        "next_acquisition_required_fields"
    ]
    assert treasury_mmf_contract["source_acquisition_execution_status"] == (
        "executed_public_sec_nmfp_ofr_mmf_context_path_context_only_no_final_investor_admission"
    )
    assert "direct{status=non_final_reconciled_context" in treasury_mmf_contract[
        "strongest_candidate_latest_values"
    ]
    treasury_tdcsim_contract = next(
        row
        for row in treasury_current_demand_contract_rows
        if row["evidence_contract_id"] == "tdcsim_route_specific_bucket_contract"
    )
    assert treasury_tdcsim_contract["current_demand_evidence_status"] == (
        "blocked_missing_non_deposit_domestic_nonbank_route"
    )
    assert treasury_tdcsim_contract["current_public_basis_value_status"] == (
        "calculation_amount_blocked_by_tdcsim_route_gap"
    )
    assert treasury_tdcsim_contract["required_unit_of_observation"] == (
        "tdcsim_holder_route_contract"
    )
    assert treasury_tdcsim_contract["admissible_evidence_required"] == (
        "source_backed_split_from_current_tdcsim_private_bucket_to_non_deposit_funded_domestic_nonbank_and_mmf_on_rrp_reserve_user_like_routes"
    )
    assert treasury_tdcsim_contract["best_available_proxy_status"] == (
        "route_contracts_present_but_source_backed_private_bucket_split_missing"
    )
    assert "source_backed_private_bucket_split" in treasury_tdcsim_contract[
        "assumption_or_missing_fields_blocking_admission"
    ]
    assert treasury_tdcsim_contract["source_acquisition_execution_status"] == (
        "executed_sibling_tdcsim_route_contract_path_target_contracts_present_private_split_missing"
    )
    assert treasury_tdcsim_contract["strongest_source_owned_candidate"] == (
        "tdcsim_target_route_contracts_present_but_private_bucket_source_split_missing"
    )
    assert "target_mmf_on_rrp=requires_source_backed_mmf_on_rrp_route_split" in (
        treasury_tdcsim_contract["strongest_candidate_latest_values"]
    )
    assert "holder_allocation" in treasury_tdcsim_contract["blocked_use"]

    bank_basis = next(
        row for row in bank_rows if row["bridge_stage_id"] == "gross_cashflow_basis"
    )
    assert bank_basis["bridge_family"] == "bank_behavior_distribution_bridge"
    assert bank_basis["current_assumption_share"] == "0.03"
    assert bank_basis["gross_cashflow_bil"] == "30.3258800"

    bank_context = next(
        row
        for row in bank_rows
        if row["bridge_stage_id"] == "bank_nim_credit_supply_context"
    )
    assert bank_context["available_context_artifacts"] == (
        "ratewall_bank_nim_credit_supply_context.csv"
    )
    assert bank_context["bridge_stage_status"] == (
        "context_sidecar_not_component_bridge"
    )

    bank_design_gate = next(
        row for row in bank_rows if row["bridge_stage_id"] == "design_gate_closeout"
    )
    assert "bank behavior/pass-through bridge" in bank_design_gate["exact_blocker"]
    bank_cashflow_contract = next(
        row
        for row in bank_current_demand_contract_rows
        if row["evidence_contract_id"] == "gross_iorb_cashflow_basis_contract"
    )
    assert bank_cashflow_contract["linked_bank_bridge_row_id"] == bank_basis[
        "forecast_evidence_bridge_row_id"
    ]
    assert bank_cashflow_contract["current_contract_outcome"] == (
        "fail_closed_cashflow_basis_only"
    )
    assert "ratewall_deposit_pricing_pass_through_context.csv" in bank_cashflow_contract[
        "current_public_basis_artifacts"
    ]
    assert "WRESBAL" in bank_cashflow_contract["current_public_basis_series_ids"]
    assert bank_cashflow_contract["current_public_basis_trace_status"] == (
        "pass_current_public_basis_trace_available"
    )
    assert bank_cashflow_contract["current_public_basis_latest_quarter"] == "2026Q2"
    assert bank_cashflow_contract["current_public_basis_value_status"] == (
        "pass_latest_deposit_pricing_context_values_available"
    )
    assert "deposit_rate_gap_to_fed_funds_pct=-3.26" in bank_cashflow_contract[
        "current_public_basis_latest_metric_summary"
    ]
    assert bank_cashflow_contract["required_unit_of_observation"] == (
        "bank_quarter_or_bank_product_month"
    )
    assert "reserve_income_cashflow" in bank_cashflow_contract[
        "required_schema_fields"
    ]
    assert "ratewall_tdc_rolling_pass_through_context.csv" in bank_cashflow_contract[
        "best_available_proxy_artifacts"
    ]
    assert bank_cashflow_contract["best_available_proxy_status"] == (
        "proxy_available_cashflow_and_pricing_context_not_recipient_timing"
    )
    assert "current_demand_timing" in bank_cashflow_contract[
        "assumption_or_missing_fields_blocking_admission"
    ]
    assert bank_cashflow_contract["source_acquisition_execution_status"] == (
        "executed_public_and_sibling_bank_pass_through_pricing_timing_context_no_current_demand_admission"
    )
    assert bank_cashflow_contract["strongest_source_owned_candidate"] == (
        "rolling_tdc_deposit_pass_through_and_deposit_pricing_context_not_retained_margin_current_demand_bridge"
    )
    assert "rolling_window_end_quarter=2026Q2" in bank_cashflow_contract[
        "strongest_candidate_latest_values"
    ]
    assert "rolling_deposit_pass_through_share=0.5307509589554447" in (
        bank_cashflow_contract["strongest_candidate_latest_values"]
    )
    assert "timing_evidence_needed=bank IORB pass-through and credit-supply behavior bridge" in (
        bank_cashflow_contract["strongest_candidate_latest_values"]
    )
    assert bank_cashflow_contract["strongest_candidate_admission_status"] == (
        "not_admitted_pass_through_and_pricing_context_lacks_retained_margin_recipient_cashflow_and_current_demand_timing"
    )
    assert "nonadditivity" in bank_cashflow_contract["nonadditivity_guardrail"]
    assert "depositor_cashflow" in bank_cashflow_contract["blocked_use"]
    bank_pricing_contract = next(
        row
        for row in bank_current_demand_contract_rows
        if row["evidence_contract_id"] == "reserve_deposit_pricing_context_contract"
    )
    assert "ratewall_deposit_pricing_pass_through_context.csv" in bank_pricing_contract[
        "current_public_basis_artifacts"
    ]
    assert "DPSACBW027SBOG" in bank_pricing_contract[
        "current_public_basis_series_ids"
    ]
    assert bank_pricing_contract["current_public_basis_latest_quarter"] == "2026Q2"
    assert "savings_deposit_rate_pct=0.38" in bank_pricing_contract[
        "current_public_basis_latest_metric_summary"
    ]
    assert "realized_yield" in bank_pricing_contract["required_schema_fields"]
    assert bank_pricing_contract["next_acquisition_target"] == (
        "source_backed_deposit_product_or_bank_panel_linking_pass_through_retention_and_spending_timing"
    )
    assert bank_pricing_contract["source_acquisition_execution_status"] == (
        "executed_public_and_sibling_bank_pass_through_pricing_timing_context_no_current_demand_admission"
    )
    bank_intermediation_contract = next(
        row
        for row in bank_current_demand_contract_rows
        if row["evidence_contract_id"] == "bank_intermediation_context_contract"
    )
    assert bank_intermediation_contract["strongest_source_owned_candidate"] == (
        "bank_nim_credit_supply_tdcpass_borrower_and_fdic_retention_route_context_not_cashflow_bridge"
    )
    assert bank_intermediation_contract["source_acquisition_execution_status"] == (
        "executed_public_bank_nim_tdcpass_borrower_and_fdic_retention_route_context_no_current_demand_admission"
    )
    assert "tdcpass_quarterly_panel.csv" in bank_intermediation_contract[
        "best_available_proxy_artifacts"
    ]
    assert "fdic_bank_margin_distribution_panel.csv" in (
        bank_intermediation_contract["best_available_proxy_artifacts"]
    )
    assert "tdcpass_aggregate_borrower_channel_context" in (
        bank_intermediation_contract["source_backed_proxy_fields"]
    )
    assert "fdic_aggregate_retained_earnings_dividend_route_context" in (
        bank_intermediation_contract["source_backed_proxy_fields"]
    )
    assert "tdcpass_latest_quarter=2025Q4" in bank_intermediation_contract[
        "strongest_candidate_latest_values"
    ]
    assert "strict_loan_core_plus_private_borrower_qoq=146.69799999999998" in (
        bank_intermediation_contract["strongest_candidate_latest_values"]
    )
    assert "fdic_latest_quarter=2026Q1" in bank_intermediation_contract[
        "strongest_candidate_latest_values"
    ]
    assert "retained_earnings_proxy_mil=6402.101" in (
        bank_intermediation_contract["strongest_candidate_latest_values"]
    )
    assert bank_intermediation_contract["strongest_candidate_admission_status"] == (
        "not_admitted_fdic_aggregate_retention_route_context_lacks_iorb_specific_retention_depositor_borrower_cashflow_timing_and_nonadditivity"
    )
    bank_gate_contract = next(
        row
        for row in bank_current_demand_contract_rows
        if row["evidence_contract_id"] == (
            "bank_behavior_current_demand_gate_contract"
        )
    )
    assert bank_gate_contract["linked_bank_bridge_row_id"] == bank_design_gate[
        "forecast_evidence_bridge_row_id"
    ]
    assert bank_gate_contract["current_demand_evidence_status"] == (
        "blocked_bank_behavior_bridge_missing"
    )
    assert bank_gate_contract["best_available_proxy_status"] == (
        "proxy_available_but_behavior_current_demand_bridge_missing"
    )
    assert "tdcpass_aggregate_borrower_channel_context" in bank_gate_contract[
        "source_backed_proxy_fields"
    ]
    assert "fdic_aggregate_retained_earnings_dividend_route_context" in (
        bank_gate_contract["source_backed_proxy_fields"]
    )
    assert "borrower_or_depositor_cashflow_response" in bank_gate_contract[
        "next_acquisition_required_fields"
    ]
    assert bank_gate_contract["strongest_source_owned_candidate"] == (
        "bank_behavior_design_gate_sources_context_only_no_current_demand_bridge"
    )
    assert bank_gate_contract["source_acquisition_execution_status"] == (
        "executed_bank_current_demand_design_gate_source_pass_no_bridge_admission"
    )
    assert bank_gate_contract["strongest_candidate_admission_status"] == (
        "not_admitted_design_gate_requires_source_backed_retention_pass_through_timing_and_nonadditivity_panel"
    )
    assert "depositor_cashflow" in bank_gate_contract["blocked_use"]


def test_forecast_treasury_recipient_domestic_nonbank_route_proxy_sidecar() -> None:
    registry_rows = _rows("ratewall_forecast_path_ratio_scenario_registry.csv")
    rows = _rows(
        "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv"
    )
    _assert_fail_closed(rows)

    assert {row["proxy_status"] for row in rows} == {
        "assumption_mode_noncanonical"
    }
    assert {row["source_status"] for row in rows} == {
        "assumption_mode_proxy_uses_source_backed_context_not_current_demand_evidence"
    }
    assert {row["assumption_mode"] for row in rows} == {"true"}
    assert {row["ref_quarter"] for row in rows} == {"2025Q4"}
    assert {row["onrrp_regime"] for row in rows if row["onrrp_regime"]} == {
        "low_stock_baseline"
    }
    assert {row["route_weight_denominator_quarters"] for row in rows} == {
        "2025Q1;2025Q2;2025Q3;2025Q4"
    }
    assert {row["route_weight_denominator_source_status"] for row in rows} == {
        "pass_source_backed_trailing_4q_z1_positive_absorption_with_mmf_split_context"
    }

    route_ids = {row["route_id"] for row in rows}
    assert "z1_mmf_sector_context" not in route_ids
    assert "retail_mmf_treasury_intermediated" in route_ids
    assert "institutional_mmf_treasury_intermediated" in route_ids

    registry_by_id = {
        row["forecast_path_ratio_scenario_registry_row_id"]: row
        for row in registry_rows
    }
    rows_by_scenario: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_scenario[row["forecast_path_ratio_scenario_registry_row_id"]].append(row)

    assert set(rows_by_scenario) == set(registry_by_id)
    assert len(rows) == len(registry_by_id) * len(route_ids)
    for scenario_id, scenario_rows in rows_by_scenario.items():
        registry_row = registry_by_id[scenario_id]
        assert {row["route_id"] for row in scenario_rows} == route_ids
        assert {row["forecast_year"] for row in scenario_rows} == {
            registry_row["forecast_year"]
        }
        assert {row["mpc_scenario"] for row in scenario_rows} == {
            registry_row["mpc_scenario"]
        }
        assert {row["maturity_scenario"] for row in scenario_rows} == {
            registry_row["maturity_scenario"]
        }
        assert {row["holder_scenario"] for row in scenario_rows} == {
            registry_row["holder_scenario"]
        }
        denominators = {
            Decimal(row["route_weight_denominator_bil"]) for row in scenario_rows
        }
        assert len(denominators) == 1
        denominator = denominators.pop()
        assert denominator > 0
        weight_sum = sum(Decimal(row["route_weight_norm"]) for row in scenario_rows)
        assert abs(weight_sum - Decimal("1")) <= Decimal("1e-24")
        for row in scenario_rows:
            assert Decimal(row["route_weight_norm"]) == (
                Decimal(row["route_weight_raw_bil"]) / denominator
            )
        support_ceiling = Decimal(
            scenario_rows[0]["domestic_nonbank_interest_cashflow_basis_bil"]
        )
        central_support = sum(
            Decimal(row["route_current_demand_support_central_bil"])
            for row in scenario_rows
        )
        assert central_support <= support_ceiling
        assert support_ceiling == Decimal(
            registry_row["domestic_nonbank_interest_cashflow_basis_bil"]
        )
        mmf_rows = [
            row
            for row in scenario_rows
            if row["source_sector_route_id"] == "z1_mmf_sector_context"
        ]
        assert {row["route_id"] for row in mmf_rows} == {
            "retail_mmf_treasury_intermediated",
            "institutional_mmf_treasury_intermediated",
        }
        assert sum(Decimal(row["route_weight_norm"]) for row in mmf_rows) > 0
        plumbing_rows = [
            row for row in scenario_rows if row["zero_rule_applied"] == "true"
        ]
        assert plumbing_rows
        assert {
            Decimal(row["route_current_demand_support_central_bil"])
            for row in plumbing_rows
        } == {Decimal("0")}
        assert {
            Decimal(row["ru_like_cashflow_memo_bil"]) for row in scenario_rows
        } == {Decimal("0")}


def test_forecast_bridge_basis_surfaces_link_stage_bridges_to_gate_specs() -> None:
    treasury_bridge_rows = _rows(
        "ratewall_forecast_treasury_beneficial_owner_recipient_bridge.csv"
    )
    treasury_rows = _rows(
        "ratewall_forecast_treasury_beneficial_owner_recipient_bridge_basis.csv"
    )
    bank_bridge_rows = _rows("ratewall_forecast_bank_behavior_distribution_bridge.csv")
    bank_rows = _rows("ratewall_forecast_bank_behavior_distribution_bridge_basis.csv")
    _assert_fail_closed(treasury_rows)
    _assert_fail_closed(bank_rows)

    treasury_bridge_by_id = {
        row["forecast_evidence_bridge_row_id"]: row for row in treasury_bridge_rows
    }
    for row in treasury_rows:
        bridge_row = treasury_bridge_by_id[row["forecast_evidence_bridge_row_id"]]
        assert row["component_id"] == bridge_row["component_id"]
        assert row["basis_stage_id"] in {
            bridge_row["bridge_stage_id"],
            "gross_and_domestic_holder_basis",
            "foreign_recycling_basis",
            "mmf_intermediation_basis",
            "tax_timing_basis",
        }
    assert sorted(int(row["basis_stage_rank"]) for row in treasury_rows) == list(
        range(1, len(treasury_rows) + 1)
    )
    assert {row["basis_stage_role"] for row in treasury_rows} >= {
        "public_context_basis",
        "restricted_protocol_requirement",
        "fail_closed_gate",
    }

    bank_bridge_by_id = {
        row["forecast_evidence_bridge_row_id"]: row for row in bank_bridge_rows
    }
    assert {
        row["forecast_evidence_bridge_row_id"] for row in bank_rows
    } == {
        bridge_id
        for bridge_id, row in bank_bridge_by_id.items()
        if row["bridge_stage_id"] != "bridge_summary"
    }
    for row in bank_rows:
        bridge_row = bank_bridge_by_id[row["forecast_evidence_bridge_row_id"]]
        assert row["component_id"] == bridge_row["component_id"]
        assert row["basis_stage_id"] in {
            bridge_row["bridge_stage_id"],
            "gross_reserve_income_basis",
            "reserve_and_deposit_pricing_context_basis",
            "bank_intermediation_context_basis",
        }
    assert sorted(int(row["basis_stage_rank"]) for row in bank_rows) == list(
        range(1, len(bank_rows) + 1)
    )

    treasury_foreign = next(
        row for row in treasury_rows if row["basis_stage_id"] == "foreign_recycling_basis"
    )
    assert treasury_foreign["linked_restricted_data_gate_id"] == (
        "foreign_treasury_holder_leakage_promotion_gate"
    )
    assert treasury_foreign["required_access_class"] == (
        "restricted_administrative_or_design_only"
    )
    assert "custody_country_placebo_must_fail" in treasury_foreign[
        "falsification_or_representativeness_rule"
    ]

    treasury_tax = next(
        row for row in treasury_rows if row["basis_stage_id"] == "tax_timing_basis"
    )
    assert treasury_tax["linked_restricted_protocol_gate_id"] == (
        "interest_income_tax_clawback_wrapper_promotion_gate"
    )
    assert "tax_exempt_or_deferred_account_placebo" in treasury_tax[
        "falsification_or_representativeness_rule"
    ]

    bank_pricing = next(
        row
        for row in bank_rows
        if row["basis_stage_id"] == "reserve_and_deposit_pricing_context_basis"
    )
    assert bank_pricing["required_artifact_or_method_bridge"] == (
        "household account-level realized yield and spending bridge"
    )
    assert bank_pricing["required_access_class"] == "public_official"

    bank_design_gate = next(
        row for row in bank_rows if row["basis_stage_id"] == "design_gate_closeout"
    )
    assert bank_design_gate["basis_surface_status"] == "fail_closed_design_gate"


def test_forecast_mapping_basis_surfaces_state_what_is_allowed_now_and_blocked() -> None:
    treasury_rows = _rows(
        "ratewall_forecast_treasury_beneficial_owner_recipient_mapping_basis.csv"
    )
    bank_rows = _rows(
        "ratewall_forecast_bank_behavior_distribution_mapping_basis.csv"
    )
    treasury_bridge_basis_rows = _rows(
        "ratewall_forecast_treasury_beneficial_owner_recipient_bridge_basis.csv"
    )
    bank_bridge_basis_rows = _rows(
        "ratewall_forecast_bank_behavior_distribution_bridge_basis.csv"
    )
    _assert_fail_closed(treasury_rows)
    _assert_fail_closed(bank_rows)

    _assert_contiguous_rank(treasury_rows, "mapping_rank")
    _assert_contiguous_rank(bank_rows, "mapping_rank")
    _assert_mapping_rows_link_bridge_basis(
        treasury_rows,
        treasury_bridge_basis_rows,
        allowed_unlinked_mapping_ids={"fed_remittance_exclusion_context_now"},
    )
    _assert_mapping_rows_link_bridge_basis(
        bank_rows,
        bank_bridge_basis_rows,
        allowed_unlinked_mapping_ids=set(),
    )

    treasury_domestic = next(
        row
        for row in treasury_rows
        if row["mapping_id"] == "domestic_private_holder_context_now"
    )
    assert treasury_domestic["mapping_role"] == "public_context_statement"
    assert treasury_domestic["eligibility_status"] == (
        "public_context_statement_allowed_now"
    )
    assert "domestic/private holder context" in treasury_domestic[
        "eligible_statement_now"
    ]
    assert "narrow treasury_interest_demand_share" in treasury_domestic[
        "blocked_statement_now"
    ]

    treasury_foreign = next(
        row
        for row in treasury_rows
        if row["mapping_id"] == "foreign_recycling_requirement"
    )
    assert treasury_foreign["mapping_role"] == "restricted_data_requirement"
    assert treasury_foreign["linked_restricted_data_gate_id"] == (
        "foreign_treasury_holder_leakage_promotion_gate"
    )
    assert treasury_foreign["eligibility_status"] == (
        "restricted_mapping_requirement_not_admitted"
    )
    assert "beneficial-owner and recycling timing bridge evidence" in (
        treasury_foreign["blocked_statement_now"]
    )

    treasury_fed = next(
        row
        for row in treasury_rows
        if row["mapping_id"] == "fed_remittance_exclusion_context_now"
    )
    assert treasury_fed["mapping_role"] == "public_context_exclusion_statement"
    assert treasury_fed["forecast_evidence_bridge_basis_row_id"] == ""
    assert treasury_fed["eligibility_status"] == (
        "public_exclusion_statement_allowed_now"
    )
    assert "public-finance timing context" in treasury_fed["eligible_statement_now"]

    treasury_tax = next(
        row for row in treasury_rows if row["mapping_id"] == "tax_timing_requirement"
    )
    assert treasury_tax["mapping_role"] == (
        "restricted_protocol_and_falsification_requirement"
    )
    assert treasury_tax["linked_restricted_protocol_gate_id"] == (
        "interest_income_tax_clawback_wrapper_promotion_gate"
    )
    assert "tax_exempt_or_deferred_account_placebo" in treasury_tax[
        "falsification_or_representativeness_rule"
    ]

    treasury_design_gate = next(
        row for row in treasury_rows if row["mapping_id"] == "design_gate_closeout"
    )
    assert treasury_design_gate["eligibility_status"] == (
        "fail_closed_noncanonical_only"
    )
    assert "canonical RW_Y" in treasury_design_gate["blocked_statement_now"]

    bank_pricing = next(
        row for row in bank_rows if row["mapping_id"] == "reserve_pricing_context_now"
    )
    assert bank_pricing["mapping_role"] == "public_context_statement"
    assert bank_pricing["eligibility_status"] == (
        "public_context_statement_allowed_now"
    )
    assert "depositor cashflow" in bank_pricing["blocked_statement_now"]

    bank_design_gate = next(
        row for row in bank_rows if row["mapping_id"] == "design_gate_closeout"
    )
    assert bank_design_gate["eligibility_status"] == (
        "fail_closed_noncanonical_only"
    )
    assert "bank-retained-margin support into depositor cashflow" in (
        bank_design_gate["blocked_statement_now"]
    )


def test_forecast_admission_candidate_surfaces_keep_prior_narrowing_blocked() -> None:
    treasury_rows = _rows(
        "ratewall_forecast_treasury_beneficial_owner_recipient_admission_candidate.csv"
    )
    bank_rows = _rows(
        "ratewall_forecast_bank_behavior_distribution_admission_candidate.csv"
    )
    treasury_mapping_rows = _rows(
        "ratewall_forecast_treasury_beneficial_owner_recipient_mapping_basis.csv"
    )
    bank_mapping_rows = _rows(
        "ratewall_forecast_bank_behavior_distribution_mapping_basis.csv"
    )
    _assert_fail_closed(treasury_rows)
    _assert_fail_closed(bank_rows)

    _assert_contiguous_rank(treasury_rows, "candidate_rank")
    _assert_contiguous_rank(bank_rows, "candidate_rank")
    _assert_admission_rows_link_mapping_basis(treasury_rows, treasury_mapping_rows)
    _assert_admission_rows_link_mapping_basis(bank_rows, bank_mapping_rows)

    treasury_domestic = next(
        row
        for row in treasury_rows
        if row["candidate_id"] == "domestic_private_holder_context_now"
    )
    assert treasury_domestic["current_public_only_candidate_status"] == (
        "admissible_public_context_statement_only"
    )
    assert treasury_domestic["restricted_or_design_candidate_status"] == ""
    assert treasury_domestic["full_bridge_pass_candidate_status"] == (
        "counterfactual_candidate_if_recipient_cashflow_and_current_demand_bridge_close"
    )
    assert treasury_domestic["prior_narrowing_candidate_status"] == (
        "blocked_until_recipient_current_demand_bridge_passes"
    )

    treasury_foreign = next(
        row
        for row in treasury_rows
        if row["candidate_id"] == "foreign_recycling_requirement"
    )
    assert treasury_foreign["current_public_only_candidate_status"] == (
        "blocked_public_context_only_requirement_not_admitted"
    )
    assert treasury_foreign["restricted_or_design_candidate_status"] == (
        "counterfactual_candidate_if_restricted_or_design_gate_passes"
    )
    assert treasury_foreign["linked_restricted_data_gate_id"] == (
        "foreign_treasury_holder_leakage_promotion_gate"
    )

    treasury_tax = next(
        row for row in treasury_rows if row["candidate_id"] == "tax_timing_requirement"
    )
    assert treasury_tax["restricted_or_design_candidate_status"] == (
        "counterfactual_candidate_if_restricted_or_design_gate_passes"
    )
    assert treasury_tax["linked_restricted_protocol_gate_id"] == (
        "interest_income_tax_clawback_wrapper_promotion_gate"
    )

    treasury_design_gate = next(
        row for row in treasury_rows if row["candidate_id"] == "design_gate_closeout"
    )
    assert treasury_design_gate["current_public_only_candidate_status"] == (
        "noncanonical_fail_closed_only"
    )
    assert treasury_design_gate["prior_narrowing_candidate_status"] == (
        "blocked_no_prior_narrowing_or_canonical_promotion"
    )

    bank_pricing = next(
        row for row in bank_rows if row["candidate_id"] == "reserve_pricing_context_now"
    )
    assert bank_pricing["current_public_only_candidate_status"] == (
        "admissible_public_context_statement_only"
    )
    assert bank_pricing["full_bridge_pass_candidate_status"] == (
        "counterfactual_candidate_if_bank_behavior_and_distribution_bridge_close"
    )
    assert bank_pricing["prior_narrowing_candidate_status"] == (
        "blocked_until_bank_behavior_current_demand_bridge_passes"
    )

    bank_design_gate = next(
        row for row in bank_rows if row["candidate_id"] == "design_gate_closeout"
    )
    assert bank_design_gate["current_public_only_candidate_status"] == (
        "noncanonical_fail_closed_only"
    )
    assert bank_design_gate["prior_narrowing_candidate_status"] == (
        "blocked_no_depositor_relabeling_or_prior_narrowing"
    )


def test_forecast_bridge_pass_review_surfaces_remain_fail_closed() -> None:
    treasury_rows = _rows(
        "ratewall_forecast_treasury_beneficial_owner_recipient_bridge_pass_review.csv"
    )
    bank_rows = _rows(
        "ratewall_forecast_bank_behavior_distribution_bridge_pass_review.csv"
    )
    treasury_candidate_rows = _rows(
        "ratewall_forecast_treasury_beneficial_owner_recipient_admission_candidate.csv"
    )
    bank_candidate_rows = _rows(
        "ratewall_forecast_bank_behavior_distribution_admission_candidate.csv"
    )
    _assert_fail_closed(treasury_rows)
    _assert_fail_closed(bank_rows)

    _assert_contiguous_rank(treasury_rows, "review_rank")
    _assert_contiguous_rank(bank_rows, "review_rank")
    _assert_bridge_pass_review_rows_link_admission_candidates(
        treasury_rows, treasury_candidate_rows
    )
    _assert_bridge_pass_review_rows_link_admission_candidates(
        bank_rows, bank_candidate_rows
    )

    treasury_domestic = next(
        row for row in treasury_rows if row["review_id"] == "domestic_private_holder_context_now"
    )
    assert treasury_domestic["current_review_status"] == (
        "review_public_context_statement_admitted_now"
    )
    assert treasury_domestic["review_closeout_status"] == (
        "context_only_review_pass_bridge_not_passed"
    )
    assert treasury_domestic["bridge_pass_minimal_test"] == (
        "map Treasury-interest cashflow from gross public context to domestic private recipient basis without holder-allocation promotion"
    )

    treasury_foreign = next(
        row for row in treasury_rows if row["review_id"] == "foreign_recycling_requirement"
    )
    assert treasury_foreign["current_review_status"] == (
        "review_blocked_pending_restricted_or_design_bridge"
    )
    assert treasury_foreign["restricted_or_design_review_status"] == (
        "restricted_or_design_gate_must_pass_before_review_can_clear"
    )
    assert treasury_foreign["bridge_pass_falsification_rule"] == (
        "custody_country_placebo_must_fail_before_beneficial_owner_leakage_use;beneficial_owner_and_recycling_timing_bridge_required_not_tic_custody_stock_context"
    )

    treasury_design_gate = next(
        row for row in treasury_rows if row["review_id"] == "design_gate_closeout"
    )
    assert treasury_design_gate["current_review_status"] == (
        "review_fail_closed_noncanonical_only"
    )
    assert treasury_design_gate["review_closeout_status"] == (
        "closeout_noncanonical_only_until_every_bridge_passes"
    )

    bank_pricing = next(
        row for row in bank_rows if row["review_id"] == "reserve_pricing_context_now"
    )
    assert bank_pricing["current_review_status"] == (
        "review_public_context_statement_admitted_now"
    )
    assert bank_pricing["bridge_pass_counterfactual_status"] == (
        "counterfactual_candidate_if_bank_behavior_and_distribution_bridge_close"
    )
    assert bank_pricing["public_pass_through_proxy_window_end_quarter"] == "2026Q2"
    assert bank_pricing["public_pass_through_proxy_observation_count"] == "46"
    assert bank_pricing["public_pass_through_proxy_value"] == (
        "0.5307509589554447"
    )
    assert bank_pricing["public_non_pass_through_complement_proxy"] == (
        "0.4692490410445553"
    )
    assert bank_pricing["public_pass_through_proxy_status"] == (
        "pass_public_rolling_tdc_pass_through_proxy_available"
    )
    assert bank_pricing["timing_bridge_status"] == (
        "blocked_no_bank_retention_or_depositor_current_demand_timing_bridge"
    )
    assert bank_pricing["bank_timing_requirement_horizon_bucket"] == "1y"
    assert bank_pricing["bank_timing_requirement_status"] == (
        "blocked_bank_iorb_timing_matrix_requires_behavior_bridge"
    )
    assert bank_pricing["bank_timing_required_fields"] == (
        "source_backed_retention_share;deposit_pass_through;"
        "current_demand_timing;nonadditivity_check;"
        "borrower_or_depositor_cashflow_response"
    )
    assert bank_pricing["bank_timing_next_evidence_target"] == (
        "bank IORB pass-through and credit-supply behavior bridge"
    )
    assert bank_pricing["bridge_admission_after_proxy_status"] == (
        "blocked_proxy_values_do_not_clear_current_demand_bridge"
    )
    assert bank_pricing["bridge_pass_minimal_test"] == (
        "show which portion of reserve-income or deposit-pricing effects reaches current private demand rather than bank retention"
    )

    bank_design_gate = next(
        row for row in bank_rows if row["review_id"] == "design_gate_closeout"
    )
    assert bank_design_gate["current_review_status"] == (
        "review_fail_closed_noncanonical_only"
    )
    assert bank_design_gate["review_closeout_status"] == (
        "closeout_noncanonical_only_until_bank_bridge_passes"
    )
    assert bank_design_gate["public_pass_through_proxy_status"] == (
        "not_applicable_no_pass_through_proxy_basis"
    )
    assert bank_design_gate["bank_timing_requirement_status"] == (
        "blocked_bank_iorb_timing_matrix_requires_behavior_bridge"
    )


def test_forecast_driver_ranking_and_dominance_identify_material_movers() -> None:
    ranking_rows = _rows("ratewall_forecast_path_ratio_driver_ranking.csv")
    dominance_rows = _rows("ratewall_forecast_path_ratio_driver_dominance_matrix.csv")
    sensitivity_rows = _rows("ratewall_forecast_path_ratio_sensitivity_summary.csv")
    registry_rows = _rows("ratewall_forecast_path_ratio_scenario_registry.csv")
    frontier_rows = _rows("ratewall_forecast_path_ratio_scenario_frontier.csv")
    interpretation_rows = _rows("ratewall_forecast_path_ratio_interpretation_registry.csv")
    leakage_rows = _rows("ratewall_forecast_path_ratio_recipient_leakage_registry.csv")
    source_specific_rows = _rows(
        "ratewall_forecast_path_ratio_source_specific_interpretation_registry.csv"
    )
    _assert_fail_closed(ranking_rows)
    _assert_fail_closed(dominance_rows)

    registry_ids = {
        row["forecast_path_ratio_scenario_registry_row_id"] for row in registry_rows
    }
    top_frontier_by_year = {
        row["forecast_year"]: row
        for row in frontier_rows
        if row["frontier_rank_within_year"] == "1"
    }
    interpretation_by_id = {
        row["forecast_path_ratio_interpretation_row_id"]: row
        for row in interpretation_rows
    }
    leakage_by_id = {
        row["forecast_path_ratio_recipient_leakage_row_id"]: row
        for row in leakage_rows
    }
    source_specific_by_id = {
        row["forecast_path_ratio_source_specific_interpretation_row_id"]: row
        for row in source_specific_rows
    }
    ranking_by_id = {
        row["forecast_path_ratio_driver_ranking_row_id"]: row for row in ranking_rows
    }

    sensitivity_keys = {
        (
            row["forecast_year"],
            row["scenario_axis"],
            row["reference_scenario_registry_row_id"],
            row["matched_scenario_registry_row_id"],
        )
        for row in sensitivity_rows
    }
    ranking_keys = {
        (
            row["forecast_year"],
            row["scenario_axis"],
            row["reference_scenario_registry_row_id"],
            row["matched_scenario_registry_row_id"],
        )
        for row in ranking_rows
    }
    assert ranking_keys == sensitivity_keys

    rows_by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ranking_rows:
        rows_by_year[row["forecast_year"]].append(row)
    assert set(rows_by_year) == set(top_frontier_by_year)
    for rows in rows_by_year.values():
        assert {row["scenario_axis"] for row in rows} == {
            "channel_conversion_profile_id",
            "holder_scenario",
            "maturity_scenario",
        }
        assert sorted(
            int(row["closeness_improvement_rank_within_year"]) for row in rows
        ) == list(range(1, len(rows) + 1))
        assert sorted(int(row["absolute_ratio_delta_rank_within_year"]) for row in rows) == list(
            range(1, len(rows) + 1)
        )

    for row in ranking_rows:
        assert row["reference_scenario_registry_row_id"] in registry_ids
        assert row["matched_scenario_registry_row_id"] in registry_ids
        assert row["frontier_scenario_registry_row_id"] == (
            top_frontier_by_year[row["forecast_year"]][
                "forecast_path_ratio_scenario_registry_row_id"
            ]
        )

        matched_interpretation = interpretation_by_id[
            row["matched_forecast_path_ratio_interpretation_row_id"]
        ]
        frontier_interpretation = interpretation_by_id[
            row["frontier_forecast_path_ratio_interpretation_row_id"]
        ]
        assert matched_interpretation["forecast_path_ratio_scenario_registry_row_id"] == (
            row["matched_scenario_registry_row_id"]
        )
        assert frontier_interpretation["forecast_path_ratio_scenario_registry_row_id"] == (
            row["frontier_scenario_registry_row_id"]
        )
        assert matched_interpretation["interpretation_boundary_status"] == (
            row["matched_interpretation_boundary_status"]
        )
        assert frontier_interpretation["interpretation_boundary_status"] == (
            row["frontier_interpretation_boundary_status"]
        )

        matched_leakage = leakage_by_id[
            row["matched_forecast_path_ratio_recipient_leakage_row_id"]
        ]
        frontier_leakage = leakage_by_id[
            row["frontier_forecast_path_ratio_recipient_leakage_row_id"]
        ]
        assert matched_leakage["forecast_recipient_leakage_status"] == (
            row["matched_forecast_recipient_leakage_status"]
        )
        assert frontier_leakage["forecast_recipient_leakage_status"] == (
            row["frontier_forecast_recipient_leakage_status"]
        )

        matched_source_specific = source_specific_by_id[
            row["matched_forecast_path_ratio_source_specific_interpretation_row_id"]
        ]
        frontier_source_specific = source_specific_by_id[
            row["frontier_forecast_path_ratio_source_specific_interpretation_row_id"]
        ]
        assert matched_source_specific[
            "source_specific_interpretation_tightening_status"
        ] == row["matched_source_specific_tightening_status"]
        assert frontier_source_specific[
            "source_specific_interpretation_tightening_status"
        ] == row["frontier_source_specific_tightening_status"]

        is_reference_row = (
            row["matched_scenario_registry_row_id"]
            == row["reference_scenario_registry_row_id"]
        )
        if is_reference_row:
            assert row["driver_effect_classification"] == "reference_no_change"
            assert row["driver_channel_classification"] == "reference_no_material_delta"
            assert Decimal(row["delta_ratio_vs_reference"]) == Decimal("0")
            assert Decimal(row["delta_numerator_bil_vs_reference"]) == Decimal("0")
            assert Decimal(row["delta_denominator_bil_vs_reference"]) == Decimal("0")
        elif row["scenario_axis"] == "maturity_scenario":
            assert row["driver_channel_classification"] == (
                "mixed_numerator_and_denominator_driver"
            )
            assert Decimal(row["delta_denominator_bil_vs_reference"]) != Decimal("0")
        elif row["scenario_axis"] == "holder_scenario":
            assert row["driver_channel_classification"] == "numerator_only_driver"
            assert Decimal(row["delta_denominator_bil_vs_reference"]) == Decimal("0")
        else:
            assert row["scenario_axis"] == "channel_conversion_profile_id"
            assert row["driver_channel_classification"] in {
                "tdc_deposit_balance_conversion_driver",
                "treasury_recipient_conversion_driver",
            }
            assert Decimal(row["delta_denominator_bil_vs_reference"]) == Decimal("0")

    assert {row["forecast_year"] for row in dominance_rows} == set(rows_by_year)
    for row in dominance_rows:
        ranking_row = ranking_by_id[row["dominant_driver_ranking_row_id"]]
        assert ranking_row["forecast_year"] == row["forecast_year"]
        assert ranking_row["closeness_improvement_rank_within_year"] == "1"
        assert row["frontier_scenario_registry_row_id"] == (
            top_frontier_by_year[row["forecast_year"]][
                "forecast_path_ratio_scenario_registry_row_id"
            ]
        )
        assert row["dominant_driver_axis"] == ranking_row["scenario_axis"]
        assert row["dominant_driver_setting"] == ranking_row["scenario_axis_setting"]
        assert row["dominant_driver_axis_role"] == ranking_row["scenario_axis_role"]
        assert row["dominant_driver_effect_classification"] == (
            ranking_row["driver_effect_classification"]
        )
        assert row["dominant_driver_channel_classification"] == (
            ranking_row["driver_channel_classification"]
        )
        assert row["dominant_row_matched_interpretation_row_id"] == (
            ranking_row["matched_forecast_path_ratio_interpretation_row_id"]
        )
        assert row["frontier_rank1_interpretation_row_id"] == (
            ranking_row["frontier_forecast_path_ratio_interpretation_row_id"]
        )
        assert row["dominant_driver_ratio_delta_vs_reference"] == (
            ranking_row["delta_ratio_vs_reference"]
        )
        assert row["dominant_driver_numerator_delta_vs_reference"] == (
            ranking_row["delta_numerator_bil_vs_reference"]
        )
        assert row["dominant_driver_denominator_delta_vs_reference"] == (
            ranking_row["delta_denominator_bil_vs_reference"]
        )

    rows_2026 = [
        row for row in ranking_rows if row["forecast_year"] == "2026"
    ]
    top_2026 = min(
        rows_2026,
        key=lambda row: int(row["closeness_improvement_rank_within_year"]),
    )
    assert top_2026["scenario_axis"] == "channel_conversion_profile_id"
    assert top_2026["scenario_axis_setting"] == "demand_active"
    assert top_2026["driver_effect_classification"] == "moves_closer_to_wall"
    assert Decimal(top_2026["delta_ratio_vs_reference"]) > Decimal("0")
    assert Decimal(top_2026["delta_numerator_bil_vs_reference"]) > Decimal("0")
    assert Decimal(top_2026["delta_denominator_bil_vs_reference"]) == Decimal("0")
    assert top_2026["frontier_axis_alignment_status"] == "frontier_uses_driver_setting"
    assert (
        top_2026["driver_channel_classification"]
        == "treasury_recipient_conversion_driver"
    )
    assert (
        top_2026["frontier_interpretation_boundary_status"]
        == "tdc_ex_direct_interest_overlap_contract_plus_assumption_only_deposit_balance_conversion"
    )
    assert (
        top_2026["frontier_forecast_recipient_leakage_status"]
        == "internal_overlap_only_not_external_recipient_leakage_bridge"
    )
    assert (
        top_2026["frontier_source_specific_tightening_status"]
        == "tdc_ex_direct_interest_overlap_context_stable_no_current_proxy_reconciliation_target"
    )

    dominance_2026 = next(
        row for row in dominance_rows if row["forecast_year"] == "2026"
    )
    assert dominance_2026["dominant_driver_axis"] == "channel_conversion_profile_id"
    assert dominance_2026["dominant_driver_setting"] == "demand_active"
    assert dominance_2026["frontier_uses_dominant_driver_setting"] == "true"
    assert (
        dominance_2026["dominant_driver_axis_channel_classification"]
        == "channel_specific_current_demand_conversion_profile"
    )
    assert dominance_2026["frontier_rank1_interpretation_row_id"]
    assert dominance_2026["frontier_rank1_interpretation_boundary_status"]
    assert (
        Decimal(dominance_2026["dominant_driver_closeness_improvement_bil"])
        >= Decimal("0")
    )


def test_forecast_consumer_outputs_stay_compact_and_preserve_boundaries() -> None:
    ladder_rows = _rows("ratewall_forecast_path_ratio_consumer_ladder.csv")
    driver_summary_rows = _rows("ratewall_forecast_path_ratio_consumer_driver_summary.csv")
    interpretation_summary_rows = _rows(
        "ratewall_forecast_path_ratio_consumer_interpretation_summary.csv"
    )
    dominance_rows = _rows("ratewall_forecast_path_ratio_driver_dominance_matrix.csv")
    frontier_rows = _rows("ratewall_forecast_path_ratio_scenario_frontier.csv")
    interpretation_rows = _rows("ratewall_forecast_path_ratio_interpretation_registry.csv")
    leakage_rows = _rows("ratewall_forecast_path_ratio_recipient_leakage_registry.csv")
    source_specific_rows = _rows(
        "ratewall_forecast_path_ratio_source_specific_interpretation_registry.csv"
    )
    _assert_fail_closed(ladder_rows)
    _assert_fail_closed(driver_summary_rows)
    _assert_fail_closed(interpretation_summary_rows)

    dominance_by_year = {row["forecast_year"]: row for row in dominance_rows}
    frontier_by_registry_id = {
        row["forecast_path_ratio_scenario_registry_row_id"]: row
        for row in frontier_rows
    }
    interpretation_by_id = {
        row["forecast_path_ratio_interpretation_row_id"]: row
        for row in interpretation_rows
    }
    leakage_by_id = {
        row["forecast_path_ratio_recipient_leakage_row_id"]: row
        for row in leakage_rows
    }
    source_specific_by_id = {
        row["forecast_path_ratio_source_specific_interpretation_row_id"]: row
        for row in source_specific_rows
    }
    expected_ladder_keys = {
        (
            row["forecast_year"],
            f"closest_to_wall_top{row['frontier_rank_within_year']}",
            row["forecast_path_ratio_scenario_registry_row_id"],
            row["forecast_path_ratio_scenario_frontier_row_id"],
        )
        for row in frontier_rows
        if int(row["frontier_rank_within_year"]) <= 3
    }
    expected_ladder_keys |= {
        (
            row["forecast_year"],
            "reference_scenario",
            row["reference_scenario_registry_row_id"],
            frontier_by_registry_id[row["reference_scenario_registry_row_id"]][
                "forecast_path_ratio_scenario_frontier_row_id"
            ],
        )
        for row in dominance_rows
    }
    assert {
        (
            row["forecast_year"],
            row["ladder_entry_role"],
            row["forecast_path_ratio_scenario_registry_row_id"],
            row["forecast_path_ratio_scenario_frontier_row_id"],
        )
        for row in ladder_rows
    } == expected_ladder_keys

    ladder_roles_by_year: dict[str, set[str]] = defaultdict(set)
    for row in ladder_rows:
        ladder_roles_by_year[row["forecast_year"]].add(row["ladder_entry_role"])
        dominance_row = dominance_by_year[row["forecast_year"]]
        assert row["linked_driver_dominance_row_id"] == (
            dominance_row["forecast_path_ratio_driver_dominance_row_id"]
        )
        interpretation_row = interpretation_by_id[
            row["linked_forecast_path_ratio_interpretation_row_id"]
        ]
        assert interpretation_row["forecast_path_ratio_scenario_registry_row_id"] == (
            row["forecast_path_ratio_scenario_registry_row_id"]
        )
        assert interpretation_row["component_id"] == row["dominant_direct_component_id"]
        assert interpretation_row["source_backed_context_status"] == (
            row["source_backed_context_status"]
        )
        assert interpretation_row["assumption_conversion_status"] == (
            row["assumption_conversion_status"]
        )
        assert interpretation_row["interpretation_boundary_status"] == (
            row["interpretation_boundary_status"]
        )
        assert (
            row["deposit_pass_through_materialization_status"]
            == "not_separately_materialized_in_forecast_bridge"
        )
    expected_roles = {
        "closest_to_wall_top1",
        "closest_to_wall_top2",
        "closest_to_wall_top3",
        "reference_scenario",
    }
    assert all(roles == expected_roles for roles in ladder_roles_by_year.values())

    top1_2026 = next(
        row
        for row in ladder_rows
        if row["forecast_year"] == "2026"
        and row["ladder_entry_role"] == "closest_to_wall_top1"
    )
    assert top1_2026["channel_conversion_profile_id"] == "demand_active"
    assert top1_2026["mpc_scenario"] == "high_mpc_20pct"
    assert top1_2026["maturity_scenario"] == "higher_wam_slower_repricing"
    assert top1_2026["holder_scenario"] == "shift_to_banks_foreigners"
    assert (
        top1_2026["interpretation_boundary_status"]
        == "tdc_ex_direct_interest_overlap_contract_plus_assumption_only_deposit_balance_conversion"
    )

    assert all(
        row["driver_setting_deposit_pass_through_materialization_status"]
        == "not_separately_materialized_in_forecast_bridge"
        for row in driver_summary_rows
    )
    assert all(
        row["frontier_deposit_pass_through_materialization_status"]
        == "not_separately_materialized_in_forecast_bridge"
        for row in driver_summary_rows
    )
    assert all(
        row["dominant_row_matched_source_specific_interpretation_row_id"]
        for row in driver_summary_rows
    )
    assert all(
        row["frontier_rank1_source_specific_interpretation_row_id"]
        for row in driver_summary_rows
    )
    assert {row["forecast_year"] for row in driver_summary_rows} == set(
        dominance_by_year
    )
    for row in driver_summary_rows:
        dominance_row = dominance_by_year[row["forecast_year"]]
        for field in (
            "reference_scenario_registry_row_id",
            "frontier_scenario_registry_row_id",
            "dominant_driver_ranking_row_id",
            "dominant_row_matched_interpretation_row_id",
            "frontier_rank1_interpretation_row_id",
            "dominant_driver_axis",
            "dominant_driver_axis_role",
            "dominant_driver_setting",
            "dominant_driver_value",
            "dominant_driver_axis_channel_classification",
            "dominant_driver_effect_classification",
            "dominant_driver_channel_classification",
            "frontier_uses_dominant_driver_setting",
            "dominant_driver_closeness_improvement_bil",
            "dominant_driver_ratio_delta_vs_reference",
            "reference_ratio",
            "frontier_rank1_ratio",
            "reference_remaining_gap_bil",
            "frontier_rank1_remaining_gap_bil",
        ):
            assert row[field] == dominance_row[field]

    driver_2026 = next(
        row for row in driver_summary_rows if row["forecast_year"] == "2026"
    )
    assert driver_2026["dominant_driver_axis"] == "channel_conversion_profile_id"
    assert driver_2026["dominant_driver_setting"] == "demand_active"
    assert (
        driver_2026["dominant_driver_axis_channel_classification"]
        == "channel_specific_current_demand_conversion_profile"
    )
    assert driver_2026["frontier_uses_dominant_driver_setting"] == "true"
    assert (
        driver_2026["frontier_interpretation_boundary_status"]
        == "tdc_ex_direct_interest_overlap_contract_plus_assumption_only_deposit_balance_conversion"
    )
    assert (
        driver_2026["frontier_forecast_recipient_leakage_status"]
        == "internal_overlap_only_not_external_recipient_leakage_bridge"
    )
    assert (
        driver_2026["driver_setting_prior_narrowing_decision"]
        == "do_not_narrow_demand_conversion_prior"
    )
    assert (
        driver_2026["frontier_source_specific_tightening_status"]
        == "tdc_ex_direct_interest_overlap_context_stable_no_current_proxy_reconciliation_target"
    )

    expected_interpretation_keys = {
        (
            row["forecast_year"],
            "reference_scenario",
            row["reference_scenario_registry_row_id"],
            component_id,
        )
        for row in dominance_rows
        for component_id in EXPECTED_FORECAST_COMPONENTS
    }
    expected_interpretation_keys |= {
        (
            row["forecast_year"],
            "frontier_rank1_scenario",
            row["frontier_scenario_registry_row_id"],
            component_id,
        )
        for row in dominance_rows
        for component_id in EXPECTED_FORECAST_COMPONENTS
    }
    assert {
        (
            row["forecast_year"],
            row["scenario_role"],
            row["forecast_path_ratio_scenario_registry_row_id"],
            row["component_id"],
        )
        for row in interpretation_summary_rows
    } == expected_interpretation_keys
    for row in interpretation_summary_rows:
        interpretation_row = interpretation_by_id[
            row["forecast_path_ratio_interpretation_row_id"]
        ]
        leakage_row = leakage_by_id[row["forecast_path_ratio_recipient_leakage_row_id"]]
        source_specific_row = source_specific_by_id[
            row["forecast_path_ratio_source_specific_interpretation_row_id"]
        ]
        assert interpretation_row["forecast_path_ratio_scenario_registry_row_id"] == (
            row["forecast_path_ratio_scenario_registry_row_id"]
        )
        assert interpretation_row["component_id"] == row["component_id"]
        assert leakage_row["forecast_path_ratio_interpretation_row_id"] == (
            row["forecast_path_ratio_interpretation_row_id"]
        )
        assert source_specific_row["forecast_path_ratio_interpretation_row_id"] == (
            row["forecast_path_ratio_interpretation_row_id"]
        )
        assert interpretation_row["interpretation_boundary_status"] == (
            row["interpretation_boundary_status"]
        )
        assert leakage_row["forecast_recipient_leakage_status"] == (
            row["forecast_recipient_leakage_status"]
        )
        assert source_specific_row[
            "source_specific_interpretation_tightening_status"
        ] == row["source_specific_interpretation_tightening_status"]

    tdc_rows = [
        row
        for row in interpretation_summary_rows
        if row["component_id"] == "tdc_deposit_current_demand_support"
    ]
    assert {
        row["deposit_pass_through_materialization_status"] for row in tdc_rows
    } == {"not_separately_materialized_in_forecast_bridge"}
    assert {
        row["assumption_conversion_status"] for row in tdc_rows
    } == {
        "assumption_only_deposit_balance_current_demand_conversion"
    }
    treasury_rows = [
        row
        for row in interpretation_summary_rows
        if row["component_id"] == "domestic_nonbank_interest_support"
    ]
    assert {
        row["forecast_recipient_leakage_status"] for row in treasury_rows
    } == {"source_backed_treasury_context_recipient_bridge_still_missing"}
    assert {
        row["can_narrow_demand_conversion_prior"] for row in treasury_rows
    } == {"false"}
    assert {
        row["source_specific_interpretation_tightening_status"] for row in treasury_rows
    } == {"context_rich_but_domestic_recipient_spending_bridge_missing"}
    bank_rows = [
        row
        for row in interpretation_summary_rows
        if row["component_id"] == "bank_retained_margin_support"
    ]
    assert {
        row["forecast_recipient_leakage_status"] for row in bank_rows
    } == {"source_backed_bank_context_behavior_bridge_still_missing"}
    assert {
        row["demand_conversion_evidence_status"] for row in bank_rows
    } == {"blocked_no_bank_behavior_to_current_demand_conversion_bridge"}
    assert {
        row["source_specific_interpretation_tightening_status"] for row in bank_rows
    } == {
        "reserve_and_deposit_pricing_context_available_but_bank_behavior_bridge_missing"
    }


def test_forecast_consumer_outputs_appear_in_release_reports() -> None:
    artifact_index = Path("outputs/reports/ratewall_release_artifact_index.md").read_text(
        encoding="utf-8"
    )
    table_plate = Path("outputs/reports/ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )
    for name in (
        "ratewall_forecast_channel_conversion_profile_registry.csv",
        "ratewall_forecast_assumption_calibration_registry.csv",
        "ratewall_forecast_assumption_bundle_registry.csv",
        "ratewall_forecast_scenario_product_summary.csv",
        "ratewall_forecast_treasury_recipient_calibration_registry.csv",
        "ratewall_forecast_treasury_recipient_calibration_comparison.csv",
        "ratewall_forecast_treasury_recipient_calibration_product_summary.csv",
        "ratewall_forecast_treasury_recipient_calibration_consumer_summary.csv",
        "ratewall_forecast_bank_margin_sidecar_summary.csv",
        "ratewall_forecast_path_ratio_recipient_leakage_registry.csv",
        "ratewall_forecast_path_ratio_source_specific_interpretation_registry.csv",
        "ratewall_forecast_path_ratio_evidence_dependency_matrix.csv",
        "ratewall_forecast_path_ratio_evidence_targeting_registry.csv",
        "ratewall_forecast_path_ratio_evidence_work_queue.csv",
        "ratewall_forecast_treasury_recipient_bridge_packet.csv",
        "ratewall_forecast_treasury_recipient_source_targeting_matrix.csv",
        "ratewall_forecast_bank_behavior_bridge_packet.csv",
        "ratewall_forecast_treasury_beneficial_owner_recipient_bridge.csv",
        "ratewall_forecast_treasury_recipient_best_proxy_basis.csv",
        "ratewall_forecast_treasury_recipient_best_proxy_admission_review.csv",
        "ratewall_forecast_treasury_recipient_best_proxy_calculation_scaffold.csv",
        "ratewall_forecast_treasury_recipient_best_proxy_gate_review.csv",
        "ratewall_forecast_treasury_recipient_current_demand_evidence_contract.csv",
        "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv",
        "ratewall_forecast_bank_behavior_distribution_bridge.csv",
        "ratewall_forecast_bank_behavior_current_demand_evidence_contract.csv",
        "ratewall_forecast_treasury_beneficial_owner_recipient_bridge_basis.csv",
        "ratewall_forecast_bank_behavior_distribution_bridge_basis.csv",
        "ratewall_forecast_treasury_beneficial_owner_recipient_mapping_basis.csv",
        "ratewall_forecast_bank_behavior_distribution_mapping_basis.csv",
        "ratewall_forecast_treasury_beneficial_owner_recipient_admission_candidate.csv",
        "ratewall_forecast_bank_behavior_distribution_admission_candidate.csv",
        "ratewall_forecast_treasury_beneficial_owner_recipient_bridge_pass_review.csv",
        "ratewall_forecast_bank_behavior_distribution_bridge_pass_review.csv",
        "ratewall_forecast_path_ratio_consumer_ladder.csv",
        "ratewall_forecast_path_ratio_consumer_driver_summary.csv",
        "ratewall_forecast_path_ratio_consumer_interpretation_summary.csv",
        "ratewall_forecast_path_ratio_pass_through_consumer_interpretation_summary.csv",
    ):
        assert name in artifact_index
        assert name in table_plate


def test_forecast_assumption_calibration_and_product_outputs_materialize() -> None:
    profile_rows = _rows("ratewall_forecast_channel_conversion_profile_registry.csv")
    calibration_rows = _rows("ratewall_forecast_assumption_calibration_registry.csv")
    bundle_rows = _rows("ratewall_forecast_assumption_bundle_registry.csv")
    product_rows = _rows("ratewall_forecast_scenario_product_summary.csv")
    _assert_fail_closed(profile_rows)
    _assert_fail_closed(calibration_rows)
    _assert_fail_closed(bundle_rows)
    _assert_fail_closed(product_rows)

    assert len(profile_rows) == 3
    assert [row["channel_conversion_profile_id"] for row in profile_rows] == [
        "conservative",
        "base",
        "demand_active",
    ]
    assert {row["treasury_recipient_current_demand_share"] for row in profile_rows} == {
        "0.05",
        "0.10",
        "0.20",
    }
    assert {row["tdc_ex_overlap_current_demand_share"] for row in profile_rows} == {
        "0.03",
        "0.07",
        "0.12",
    }
    assert {
        row["tdc_deposit_balance_current_demand_conversion_assumption"]
        for row in profile_rows
    } == {
        "0.03",
        "0.07",
        "0.12",
    }
    assert {
        row["bank_retained_margin_direct_demand_share"] for row in profile_rows
    } == {"0.00", "0.01", "0.02"}

    assert len(bundle_rows) == 297
    assert Counter(row["channel_conversion_profile_id"] for row in bundle_rows) == {
        "conservative": 99,
        "base": 99,
        "demand_active": 99,
    }

    families = Counter(row["parameter_family"] for row in calibration_rows)
    assert families["treasury_interest_current_demand_conversion"] == 3
    assert families["tdc_deposit_balance_current_demand_conversion"] == 3
    assert families["bank_margin_direct_demand_conversion"] == 3
    assert families["deposit_pass_through_beta"] == 4

    assert len(product_rows) == 33
    assert Counter(row["channel_conversion_profile_id"] for row in product_rows) == {
        "conservative": 11,
        "base": 11,
        "demand_active": 11,
    }
    assert {
        row["wall_case_classification"] for row in product_rows
    } <= {"wall_hit", "near_wall", "mostly_tightening"}


def test_forecast_treasury_recipient_calibration_outputs_materialize_and_stay_monotone() -> None:
    registry_rows = _rows("ratewall_forecast_treasury_recipient_calibration_registry.csv")
    comparison_rows = _rows(
        "ratewall_forecast_treasury_recipient_calibration_comparison.csv"
    )
    product_rows = _rows(
        "ratewall_forecast_treasury_recipient_calibration_product_summary.csv"
    )
    _assert_fail_closed(registry_rows)
    _assert_fail_closed(comparison_rows)
    _assert_fail_closed(product_rows)

    assert len(registry_rows) == 3
    assert [row["treasury_calibration_id"] for row in registry_rows] == [
        "low",
        "base",
        "high",
    ]
    assert [row["treasury_calibration_band"] for row in registry_rows] == [
        "low",
        "base",
        "high",
    ]
    assert {
        row["linked_interest_recipient_leakage_bridge_assumption_set"]
        for row in registry_rows
    } == {
        "base_current_100bps",
        "assumption_mode_combined_recipient_leakage_wrappers",
        "strong_contractionary_drag_nonhit",
    }

    assert len(comparison_rows) == 891
    assert Counter(row["treasury_calibration_id"] for row in comparison_rows) == {
        "low": 297,
        "base": 297,
        "high": 297,
    }

    rows_2026_base_profile = sorted(
        [
            row
            for row in comparison_rows
            if row["forecast_year"] == "2026"
            and row["channel_conversion_profile_id"] == "base"
            and row["maturity_scenario"] == "higher_wam_slower_repricing"
            and row["holder_scenario"] == "shift_to_banks_foreigners"
        ],
        key=lambda row: {"low": 0, "base": 1, "high": 2}[row["treasury_calibration_id"]],
    )
    assert [row["treasury_calibration_id"] for row in rows_2026_base_profile] == [
        "low",
        "base",
        "high",
    ]
    adjusted_ratios = [
        Decimal(row["adjusted_forecast_incremental_path_ratio"])
        for row in rows_2026_base_profile
    ]
    assert adjusted_ratios[0] < adjusted_ratios[1] < adjusted_ratios[2]
    adjusted_gaps = [
        Decimal(row["adjusted_remaining_gap_to_wall_bil"])
        for row in rows_2026_base_profile
    ]
    assert adjusted_gaps[0] > Decimal("0")
    assert adjusted_gaps[1:] == [Decimal("0"), Decimal("0")]
    assert [
        row["treasury_calibration_effect_classification"]
        for row in rows_2026_base_profile
    ] == [
        "moves_further_from_wall",
        "reference_no_change",
        "no_gap_change",
    ]

    assert len(product_rows) == 99
    assert Counter(row["treasury_calibration_id"] for row in product_rows) == {
        "low": 33,
        "base": 33,
        "high": 33,
    }
    assert Counter(row["channel_conversion_profile_id"] for row in product_rows) == {
        "conservative": 33,
        "base": 33,
        "demand_active": 33,
    }
    assert {
        row["wall_case_classification"] for row in product_rows
    } <= {"wall_hit", "near_wall", "mostly_tightening"}
    assert {row["dominant_assumption_axis"] for row in product_rows} == {
        "treasury_recipient_calibration_id"
    }


def test_forecast_treasury_consumer_and_bank_sidecar_summaries_materialize() -> None:
    treasury_rows = _rows(
        "ratewall_forecast_treasury_recipient_calibration_consumer_summary.csv"
    )
    bank_rows = _rows("ratewall_forecast_bank_margin_sidecar_summary.csv")
    _assert_fail_closed(treasury_rows)
    _assert_fail_closed(bank_rows)

    assert len(treasury_rows) == 33
    assert Counter(row["channel_conversion_profile_id"] for row in treasury_rows) == {
        "conservative": 11,
        "base": 11,
        "demand_active": 11,
    }
    assert {
        row["treasury_calibration_scenario_stability_status"] for row in treasury_rows
    } <= {
        "same_frontier_scenario_across_treasury_bands",
        "frontier_scenario_changes_across_treasury_bands",
    }

    base_2026 = next(
        row
        for row in treasury_rows
        if row["forecast_year"] == "2026"
        and row["channel_conversion_profile_id"] == "base"
    )
    assert base_2026["dominant_assumption_axis"] == "treasury_recipient_calibration_id"
    assert (
        base_2026["treasury_calibration_scenario_stability_status"]
        == "same_frontier_scenario_across_treasury_bands"
    )
    assert (
        Decimal(base_2026["adjusted_forecast_incremental_path_ratio_low"])
        < Decimal(base_2026["adjusted_forecast_incremental_path_ratio_base"])
        < Decimal(base_2026["adjusted_forecast_incremental_path_ratio_high"])
    )
    assert {
        Decimal(base_2026["adjusted_remaining_gap_to_wall_bil_low"]),
        Decimal(base_2026["adjusted_remaining_gap_to_wall_bil_base"]),
        Decimal(base_2026["adjusted_remaining_gap_to_wall_bil_high"]),
    } == {Decimal("0"), Decimal("11.14294302163864458903307019")}
    assert base_2026["low_effect_classification"] == "moves_further_from_wall"
    assert base_2026["high_effect_classification"] == "no_gap_change"

    assert len(bank_rows) == 33
    assert Counter(row["channel_conversion_profile_id"] for row in bank_rows) == {
        "conservative": 11,
        "base": 11,
        "demand_active": 11,
    }
    assert {
        row["bank_margin_vs_depositor_boundary"] for row in bank_rows
    } == {"bank_retained_margin_support_not_depositor_cashflow"}
    assert {
        row["interpretation_boundary_status"] for row in bank_rows
    } == {
        "source_backed_reserve_and_deposit_pricing_context_assumption_only_bank_margin_proxy"
    }
    assert {
        row["bank_sidecar_role_status"] for row in bank_rows
    } <= {
        "inactive_non_depositor_sidecar",
        "subordinate_non_depositor_sidecar",
        "material_but_non_depositor_sidecar",
    }
    assert "material_but_non_depositor_sidecar" not in {
        row["bank_sidecar_role_status"] for row in bank_rows
    }
    demand_active_2036 = next(
        row
        for row in bank_rows
        if row["forecast_year"] == "2036"
        and row["channel_conversion_profile_id"] == "demand_active"
    )
    assert Decimal(demand_active_2036["bank_share_vs_treasury_support"]) < Decimal("0.10")
    assert (
        demand_active_2036["bank_sidecar_role_status"]
        == "subordinate_non_depositor_sidecar"
    )


def test_forecast_product_decision_casebook_consolidates_forecast_surfaces() -> None:
    casebook_rows = _rows("ratewall_forecast_product_decision_casebook.csv")
    product_rows = _rows("ratewall_forecast_scenario_product_summary.csv")
    treasury_rows = _rows(
        "ratewall_forecast_treasury_recipient_calibration_consumer_summary.csv"
    )
    bank_rows = _rows("ratewall_forecast_bank_margin_sidecar_summary.csv")
    pass_rows = _rows("ratewall_forecast_path_ratio_pass_through_dominance.csv")
    dependency_rows = _rows("ratewall_forecast_path_ratio_evidence_dependency_matrix.csv")
    work_queue_rows = _rows("ratewall_forecast_path_ratio_evidence_work_queue.csv")
    _assert_fail_closed(casebook_rows)

    assert len(casebook_rows) == 33
    assert Counter(row["channel_conversion_profile_id"] for row in casebook_rows) == {
        "conservative": 11,
        "base": 11,
        "demand_active": 11,
    }
    product_ids = {
        row["forecast_scenario_product_summary_row_id"] for row in product_rows
    }
    treasury_ids = {
        row["forecast_treasury_recipient_calibration_consumer_summary_row_id"]
        for row in treasury_rows
    }
    bank_ids = {row["forecast_bank_margin_sidecar_summary_row_id"] for row in bank_rows}
    pass_ids = {row["forecast_pass_through_dominance_row_id"] for row in pass_rows}
    dependency_ids = {
        row["forecast_path_ratio_evidence_dependency_row_id"]
        for row in dependency_rows
        if row["frontier_family"] == "base_frontier_top1"
    }
    work_queue_ids = {
        row["forecast_path_ratio_evidence_work_queue_row_id"]
        for row in work_queue_rows
    }

    for row in casebook_rows:
        assert row["linked_forecast_scenario_product_summary_row_id"] in product_ids
        assert (
            row["linked_treasury_recipient_calibration_consumer_summary_row_id"]
            in treasury_ids
        )
        assert row["linked_bank_margin_sidecar_summary_row_id"] in bank_ids
        assert row["linked_pass_through_dominance_row_id"] in pass_ids
        assert row["linked_base_frontier_evidence_dependency_row_id"] in dependency_ids
        assert row["linked_component_evidence_work_queue_row_id"] in work_queue_ids
        assert row["decision_reportability_status"] == (
            "reportable_assumption_mode_casebook_row_noncanonical"
        )
        assert row["tdcsim_contract_mapping_status"] == (
            "mapped_tdcsim_contract_available_assumption_mode"
        )
        assert row["blocked_use"] == "runtime_default;canonical_rw_y"
        assert "noncanonical" in row["casebook_safe_sentence"]
        assert "canonical RW_Y claims" in row["casebook_safe_sentence"]

    manifest = Path("outputs/tables/ratewall_release_manifest.json").read_text(
        encoding="utf-8"
    )
    artifact_index = Path("outputs/reports/ratewall_release_artifact_index.md").read_text(
        encoding="utf-8"
    )
    table_plate = Path("outputs/reports/ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )
    for text in (manifest, artifact_index, table_plate):
        assert "ratewall_forecast_product_decision_casebook.csv" in text


def test_forecast_product_pass_through_frontier_crosswalk_summarizes_frontier() -> None:
    crosswalk_rows = _rows(
        "ratewall_forecast_product_pass_through_frontier_crosswalk.csv"
    )
    casebook_rows = _rows("ratewall_forecast_product_decision_casebook.csv")
    frontier_rows = _rows("ratewall_forecast_path_ratio_pass_through_scenario_frontier.csv")
    _assert_fail_closed(crosswalk_rows)

    assert len(crosswalk_rows) == 11
    assert {row["forecast_year"] for row in crosswalk_rows} == {
        str(year) for year in range(2026, 2037)
    }
    base_casebook_ids = {
        row["forecast_product_decision_casebook_row_id"]
        for row in casebook_rows
        if row["channel_conversion_profile_id"] == "base"
    }
    top_frontier_ids = {
        row["forecast_pass_through_scenario_frontier_row_id"]
        for row in frontier_rows
        if row["frontier_tier"] == "closest_to_wall_top1"
    }
    for row in crosswalk_rows:
        assert row["linked_base_casebook_row_id"] in base_casebook_ids
        assert row["linked_pass_through_frontier_row_id"] in top_frontier_ids
        assert row["base_channel_conversion_profile_id"] == "base"
        assert row["frontier_pass_through_scenario"]
        assert row["frontier_pass_through_beta"]
        assert row["decision_reportability_status"] == (
            "reportable_assumption_mode_baseline_vs_pass_through_frontier_noncanonical"
        )
        assert row["allowed_use"] == "forecast_product_pass_through_frontier_crosswalk"
        assert row["blocked_use"] == "runtime_default;canonical_rw_y"
        assert "noncanonical" in row["crosswalk_safe_sentence"]
        assert "canonical RW_Y claims" in row["crosswalk_safe_sentence"]

    status_counts = Counter(
        row["pass_through_product_readability_status"] for row in crosswalk_rows
    )
    assert status_counts

    manifest = Path("outputs/tables/ratewall_release_manifest.json").read_text(
        encoding="utf-8"
    )
    artifact_index = Path("outputs/reports/ratewall_release_artifact_index.md").read_text(
        encoding="utf-8"
    )
    table_plate = Path("outputs/reports/ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )
    for text in (manifest, artifact_index, table_plate):
        assert "ratewall_forecast_product_pass_through_frontier_crosswalk.csv" in text


def test_forecast_product_reviewer_decision_summary_links_evidence_queue() -> None:
    summary_rows = _rows("ratewall_forecast_product_reviewer_decision_summary.csv")
    crosswalk_rows = _rows(
        "ratewall_forecast_product_pass_through_frontier_crosswalk.csv"
    )
    dependency_rows = _rows("ratewall_forecast_path_ratio_evidence_dependency_matrix.csv")
    work_queue_rows = _rows("ratewall_forecast_path_ratio_evidence_work_queue.csv")
    _assert_fail_closed(summary_rows)

    assert len(summary_rows) == 11
    crosswalk_ids = {
        row["forecast_product_pass_through_frontier_crosswalk_row_id"]
        for row in crosswalk_rows
    }
    dependency_ids = {
        row["forecast_path_ratio_evidence_dependency_row_id"]
        for row in dependency_rows
    }
    work_queue_ids = {
        row["forecast_path_ratio_evidence_work_queue_row_id"]
        for row in work_queue_rows
    }
    for row in summary_rows:
        assert row["linked_pass_through_frontier_crosswalk_row_id"] in crosswalk_ids
        assert row["linked_base_frontier_evidence_dependency_row_id"] in dependency_ids
        assert (
            row["linked_pass_through_frontier_evidence_dependency_row_id"]
            in dependency_ids
        )
        assert row["linked_current_evidence_work_queue_row_id"] in work_queue_ids
        assert row["pass_through_scenario"]
        assert row["pass_through_beta"]
        assert row["reviewer_next_backend_action"]
        assert row["allowed_use"] == "forecast_product_reviewer_decision_summary"
        assert row["blocked_use"] == "runtime_default;canonical_rw_y"
        assert "noncanonical" in row["reviewer_safe_sentence"]
        assert "canonical RW_Y claims" in row["reviewer_safe_sentence"]

    assert {
        row["reviewer_summary_status"] for row in summary_rows
    } <= {
        "reviewer_summary_boundary_maintenance",
        "reviewer_summary_frontier_evidence_target",
        "reviewer_summary_secondary_evidence_target",
    }

    manifest = Path("outputs/tables/ratewall_release_manifest.json").read_text(
        encoding="utf-8"
    )
    artifact_index = Path("outputs/reports/ratewall_release_artifact_index.md").read_text(
        encoding="utf-8"
    )
    table_plate = Path("outputs/reports/ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )
    for text in (manifest, artifact_index, table_plate):
        assert "ratewall_forecast_product_reviewer_decision_summary.csv" in text

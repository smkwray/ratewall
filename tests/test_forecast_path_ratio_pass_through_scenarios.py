from __future__ import annotations

import csv
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUTS = Path("outputs/tables")


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _optional_rows(name: str) -> list[dict[str, str]]:
    path = OUTPUTS / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _pass_through_axis_rows() -> list[dict[str, str]]:
    return _rows("ratewall_forecast_path_ratio_pass_through_scenario_axis.csv")


def _pass_through_axis_by_scenario() -> dict[str, dict[str, str]]:
    return {
        row["pass_through_scenario"]: row for row in _pass_through_axis_rows()
    }


def _rows_by(
    rows: list[dict[str, str]], field: str
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row[field]].append(row)
    return grouped


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        _assert_guardrails_false(row)


def _assert_guardrails_false(row: dict[str, str]) -> None:
    for field in ARCHITECTURE_GUARDRAIL_FIELDS:
        assert row[field] == "false"


def test_forecast_pass_through_axis_materializes_explicit_scenarios() -> None:
    rows = _rows("ratewall_forecast_path_ratio_pass_through_scenario_axis.csv")
    _assert_fail_closed(rows)

    assert len({row["pass_through_scenario"] for row in rows}) == len(rows)
    assert {row["pass_through_scenario"] for row in rows} == {
        "low_pandemic_exclusion_2020",
        "normal_forward_h0",
        "high_recent_rolling_h0",
        "high_full_sample_h0",
    }
    roles = {row["pass_through_scenario"]: row["pass_through_scenario_role"] for row in rows}
    assert (
        roles["normal_forward_h0"]
        == "default_evidence_b_import_contract_forward_normal"
    )
    assert rows[0]["blocked_use"].startswith("runtime_default")


def test_forecast_pass_through_registry_rescales_only_tdc_support_leg() -> None:
    base_rows = _rows("ratewall_forecast_path_ratio_scenario_registry.csv")
    pass_rows = _rows("ratewall_forecast_path_ratio_pass_through_scenario_registry.csv")
    axis_by_scenario = _pass_through_axis_by_scenario()
    _assert_fail_closed(pass_rows)

    base_by_id = {
        row["forecast_path_ratio_scenario_registry_row_id"]: row for row in base_rows
    }
    assert len(pass_rows) == len(base_by_id) * len(axis_by_scenario)
    assert Counter(row["forecast_year"] for row in pass_rows) == {
        year: len(rows) * len(axis_by_scenario)
        for year, rows in _rows_by(base_rows, "forecast_year").items()
    }
    assert Counter(row["pass_through_scenario"] for row in pass_rows) == {
        scenario: len(base_by_id) for scenario in axis_by_scenario
    }
    assert Counter(row["pass_through_scenario_role"] for row in pass_rows) == {
        axis_row["pass_through_scenario_role"]: len(base_by_id)
        for axis_row in axis_by_scenario.values()
    }

    rows_by_base: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pass_rows:
        rows_by_base[row["base_forecast_path_ratio_scenario_registry_row_id"]].append(row)

    assert set(rows_by_base) == set(base_by_id)
    for base_id, rows in rows_by_base.items():
        assert {row["pass_through_scenario"] for row in rows} == set(axis_by_scenario)
        base_row = base_by_id[base_id]
        base_numerator = Decimal(base_row["numerator_total_bil"])
        tdc_ex_overlap = Decimal(base_row["tdc_change_ex_overlap_bil"])
        tdc_chi = Decimal(
            base_row["tdc_deposit_balance_current_demand_conversion_assumption"]
        )
        original_tdc = None
        for row in rows:
            beta = Decimal(row["pass_through_beta"])
            row_original_tdc = Decimal(row["original_tdc_current_demand_support_bil"])
            adjusted_tdc = Decimal(row["adjusted_tdc_current_demand_support_bil"])
            delta = Decimal(row["tdc_support_delta_bil"])
            numerator = Decimal(row["numerator_total_bil"])
            assert Decimal(row["denominator_bil"]) == Decimal(base_row["denominator_bil"])
            assert abs(adjusted_tdc - tdc_ex_overlap * beta * tdc_chi) <= Decimal(
                "1e-24"
            )
            if original_tdc is None:
                original_tdc = row_original_tdc
            else:
                assert row_original_tdc == original_tdc
            assert row_original_tdc <= abs(tdc_ex_overlap)
            assert abs(numerator - (base_numerator + delta)) <= Decimal("1e-24")
        assert original_tdc is not None
        ordered = sorted(rows, key=lambda row: Decimal(row["pass_through_beta"]))
        for previous, current in zip(ordered, ordered[1:]):
            delta_beta = Decimal(current["pass_through_beta"]) - Decimal(
                previous["pass_through_beta"]
            )
            delta_tdc_support = Decimal(
                current["adjusted_tdc_current_demand_support_bil"]
            ) - Decimal(previous["adjusted_tdc_current_demand_support_bil"])
            assert abs(delta_tdc_support - tdc_ex_overlap * tdc_chi * delta_beta) <= Decimal(
                "1e-24"
            )
            assert Decimal(current["denominator_bil"]) == Decimal(
                previous["denominator_bil"]
            )


def test_tdc_assumption_mode_channel_consolidates_headline_beta_chi_chain() -> None:
    registry_rows = _optional_rows("ratewall_forecast_path_ratio_scenario_registry.csv")
    tdc_rows = _rows("ratewall_tdc_assumption_mode_channel.csv")

    registry_by_id = {
        row["forecast_path_ratio_scenario_registry_row_id"]: row for row in registry_rows
    }
    if registry_by_id:
        assert len(tdc_rows) == len(registry_by_id)
        assert {
            row["forecast_path_ratio_scenario_registry_row_id"] for row in tdc_rows
        } == set(registry_by_id)
    else:
        assert len(tdc_rows) == len(
            {row["forecast_path_ratio_scenario_registry_row_id"] for row in tdc_rows}
        )
    assert Counter(
        (
            row["forecast_year"],
            row["forecast_scenario_id"],
            row["horizon"],
        )
        for row in tdc_rows
    ) == {
        (
            row["forecast_year"],
            row["forecast_scenario_id"],
            row["horizon"],
        ): 1
        for row in tdc_rows
    }

    assert {row["canonical_ratio_entry"] for row in tdc_rows} == {"false"}
    selector_rows = [row for row in tdc_rows if row["provisional_selector_row"] == "true"]
    years = {row["forecast_year"] for row in tdc_rows}
    assert len(selector_rows) == len(years)
    assert {
        (
            row["channel_conversion_profile_id"],
            row["maturity_scenario"],
            row["holder_scenario"],
        )
        for row in selector_rows
    } == {
        (
            "base",
            "higher_wam_slower_repricing",
            "current_holder_distribution",
        )
    }
    assert {
        row["ratewall_ratio"]
        for row in selector_rows
        if row["forecast_year"] == "2026"
    } == {"0.7999562733566150813589606680"}

    for row in tdc_rows:
        _assert_guardrails_false(row)
        assert row["canonical_ratio_entry"] == "false"
        assert row["ratio_object_id"] == "rw_tdc_forward_headline_assumption_mode"
        assert row["claim_boundary"].startswith(
            "TDC support is a labeled Assumption-Mode prior chain"
        )
        assert "not the static RateWall N/D object" in row["claim_boundary"]
        assert "Two-headline crosswalk" in row["claim_boundary"]
        assert "rw_legacy_static_assumption_mode" in row["claim_boundary"]
        assert "rw_tdc_forward_headline_assumption_mode" in row["claim_boundary"]
        assert "EA-TDC net deposit materialization prior" in row["claim_boundary"]
        assert "current-demand conversion prior" in row["claim_boundary"]
        assert "empirical wall claim" in row["claim_boundary"]
        assert "beta_times_chi_no_full_tdc_double_count" in row["source_status"]
        assert "runtime_default" in row["blocked_use"]
        assert "evidence_mode" in row["blocked_use"]

        beta = Decimal(row["tdc_materialization_beta"])
        chi = Decimal(row["deposit_current_demand_share"])
        tdc_full = Decimal(row["tdc_change_bil"])
        direct_overlap = Decimal(row["direct_interest_overlap_cashflow_bil"])
        ex_overlap = Decimal(row["tdc_change_ex_overlap_bil"])
        net_materialized = Decimal(row["tdc_net_materialized_deposits_bil"])
        support = Decimal(row["tdc_current_demand_support_bil"])
        assert tdc_full - direct_overlap == ex_overlap
        assert abs(net_materialized - ex_overlap * beta) <= Decimal("1e-24")
        assert abs(Decimal(row["derived_beta_times_chi"]) - beta * chi) <= Decimal(
            "1e-24"
        )
        assert abs(support - ex_overlap * beta * chi) <= Decimal("1e-24")
        assert abs(support) < abs(ex_overlap * chi)
        registry = registry_by_id.get(row["forecast_path_ratio_scenario_registry_row_id"])
        if registry is not None:
            assert tdc_full == Decimal(registry["tdc_full_cashflow_basis_bil"])
            assert ex_overlap == Decimal(registry["tdc_change_ex_overlap_bil"])
            assert row["ratewall_ratio"] == registry["forecast_incremental_path_ratio"]
            assert row["denominator_bil"] == registry["denominator_bil"]


def test_forecast_pass_through_frontier_and_consumer_ladder_are_deterministic() -> None:
    registry_rows = _rows("ratewall_forecast_path_ratio_pass_through_scenario_registry.csv")
    frontier_rows = _rows("ratewall_forecast_path_ratio_pass_through_scenario_frontier.csv")
    ladder_rows = _rows("ratewall_forecast_path_ratio_pass_through_consumer_ladder.csv")
    interpretation_rows = _rows(
        "ratewall_forecast_path_ratio_pass_through_consumer_interpretation_summary.csv"
    )
    _assert_fail_closed(frontier_rows)
    _assert_fail_closed(ladder_rows)
    _assert_fail_closed(interpretation_rows)

    assert len(frontier_rows) == len(registry_rows)
    rows_by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in frontier_rows:
        rows_by_year[row["forecast_year"]].append(row)
    for rows in rows_by_year.values():
        assert sorted(int(row["frontier_rank_within_year"]) for row in rows) == list(
            range(1, len(rows) + 1)
        )

    years = {row["forecast_year"] for row in frontier_rows}
    ladder_roles = {
        "closest_to_wall_top1",
        "closest_to_wall_top2",
        "closest_to_wall_top3",
        "reference_scenario",
    }
    assert len(ladder_rows) == len(years) * len(ladder_roles)
    assert Counter(row["ladder_entry_role"] for row in ladder_rows) == {
        role: len(years) for role in ladder_roles
    }
    reference_rows = [row for row in ladder_rows if row["ladder_entry_role"] == "reference_scenario"]
    assert {row["pass_through_scenario"] for row in reference_rows} == {
        "normal_forward_h0"
    }
    components = {row["component_id"] for row in interpretation_rows}
    assert len(interpretation_rows) == len(ladder_rows) * len(components)
    assert Counter(row["ladder_entry_role"] for row in interpretation_rows) == {
        role: len(years) * len(components) for role in ladder_roles
    }
    assert Counter(row["component_id"] for row in interpretation_rows) == {
        component: len(ladder_rows) for component in components
    }
    tdc_rows = [
        row for row in interpretation_rows if row["component_id"] == "tdc_deposit_current_demand_support"
    ]
    assert {
        row["component_pass_through_role"] for row in tdc_rows
    } == {"pass_through_adjusted_ex_overlap_tdc_beta_chi_component"}
    assert {
        row["pass_through_interpretation_summary"] for row in tdc_rows
    } == {"pass_through_scenario_applies_beta_once_to_ex_overlap_tdc_before_chi"}
    treasury_rows = [
        row
        for row in interpretation_rows
        if row["component_id"] == "domestic_nonbank_interest_support"
    ]
    assert all(
        row["forecast_path_ratio_source_specific_interpretation_row_id"]
        for row in treasury_rows
    )
    assert {
        row["source_specific_interpretation_tightening_status"] for row in treasury_rows
    } == {"context_rich_but_domestic_recipient_spending_bridge_missing"}
    bank_rows = [
        row for row in interpretation_rows if row["component_id"] == "bank_retained_margin_support"
    ]
    assert {
        row["source_specific_interpretation_tightening_status"] for row in bank_rows
    } == {
        "reserve_and_deposit_pricing_context_available_but_bank_behavior_bridge_missing"
    }

    registry_ids = {
        row["forecast_pass_through_scenario_registry_row_id"] for row in registry_rows
    }
    assert {
        row["forecast_pass_through_scenario_registry_row_id"] for row in frontier_rows
    } <= registry_ids


def test_critical_beta_frontier_solves_minimum_beta_by_year() -> None:
    pass_rows = _rows("ratewall_forecast_path_ratio_pass_through_scenario_registry.csv")
    critical_rows = _rows("ratewall_critical_beta_frontier.csv")
    _assert_fail_closed(critical_rows)

    years = {row["forecast_year"] for row in pass_rows}
    reference_families = {
        "min_critical_beta_by_year",
        "base_current_reference_by_year",
        "conservative_current_reference_by_year",
        "aggressive_current_reference_by_year",
    }
    assert len(critical_rows) == len(years) * len(reference_families)
    assert Counter(row["critical_beta_reference_family"] for row in critical_rows) == {
        family: len(years) for family in reference_families
    }
    assert {row["frontier_rank_within_year"] for row in critical_rows} == {
        "1",
        "2",
        "3",
        "4",
    }

    rows_by_base: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pass_rows:
        rows_by_base[row["base_forecast_path_ratio_scenario_registry_row_id"]].append(row)

    expected_by_family: dict[tuple[str, str], tuple[Decimal, str]] = {}
    family_targets = {
        "base_current_reference_by_year": (
            "base_mpc_10pct",
            "current_wam_cbo_rate_path",
            "current_holder_distribution",
        ),
        "conservative_current_reference_by_year": (
            "low_mpc_5pct",
            "current_wam_cbo_rate_path",
            "current_holder_distribution",
        ),
        "aggressive_current_reference_by_year": (
            "high_mpc_20pct",
            "current_wam_cbo_rate_path",
            "current_holder_distribution",
        ),
    }
    for base_id, rows in rows_by_base.items():
        reference = min(rows, key=lambda row: Decimal(row["pass_through_beta"]))
        denominator = Decimal(reference["denominator_bil"])
        adjusted_tdc = Decimal(reference["adjusted_tdc_current_demand_support_bil"])
        adjusted_numerator = Decimal(reference["numerator_total_bil"])
        coefficient = Decimal(reference["tdc_change_ex_overlap_bil"]) * Decimal(
            reference["current_demand_conversion_value"]
        )
        if denominator <= 0 or coefficient <= 0:
            continue
        critical_beta = (denominator - (adjusted_numerator - adjusted_tdc)) / coefficient
        year = reference["forecast_year"]
        min_key = (year, "min_critical_beta_by_year")
        if min_key not in expected_by_family or critical_beta < expected_by_family[min_key][0]:
            expected_by_family[min_key] = (critical_beta, base_id)
        scenario_key = (
            reference["mpc_scenario"],
            reference["maturity_scenario"],
            reference["holder_scenario"],
        )
        for family, target in family_targets.items():
            if scenario_key == target:
                expected_by_family[(year, family)] = (critical_beta, base_id)

    assert {
        (row["forecast_year"], row["critical_beta_reference_family"])
        for row in critical_rows
    } == set(expected_by_family)
    for row in critical_rows:
        expected_beta, expected_base_id = expected_by_family[
            (row["forecast_year"], row["critical_beta_reference_family"])
        ]
        assert row["base_forecast_path_ratio_scenario_registry_row_id"] == expected_base_id
        reported_beta = Decimal(row["critical_beta_to_wall"])
        assert abs(reported_beta - expected_beta) <= Decimal(
            "0.000000000000000000000001"
        )
        coefficient = Decimal(row["tdc_beta_support_coefficient_bil"])
        numerator_without_tdc = Decimal(row["numerator_without_tdc_beta_bil"])
        denominator = Decimal(row["denominator_bil"])
        assert abs(numerator_without_tdc + coefficient * reported_beta - denominator) <= Decimal(
            "0.000000000000000000000001"
        )
        max_beta = Decimal(row["max_materialized_pass_through_beta"])
        default_beta = Decimal(row["default_pass_through_beta"])
        if reported_beta <= 0:
            expected_bucket = "already_at_wall_without_tdc"
            expected_status = "wall_hit_without_tdc_beta"
        elif reported_beta <= max_beta:
            expected_bucket = "feasible_0_to_1"
            expected_status = "wall_reachable_with_materialized_beta_axis"
        elif reported_beta <= Decimal("1"):
            expected_bucket = "feasible_0_to_1"
            expected_status = "requires_unmaterialized_higher_beta_within_unit_interval"
        else:
            expected_bucket = "requires_above_1"
            expected_status = "requires_beta_above_one_not_interpretable"
        assert row["critical_beta_bucket"] == expected_bucket
        assert row["critical_beta_frontier_status"] == expected_status
        assert row["wall_reachable_under_default_beta"] == str(
            reported_beta <= default_beta
        ).lower()
        assert row["wall_reachable_under_materialized_beta_axis"] == str(
            reported_beta <= max_beta
        ).lower()
        assert row["wall_reachable_under_unit_beta"] == str(
            reported_beta <= Decimal("1")
        ).lower()
        assert "posterior_beta_claim" in row["blocked_use"]
        assert "critical_beta_solved_from_existing_ex_overlap_chi_pass_through_grid" in row[
            "source_status"
        ]
        assert row["critical_beta_reference_family"] in row["source_status"]


def test_forecast_pass_through_comparison_and_delta_summary_hold_other_axes_fixed() -> None:
    comparison_rows = _rows("ratewall_forecast_path_ratio_pass_through_comparison.csv")
    delta_rows = _rows("ratewall_forecast_path_ratio_pass_through_delta_summary.csv")
    pass_rows = _rows("ratewall_forecast_path_ratio_pass_through_scenario_registry.csv")
    axis_by_scenario = _pass_through_axis_by_scenario()
    _assert_fail_closed(comparison_rows)
    _assert_fail_closed(delta_rows)

    years = {row["forecast_year"] for row in comparison_rows}
    assert len(comparison_rows) == len(pass_rows)
    assert len(delta_rows) == len(years) * len(axis_by_scenario)
    assert Counter(row["compared_pass_through_scenario"] for row in comparison_rows) == {
        scenario: len(pass_rows) // len(axis_by_scenario)
        for scenario in axis_by_scenario
    }

    rows_by_bundle: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in comparison_rows:
        rows_by_bundle[
            (
                row["forecast_year"],
                row["mpc_scenario"],
                row["maturity_scenario"],
                row["holder_scenario"],
            )
        ].append(row)
    for bundle_rows in rows_by_bundle.values():
        assert {row["compared_pass_through_scenario"] for row in bundle_rows} == set(
            axis_by_scenario
        )
        reference_rows = [
            row for row in bundle_rows if row["pass_through_effect_classification"] == "reference_no_change"
        ]
        assert len(reference_rows) == 1
        reference = reference_rows[0]
        assert reference["compared_pass_through_scenario"] == "normal_forward_h0"
        assert Decimal(reference["delta_ratio"]) == Decimal("0")
        assert Decimal(reference["delta_remaining_gap_bil"]) == Decimal("0")

    assert Counter(row["pass_through_scenario"] for row in delta_rows) == {
        scenario: len(years) for scenario in axis_by_scenario
    }
    base_delta_rows = [
        row for row in delta_rows if row["pass_through_scenario"] == "normal_forward_h0"
    ]
    assert {
        Decimal(row["strongest_delta_remaining_gap_bil"]) for row in base_delta_rows
    } == {Decimal("0")}
    assert {
        row["strongest_treasury_recipient_leakage_status"] for row in delta_rows
    } == {"source_backed_treasury_context_recipient_bridge_still_missing"}
    assert {
        row["strongest_bank_recipient_leakage_status"] for row in delta_rows
    } == {"source_backed_bank_context_behavior_bridge_still_missing"}
    assert {
        row["strongest_tdc_recipient_leakage_status"] for row in delta_rows
    } == {"internal_overlap_only_not_external_recipient_leakage_bridge"}
    assert {
        row["strongest_pass_through_interpretation_scope"] for row in delta_rows
    } == {
        "pass_through_moves_ex_overlap_tdc_beta_chi_leg_while_treasury_and_bank_components_keep_existing_context_and_assumption_boundaries"
    }


def test_forecast_pass_through_dominance_compares_against_existing_driver_axis() -> None:
    dominance_rows = _rows("ratewall_forecast_path_ratio_pass_through_dominance.csv")
    existing_dominance_rows = _rows("ratewall_forecast_path_ratio_driver_dominance_matrix.csv")
    _assert_fail_closed(dominance_rows)

    existing_by_year = {row["forecast_year"]: row for row in existing_dominance_rows}
    assert {row["forecast_year"] for row in dominance_rows} == set(existing_by_year)

    for row in dominance_rows:
        existing = existing_by_year[row["forecast_year"]]
        assert row["dominant_non_pass_through_driver_row_id"] == existing[
            "forecast_path_ratio_driver_dominance_row_id"
        ]
        assert row["dominant_non_pass_through_axis"] in {
            "channel_conversion_profile_id",
            "mpc_scenario",
            "maturity_scenario",
            "holder_scenario",
        }
        assert row["dominance_comparison_classification"] in {
            "pass_through_larger_mover_than_non_pass_through_driver",
            "pass_through_smaller_mover_than_non_pass_through_driver",
            "pass_through_same_size_as_non_pass_through_driver",
        }

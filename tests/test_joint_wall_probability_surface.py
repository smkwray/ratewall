from __future__ import annotations

import pytest
import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUTS = Path("outputs/tables")
TABLE_PLATE = Path("outputs/reports/ratewall_table_plate.md")
RELEASE_INDEX = Path("outputs/reports/ratewall_release_artifact_index.md")
SOURCE_ARCHIVE = Path("outputs/release/ratewall_release_23_0_source_archive.zip")
SURFACE_SEED = "deterministic_grid_ratewall_joint_wall_probability_v1"
PROBABILITY_CLAIM = (
    "conditional_named_grid_share_not_empirical_or_posterior_probability"
)


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def test_joint_wall_probability_axis_registry_names_axes_and_blocks_probability_claims() -> None:
    rows = _rows("ratewall_joint_wall_probability_axis_registry.csv")
    _assert_fail_closed(rows)

    by_axis = {row["axis_id"]: row for row in rows}
    assert set(by_axis) == {
        "recipient_current_demand_conversion",
        "runtime_denominator_drag_case",
        "tdc_deposit_current_demand_conversion",
        "deposit_pass_through_beta",
        "holder_route",
        "maturity_repricing_path",
        "object_family_guardrail",
        "probability_interpretation",
    }
    assert by_axis["object_family_guardrail"]["blocked_surface_use"] == (
        "legacy_static_assumption_mode;bounded_h8_review_only;policy_path_review_only"
    )
    assert by_axis["probability_interpretation"]["axis_values"] == PROBABILITY_CLAIM
    assert "posterior_probability" in by_axis["probability_interpretation"][
        "blocked_surface_use"
    ]


def test_joint_wall_probability_surface_keeps_object_families_separate() -> None:
    rows = _rows("ratewall_joint_wall_probability_surface.csv")
    _assert_fail_closed(rows)

    assert len(rows) == 2673
    assert {row["surface_seed"] for row in rows} == {SURFACE_SEED}
    assert {row["prior_pack_id"] for row in rows} == {"named_grid_equal_weight_v1"}
    assert {row["probability_claim_status"] for row in rows} == {PROBABILITY_CLAIM}
    assert {row["object_family_index_status"] for row in rows} == {
        "pass_active_output_index_guardrail"
    }
    assert {row["headline_surface_allowed"] for row in rows} == {"true"}

    admitted_families = {row["object_family"] for row in rows}
    assert admitted_families == {
        "runtime_empirical_annual_flow",
        "forecast_tdc_family",
        "forecast_path_beta_sensitivity",
    }
    forbidden_text = ";".join(
        row["object_family"]
        + ";"
        + row["denominator_anchor_id"]
        + ";"
        + row["source_artifact"]
        for row in rows
    )
    assert "legacy_assumption_anchor_base_current_100bps" not in forbidden_text
    assert "bounded_h8" not in forbidden_text
    assert "policy_path" not in forbidden_text

    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in rows:
        counts[
            (
                row["object_family"],
                row["support_variant"],
                row["denominator_case"],
            )
        ] += 1
    assert counts[
        (
            "runtime_empirical_annual_flow",
            "runtime_support_offset_100bp_year_equivalent",
            "center_drag",
        )
    ] == 297
    assert counts[
        (
            "runtime_empirical_annual_flow",
            "runtime_support_offset_100bp_year_equivalent",
            "ci95_low_drag",
        )
    ] == 297
    assert counts[
        (
            "runtime_empirical_annual_flow",
            "runtime_support_offset_100bp_year_equivalent",
            "ci95_high_drag",
        )
    ] == 297
    assert counts[
        ("forecast_tdc_family", "interest_only_support", "forecast_conventional_drag")
    ] == 297
    assert counts[
        ("forecast_tdc_family", "tdc_ex_overlap_support", "forecast_conventional_drag")
    ] == 297
    assert counts[
        (
            "forecast_path_beta_sensitivity",
            "explicit_pass_through_beta_support",
            "forecast_path_denominator",
        )
    ] == 1188


def test_joint_wall_probability_summary_matches_surface_counts() -> None:
    surface = _rows("ratewall_joint_wall_probability_surface.csv")
    summary = _rows("ratewall_joint_wall_probability_summary.csv")
    _assert_fail_closed(summary)

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in surface:
        grouped[
            (row["object_family"], row["support_variant"], row["denominator_case"])
        ].append(row)

    assert len(summary) == len(grouped)
    for row in summary:
        key = (row["object_family"], row["support_variant"], row["denominator_case"])
        source_rows = grouped[key]
        hit_count = sum(source_row["wall_hit"] == "true" for source_row in source_rows)
        expected_share = Decimal(hit_count) / Decimal(len(source_rows))
        assert int(row["surface_row_count"]) == len(source_rows)
        assert int(row["wall_hit_count"]) == hit_count
        assert Decimal(row["conditional_wall_hit_share"]) == expected_share
        assert row["probability_claim_status"] == PROBABILITY_CLAIM
        assert "empirical_probability_claim" in row["blocked_use"]


def test_joint_wall_probability_monotonicity_for_materialized_axes() -> None:
    rows = _rows("ratewall_joint_wall_probability_surface.csv")

    runtime_groups: dict[tuple[str, str, str, str], dict[str, Decimal]] = defaultdict(dict)
    for row in rows:
        if row["object_family"] == "runtime_empirical_annual_flow":
            runtime_groups[
                (
                    row["forecast_year"],
                    row["mpc_scenario"],
                    row["maturity_scenario"],
                    row["holder_scenario"],
                )
            ][row["denominator_case"]] = Decimal(row["wall_ratio_or_offset"])
    for values in runtime_groups.values():
        assert values["ci95_low_drag"] >= values["center_drag"]
        assert values["center_drag"] >= values["ci95_high_drag"]

    tdc_groups: dict[tuple[str, str, str], list[tuple[Decimal, Decimal]]] = defaultdict(list)
    for row in rows:
        if (
            row["object_family"] == "forecast_tdc_family"
            and row["support_variant"] == "tdc_ex_overlap_support"
        ):
            tdc_groups[
                (row["forecast_year"], row["maturity_scenario"], row["holder_scenario"])
            ].append(
                (
                    Decimal(row["tdc_deposit_conversion_axis"]),
                    Decimal(row["wall_ratio_or_offset"]),
                )
            )
    for values in tdc_groups.values():
        ordered = sorted(values)
        assert all(
            ordered[index][1] <= ordered[index + 1][1]
            for index in range(len(ordered) - 1)
        )

    beta_groups: dict[tuple[str, str, str, str], list[tuple[Decimal, Decimal]]] = defaultdict(list)
    for row in rows:
        if row["object_family"] == "forecast_path_beta_sensitivity":
            beta_groups[
                (
                    row["forecast_year"],
                    row["mpc_scenario"],
                    row["maturity_scenario"],
                    row["holder_scenario"],
                )
            ].append(
                (
                    Decimal(row["pass_through_beta"]),
                    Decimal(row["wall_ratio_or_offset"]),
                )
            )
    for values in beta_groups.values():
        ordered = sorted(values)
        nondecreasing = all(
            ordered[index][1] <= ordered[index + 1][1]
            for index in range(len(ordered) - 1)
        )
        nonincreasing = all(
            ordered[index][1] >= ordered[index + 1][1]
            for index in range(len(ordered) - 1)
        )
        assert nondecreasing or nonincreasing


def test_joint_wall_probability_outputs_are_released_and_archived() -> None:
    expected = {
        "ratewall_joint_wall_probability_axis_registry.csv",
        "ratewall_joint_wall_probability_surface.csv",
        "ratewall_joint_wall_probability_summary.csv",
    }
    for path in (TABLE_PLATE, RELEASE_INDEX):
        text = path.read_text(encoding="utf-8")
        for name in expected:
            assert name in text

    active = {Path(row["artifact_path"]).name for row in _rows("ratewall_active_output_index.csv")}
    assert expected <= active
    assert SOURCE_ARCHIVE.exists()


def test_wall_denominator_contract_blocks_runtime_anchor_overclaiming() -> None:
    rows = _rows("ratewall_wall_denominator_path_contract.csv")
    _assert_fail_closed(rows)

    runtime_default = next(
        row
        for row in rows
        if row["wall_denominator_path_contract_row_id"] == "wall_denom_contract::0001"
    )
    assert runtime_default["ratio_object_id"] == "rw_runtime_support_offset_af_fixed"
    assert runtime_default["denominator_object_id"] == (
        "literature_annual_flow_bridge_candidate"
    )
    assert runtime_default["runtime_direct_ratio_allowed"] == "true"
    assert runtime_default["historical_primary_allowed"] == "false"
    assert runtime_default["forecast_primary_allowed"] == "false"
    assert "canonical_rw_y" in runtime_default["blocked_use"]
    assert "Evidence_Mode" in runtime_default["blocked_use"]
    assert "denominator_prior" in runtime_default["blocked_use"]
    assert "support-offset diagnostics only" in runtime_default["safe_sentence"]

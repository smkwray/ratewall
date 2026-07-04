from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from ratewall.databook.denominator_bridge_program import (
    _LEGACY_ANCHOR_NAMES,
    _LITERATURE_SOURCE_ID,
    _PRIMARY_BOUNDED_SOURCE_ID,
    _annual_support_denominator_compatibility_registry_rows,
    _blocked_residualized_ffr_bridge_state,
    _denominator_scale_conflict_adjudication_rows,
)
from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS


OUTPUT_TABLES = Path("outputs/tables")
ARTIFACT = "ratewall_annual_flow_runtime_family_registry.csv"


def _rows() -> list[dict[str, str]]:
    with (OUTPUT_TABLES / ARTIFACT).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_runtime_family_registry_promotes_literature_and_keeps_legacy_as_sensitivity_only() -> None:
    rows = {row["denominator_source_id"]: row for row in _rows()}

    literature = rows["literature_annual_flow_bridge_candidate"]
    assert literature["default_runtime_anchor"] == "true"
    assert literature["scenario_runtime_allowed"] == "true"
    assert literature["runtime_family_role"] == (
        "primary_empirical_annual_flow_runtime_anchor"
    )
    assert Decimal(literature["runtime_anchor_value_pp_gdp"]) == Decimal("0.776")
    assert Decimal(literature["runtime_ci95_low_pp_gdp"]) == Decimal(
        "0.409223074571"
    )
    assert Decimal(literature["runtime_ci95_high_pp_gdp"]) == Decimal(
        "1.143212012336"
    )

    legacy = rows["legacy_assumption_anchor_base_current_100bps"]
    assert legacy["default_runtime_anchor"] == "false"
    assert legacy["sensitivity_only"] == "true"
    assert legacy["scenario_runtime_allowed"] == "true"
    assert legacy["runtime_policy_status"] == (
        "pass_assumption_mode_sensitivity_only_not_default_runtime"
    )


def test_runtime_family_registry_keeps_forbidden_switches_false() -> None:
    for row in _rows():
        assert row["canonical_ratio_entry"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        for field in FORBIDDEN_SWITCH_FIELDS:
            assert row[field] == "false"


def test_denominator_compatibility_fails_closed_without_literature_h8_translation() -> None:
    blocked_bridge = _blocked_residualized_ffr_bridge_state(
        blocker="fixture_missing_residualized_ffr_inputs"
    )
    anchor_rows = [
        {
            "denominator_source_id": source_id,
            "timing_alignment_class": timing_class,
        }
        for source_id, timing_class in (
            (_LEGACY_ANCHOR_NAMES["base_current_100bps"], "annual_flow"),
            (_LEGACY_ANCHOR_NAMES["high_fiscal_offset_no_hit"], "annual_flow"),
            (_LITERATURE_SOURCE_ID, "blocked_annual_window_formalization_pending"),
            (_PRIMARY_BOUNDED_SOURCE_ID, "blocked_not_annual_flow_h8_cumulative"),
        )
    ]

    rows = _annual_support_denominator_compatibility_registry_rows(
        annual_flow_anchor_registry_rows=anchor_rows,
        residualized_bridge=blocked_bridge,
        frbus_100bp_year_fspdp_proxy_benchmark_rows=[],
    )
    literature_h8 = next(
        row
        for row in rows
        if row["compatibility_row_id"]
        == "annual_support_denominator_compatibility::literature_h8_mapped"
    )

    assert literature_h8["translation_row_id"] == ""
    assert literature_h8["comparability_status"] == (
        "blocked_literature_h8_translation_missing"
    )
    assert literature_h8["allowed_use"] == "methodology_scaffold_only"
    assert "residualized-FFR replication inputs" in literature_h8["exact_blocker"]


def test_scale_conflict_rows_fail_closed_without_literature_translations() -> None:
    blocked_bridge = _blocked_residualized_ffr_bridge_state(
        blocker="fixture_missing_residualized_ffr_inputs"
    )
    anchor_rows = [
        {
            "denominator_source_id": _LEGACY_ANCHOR_NAMES["base_current_100bps"],
            "denominator_source_class": "legacy_current_100bps",
            "timing_alignment_class": "annual_flow",
            "anchor_value_pp_gdp": "0.35",
        },
        {
            "denominator_source_id": _LEGACY_ANCHOR_NAMES[
                "high_fiscal_offset_no_hit"
            ],
            "denominator_source_class": "legacy_high",
            "timing_alignment_class": "annual_flow",
            "anchor_value_pp_gdp": "1.30",
        },
        {
            "denominator_source_id": _LITERATURE_SOURCE_ID,
            "denominator_source_class": "residualized_ffr_literature_bridge",
            "timing_alignment_class": "blocked_annual_window_formalization_pending",
            "anchor_value_pp_gdp": "",
        },
    ]
    rows = _denominator_scale_conflict_adjudication_rows(
        bounded_denominator_registry_rows=[
            {
                "primary_denominator_horizon": "true",
                "review_center_d_y": "9.0",
                "bounded_ci_low_d_y": "6.0",
                "bounded_ci_high_d_y": "12.0",
            }
        ],
        annual_flow_anchor_registry_rows=anchor_rows,
        residualized_bridge=blocked_bridge,
        frbus_100bp_year_fspdp_proxy_benchmark_rows=[
            {
                "component_mapping_id": "ecnia_plus_ebfi_plus_eh_fspdp_proxy",
                "component_id": "fspdp_proxy",
                "horizon_q": "8",
                "model_d_y_per_100bp_year": "1.1",
            }
        ],
    )
    rows_by_id = {row["adjudication_row_id"]: row for row in rows}

    annual_flow = rows_by_id[
        "denominator_scale_conflict::annual_flow_base_vs_literature_year1"
    ]
    assert annual_flow["adjudication_status"] == (
        "blocked_literature_year1_translation_missing"
    )
    assert annual_flow["right_value_pp_gdp_per_100bp_year"] == ""
    assert "residualized-FFR replication inputs" in annual_flow["exact_blocker"]

    literature_h8 = rows_by_id[
        "denominator_scale_conflict::bounded_h8_vs_literature_h8"
    ]
    assert literature_h8["adjudication_status"] == (
        "blocked_literature_h8_translation_missing"
    )
    assert literature_h8["right_value_pp_gdp_per_100bp_year"] == ""
    assert "residualized-FFR replication inputs" in literature_h8["exact_blocker"]

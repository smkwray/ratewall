from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS


OUTPUT_TABLES = Path("outputs/tables")
ARTIFACT = "ratewall_annual_flow_denominator_anchor_registry.csv"


def _rows() -> list[dict[str, str]]:
    with (OUTPUT_TABLES / ARTIFACT).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_annual_flow_anchor_registry_promotes_literature_runtime_anchor_and_blocks_h8_as_anchor() -> None:
    rows = {row["denominator_source_id"]: row for row in _rows()}
    assert {
        "legacy_assumption_anchor_base_current_100bps",
        "legacy_assumption_anchor_high_fiscal_offset_no_hit",
        "literature_annual_flow_bridge_candidate",
        "bounded_h8_overlay_review_center",
    } <= set(rows)

    assert Decimal(rows["legacy_assumption_anchor_base_current_100bps"]["anchor_value_pp_gdp"]) == Decimal(
        "0.776"
    )
    assert Decimal(
        rows["legacy_assumption_anchor_high_fiscal_offset_no_hit"][
            "anchor_value_pp_gdp"
        ]
    ) == Decimal("0.7")
    assert (
        rows["legacy_assumption_anchor_base_current_100bps"]["scenario_runtime_allowed"]
        == "true"
    )
    assert (
        rows["legacy_assumption_anchor_high_fiscal_offset_no_hit"][
            "anchor_empirical_status"
        ]
        == "pass_assumption_mode_sensitivity_only_not_default_runtime"
    )
    assert rows["legacy_assumption_anchor_base_current_100bps"]["anchor_role"] == (
        "fallback_assumption_mode_sensitivity_anchor"
    )

    assert (
        rows["literature_annual_flow_bridge_candidate"]["scenario_runtime_allowed"]
        == "true"
    )
    assert rows["literature_annual_flow_bridge_candidate"]["anchor_empirical_status"] == (
        "pass_primary_empirical_annual_flow_runtime_anchor"
    )
    assert "default empirical runtime anchor" in rows["literature_annual_flow_bridge_candidate"][
        "exact_blocker"
    ]
    assert rows["literature_annual_flow_bridge_candidate"]["timing_alignment_class"] == (
        "annual_flow_h4_endpoint_proxy"
    )
    assert rows["literature_annual_flow_bridge_candidate"]["anchor_role"] == (
        "primary_empirical_annual_flow_runtime_anchor"
    )
    assert (
        Decimal(rows["literature_annual_flow_bridge_candidate"]["anchor_value_pp_gdp"])
        > Decimal("0")
    )

    assert rows["bounded_h8_overlay_review_center"]["scenario_runtime_allowed"] == "false"
    assert rows["bounded_h8_overlay_review_center"]["timing_alignment_class"] == (
        "blocked_not_annual_flow_h8_cumulative"
    )
    assert rows["bounded_h8_overlay_review_center"]["anchor_role"] == (
        "overlay_only_not_annual_flow_anchor"
    )


def test_annual_flow_anchor_registry_preserves_guardrails() -> None:
    for row in _rows():
        assert row["canonical_ratio_entry"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        for field in FORBIDDEN_SWITCH_FIELDS:
            assert row[field] == "false"

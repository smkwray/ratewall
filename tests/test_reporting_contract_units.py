from __future__ import annotations

from decimal import Decimal

import pytest

from ratewall.databook.denominator_bridge_program import (
    _annual_support_numerator_contract_rows,
    _annual_support_numerator_uncertainty_envelope_rows,
    _runtime_annual_flow_support_offset_scenario_rows,
)
from ratewall.rwtam.v1 import _headline_row


_DENOMINATOR_SOURCE_IDS = (
    "literature_annual_flow_bridge_candidate",
    "legacy_assumption_anchor_base_current_100bps",
    "legacy_assumption_anchor_high_fiscal_offset_no_hit",
    "bounded_h8_overlay_review_center",
    "literature_h8_mapped_review_only",
    "frbus_h8_component_proxy",
)


def _headline_output() -> dict[str, str]:
    return _headline_row(
        {
            "year": "2026",
            "dose_mode": "persistent_level",
            "band": "base",
            "ricardian_offset": Decimal("0"),
            "N": Decimal("20"),
            "D": Decimal("10"),
            "net": Decimal("10"),
            "nominal_gdp_bil": Decimal("200"),
            "RW": Decimal("2"),
            "bottom_up_D_to_legacy_D": Decimal("1"),
        },
        "annual",
    )


def _synthetic_contract_row() -> dict[str, str]:
    return {
        "contract_row_id": "contract::2026::base",
        "ratio_id": "RW_Y",
        "forecast_year": "2026",
        "mpc_scenario": "base_mpc_10pct",
        "maturity_scenario": "current_wam_cbo_rate_path",
        "holder_scenario": "current_holder_distribution",
        "nominal_gdp_bil": "200",
        "runtime_current_window_numerator_bil": "10",
        "support_gdp_pct": "5",
        "timing_class": "annual_flow_current_window",
        "uncertainty_status": "synthetic_unit_test",
        "reconciliation_status": "pass_direct_components_reconcile_to_runtime_numerator",
        "runtime_allowed": "true",
        "exact_blocker": "",
        "blocked_use": "canonical_RW_Y",
    }


def _synthetic_source_gate_row() -> dict[str, str]:
    return {
        "contract_row_id": "contract::2026::base",
        "runtime_component_eligible": "true",
        "source_gate_status": "pass_direct_runtime_component_source_classified",
        "exact_blocker": "",
    }


def _synthetic_uncertainty_rows() -> list[dict[str, str]]:
    return _annual_support_numerator_uncertainty_envelope_rows(
        annual_support_numerator_contract_rows=[_synthetic_contract_row()],
        annual_support_numerator_source_gate_rows=[_synthetic_source_gate_row()],
    )


def _synthetic_runtime_rows() -> list[dict[str, str]]:
    anchors = [
        {
            "denominator_source_id": source_id,
            "denominator_source_class": "synthetic_annual_flow_anchor",
            "anchor_role": "synthetic_unit_test",
            "anchor_value_pp_gdp": "2",
        }
        for source_id in _DENOMINATOR_SOURCE_IDS
    ]
    runtime_families = [
        {
            "denominator_source_id": source_id,
            "runtime_anchor_value_pp_gdp": "2",
            "runtime_ci95_low_pp_gdp": "1",
            "runtime_ci95_high_pp_gdp": "3",
            "runtime_family_role": "synthetic_unit_test",
            "default_runtime_anchor": (
                "true"
                if source_id == "literature_annual_flow_bridge_candidate"
                else "false"
            ),
            "sensitivity_only": "false",
        }
        for source_id in _DENOMINATOR_SOURCE_IDS
    ]
    compatibility = [
        {
            "denominator_source_id": source_id,
            "runtime_anchor_allowed": "true",
            "support_offset_computation_allowed": "true",
            "denominator_timing_class": "annual_flow_direct",
            "exact_blocker": "",
            "safe_sentence": "Synthetic unit-test row.",
            "next_backend_action": "none",
            "allowed_use": "synthetic_unit_test",
            "blocked_use": "canonical_RW_Y",
        }
        for source_id in _DENOMINATOR_SOURCE_IDS
    ]
    return _runtime_annual_flow_support_offset_scenario_rows(
        annual_support_numerator_contract_rows=[_synthetic_contract_row()],
        annual_support_numerator_source_gate_rows=[_synthetic_source_gate_row()],
        annual_support_numerator_uncertainty_envelope_rows=(
            _synthetic_uncertainty_rows()
        ),
        annual_flow_anchor_registry_rows=anchors,
        annual_flow_runtime_family_registry_rows=runtime_families,
        annual_support_denominator_compatibility_registry_rows=compatibility,
    )


def _assert_gdp_unit_suffixes(
    row: dict[str, str],
    *,
    expected_share: Decimal,
) -> None:
    unit_fields = {
        field: value
        for field, value in row.items()
        if field.endswith(("_gdp_share", "_gdp_pct"))
    }
    assert unit_fields
    for field, value in unit_fields.items():
        expected = (
            expected_share * Decimal("100")
            if field.endswith("_gdp_pct")
            else expected_share
        )
        assert Decimal(value) == expected


def test_gdp_unit_suffixes_distinguish_fraction_from_percentage() -> None:
    headline = _headline_output()
    contract = _annual_support_numerator_contract_rows(
        annual_support_numerator_component_registry_rows=[
            {
                "contract_row_id": "contract::2026",
                "forecast_year": "2026",
                "mpc_scenario": "base",
                "maturity_scenario": "base",
                "holder_scenario": "base",
                "component_id": "combined_current_demand_support_total",
                "component_value_bil": "10",
                "directly_added_to_final_numerator": "true",
            }
        ],
        forecast_holder_tdc_consistency_bridge_rows=[
            {
                "forecast_year": "2026",
                "mpc_scenario": "base",
                "maturity_scenario": "base",
                "holder_scenario": "base",
                "nominal_gdp_bil": "200",
            }
        ],
    )[0]

    _assert_gdp_unit_suffixes(headline, expected_share=Decimal("0.05"))
    _assert_gdp_unit_suffixes(contract, expected_share=Decimal("0.05"))
    assert "net_pct_gdp" not in headline
    assert "support_pct_of_gdp" not in contract


def test_uncertainty_envelope_gdp_pct_keys_and_units() -> None:
    row = _synthetic_uncertainty_rows()[0]

    _assert_gdp_unit_suffixes(row, expected_share=Decimal("0.05"))
    assert "support_pct_current_gdp" not in row
    assert "support_pct_lower_bound_gdp" not in row
    assert "support_pct_base_case_gdp" not in row
    assert "support_pct_upper_bound_gdp" not in row


def test_runtime_support_offset_gdp_pct_keys_and_units() -> None:
    rows = _synthetic_runtime_rows()

    assert len(rows) == len(_DENOMINATOR_SOURCE_IDS)
    for row in rows:
        _assert_gdp_unit_suffixes(row, expected_share=Decimal("0.05"))
        assert "support_pct_of_gdp" not in row
        assert "support_pct_of_gdp_numerator_lower_bound" not in row
        assert "support_pct_of_gdp_numerator_base_case" not in row
        assert "support_pct_of_gdp_numerator_upper_bound" not in row


def test_gdp_share_scaling_mutation_fails_schema_contract() -> None:
    row = _headline_output()
    row["net_gdp_share"] = str(
        Decimal(row["net_gdp_share"]) * Decimal("100")
    )

    with pytest.raises(AssertionError):
        _assert_gdp_unit_suffixes(row, expected_share=Decimal("0.05"))

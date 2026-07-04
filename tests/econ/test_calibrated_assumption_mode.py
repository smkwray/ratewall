from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from ratewall.accounting.assumption_engine import (
    CONVENTIONAL_DRAG_COMPONENT_EVIDENCE_STATUS,
    CONVENTIONAL_DRAG_COMPONENT_VALUE_BASIS,
    CONVENTIONAL_DRAG_DECOMPOSITION_STATUS,
    DENOMINATOR_REALLOCATION_SIDECAR_IMPACT_RULE,
    DENOMINATOR_REPLACEMENT_IMPACT_ALLOWED_USE,
    DENOMINATOR_REPLACEMENT_IMPACT_BLOCKED_USE,
    DENOMINATOR_REPLACEMENT_IMPACT_STATUS,
    DENOMINATOR_REPLACEMENT_ALLOWED_USE,
    DENOMINATOR_REPLACEMENT_BLOCKED_USE,
    DENOMINATOR_REPLACEMENT_EVIDENCE_STATUS,
    DENOMINATOR_REPLACEMENT_MAIN_RATIO_RULE,
    DENOMINATOR_REPLACEMENT_RESEARCH_STATUS,
    DEFAULT_RATEWALL_ASSUMPTIONS,
    TDSP_BORROWING_COST_DIAGNOSTIC_LENS_ROLE,
    TDSP_BORROWING_COST_OVERLAP_RULE,
    TDSP_IMPACT_CANDIDATE_LENS,
    TDSP_IMPACT_REQUIRED_EVIDENCE,
    conventional_drag_decomposition_rows,
    conventional_drag_replacement_reallocation_impact_rows,
    conventional_drag_replacement_reallocation_contract_rows,
    net_countervailing_channel_rows,
    solve_assumption,
    split_denominator_comparison_row,
)
from ratewall.accounting.ratewall_threshold import (
    CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
    CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE_HIGH,
    CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE_LOW,
    DEFAULT_THRESHOLD_SCENARIOS,
)
from ratewall.databook.path_ratio_program import (
    LITERATURE_ANNUAL_FLOW_RUNTIME_ANCHOR_INTERVAL_PP,
    LITERATURE_ANNUAL_FLOW_RUNTIME_ANCHOR_PP_STR,
    LITERATURE_ANNUAL_FLOW_RUNTIME_ANCHOR_SHARE,
    _forecast_channel_conversion_profile_specs,
    _forecast_profile_supports,
    forecast_path_ratio_pass_through_scenario_registry_rows,
    ratio_object_registry_rows,
)
from ratewall.databook.tdcsim_contracts import (
    tdc_forward_assumption_registry_rows,
    tdc_forward_component_audit_rows,
    tdc_forward_invariant_audit_rows,
    tdc_forward_overlap_guardrail_rows,
    tdc_forward_projection_surface_rows,
)


SOLVER_INPUTS = {
    "gdp_bil": Decimal("1000"),
    "treasury_interest_impulse_bil": Decimal("10"),
    "iorb_interest_impulse_bil": Decimal("5"),
    "on_rrp_interest_impulse_bil": Decimal("3"),
    "current_remittance_reduction_bil": Decimal("1"),
    "future_remittance_drag_bil": Decimal("1"),
}
ASSUMPTION_SETS = Path(__file__).resolve().parents[2] / "configs" / (
    "ratewall_assumption_sets.yml"
)
SOURCE_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "sources.yml"


def _assumption(name: str):
    return next(
        assumption
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
        if assumption.name == name
    )


def _solve(assumption):
    return solve_assumption(assumption=assumption, **SOLVER_INPUTS)


def _ratio(result: dict[str, str]) -> Decimal:
    return Decimal(result["ratewall_offset_ratio"])


def _assert_scalar_numerator_reconciles(result: dict[str, str]) -> None:
    channel_total = sum(
        Decimal(row["scalar_channel_value_bil"])
        for row in net_countervailing_channel_rows(result)
        if row["directly_added_to_final_numerator"] == "true"
    )
    assert channel_total == Decimal(result["scalar_countervailing_total_bil"])


def _assert_scalar_denominator_reconciles(result: dict[str, str]) -> None:
    component_total = sum(
        Decimal(row["headline_denominator_component_value_bil"])
        for row in conventional_drag_decomposition_rows(result)
    )
    assert component_total == Decimal(result["conventional_contractionary_effect_bil"])


def test_conventional_drag_decomposition_is_fixed_allocation_not_additive_tdsp() -> None:
    result = _solve(_assumption("literature_calibrated_base"))
    rows = conventional_drag_decomposition_rows(result)
    by_component = {row["denominator_component"]: row for row in rows}

    assert set(by_component) == {
        "borrowing_cost_drag",
        "credit_supply_drag",
        "asset_price_drag",
        "expectations_drag",
        "exchange_rate_external_drag",
    }
    assert sum(Decimal(row["component_value_bil"]) for row in rows) == Decimal(
        result["split_denominator_conventional_drag_bil"]
    )
    assert sum(
        Decimal(row["headline_denominator_component_value_bil"]) for row in rows
    ) == Decimal(result["conventional_contractionary_effect_bil"])
    assert {row["component_value_basis"] for row in rows} == {
        CONVENTIONAL_DRAG_COMPONENT_VALUE_BASIS
    }
    assert {row["denominator_allocation_status"] for row in rows} == {
        CONVENTIONAL_DRAG_DECOMPOSITION_STATUS
    }
    assert {row["component_evidence_status"] for row in rows} == {
        CONVENTIONAL_DRAG_COMPONENT_EVIDENCE_STATUS
    }
    assert {row["incremental_drag_allowed"] for row in rows} == {"false"}
    assert {
        row["main_ratio_effect_requires_denominator_replacement"] for row in rows
    } == {"true"}
    assert {row["tdsp_current_demand_incremental_drag_allowed"] for row in rows} == {
        "false"
    }

    borrowing = by_component["borrowing_cost_drag"]
    assert borrowing["tdsp_current_demand_lens_role"] == (
        TDSP_BORROWING_COST_DIAGNOSTIC_LENS_ROLE
    )
    assert borrowing["tdsp_current_demand_overlap_rule"] == (
        TDSP_BORROWING_COST_OVERLAP_RULE
    )
    for component, row in by_component.items():
        if component == "borrowing_cost_drag":
            continue
        assert row["tdsp_current_demand_lens_role"] == (
            "not_tdsp_current_demand_lens_component"
        )
        assert row["tdsp_current_demand_overlap_rule"] == (
            "tdsp_not_assigned_to_this_denominator_component"
        )


def test_conventional_drag_decomposition_keeps_scalar_and_split_bases_separate() -> None:
    scaled = replace(
        _assumption("literature_calibrated_base"),
        split_denominator_total_drag_multiplier=Decimal("1.20"),
    )
    result = _solve(scaled)
    rows = conventional_drag_decomposition_rows(result)

    assert Decimal(result["split_denominator_conventional_drag_bil"]) > Decimal(
        result["conventional_contractionary_effect_bil"]
    )
    assert sum(Decimal(row["component_value_bil"]) for row in rows) == Decimal(
        result["split_denominator_conventional_drag_bil"]
    )
    assert sum(
        Decimal(row["headline_denominator_component_value_bil"]) for row in rows
    ) == Decimal(result["conventional_contractionary_effect_bil"])


def test_tdsp_source_metadata_stays_out_of_conventional_drag_proxy_slot() -> None:
    sources = yaml.safe_load(SOURCE_CONFIG.read_text(encoding="utf-8"))["series"]

    assert sources["TDSP"]["liability_channel"] == "private_credit"
    assert sources["TDSP"]["liability_channel"] != (
        "conventional_drag_borrowing_cost_proxy"
    )
    assert sources["BAA"]["liability_channel"] == (
        "conventional_drag_borrowing_cost_proxy"
    )
    assert sources["TREASURY_HQM_EOM_10Y_PAR"]["liability_channel"] == (
        "conventional_drag_borrowing_cost_proxy"
    )


def test_denominator_replacement_contract_is_fail_closed_and_nonadditive() -> None:
    result = _solve(_assumption("literature_calibrated_base"))
    rows = conventional_drag_replacement_reallocation_contract_rows(result)
    by_component = {row["denominator_component"]: row for row in rows}

    assert set(by_component) == {
        "borrowing_cost_drag",
        "credit_supply_drag",
        "asset_price_drag",
        "expectations_drag",
        "exchange_rate_external_drag",
    }
    assert sum(
        Decimal(row["headline_denominator_component_value_bil"]) for row in rows
    ) == Decimal(result["conventional_contractionary_effect_bil"])
    assert sum(
        Decimal(row["split_denominator_component_value_bil"]) for row in rows
    ) == Decimal(result["split_denominator_conventional_drag_bil"])
    assert {row["replacement_reallocation_status"] for row in rows} == {
        DENOMINATOR_REPLACEMENT_RESEARCH_STATUS
    }
    assert {row["component_replacement_evidence_status"] for row in rows} == {
        DENOMINATOR_REPLACEMENT_EVIDENCE_STATUS
    }
    assert {row["main_ratio_effect_rule"] for row in rows} == {
        DENOMINATOR_REPLACEMENT_MAIN_RATIO_RULE
    }
    for field in (
        "share_reallocation_behaviorally_neutral",
        "additive_drag_allowed",
        "replacement_denominator_admitted",
        "reallocation_admitted",
        "denominator_prior_update_allowed",
        "enters_main_ratio",
        "canonical_ratio_entry",
        "evidence_mode_enabled",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "main_offset_ratio_changed_this_tranche",
        "dynamic_equation_changed_this_tranche",
    ):
        assert {row[field] for row in rows} == {"false"}
    assert {row["allowed_use"] for row in rows} == {
        DENOMINATOR_REPLACEMENT_ALLOWED_USE
    }
    assert {row["blocked_use"] for row in rows} == {
        DENOMINATOR_REPLACEMENT_BLOCKED_USE
    }
    assert {row["sidecar_subbase_impact_review_required"] for row in rows} == {
        "true"
    }
    assert {row["sidecar_subbase_impact_boundary"] for row in rows} == {
        "share_reallocation_can_change_borrowing_credit_sidecar_bases_even_when_"
        "headline_denominator_is_unchanged"
    }
    assert all(
        "sidecar_subbase_impact_review" in row["required_evidence"]
        for row in rows
    )

    borrowing = by_component["borrowing_cost_drag"]
    assert borrowing["candidate_diagnostic_lens"] == (
        "tdsp_household_debt_service_context_only_for_borrowing_cost_subcomponent"
    )
    assert borrowing["tdsp_role"] == (
        "tdsp_may_reallocate_borrowing_cost_subcomponent_only_after_core_"
        "current_demand_bridge_and_policy_path_admission"
    )
    for component, row in by_component.items():
        if component == "borrowing_cost_drag":
            continue
        assert row["tdsp_role"].startswith("tdsp_not_assigned_to_")


def test_denominator_replacement_impact_model_is_fail_closed_for_tdsp() -> None:
    result = _solve(_assumption("literature_calibrated_base"))
    rows = conventional_drag_replacement_reallocation_impact_rows(
        result,
        candidate_lens=TDSP_IMPACT_CANDIDATE_LENS,
        proposed_effect="reallocation",
    )
    by_component = {row["denominator_component"]: row for row in rows}

    assert set(by_component) == {
        "borrowing_cost_drag",
        "credit_supply_drag",
        "asset_price_drag",
        "expectations_drag",
        "exchange_rate_external_drag",
    }
    assert by_component["borrowing_cost_drag"]["component_scope_status"] == (
        "candidate_lens_matches_borrowing_cost_drag_diagnostic_only"
    )
    assert by_component["borrowing_cost_drag"]["candidate_lens_scope_match"] == "true"
    for component, row in by_component.items():
        if component == "borrowing_cost_drag":
            continue
        assert row["component_scope_status"] == (
            "blocked_candidate_lens_outside_component_scope"
        )
        assert row["candidate_lens_scope_match"] == "false"

    assert {row["impact_status"] for row in rows} == {
        DENOMINATOR_REPLACEMENT_IMPACT_STATUS
    }
    assert {row["required_evidence_before_effect"] for row in rows} == {
        TDSP_IMPACT_REQUIRED_EVIDENCE
    }
    assert {row["allowed_use"] for row in rows} == {
        DENOMINATOR_REPLACEMENT_IMPACT_ALLOWED_USE
    }
    assert {row["blocked_use"] for row in rows} == {
        DENOMINATOR_REPLACEMENT_IMPACT_BLOCKED_USE
    }
    for field in (
        "replacement_denominator_admitted",
        "reallocation_admitted",
        "additive_drag_allowed",
        "runtime_denominator_effect_allowed",
        "main_ratio_effect_allowed",
        "denominator_prior_update_allowed",
        "enters_main_ratio",
        "canonical_ratio_entry",
        "evidence_mode_enabled",
        "formula_replacement_allowed",
        "split_denominator_promotion_allowed",
        "main_offset_ratio_changed_this_tranche",
        "dynamic_equation_changed_this_tranche",
        "share_reallocation_behaviorally_neutral",
    ):
        assert {row[field] for row in rows} == {"false"}
    for field in (
        "headline_denominator_delta_bil",
        "split_denominator_delta_bil",
        "main_ratio_delta_bil",
    ):
        assert {row[field] for row in rows} == {"0"}
    assert {row["sidecar_subbase_impact_review_required"] for row in rows} == {
        "true"
    }
    assert {row["sidecar_subbase_impact_rule"] for row in rows} == {
        DENOMINATOR_REALLOCATION_SIDECAR_IMPACT_RULE
    }


@pytest.mark.parametrize(
    ("proposed_effect", "expected_sidecar_review", "expected_sidecar_rule"),
    (
        (
            "diagnostic",
            "false",
            "not_applicable_no_share_reallocation_requested",
        ),
        (
            "replacement",
            "false",
            "not_applicable_no_share_reallocation_requested",
        ),
        (
            "reallocation",
            "true",
            DENOMINATOR_REALLOCATION_SIDECAR_IMPACT_RULE,
        ),
    ),
)
def test_denominator_replacement_impact_model_keeps_effect_channels_zero(
    proposed_effect: str,
    expected_sidecar_review: str,
    expected_sidecar_rule: str,
) -> None:
    result = _solve(_assumption("literature_calibrated_base"))
    rows = conventional_drag_replacement_reallocation_impact_rows(
        result,
        proposed_effect=proposed_effect,
    )

    for field in (
        "headline_denominator_delta_bil",
        "split_denominator_delta_bil",
        "main_ratio_delta_bil",
    ):
        assert {row[field] for row in rows} == {"0"}
    for field in (
        "replacement_denominator_admitted",
        "reallocation_admitted",
        "additive_drag_allowed",
        "runtime_denominator_effect_allowed",
        "main_ratio_effect_allowed",
        "denominator_prior_update_allowed",
        "enters_main_ratio",
        "canonical_ratio_entry",
        "evidence_mode_enabled",
        "formula_replacement_allowed",
        "split_denominator_promotion_allowed",
        "main_offset_ratio_changed_this_tranche",
        "dynamic_equation_changed_this_tranche",
        "share_reallocation_behaviorally_neutral",
    ):
        assert {row[field] for row in rows} == {"false"}
    assert {row["sidecar_subbase_impact_review_required"] for row in rows} == {
        expected_sidecar_review
    }
    assert {row["sidecar_subbase_impact_rule"] for row in rows} == {
        expected_sidecar_rule
    }


def test_denominator_replacement_impact_model_rejects_unsupported_inputs() -> None:
    result = _solve(_assumption("literature_calibrated_base"))

    with pytest.raises(ValueError, match="unsupported denominator replacement candidate"):
        conventional_drag_replacement_reallocation_impact_rows(
            result,
            candidate_lens="generic_mpc_proxy",
        )
    with pytest.raises(ValueError, match="unsupported denominator replacement effect"):
        conventional_drag_replacement_reallocation_impact_rows(
            result,
            proposed_effect="additive_drag",
        )


def test_literature_calibrated_base_is_canonical_static_assumption() -> None:
    base = _assumption("base_current_100bps")
    calibrated = _assumption("literature_calibrated_base")

    for assumption in (base, calibrated):
        assert assumption.contractionary_drag_gdp_share == Decimal("0.00776")
        assert assumption.foreign_treasury_holder_leakage_share == Decimal("0.28")
        assert assumption.firm_liquid_asset_cushion_share == Decimal("0.00")
        assert assumption.firm_rollover_pressure_share == Decimal("0.00")
        assert assumption.assumption_status == "literature_calibrated_base"

    assert _assumption("literature_calibrated_low").contractionary_drag_gdp_share == Decimal(
        "0.0035"
    )
    assert _assumption("literature_calibrated_high").contractionary_drag_gdp_share == Decimal(
        "0.0130"
    )


def test_static_assumption_engine_has_no_tdc_hook() -> None:
    engine_source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "ratewall"
        / "accounting"
        / "assumption_engine.py"
    ).read_text(encoding="utf-8")

    assert "tdc" not in engine_source.lower()
    assert "treasury deposit channel" not in engine_source.lower()


def test_canonical_denominator_constant_matches_runtime_threshold_and_yaml() -> None:
    configured = {
        row["name"]: Decimal(str(row["contractionary_drag_gdp_share"]))
        for row in yaml.safe_load(ASSUMPTION_SETS.read_text(encoding="utf-8"))[
            "assumption_sets"
        ]
        if row["name"] in {"base_current_100bps", "literature_calibrated_base"}
    }
    canonical = ratio_object_registry_rows()[0]

    assert configured == {
        "base_current_100bps": CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
        "literature_calibrated_base": CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
    }
    assert {
        _assumption("base_current_100bps").contractionary_drag_gdp_share,
        _assumption("literature_calibrated_base").contractionary_drag_gdp_share,
        LITERATURE_ANNUAL_FLOW_RUNTIME_ANCHOR_SHARE,
    } == {CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE}
    assert {
        scenario.contractionary_drag_gdp_share for scenario in DEFAULT_THRESHOLD_SCENARIOS
    } == {CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE}
    assert LITERATURE_ANNUAL_FLOW_RUNTIME_ANCHOR_INTERVAL_PP == (
        CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE_LOW * Decimal("100"),
        CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE_HIGH * Decimal("100"),
    )
    assert "interval_pp_gdp=[0.35,1.30]" in canonical["denominator_rule"]
    assert "[0.35, 1.30]" in canonical["safe_sentence"]


def test_legacy_static_ratio_object_uses_current_canonical_denominator_label() -> None:
    static = next(
        row
        for row in ratio_object_registry_rows()
        if row["ratio_object_id"] == "rw_legacy_static_assumption_mode"
    )

    assert static["denominator_rule"] == (
        "legacy_static_current_canonical_gdp_share_not_empirical_runtime_anchor;"
        f"center_pp_gdp={LITERATURE_ANNUAL_FLOW_RUNTIME_ANCHOR_PP_STR}"
    )
    assert LITERATURE_ANNUAL_FLOW_RUNTIME_ANCHOR_PP_STR in static["denominator_rule"]
    assert "0.006" not in static["denominator_rule"]
    assert "0.006" not in static["forbidden_sentence"]


def test_threshold_scenarios_do_not_carry_decorative_deposit_beta() -> None:
    assert all(
        not hasattr(scenario, "deposit_beta")
        for scenario in DEFAULT_THRESHOLD_SCENARIOS
    )
    assert "high_deposit_beta_financial_retention" not in {
        scenario.name for scenario in DEFAULT_THRESHOLD_SCENARIOS
    }


def test_single_canonical_annual_flow_ratio_surface_and_guardrails() -> None:
    rows = ratio_object_registry_rows()
    canonical = [row for row in rows if row["canonical_ratio_entry"] == "true"]

    assert [row["ratio_object_id"] for row in canonical] == [
        "rw_runtime_support_offset_af_fixed"
    ]
    assert canonical[0]["fixed_runtime_anchor_role"] == "canonical_annual_flow_default"
    assert canonical[0]["evidence_mode_enabled"] == "false"
    assert "Evidence_Mode" in canonical[0]["blocked_use"]


def test_cushion_active_does_not_create_residual_denominator_coupling() -> None:
    base = _assumption("literature_calibrated_base")
    low_drag = solve_assumption(
        assumption=replace(
            base,
            firm_liquid_asset_cushion_share=Decimal("0.18"),
            firm_rollover_pressure_share=Decimal("0.08"),
            contractionary_drag_gdp_share=Decimal("0.0035"),
        ),
        **SOLVER_INPUTS,
    )
    high_drag = solve_assumption(
        assumption=replace(
            base,
            firm_liquid_asset_cushion_share=Decimal("0.18"),
            firm_rollover_pressure_share=Decimal("0.08"),
            contractionary_drag_gdp_share=Decimal("0.0130"),
        ),
        **SOLVER_INPUTS,
    )

    assert Decimal(high_drag["conventional_contractionary_effect_bil"]) > Decimal(
        low_drag["conventional_contractionary_effect_bil"]
    )
    assert Decimal(high_drag["scalar_countervailing_total_bil"]) == Decimal(
        low_drag["scalar_countervailing_total_bil"]
    )
    assert Decimal(high_drag["ratewall_offset_ratio"]) < Decimal(
        low_drag["ratewall_offset_ratio"]
    )


def test_exp8_firm_cushion_rollover_diagnostics_do_not_enter_headline_n() -> None:
    diagnostic = _assumption("assumption_mode_firm_cushion_rollover_entry")
    active = _solve(diagnostic)
    held = _solve(
        replace(
            diagnostic,
            firm_liquid_asset_cushion_share=Decimal("0"),
            firm_rollover_pressure_share=Decimal("0"),
        )
    )

    assert diagnostic.firm_cash_attenuation_share == Decimal("0.00")
    assert diagnostic.firm_liquid_asset_cushion_share == Decimal("0.05")
    assert diagnostic.firm_rollover_pressure_share == Decimal("0.12")
    assert Decimal(active["firm_liquid_asset_cushion_offset_bil"]) > 0
    assert Decimal(active["firm_rollover_pressure_drag_bil"]) > 0
    assert active["scalar_countervailing_total_bil"] == held[
        "scalar_countervailing_total_bil"
    ]

    rows = {
        row["net_channel"]: row
        for row in net_countervailing_channel_rows(active)
        if row["net_channel"]
        in {"firm_liquid_asset_cushion", "firm_rollover_pressure_drag"}
    }
    assert set(rows) == {
        "firm_liquid_asset_cushion",
        "firm_rollover_pressure_drag",
    }
    for row in rows.values():
        assert Decimal(row["channel_value_bil"]) != 0
        assert row["scalar_channel_value_bil"] == "0"
        assert row["split_channel_value_bil"] == "0"
        assert row["directly_added_to_final_numerator"] == "false"
        assert row["numerator_inclusion_scope"] == "diagnostic_only_owner_gated"
        assert row["additivity_scope"] == "diagnostic_owner_gated_nonadditive"


def test_safe_asset_drag_does_not_reuse_denominator_as_headline_numerator_basis() -> None:
    base = replace(
        _assumption("literature_calibrated_base"),
        safe_asset_allocation_drag_share=Decimal("0.10"),
    )
    low_drag = _solve(replace(base, contractionary_drag_gdp_share=Decimal("0.0035")))
    high_drag = _solve(replace(base, contractionary_drag_gdp_share=Decimal("0.0130")))

    assert Decimal(high_drag["conventional_contractionary_effect_bil"]) > Decimal(
        low_drag["conventional_contractionary_effect_bil"]
    )
    assert Decimal(high_drag["safe_asset_allocation_drag_bil"]) == Decimal(
        low_drag["safe_asset_allocation_drag_bil"]
    )
    assert Decimal(high_drag["scalar_countervailing_total_bil"]) == Decimal(
        low_drag["scalar_countervailing_total_bil"]
    )


def test_legacy_safe_asset_offset_is_discounted_when_same_basis_channels_active() -> None:
    base = replace(
        _assumption("literature_calibrated_base"),
        safe_asset_allocation_offset_share=Decimal("0.20"),
    )
    active = _solve(base)
    disjoint = _solve(
        replace(
            base,
            treasury_interest_demand_share=Decimal("0"),
            iorb_recipient_demand_share=Decimal("0"),
            on_rrp_recipient_demand_share=Decimal("0"),
            retail_safe_yield_pass_through_beta=Decimal("0"),
            household_safe_asset_stock_share=Decimal("0"),
            household_safe_asset_access_conditioner=Decimal("0"),
            household_safe_yield_current_spend_share=Decimal("0"),
            deposit_mmf_substitution_conditioner=Decimal("0"),
        )
    )
    exp1_active = _solve(
        replace(
            base,
            treasury_interest_demand_share=Decimal("0"),
            iorb_recipient_demand_share=Decimal("0"),
            on_rrp_recipient_demand_share=Decimal("0"),
            retail_safe_yield_pass_through_beta=Decimal("0.40"),
            household_safe_asset_stock_share=Decimal("0.50"),
            household_safe_asset_access_conditioner=Decimal("0.50"),
            household_safe_yield_current_spend_share=Decimal("0.08"),
        )
    )

    assert Decimal(active["safe_asset_allocation_offset_share"]) == Decimal("0")
    assert Decimal(active["safe_asset_allocation_offset_bil"]) == Decimal("0")
    assert Decimal(active["safe_asset_allocation_drag_bil"]) > Decimal("0")
    assert Decimal(disjoint["safe_asset_allocation_offset_share"]) == Decimal("0.20")
    assert Decimal(disjoint["safe_asset_allocation_offset_bil"]) > Decimal("0")
    assert Decimal(exp1_active["safe_asset_allocation_offset_share"]) == Decimal("0")
    assert Decimal(exp1_active["safe_asset_allocation_offset_bil"]) == Decimal("0")


def test_tdc_beta_times_chi_replaces_kappa_only_and_full_tdc_shortcut() -> None:
    profiles, _ = _forecast_channel_conversion_profile_specs()
    registry_rows = tdc_forward_assumption_registry_rows()
    tdcsim_chi = {
        row["assumption_id"]: Decimal(row["assumption_value"])
        for row in registry_rows
        if row["assumption_family"] == "tdc_deposit_current_demand_conversion"
    }
    tdcsim_beta = {
        row["assumption_id"]: Decimal(row["assumption_value"])
        for row in registry_rows
        if row["assumption_family"] == "tdc_materialization_beta"
    }

    assert {
        key: Decimal(profile["tdc_deposit_balance_current_demand_conversion_assumption"])
        for key, profile in profiles.items()
    } == {
        "conservative": Decimal("0.03"),
        "base": Decimal("0.07"),
        "demand_active": Decimal("0.12"),
    }
    assert tdcsim_chi == {
        "tdc_deposit_conversion_low": Decimal("0.03"),
        "tdc_deposit_conversion_base": Decimal("0.07"),
        "tdc_deposit_conversion_high": Decimal("0.12"),
    }
    assert tdcsim_beta["tdc_materialization_beta_normal_forward"].quantize(
        Decimal("0.000001")
    ) == Decimal("0.342018")

    support = _forecast_profile_supports(
        {
            "mpc_scenario": "base_mpc_10pct",
            "domestic_nonbank_interest_support_bil": "0",
            "domestic_nonbank_current_spend_share_assumption": "0",
            "bank_retained_margin_support_bil": "0",
            "bank_retained_margin_spend_share_assumption": "0",
            "tdc_full_bil": "100",
            "tdc_change_ex_overlap_bil": "100",
        }
    )
    assert support["tdc_share"] == Decimal("0.07")
    assert Decimal(str(support["tdc_materialization_beta"])).quantize(
        Decimal("0.000001")
    ) == Decimal("0.342018")
    assert Decimal(str(support["tdc_support"])).quantize(Decimal("0.0000001")) == Decimal(
        "2.3941231"
    )

    base_rows = [
        {
            "forecast_path_ratio_scenario_registry_row_id": "base::1",
            "forecast_incremental_path_ratio_row_id": "forecast::1",
            "forecast_year": "2026",
            "forecast_scenario_id": "scenario",
            "source_row_handle": "scenario::source",
            "scenario_bundle_label": "scenario",
            "mpc_scenario": "base_mpc_10pct",
            "tdc_deposit_balance_current_demand_conversion_assumption": "0.25",
            "projected_tdc_change_bil": "100",
            "denominator_bil": "200",
            "numerator_total_bil": "50",
            "row_reportability_status": "reportable",
            "maturity_scenario": "current_wam_cbo_rate_path",
            "repricing_path_role": "current_wam",
            "repricing_path_value": "1",
            "holder_scenario": "current_holder_distribution",
            "holder_mix_role": "current",
            "domestic_nonbank_holder_share": "0.5",
            "bank_holder_share": "0.2",
            "foreign_holder_share": "0.28",
            "central_bank_holder_share": "0.02",
            "tdc_path_role": "sidecar",
            "tdc_change_ex_overlap_bil": "100",
            "exact_blocker": "",
            "source_status": "fixture",
        }
    ]
    decomposition_rows = [
        {
            "forecast_path_ratio_scenario_registry_row_id": "base::1",
            "component_id": "tdc_deposit_current_demand_support",
            "component_value_bil": "10",
        },
        {
            "forecast_path_ratio_scenario_registry_row_id": "base::1",
            "component_id": "domestic_nonbank_interest_support",
            "component_value_bil": "20",
        },
        {
            "forecast_path_ratio_scenario_registry_row_id": "base::1",
            "component_id": "bank_retained_margin_support",
            "component_value_bil": "5",
        },
    ]
    pass_rows = [
        {
            "forecast_pass_through_scenario_row_id": "pass::base",
            "pass_through_scenario": "base",
            "pass_through_scenario_role": "default_source_backed_forward_normal",
            "pass_through_beta": "0.3249",
            "pass_through_lower95": "0.2479",
            "pass_through_upper95": "0.6163",
            "tdc_deposit_pass_through_source_import_row_id": "source::beta",
            "source_status": "evidence1_beta",
        }
    ]

    rows = forecast_path_ratio_pass_through_scenario_registry_rows(
        forecast_path_ratio_scenario_registry_rows=base_rows,
        forecast_path_ratio_decomposition_rows=decomposition_rows,
        forecast_path_ratio_pass_through_scenario_axis_rows=pass_rows,
    )

    assert len(rows) == 1
    assert Decimal(rows[0]["adjusted_tdc_current_demand_support_bil"]) == Decimal(
        "8.1225"
    )
    assert Decimal(rows[0]["tdc_support_delta_bil"]) == Decimal("-1.8775")
    assert Decimal(rows[0]["numerator_total_bil"]) == Decimal("48.1225")
    assert rows[0]["current_demand_conversion_role"] == (
        "tdc_beta_materialization_then_chi_current_demand"
    )
    assert rows[0]["current_demand_conversion_value"] == "0.25"
    assert "beta_applied_once_to_ex_overlap_tdc_then_chi" in rows[0][
        "source_status"
    ]


def test_tdcsim_remittance_component_proves_static_xor_invariant() -> None:
    component_rows = tdc_forward_component_audit_rows()
    remittance_rows = [
        row
        for row in component_rows
        if row["component_key"] == "central_bank_remittance_to_tga"
    ]

    assert remittance_rows
    assert {row["holder_bucket"] for row in remittance_rows} == {"CB"}
    assert {row["cash_component_key"] for row in remittance_rows} == {
        "central_bank_remittance_to_tga"
    }
    assert {row["enters_direct_interest_support"] for row in remittance_rows} == {
        "false"
    }
    assert {
        row["enters_tdc_deposit_support_default"] for row in remittance_rows
    } == {"false"}
    assert {row["component_dual_entry_status"] for row in remittance_rows} == {
        "pass_mutually_exclusive"
    }

    invariant_rows = tdc_forward_invariant_audit_rows(
        projection_rows=tdc_forward_projection_surface_rows(),
        component_rows=component_rows,
        overlap_rows=tdc_forward_overlap_guardrail_rows(),
    )
    remittance_invariant = next(
        row
        for row in invariant_rows
        if row["audit_item"] == "tdcsim_forward_remittance_static_xor_proven"
    )
    assert remittance_invariant["audit_status"] == "pass"
    assert remittance_invariant["main_offset_ratio_changed_this_tranche"] == "false"
    assert remittance_invariant["formula_replacement_allowed"] == "false"


@pytest.mark.parametrize(
    "field",
    [
        "treasury_interest_demand_share",
        "iorb_recipient_demand_share",
        "on_rrp_recipient_demand_share",
        "current_remittance_demand_share",
        "firm_cash_attenuation_share",
        "zero_interest_credit_attenuation_share",
    ],
)
def test_demand_conversion_shares_increase_ratewall_ratio(field: str) -> None:
    base = _assumption("literature_calibrated_base")
    low = _solve(replace(base, **{field: Decimal("0.01")}))
    high = _solve(replace(base, **{field: Decimal("0.20")}))

    assert _ratio(high) > _ratio(low)
    assert Decimal(high["scalar_countervailing_total_bil"]) > Decimal(
        low["scalar_countervailing_total_bil"]
    )


@pytest.mark.parametrize(
    "field",
    [
        "fiscal_offset_share",
        "tga_liquidity_offset_share",
        "interest_income_tax_timing_leakage_share",
        "safe_asset_allocation_drag_share",
        "deposit_mmf_substitution_drag_share",
    ],
)
def test_absorber_and_drag_shares_decrease_ratewall_ratio(field: str) -> None:
    base = replace(
        _assumption("literature_calibrated_base"),
        deposit_mmf_substitution_conditioner=Decimal("0.50"),
        retail_safe_yield_pass_through_beta=Decimal("0.50"),
        household_safe_yield_current_spend_share=Decimal("0.20"),
    )
    low = _solve(replace(base, **{field: Decimal("0.00")}))
    high = _solve(replace(base, **{field: Decimal("0.30")}))

    assert _ratio(high) < _ratio(low)


def test_exp1_safe_yield_activation_uses_evidence_c_bands_without_legacy_overlap() -> None:
    safe_yield = _assumption("assumption_mode_safe_yield_capture_entry")
    paired = _assumption("assumption_mode_deposit_mmf_paired_entry")

    for assumption in (safe_yield, paired):
        assert assumption.safe_asset_allocation_offset_share == Decimal("0.00")
        assert assumption.safe_asset_allocation_drag_share == Decimal("0.00")
        assert assumption.retail_safe_yield_pass_through_beta == Decimal("0.40")
        assert assumption.household_safe_yield_current_spend_share == Decimal("0.08")

    safe_result = _solve(safe_yield)
    paired_result = _solve(paired)
    assert Decimal(safe_result["safe_asset_allocation_offset_bil"]) == Decimal("0")
    assert Decimal(safe_result["safe_asset_allocation_drag_bil"]) == Decimal("0")
    assert Decimal(paired_result["household_safe_yield_capture_offset_bil"]) > 0
    assert Decimal(paired_result["deposit_mmf_substitution_offset_bil"]) > 0
    assert Decimal(paired_result["deposit_mmf_substitution_drag_bil"]) > 0


def test_exp1_deposit_mmf_drag_uses_scalar_credit_supply_basis() -> None:
    base = _assumption("assumption_mode_deposit_mmf_paired_entry")
    result = _solve(base)
    scalar_credit_supply_drag = (
        Decimal(result["conventional_contractionary_effect_bil"])
        * Decimal(str(base.credit_supply_drag_share))
    )
    expected_drag = (
        scalar_credit_supply_drag
        * Decimal(result["deposit_mmf_incremental_access_share"])
        * Decimal(result["deposit_mmf_substitution_drag_share"])
    )
    assert Decimal(result["deposit_mmf_substitution_drag_bil"]) == expected_drag

    low_credit_share = Decimal("0.10")
    high_credit_share = Decimal("0.30")
    low = _solve(
        replace(
            base,
            borrowing_cost_drag_share=(
                base.borrowing_cost_drag_share
                + base.credit_supply_drag_share
                - low_credit_share
            ),
            credit_supply_drag_share=low_credit_share,
        )
    )
    high = _solve(
        replace(
            base,
            borrowing_cost_drag_share=(
                base.borrowing_cost_drag_share
                + base.credit_supply_drag_share
                - high_credit_share
            ),
            credit_supply_drag_share=high_credit_share,
        )
    )
    assert Decimal(high["deposit_mmf_substitution_drag_bil"]) > Decimal(
        low["deposit_mmf_substitution_drag_bil"]
    )


def test_split_denominator_multiplier_is_non_load_bearing_for_headline() -> None:
    base = _assumption("literature_calibrated_base")
    low = _solve(replace(base, split_denominator_total_drag_multiplier=Decimal("1.00")))
    high = _solve(replace(base, split_denominator_total_drag_multiplier=Decimal("1.25")))

    assert Decimal(high["split_denominator_conventional_drag_bil"]) > Decimal(
        low["split_denominator_conventional_drag_bil"]
    )
    assert Decimal(high["split_denominator_offset_ratio"]) < Decimal(
        low["split_denominator_offset_ratio"]
    )
    for field in (
        "ratewall_offset_ratio",
        "wall_hit_under_assumptions",
        "decisive_margin_bil",
        "required_countervailing_for_hit_bil",
        "remaining_gap_to_wall_bil",
        "excess_over_wall_bil",
    ):
        assert high[field] == low[field]

    robustness_boundary = (
        "split_denominator_robustness_lane_non_load_bearing_for_headline_hit_"
        "verdict_assumption_mode_not_empirical_estimate"
    )
    split_row = split_denominator_comparison_row(high)
    assert split_row["enters_main_ratio"] == "false"
    assert split_row["split_denominator_promotion_allowed"] == "false"
    assert split_row["allowed_use"] == "robustness_decomposition_only"
    assert split_row["blocked_use"] == "headline_hit_verdict;canonical_rw_y;evidence_mode"
    assert split_row["claim_boundary"] == robustness_boundary
    assert {
        row["claim_boundary"] for row in conventional_drag_decomposition_rows(high)
    } == {robustness_boundary}


def test_higher_canonical_denominator_decreases_ratewall_ratio() -> None:
    base = _assumption("literature_calibrated_base")
    low = _solve(replace(base, contractionary_drag_gdp_share=Decimal("0.0035")))
    high = _solve(replace(base, contractionary_drag_gdp_share=Decimal("0.0130")))

    assert Decimal(high["conventional_contractionary_effect_bil"]) > Decimal(
        low["conventional_contractionary_effect_bil"]
    )
    assert _ratio(high) < _ratio(low)


def test_static_headline_uses_state_neutral_debt_denominator() -> None:
    result = _solve(_assumption("literature_calibrated_base"))

    assert Decimal(result["debt_state_drag_multiplier"]) == Decimal("1.00")
    assert Decimal(result["conventional_contractionary_effect_bil"]) == Decimal(
        result["conventional_contractionary_anchor_bil"]
    )
    assert _ratio(result) == (
        Decimal(result["scalar_countervailing_total_bil"])
        / Decimal(result["conventional_contractionary_anchor_bil"])
    )


def test_debt_state_drag_multiplier_sensitivity_is_d_only() -> None:
    base = _assumption("literature_calibrated_base")
    active = _solve(base)
    lower_drag = _solve(replace(base, debt_state_drag_multiplier=Decimal("0.70")))

    assert base.debt_state_drag_multiplier == Decimal("1.00")
    assert Decimal(active["conventional_contractionary_effect_bil"]) == Decimal(
        active["conventional_contractionary_anchor_bil"]
    )
    assert Decimal(lower_drag["conventional_contractionary_effect_bil"]) == (
        Decimal(active["conventional_contractionary_effect_bil"]) * Decimal("0.70")
    )
    assert _ratio(lower_drag) > _ratio(active)

    for field in (
        "scalar_countervailing_total_bil",
        "private_recipient_cashflow_impulse_bil",
        "treasury_interest_impulse_bil",
        "treasury_interest_demand_offset_bil",
        "current_remittance_reduction_bil",
        "current_remittance_demand_offset_bil",
        "future_remittance_drag_bil",
        "future_remittance_drag_demand_offset_bil",
    ):
        assert active[field] == lower_drag[field]


def test_foreign_leakage_reduces_canonical_interest_support_and_ratewall() -> None:
    base = _assumption("literature_calibrated_base")
    clean = _solve(replace(base, foreign_treasury_holder_leakage_share=Decimal("0")))
    leaky = _solve(replace(base, foreign_treasury_holder_leakage_share=Decimal("0.25")))

    assert Decimal(leaky["treasury_interest_demand_offset_bil"]) < Decimal(
        clean["treasury_interest_demand_offset_bil"]
    )
    assert Decimal(leaky["scalar_countervailing_total_bil"]) < Decimal(
        clean["scalar_countervailing_total_bil"]
    )
    assert _ratio(leaky) < _ratio(clean)


def test_fiscal_and_tga_offsets_never_exceed_gross_net_interest_base() -> None:
    result = _solve(_assumption("literature_calibrated_base"))
    fiscal = Decimal(result["fiscal_offset_bil"])
    tga = Decimal(result["tga_liquidity_offset_bil"])
    gross_base = Decimal(result["net_interest_before_fiscal_tga_offsets_bil"])

    assert fiscal >= 0
    assert tga >= 0
    assert fiscal + tga <= gross_base


def test_headline_numerator_and_denominator_values_reconcile_to_totals() -> None:
    result = _solve(_assumption("literature_calibrated_base"))

    _assert_scalar_numerator_reconciles(result)
    _assert_scalar_denominator_reconciles(result)




def test_sidecar_overlap_discount_is_bounded_and_cannot_make_negative_drag() -> None:
    base = replace(
        _assumption("literature_calibrated_base"),
        rate_sensitive_consumer_credit_stock_share_gdp=Decimal("0.08"),
        consumer_credit_reprice_beta=Decimal("0.50"),
        consumer_credit_cashflow_drag_conversion=Decimal("0.50"),
        cre_refi_drag_gdp_share_per_100bp_year=Decimal("0.02"),
        private_credit_ndfi_credit_drag_share=Decimal("0.20"),
        fixed_mortgage_payment_shield_share_of_household_borrowing_drag=Decimal("0.10"),
        denominator_sidecar_overlap_discount_share=Decimal("0.40"),
    )
    result = _solve(base)

    gross_sidecar = Decimal(result["denominator_sidecar_positive_drag_total_bil"])
    discount = Decimal(result["denominator_sidecar_overlap_discount_bil"])
    adjusted = Decimal(result["denominator_sidecar_adjusted_conventional_drag_bil"])

    assert gross_sidecar > 0
    assert Decimal("0") <= discount <= gross_sidecar
    assert adjusted >= 0


def test_unit_scaling_doubles_nominal_flows_but_preserves_ratewall_ratio() -> None:
    base = _assumption("literature_calibrated_base")
    normal = _solve(base)
    scaled = solve_assumption(
        assumption=base,
        gdp_bil=SOLVER_INPUTS["gdp_bil"] * 2,
        treasury_interest_impulse_bil=SOLVER_INPUTS["treasury_interest_impulse_bil"] * 2,
        iorb_interest_impulse_bil=SOLVER_INPUTS["iorb_interest_impulse_bil"] * 2,
        on_rrp_interest_impulse_bil=SOLVER_INPUTS["on_rrp_interest_impulse_bil"] * 2,
        current_remittance_reduction_bil=SOLVER_INPUTS[
            "current_remittance_reduction_bil"
        ]
        * 2,
        future_remittance_drag_bil=SOLVER_INPUTS["future_remittance_drag_bil"] * 2,
    )

    assert Decimal(scaled["scalar_countervailing_total_bil"]) == (
        Decimal(normal["scalar_countervailing_total_bil"]) * 2
    )
    assert Decimal(scaled["conventional_contractionary_effect_bil"]) == (
        Decimal(normal["conventional_contractionary_effect_bil"]) * 2
    )
    assert _ratio(scaled) == _ratio(normal)


def test_split_denominator_shares_must_sum_to_one() -> None:
    base = _assumption("literature_calibrated_base")

    with pytest.raises(ValueError, match="component shares must sum to 1"):
        _solve(replace(base, borrowing_cost_drag_share=Decimal("0.50")))

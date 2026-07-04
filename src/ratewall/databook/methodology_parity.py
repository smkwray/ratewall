"""Methodology parity ledger across current, forecast, and historical RateWall."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_FORECAST_READOUT_DIR = Path("var/preliminary_scenario_results/forecast_10y")
DEFAULT_BETA_CHI_CALIBRATION_DIR = Path(
    "var/preliminary_scenario_results/beta_chi_calibration_readout"
)
DEFAULT_RATIO_REGISTRY_PATH = Path("outputs/tables/ratewall_ratio_object_registry.csv")
DEFAULT_DENOMINATOR_CONTRACT_PATH = Path(
    "outputs/tables/ratewall_wall_denominator_path_contract.csv"
)

METHODOLOGY_PARITY_CHANNEL_FIELDS = [
    "methodology_parity_channel_row_id",
    "channel_id",
    "channel_label",
    "surface_id",
    "surface_label",
    "surface_family",
    "numerator_treatment",
    "denominator_treatment",
    "model_role",
    "surface_entry_role",
    "centrality",
    "measurement_basis",
    "overlap_guard",
    "comparability_gap",
    "parity_status",
    "next_model_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

METHODOLOGY_PARITY_DENOMINATOR_FIELDS = [
    "methodology_parity_denominator_row_id",
    "surface_id",
    "surface_label",
    "denominator_object_id",
    "denominator_role",
    "denominator_rule",
    "fixed_anchor_component",
    "path_component",
    "moving_rate_response",
    "centrality",
    "comparability_gap",
    "next_model_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

METHODOLOGY_PARITY_ROADMAP_FIELDS = [
    "methodology_parity_roadmap_row_id",
    "priority_rank",
    "workstream_id",
    "workstream_label",
    "model_reason",
    "inputs_needed",
    "implementation_target",
    "promotion_test",
    "expected_model_effect",
    "do_not_do",
    "status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class MethodologyParityError(ValueError):
    """Raised when methodology parity inputs are missing or inconsistent."""


SURFACE_DEFINITIONS = {
    "current_assumption_runtime": {
        "surface_label": "Current/canonical assumption runtime",
        "surface_family": "current_or_static",
    },
    "forecast_central_tdcsim_cbo": {
        "surface_label": "10-year TDCSim/CBO central forecast",
        "surface_family": "forecast",
    },
    "forecast_sensitivity_tdcsim_cbo": {
        "surface_label": "10-year TDCSim/CBO sensitivity forecast",
        "surface_family": "forecast",
    },
    "historical_path_context": {
        "surface_label": "Historical path/context surface",
        "surface_family": "historical",
    },
}

CURRENT_RUNTIME_CENTRAL_CHANNELS = {
    "net_interest_after_fiscal_tga_offsets",
    "current_remittance_demand_offset",
    "future_remittance_drag_demand_offset",
    "iorb_recipient_demand_channel",
    "on_rrp_recipient_demand_channel",
    "fiscal_offset",
    "tga_liquidity_offset",
    "interest_income_tax_timing_drag",
    "firm_cash_attenuation",
    "safe_asset_allocation_offset",
    "safe_asset_allocation_drag",
    "zero_interest_credit_attenuation",
    "household_safe_yield_capture",
    "deposit_mmf_substitution_offset",
    "deposit_mmf_substitution_drag",
}

FORECAST_CENTRAL_CLASSIFICATIONS = {
    "included",
    "included_as_public_interest_replacement_block",
    "integrated_in_public_interest_net_block",
    "integrated_in_public_interest_net_block_with_state_guard",
    "integrated_in_public_interest_net_block_absorber",
    "replaced_by_current_tdcsim_holder_filter",
}

FORECAST_SENSITIVITY_CLASSIFICATIONS = {
    "projection_required_as_bounded_sensitivity",
    "projection_required_as_bounded_residual_sensitivity",
    "projection_required_as_paired_bounded_sensitivity",
}

HISTORICAL_SOURCE_CONTEXT_CHANNELS = {
    "net_interest_after_fiscal_tga_offsets",
    "current_remittance_demand_offset",
    "future_remittance_drag_demand_offset",
    "iorb_recipient_demand_channel",
    "on_rrp_recipient_demand_channel",
    "fiscal_offset",
    "tga_liquidity_offset",
    "firm_cash_attenuation",
    "safe_asset_allocation_drag",
    "household_safe_yield_capture",
    "deposit_mmf_substitution_offset",
    "deposit_mmf_substitution_drag",
    "tdc_ex_overlap_current_demand_support",
}


def methodology_parity_channel_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Build channel-by-surface methodology parity rows."""

    forecast_dir = Path(forecast_readout_dir)
    classification_rows = _read_required(
        forecast_dir / "ratewall_forecast_channel_classification.csv"
    )
    plan_rows = _read_optional(forecast_dir / "ratewall_forecast_numerator_channel_plan.csv")
    plan_by_channel = {row["channel_id"]: row for row in plan_rows}
    out: list[dict[str, str]] = []
    for channel in classification_rows:
        for surface_id in SURFACE_DEFINITIONS:
            out.append(_surface_channel_row(channel, surface_id, plan_by_channel))
    return out


def methodology_parity_denominator_rows(
    *,
    denominator_contract_path: str | Path = DEFAULT_DENOMINATOR_CONTRACT_PATH,
) -> list[dict[str, str]]:
    """Build denominator comparability rows for the major surfaces."""

    contracts = _read_required(Path(denominator_contract_path))
    rows: list[dict[str, str]] = []
    rows.append(
        _denominator_row(
            surface_id="current_assumption_runtime",
            contract=_find_contract(
                contracts,
                ratio_object_id="rw_runtime_support_offset_af_fixed",
                row_role="runtime_default_primary",
            ),
            denominator_rule="fixed_annual_flow_100bp_year_runtime_anchor",
            path_component="not_applicable",
            moving_rate_response="none_fixed_runtime_object",
            centrality="central_current_runtime_only",
            gap=(
                "not_comparable_to_path_forecast_without_explicit_fixed_vs_path_"
                "denominator_bridge"
            ),
            action=(
                "keep_fixed_runtime_D_visible_as_current_reference_and_do_not_use_as_"
                "forecast_or_historical_primary_D"
            ),
        )
    )
    rows.append(
        _denominator_row(
            surface_id="forecast_central_tdcsim_cbo",
            contract=_find_contract(
                contracts,
                ratio_object_id="rw_forecast_wall_ratio_path",
                row_role="forecast_primary_path_required",
            ),
            denominator_rule=(
                "cbo_gdp_scaled_anchor_plus_selected_moving_D_for_rate_scenarios"
            ),
            path_component="cbo_nominal_gdp_path;scenario_rate_overlay",
            moving_rate_response=(
                "selected_frbus_structural_term_premium_c_D_1.1198692004749646"
            ),
            centrality="central_forecast_scenario_D",
            gap=(
                "forecast_D_moves_with_rate_scenarios_but_current_runtime_D_is_fixed"
            ),
            action=(
                "keep_moving_D_in_all_rate_changing_forecast_scenarios_and_add_"
                "fixed_D_comparison_only_if_needed"
            ),
        )
    )
    rows.append(
        _denominator_row(
            surface_id="forecast_sensitivity_tdcsim_cbo",
            contract=_find_contract(
                contracts,
                ratio_object_id="rw_forecast_wall_ratio_path",
                row_role="forecast_primary_path_required",
            ),
            denominator_rule="same_as_forecast_central_for_comparable_sensitivities",
            path_component="inherits_forecast_central_selected_D",
            moving_rate_response=(
                "selected_frbus_structural_term_premium_c_D_1.1198692004749646"
            ),
            centrality="sensitivity_not_headline",
            gap=(
                "residual_credit_drag_sensitivities_can_overlap_moving_D_if_not_guarded"
            ),
            action="keep_credit_drag_overlap_guard_and_report_D_delta_next_to_N_delta",
        )
    )
    rows.append(
        _denominator_row(
            surface_id="historical_path_context",
            contract=_find_contract(
                contracts,
                ratio_object_id="rw_historical_wall_ratio_path",
                row_role="historical_primary_path_required",
            ),
            denominator_rule="historical_path_denominator_with_rate_exposure",
            path_component="historical_rate_gap_pct_points;near_zero_guard",
            moving_rate_response="historical_rate_path_mechanical_not_scenario_response",
            centrality="historical_context_not_classifier",
            gap=(
                "historical_path_D_is_not_the_current_fixed_D_and_not_the_forecast_"
                "scenario_moving_D"
            ),
            action=(
                "keep_historical_as_validation_context_until_historical_TDC_and_"
                "public_interest_block_are_rebuilt_on_same_channel_map"
            ),
        )
    )
    return rows


def methodology_parity_roadmap_rows(
    *,
    channel_rows: Sequence[Mapping[str, str]],
    denominator_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Build the concrete model roadmap implied by parity gaps."""

    _require_surface_rows(channel_rows, denominator_rows)
    specs = [
        {
            "rank": "1",
            "id": "core_support_numerator_parity",
            "label": "Build shared public-interest and TDC support numerator objects",
            "reason": (
                "Forecast central already uses TDC ex-overlap support plus one "
                "public-interest replacement block; current and historical surfaces "
                "still expose broader or older channel treatments."
            ),
            "inputs": (
                "forecast public-interest net block; TDCSim ex-overlap TDC; exact "
                "beta 0.34201759129420367; chi 0.07; current and historical source "
                "adapters where available"
            ),
            "target": (
                "shared public_interest_net_block and tdc_ex_overlap_support objects, "
                "plus a core_support_numerator_surface"
            ),
            "test": (
                "selected_N_equals_TDC_ex_overlap_support_plus_public_interest_net_block"
                "_plus_admitted_residual_delta; direct_and_bank_interest_are_block_"
                "inputs_not_standalone_selected_terms"
            ),
            "effect": "highest_for_cross_surface_N_comparability",
            "avoid": (
                "do_not_add_public_interest_block_on_top_of_direct_and_bank_interest;"
                "do_not_use_tdc_full_or_mmf_0_97_as_beta_or_chi"
            ),
            "status": "next_large_high_likelihood_model_build",
        },
        {
            "rank": "2",
            "id": "denominator_comparability_bridge",
            "label": "Expose fixed-D, path-D, and moving-D variants side by side",
            "reason": (
                "Current runtime D is fixed, forecast rate scenarios move D, and "
                "historical uses path exposure; final rate-changing scenarios must "
                "not silently reuse fixed D."
            ),
            "inputs": (
                "wall denominator contract; selected FRB/US structural moving-D "
                "coefficient; CBO GDP path; scenario rate overlays; historical rate gaps"
            ),
            "target": (
                "one denominator parity bridge that emits fixed, path, moving, and "
                "selected D columns for each comparable row"
            ),
            "test": (
                "rate-changing forecast scenarios use moving_D as selected_D; fixed_D "
                "is comparison-only; non-rate holder scenarios do not move D except "
                "through approved path scaling"
            ),
            "effect": "highest_for_interpreting_rate_scenario_magnitude",
            "avoid": (
                "do_not_freeze_D_for_rate_scenarios;do_not_change_c_D_or_claim_"
                "empirical_Evidence_Mode"
            ),
            "status": "can_run_in_parallel_with_core_numerator_parity",
        },
        {
            "rank": "3",
            "id": "residual_replacement_channel_closure",
            "label": "Close firm-liquidity and residual safe-asset channels with admission gates",
            "reason": (
                "Current runtime has strong but overlap-prone channels; forecast central "
                "needs explicit replacement, sensitivity, sidecar, or parked treatment "
                "instead of silent exclusion."
            ),
            "inputs": (
                "firm liquid assets; residual sensitivity rows; public-interest residual "
                "basis; moving-D overlap fields; zero/low-APR materiality screen"
            ),
            "target": (
                "firm_liquidity_replacement decision, residual_safe_asset_drag gate, "
                "and residual_channel_admission_matrix"
            ),
            "test": (
                "firm_cash_and_firm_cushion_do_not_stack; safe_asset_drag_nonzero_only_"
                "with_disjoint_residual_basis; deposit_mmf_offset_and_drag_remain_paired"
            ),
            "effect": "medium_for_N_level_and_sensitivity_bands",
            "avoid": (
                "do_not_promote_safe_asset_drag_zero_credit_or_rollover_pressure_without_"
                "nonoverlap_basis"
            ),
            "status": "after_core_support_and_denominator_overlap_fields_are_available",
        },
        {
            "rank": "4",
            "id": "historical_comparable_adapter",
            "label": "Rebuild historical context on the shared channel and denominator map",
            "reason": (
                "Historical rows are useful context but should not be rebuilt until "
                "the shared numerator and denominator objects are stable."
            ),
            "inputs": (
                "historical GDP/rates/reserves/IORB/ON RRP/federal interest; historical "
                "TDC bridge where source-backed; shared public-interest and denominator "
                "objects"
            ),
            "target": (
                "historical comparable adapter with the same channel IDs and denominator "
                "variants, while preserving historical_ratio_not_classifier"
            ),
            "test": (
                "historical_ratio_not_classifier_true; no historical value inferred "
                "from forecast assumptions; public-interest and TDC rows source-backed "
                "or explicitly partial"
            ),
            "effect": "medium_for_validation_and_cross_surface_comparability",
            "avoid": "do_not_call_historical_context_a_classifier_or_Evidence_Mode_object",
            "status": "last_after_shared_current_forecast_objects_are_stable",
        },
    ]
    return [_roadmap_row(spec) for spec in specs]


def methodology_parity_readout_markdown(
    *,
    channel_rows: Sequence[Mapping[str, str]],
    denominator_rows: Sequence[Mapping[str, str]],
    roadmap_rows: Sequence[Mapping[str, str]],
) -> str:
    """Return a concise methodology parity readout."""

    central_forecast = [
        row
        for row in channel_rows
        if row["surface_id"] == "forecast_central_tdcsim_cbo"
        and row["centrality"] == "central"
    ]
    sensitivity_forecast = [
        row
        for row in channel_rows
        if row["surface_id"] == "forecast_sensitivity_tdcsim_cbo"
        and row["centrality"] == "sensitivity"
    ]
    current_central = [
        row
        for row in channel_rows
        if row["surface_id"] == "current_assumption_runtime"
        and row["centrality"] == "central"
    ]
    historical_context = [
        row
        for row in channel_rows
        if row["surface_id"] == "historical_path_context"
        and row["centrality"] in {"context", "partial_context"}
    ]
    lines = [
        "# Methodology Parity Readout",
        "",
        "## Bottom Line",
        "",
        (
            "The current, forecast, and historical surfaces should be made "
            "comparable by channel treatment, not by deleting strong methods. "
            "The next model work should promote shared public-interest and TDC "
            "objects, expose denominator variants side by side, and keep overlap-prone "
            "channels as replacements or sensitivities until their basis is disjoint."
        ),
        "",
        "## Current Coverage",
        "",
        f"- Current/runtime central or active channels: `{len(current_central)}`.",
        f"- Forecast central channels: `{len(central_forecast)}`.",
        f"- Forecast sensitivity channels: `{len(sensitivity_forecast)}`.",
        f"- Historical context/partial-context channels: `{len(historical_context)}`.",
        f"- Denominator parity rows: `{len(denominator_rows)}`.",
        "",
        "## Main Methodology Gaps",
        "",
        "- Forecast central is more scenario-grounded, but it is narrower than the current assumption runtime.",
        "- Current runtime has broader numerator channels, but its denominator is fixed and not a scenario path.",
        "- Historical rows have useful source-backed paths, but they are not a final classifier.",
        "- Rate-changing forecast scenarios must keep moving D; fixed-D comparisons should be labeled comparison-only.",
        "",
        "## Roadmap",
        "",
    ]
    for row in roadmap_rows:
        lines.append(
            f"{row['priority_rank']}. `{row['workstream_id']}` - "
            f"{row['workstream_label']}: {row['status']}."
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- No row in this parity readout changes N, D, beta, chi, or canonical/headline status.",
            "- The output is a build map for making model estimates comparable.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_methodology_parity_outputs(
    output_dir: str | Path,
    *,
    channel_rows: Sequence[Mapping[str, str]],
    denominator_rows: Sequence[Mapping[str, str]],
    roadmap_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write methodology parity CSVs and Markdown readout."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "channel_csv": out / "ratewall_methodology_parity_channels.csv",
        "denominator_csv": out / "ratewall_methodology_parity_denominators.csv",
        "roadmap_csv": out / "ratewall_methodology_parity_roadmap.csv",
        "readout_md": out / "methodology_parity_readout.md",
    }
    write_rows(
        paths["channel_csv"],
        [dict(row) for row in channel_rows],
        METHODOLOGY_PARITY_CHANNEL_FIELDS,
    )
    write_rows(
        paths["denominator_csv"],
        [dict(row) for row in denominator_rows],
        METHODOLOGY_PARITY_DENOMINATOR_FIELDS,
    )
    write_rows(
        paths["roadmap_csv"],
        [dict(row) for row in roadmap_rows],
        METHODOLOGY_PARITY_ROADMAP_FIELDS,
    )
    paths["readout_md"].write_text(
        methodology_parity_readout_markdown(
            channel_rows=channel_rows,
            denominator_rows=denominator_rows,
            roadmap_rows=roadmap_rows,
        ),
        encoding="utf-8",
    )
    return paths


def _surface_channel_row(
    channel: Mapping[str, str],
    surface_id: str,
    plan_by_channel: Mapping[str, Mapping[str, str]],
) -> dict[str, str]:
    channel_id = channel["channel_id"]
    classification = channel["classification"]
    plan = plan_by_channel.get(channel_id, {})
    treatment = _surface_treatment(channel_id, classification, surface_id)
    surface = SURFACE_DEFINITIONS[surface_id]
    return {
        "methodology_parity_channel_row_id": (
            f"methodology_parity::{channel_id}::{surface_id}"
        ),
        "channel_id": channel_id,
        "channel_label": channel["channel_label"],
        "surface_id": surface_id,
        "surface_label": surface["surface_label"],
        "surface_family": surface["surface_family"],
        "numerator_treatment": treatment["numerator_treatment"],
        "denominator_treatment": treatment["denominator_treatment"],
        "model_role": treatment["model_role"],
        "surface_entry_role": _surface_entry_role(channel, surface_id, treatment),
        "centrality": treatment["centrality"],
        "measurement_basis": treatment["measurement_basis"],
        "overlap_guard": treatment["overlap_guard"],
        "comparability_gap": treatment["comparability_gap"],
        "parity_status": treatment["parity_status"],
        "next_model_action": plan.get(
            "next_model_action",
            treatment["next_model_action"],
        ),
        "allowed_use": "methodology_parity_model_roadmap",
        "blocked_use": (
            "canonical_headline_promotion;evidence_mode_claim;"
            "silent_channel_deletion;silent_methodology_merger"
        ),
        "claim_boundary": "parity_readout_only_not_n_or_d_change",
    }


def _surface_treatment(
    channel_id: str,
    classification: str,
    surface_id: str,
) -> dict[str, str]:
    if surface_id == "current_assumption_runtime":
        return _current_treatment(channel_id)
    if surface_id == "forecast_central_tdcsim_cbo":
        return _forecast_central_treatment(channel_id, classification)
    if surface_id == "forecast_sensitivity_tdcsim_cbo":
        return _forecast_sensitivity_treatment(channel_id, classification)
    if surface_id == "historical_path_context":
        return _historical_treatment(channel_id)
    raise MethodologyParityError(f"unknown surface: {surface_id}")


def _current_treatment(channel_id: str) -> dict[str, str]:
    if channel_id in CURRENT_RUNTIME_CENTRAL_CHANNELS:
        return _treatment(
            numerator="included_or_configurable_in_assumption_runtime_N",
            denominator="fixed_runtime_annual_flow_D",
            role="current_assumption_channel",
            centrality="central",
            basis="RateWall assumption engine channel or guarded scalar term",
            guard="runtime overlap guards apply where configured",
            gap="current_method_exists_but_not_all_channels_have_forecast_path",
            parity="current_has_method_needs_forecast_or_historical_adapter",
            action="map_current_channel_into_shared_parity_treatment",
        )
    if channel_id == "tdc_ex_overlap_current_demand_support":
        return _treatment(
            numerator="available_in_tdc_family_bridge_not_static_runtime_central",
            denominator="fixed_runtime_annual_flow_D_if_compared",
            role="tdc_bridge_context",
            centrality="sidecar",
            basis="TDC bridge/TDCSim context rather than static current assumption engine",
            guard="overlap_removed_before_beta_chi",
            gap="forecast_has_cleaner_tdcsim_cbo_tdc_path_than_current_runtime",
            parity="needs_current_period_tdc_adapter",
            action="build shared TDC ex-overlap object before current/forecast comparison",
        )
    return _treatment(
        numerator="not_current_runtime_central_or_replacement_only",
        denominator="fixed_runtime_annual_flow_D_if_compared",
        role="noncentral_or_replacement_channel",
        centrality="blocked_or_replacement",
        basis="not a standalone current-runtime central numerator row",
        guard="must not be stacked with overlapping current channel",
        gap="requires explicit replacement or sidecar treatment",
        parity="not_yet_comparable_as_central_channel",
        action="keep as replacement/sidecar unless promoted by parity test",
    )


def _forecast_central_treatment(channel_id: str, classification: str) -> dict[str, str]:
    if channel_id in {
        "direct_treasury_interest_support",
        "bank_treasury_interest_support",
    }:
        return _treatment(
            numerator="replacement_block_input_not_selected_standalone_N",
            denominator="selected_forecast_moving_or_path_D",
            role="public_interest_replacement_block_input",
            centrality="central_block_input",
            basis="legacy first-forecast interest support retained as a net-block input",
            guard="must not be added on top of the public-interest net block",
            gap="needs current/historical adapter for direct comparison",
            parity="forecast_method_retained_as_replacement_block_input",
            action="carry as block input and comparison lane, not standalone selected N",
        )
    if classification == "included_as_public_interest_replacement_block":
        return _treatment(
            numerator="included_in_selected_forecast_central_N",
            denominator="selected_forecast_moving_or_path_D",
            role="public_interest_replacement_block_output",
            centrality="central",
            basis="net public-interest replacement block",
            guard="replaces legacy direct plus bank interest rows",
            gap="needs current/historical adapter for direct comparison",
            parity="forecast_central_replacement_block_available",
            action="promote matching current/historical adapter where source basis exists",
        )
    if classification == "replaced_by_current_tdcsim_holder_filter":
        return _treatment(
            numerator="diagnostic_guard_not_selected_standalone_N",
            denominator="selected_forecast_moving_or_path_D",
            role="holder_filter_guard",
            centrality="central_guard",
            basis="TDCSim holder-filtered direct and bank Treasury bases",
            guard="do not apply a second foreign-holder haircut",
            gap="current/historical holder basis may need explicit adapter labels",
            parity="forecast_holder_filter_guard_available",
            action="carry as guard/provenance row only",
        )
    if classification in FORECAST_CENTRAL_CLASSIFICATIONS:
        if classification.startswith("integrated_in_public_interest_net_block"):
            return _treatment(
                numerator="replacement_block_input_not_selected_standalone_N",
                denominator="selected_forecast_moving_or_path_D",
                role="public_interest_replacement_block_input",
                centrality="central_block_input",
                basis="public-interest net-block subcomponent or absorber",
                guard="must remain inside the net block and not be added separately",
                gap="needs current/historical adapter for direct comparison",
                parity="forecast_method_retained_as_replacement_block_input",
                action="carry as signed block input/absorber inside public-interest parity",
            )
        return _treatment(
            numerator="included_in_forecast_central_N",
            denominator="selected_forecast_moving_or_path_D",
            role="forecast_central_channel",
            centrality="central",
            basis="TDCSim/CBO forecast output or public-interest replacement block",
            guard="net block replaces legacy interest rows; holder filter avoids second foreign haircut",
            gap="needs current/historical adapter for direct comparison",
            parity="forecast_central_method_available",
            action="promote matching current/historical adapter where source basis exists",
        )
    return _treatment(
        numerator="not_in_forecast_central_N",
        denominator="selected_forecast_moving_or_path_D",
        role="forecast_noncentral_channel",
        centrality="not_central",
        basis="classification keeps channel outside central forecast",
        guard="blocked unless no-overlap and source path are proven",
        gap="forecast central narrower than current runtime",
        parity="forecast_gap_or_deliberate_exclusion",
        action="use classification-specific roadmap before central promotion",
    )


def _forecast_sensitivity_treatment(
    channel_id: str,
    classification: str,
) -> dict[str, str]:
    if classification in FORECAST_SENSITIVITY_CLASSIFICATIONS:
        return _treatment(
            numerator="included_in_forecast_sensitivity_N",
            denominator="inherits_selected_forecast_moving_or_path_D",
            role="forecast_sensitivity_channel",
            centrality="sensitivity",
            basis="bounded forecast residual sensitivity",
            guard="paired terms and denominator-overlap guard where relevant",
            gap="not yet central because assumption/evidence is weaker",
            parity="sensitivity_available_not_central",
            action="decide whether to promote, replace, or keep sensitivity",
        )
    if channel_id in {
        "safe_asset_allocation_drag",
        "zero_interest_credit_attenuation",
        "firm_liquid_asset_cushion",
        "firm_rollover_pressure_drag",
    }:
        return _treatment(
            numerator="planned_or_blocked_sensitivity_only",
            denominator="inherits_selected_forecast_D_if_used",
            role="forecast_gap_channel",
            centrality="planned_or_blocked",
            basis="remaining channel plan rather than central forecast row",
            guard="must prove disjoint basis or replacement logic",
            gap="needs real modeling decision before central use",
            parity="gap_mapped_not_closed",
            action="complete channel-specific admission test",
        )
    return _treatment(
        numerator="not_needed_as_forecast_sensitivity",
        denominator="inherits_selected_forecast_D_if_compared",
        role="already_central_or_not_applicable",
        centrality="not_applicable",
        basis="central/replacement treatment already handles this channel or excludes it",
        guard="do not duplicate central channel in sensitivity",
        gap="no separate sensitivity needed unless assumption is reopened",
        parity="sensitivity_not_required",
        action="keep out of sensitivity unless a distinct assumption is introduced",
    )


def _historical_treatment(channel_id: str) -> dict[str, str]:
    if channel_id in HISTORICAL_SOURCE_CONTEXT_CHANNELS:
        return _treatment(
            numerator="historical_context_or_partial_path_available",
            denominator="historical_path_D_or_context_D",
            role="historical_validation_context",
            centrality="context",
            basis="source-backed historical paths or partial TDC/context ledgers",
            guard="historical rows are not evidence-mode classifiers",
            gap="historical path not rebuilt on full shared forecast/current channel map",
            parity="historical_context_available_but_not_final_parity",
            action="rebuild historical adapter on shared channel ids after forecast/current parity",
        )
    return _treatment(
        numerator="not_historical_context_ready",
        denominator="historical_path_D_if_compared",
        role="historical_gap_channel",
        centrality="not_ready",
        basis="no comparable historical channel adapter in current parity readout",
        guard="do not infer missing historical path from current or forecast assumption",
        gap="historical adapter missing",
        parity="historical_gap",
        action="leave unmapped until source-backed historical adapter exists",
    )


def _treatment(
    *,
    numerator: str,
    denominator: str,
    role: str,
    centrality: str,
    basis: str,
    guard: str,
    gap: str,
    parity: str,
    action: str,
) -> dict[str, str]:
    return {
        "numerator_treatment": numerator,
        "denominator_treatment": denominator,
        "model_role": role,
        "centrality": centrality,
        "measurement_basis": basis,
        "overlap_guard": guard,
        "comparability_gap": gap,
        "parity_status": parity,
        "next_model_action": action,
    }


def _surface_entry_role(
    channel: Mapping[str, str],
    surface_id: str,
    treatment: Mapping[str, str],
) -> str:
    if surface_id == "forecast_central_tdcsim_cbo":
        return channel.get(
            "selected_central_entry_role",
            treatment["model_role"],
        )
    if surface_id == "forecast_sensitivity_tdcsim_cbo":
        if treatment["centrality"] in {"sensitivity", "planned_or_blocked"}:
            return treatment["centrality"]
        return "not_applicable_to_forecast_sensitivity"
    if surface_id == "current_assumption_runtime":
        if treatment["centrality"] == "central":
            return "standalone_current_runtime_term_or_configurable_channel"
        return treatment["centrality"]
    if surface_id == "historical_path_context":
        if treatment["centrality"] in {"context", "partial_context"}:
            return "historical_context_not_classifier"
        return treatment["centrality"]
    return treatment["model_role"]


def _denominator_row(
    *,
    surface_id: str,
    contract: Mapping[str, str],
    denominator_rule: str,
    path_component: str,
    moving_rate_response: str,
    centrality: str,
    gap: str,
    action: str,
) -> dict[str, str]:
    surface = SURFACE_DEFINITIONS[surface_id]
    return {
        "methodology_parity_denominator_row_id": f"methodology_parity_D::{surface_id}",
        "surface_id": surface_id,
        "surface_label": surface["surface_label"],
        "denominator_object_id": contract.get("denominator_object_id", ""),
        "denominator_role": contract.get("denominator_role", ""),
        "denominator_rule": denominator_rule,
        "fixed_anchor_component": contract.get("fixed_anchor_component", ""),
        "path_component": path_component,
        "moving_rate_response": moving_rate_response,
        "centrality": centrality,
        "comparability_gap": gap,
        "next_model_action": action,
        "allowed_use": "methodology_parity_denominator_comparison",
        "blocked_use": (
            "silent_D_reuse_across_surfaces;freezing_D_for_rate_scenarios;"
            "canonical_headline_promotion"
        ),
        "claim_boundary": "denominator_parity_readout_only_not_D_change",
    }


def _roadmap_row(spec: Mapping[str, str]) -> dict[str, str]:
    return {
        "methodology_parity_roadmap_row_id": f"methodology_parity_roadmap::{spec['id']}",
        "priority_rank": spec["rank"],
        "workstream_id": spec["id"],
        "workstream_label": spec["label"],
        "model_reason": spec["reason"],
        "inputs_needed": spec["inputs"],
        "implementation_target": spec["target"],
        "promotion_test": spec["test"],
        "expected_model_effect": spec["effect"],
        "do_not_do": spec["avoid"],
        "status": spec["status"],
        "allowed_use": "model_roadmap_for_methodology_parity",
        "blocked_use": "release_packaging_or_claim_promotion_without_model_gate",
        "claim_boundary": "roadmap_only_not_model_value_change",
    }


def _require_surface_rows(
    channel_rows: Sequence[Mapping[str, str]],
    denominator_rows: Sequence[Mapping[str, str]],
) -> None:
    surfaces = {row["surface_id"] for row in channel_rows}
    missing = set(SURFACE_DEFINITIONS) - surfaces
    if missing:
        raise MethodologyParityError(
            "missing channel surface rows: " + ", ".join(sorted(missing))
        )
    denom_surfaces = {row["surface_id"] for row in denominator_rows}
    missing_denoms = set(SURFACE_DEFINITIONS) - denom_surfaces
    if missing_denoms:
        raise MethodologyParityError(
            "missing denominator surface rows: " + ", ".join(sorted(missing_denoms))
        )


def _find_contract(
    rows: Sequence[Mapping[str, str]],
    *,
    ratio_object_id: str,
    row_role: str,
) -> Mapping[str, str]:
    for row in rows:
        if row.get("ratio_object_id") == ratio_object_id and row.get("row_role") == row_role:
            return row
    raise MethodologyParityError(
        f"missing denominator contract for {ratio_object_id} / {row_role}"
    )


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise MethodologyParityError(f"missing required input: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_optional(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

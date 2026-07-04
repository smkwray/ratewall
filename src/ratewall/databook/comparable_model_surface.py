"""Comparable current/forecast/historical model review surface."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_METHODOLOGY_PARITY_DIR = Path(
    "var/preliminary_scenario_results/methodology_parity"
)
DEFAULT_CORE_SUPPORT_DIR = Path("var/preliminary_scenario_results/core_support_parity")
DEFAULT_DENOMINATOR_PARITY_DIR = Path(
    "var/preliminary_scenario_results/denominator_parity"
)
DEFAULT_RESIDUAL_CLOSURE_DIR = Path(
    "var/preliminary_scenario_results/residual_channel_closure"
)
DEFAULT_HISTORICAL_ADAPTER_DIR = Path(
    "var/preliminary_scenario_results/historical_comparable_adapter"
)
DEFAULT_SOURCE_METHOD_DIR = Path("var/preliminary_scenario_results/source_method_matrix")
DEFAULT_FORECAST_READOUT_DIR = Path("var/preliminary_scenario_results/forecast_10y")
DEFAULT_FORECAST_HARDENING_DIR = Path(
    "var/preliminary_scenario_results/forecast_hardening"
)
DEFAULT_CURRENT_OVERLAY_DIR = Path(
    "var/preliminary_scenario_results/current_observed_overlay"
)
DEFAULT_REALIZED_SAFE_YIELD_DIR = Path(
    "var/preliminary_scenario_results/realized_safe_yield_income"
)
DEFAULT_HISTORICAL_PROVISIONAL_DIR = Path(
    "var/preliminary_scenario_results/historical_provisional_estimate"
)

COMPARABLE_CHANNEL_SURFACE_FIELDS = [
    "comparable_channel_surface_row_id",
    "surface_id",
    "surface_family",
    "channel_id",
    "channel_label",
    "shared_channel_family",
    "surface_channel_role",
    "object_role",
    "model_treatment_status",
    "representative_period",
    "representative_numerator_value_bil",
    "source_row_count",
    "central_N_treatment",
    "sensitivity_treatment",
    "replacement_group",
    "denominator_treatment",
    "historical_ratio_not_classifier",
    "source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

COMPARABLE_DENOMINATOR_SURFACE_FIELDS = [
    "comparable_denominator_surface_row_id",
    "surface_id",
    "surface_family",
    "denominator_variant",
    "denominator_role",
    "object_role",
    "selected_variant",
    "representative_period",
    "representative_denominator_value_bil",
    "fixed_anchor_component_pp_gdp",
    "rate_response_status",
    "source_row_count",
    "historical_ratio_not_classifier",
    "source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

COMPARABLE_REVIEW_SUMMARY_FIELDS = [
    "comparable_review_summary_row_id",
    "summary_scope",
    "surface_id",
    "metric_id",
    "metric_value",
    "interpretation",
    "allowed_use",
    "blocked_use",
]

COMPARABLE_MODEL_STATUS_FIELDS = [
    "comparable_model_status_row_id",
    "surface_id",
    "surface_family",
    "status_role",
    "object_role",
    "representative_period",
    "representative_case",
    "selected_or_provisional_n_bil",
    "selected_or_provisional_d_bil",
    "selected_or_provisional_ratewall_ratio",
    "numerator_method_plain",
    "denominator_method_plain",
    "source_method_status",
    "final_classifier_allowed",
    "headline_promotion_allowed",
    "main_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

COMPARABLE_GAP_PRIORITY_FIELDS = [
    "comparable_gap_priority_row_id",
    "priority_rank",
    "gap_id",
    "surface_id",
    "model_area",
    "object_role",
    "priority_bucket",
    "materiality_status",
    "feasibility_status",
    "current_source_status",
    "central_n_delta_bil_allowed",
    "gap_description",
    "next_model_action",
    "do_not_do",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class ComparableModelSurfaceError(ValueError):
    """Raised when comparable surface inputs are missing or inconsistent."""


PUBLIC_INTEREST_VALUE_COLUMNS = {
    "direct_treasury_interest_support": "direct_treasury_current_demand_support_bil",
    "bank_treasury_interest_support": "bank_treasury_current_demand_support_bil",
    "net_interest_after_fiscal_tga_offsets": "net_interest_after_fiscal_tga_offsets_bil",
    "current_remittance_demand_offset": (
        "projected_current_remittance_demand_offset_bil"
    ),
    "future_remittance_drag_demand_offset": (
        "projected_future_remittance_drag_demand_offset_bil"
    ),
    "iorb_recipient_demand_channel": "projected_iorb_current_demand_support_bil",
    "on_rrp_recipient_demand_channel": "projected_on_rrp_current_demand_support_bil",
    "fiscal_offset": "fiscal_offset_bil",
    "tga_liquidity_offset": "tga_liquidity_offset_bil",
    "interest_income_tax_timing_drag": "interest_income_tax_timing_drag_bil",
}


def comparable_channel_surface_rows(
    *,
    methodology_parity_dir: str | Path = DEFAULT_METHODOLOGY_PARITY_DIR,
    core_support_dir: str | Path = DEFAULT_CORE_SUPPORT_DIR,
    residual_closure_dir: str | Path = DEFAULT_RESIDUAL_CLOSURE_DIR,
    historical_adapter_dir: str | Path = DEFAULT_HISTORICAL_ADAPTER_DIR,
) -> list[dict[str, str]]:
    """Return channel rows comparing current, forecast, and historical surfaces."""

    methodology_rows = _read_required(
        Path(methodology_parity_dir) / "ratewall_methodology_parity_channels.csv"
    )
    tdc_rows = _read_required(
        Path(core_support_dir) / "ratewall_tdc_ex_overlap_support_shared.csv"
    )
    public_rows = _read_required(
        Path(core_support_dir) / "ratewall_public_interest_net_block_shared.csv"
    )
    residual_rows = _read_required(
        Path(residual_closure_dir) / "ratewall_residual_channel_admission_matrix.csv"
    )
    historical_status_rows = _read_required(
        Path(historical_adapter_dir) / "ratewall_historical_channel_adapter_status.csv"
    )
    historical_component_rows = _read_required(
        Path(historical_adapter_dir) / "ratewall_historical_comparable_surface.csv"
    )

    residual_by_channel = {row["channel_id"]: row for row in residual_rows}
    historical_status_by_channel = {
        row["channel_id"]: row for row in historical_status_rows
    }
    historical_counts = Counter(row["channel_id"] for row in historical_component_rows)
    historical_values = _representative_historical_values(historical_component_rows)
    tdc_representative = _representative_row(tdc_rows)
    public_representative = _representative_row(public_rows)

    out: list[dict[str, str]] = []
    for row in methodology_rows:
        channel_id = row["channel_id"]
        surface_id = row["surface_id"]
        historical_ratio_not_classifier = (
            "true" if surface_id == "historical_path_context" else ""
        )
        source_row_count = ""
        representative_period = ""
        representative_value = ""
        source_status = row["parity_status"]
        central_n_treatment = _central_n_treatment(row)
        sensitivity_treatment = ""
        replacement_group = ""
        if surface_id == "forecast_central_tdcsim_cbo":
            representative_period, representative_value, source_row_count, source_status = (
                _forecast_channel_value(
                    channel_id=channel_id,
                    tdc_representative=tdc_representative,
                    tdc_row_count=len(tdc_rows),
                    public_representative=public_representative,
                    public_row_count=len(public_rows),
                    fallback_status=row["parity_status"],
                )
            )
        elif surface_id == "forecast_sensitivity_tdcsim_cbo":
            residual = residual_by_channel.get(channel_id)
            if residual is not None:
                sensitivity_treatment = residual["sensitivity_treatment"]
                replacement_group = residual["replacement_group"]
                central_n_treatment = residual["central_N_treatment"]
                source_status = residual["source_or_calibration_status"]
                source_row_count = "1"
        elif surface_id == "historical_path_context":
            status = historical_status_by_channel[channel_id]
            source_row_count = status["historical_source_row_count"]
            source_status = status["source_status"]
            representative_period, representative_value = historical_values.get(
                channel_id, ("", "")
            )
            if historical_counts[channel_id]:
                source_row_count = str(historical_counts[channel_id])
            central_n_treatment = "historical_context_not_central_N"
        out.append(
            {
                "comparable_channel_surface_row_id": (
                    f"comparable_channel_surface::{surface_id}::{channel_id}"
                ),
                "surface_id": surface_id,
                "surface_family": row["surface_family"],
                "channel_id": channel_id,
                "channel_label": row["channel_label"],
                "shared_channel_family": _shared_channel_family(channel_id),
                "surface_channel_role": row["surface_entry_role"],
                "object_role": _channel_object_role(row),
                "model_treatment_status": row["centrality"],
                "representative_period": representative_period,
                "representative_numerator_value_bil": representative_value,
                "source_row_count": source_row_count,
                "central_N_treatment": central_n_treatment,
                "sensitivity_treatment": sensitivity_treatment,
                "replacement_group": replacement_group,
                "denominator_treatment": row["denominator_treatment"],
                "historical_ratio_not_classifier": historical_ratio_not_classifier,
                "source_status": source_status,
                "allowed_use": "forecast_current_historical_model_review",
                "blocked_use": (
                    "canonical_headline_promotion;evidence_mode_claim;"
                    "missing_value_backfill;model_value_change"
                ),
                "claim_boundary": "comparable_review_surface_no_n_d_beta_chi_change",
            }
        )
    return out


def comparable_denominator_surface_rows(
    *,
    methodology_parity_dir: str | Path = DEFAULT_METHODOLOGY_PARITY_DIR,
    denominator_parity_dir: str | Path = DEFAULT_DENOMINATOR_PARITY_DIR,
    historical_adapter_dir: str | Path = DEFAULT_HISTORICAL_ADAPTER_DIR,
) -> list[dict[str, str]]:
    """Return denominator rows comparing fixed, path, moving, and historical variants."""

    methodology_rows = _read_required(
        Path(methodology_parity_dir) / "ratewall_methodology_parity_denominators.csv"
    )
    forecast_variants = _read_required(
        Path(denominator_parity_dir) / "ratewall_denominator_variant_surface.csv"
    )
    historical_variants = _read_required(
        Path(historical_adapter_dir) / "ratewall_historical_denominator_variant_bridge.csv"
    )
    forecast_by_variant = _representative_forecast_denominator_variants(
        forecast_variants
    )
    methodology_by_surface = {row["surface_id"]: row for row in methodology_rows}
    out: list[dict[str, str]] = []
    current = methodology_by_surface["current_assumption_runtime"]
    out.append(
        _denominator_row(
            surface_id="current_assumption_runtime",
            surface_family="current_or_static",
            variant="fixed_runtime_D",
            role=current["denominator_role"],
            selected="true",
            period="current_runtime_reference",
            value="",
            fixed_anchor=current["fixed_anchor_component"],
            rate_status=current["moving_rate_response"],
            source_row_count="1",
            historical_not_classifier="",
            source_status="methodology_parity_denominator_contract_only",
        )
    )
    forecast = methodology_by_surface["forecast_central_tdcsim_cbo"]
    for variant, row in forecast_by_variant.items():
        out.append(
            _denominator_row(
                surface_id="forecast_central_tdcsim_cbo",
                surface_family="forecast",
                variant=variant,
                role=row["variant_role"],
                selected=row["selected_variant"],
                period=row["fiscal_year"],
                value=row["denominator_value_bil"],
                fixed_anchor=forecast["fixed_anchor_component"],
                rate_status=forecast["moving_rate_response"],
                source_row_count=str(
                    sum(
                        1
                        for candidate in forecast_variants
                        if candidate["denominator_variant"] == variant
                    )
                ),
                historical_not_classifier="",
                source_status="source_backed_forecast_denominator_variant_surface",
            )
        )
    for row in historical_variants:
        out.append(
            _denominator_row(
                surface_id="historical_path_context",
                surface_family="historical",
                variant=row["denominator_variant"],
                role=row["variant_role"],
                selected=row["selected_variant"],
                period="historical_context",
                value=row["historical_path_D_bil"]
                or row["fixed_D_comparison_bil"]
                or row["moving_D_bil"],
                fixed_anchor=row["fixed_anchor_component_pp_gdp"],
                rate_status="historical_rate_path_not_forecast_scenario_response",
                source_row_count="1",
                historical_not_classifier=row["historical_ratio_not_classifier"],
                source_status=row["source_status"],
            )
        )
    return out


def comparable_review_summary_rows(
    channel_rows: Sequence[Mapping[str, str]],
    denominator_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return compact summary counts for the comparable review surface."""

    rows: list[dict[str, str]] = []
    for surface_id in sorted({row["surface_id"] for row in channel_rows}):
        surface_rows = [row for row in channel_rows if row["surface_id"] == surface_id]
        rows.extend(
            [
                _summary(
                    surface_id,
                    "channel_rows",
                    str(len(surface_rows)),
                    "shared channel rows on this surface",
                ),
                _summary(
                    surface_id,
                    "selected_n_rows",
                    str(
                        sum(row["object_role"] == "selected_n" for row in surface_rows)
                    ),
                    "rows selected into N on this surface",
                ),
                _summary(
                    surface_id,
                    "selected_block_input_rows",
                    str(
                        sum(
                            row["object_role"] == "selected_block_input"
                            for row in surface_rows
                        )
                    ),
                    "rows feeding selected blocks without standalone add-on treatment",
                ),
                _summary(
                    surface_id,
                    "source_gap_rows",
                    str(
                        sum(
                            row["source_status"]
                            in {
                                "not_source_backed_in_current_adapter",
                                "historical_gap",
                            }
                            or row["model_treatment_status"] == "not_ready"
                            for row in surface_rows
                        )
                    ),
                    "rows requiring source-backed adapter work before numeric comparison",
                ),
            ]
        )
    rows.append(
        _summary(
            "all_surfaces",
            "denominator_variant_rows",
            str(len(denominator_rows)),
            "fixed/path/moving/current/historical denominator labels in the review",
        )
    )
    rows.append(
        _summary(
            "all_surfaces",
            "historical_classifier_rows",
            str(
                sum(
                    row["historical_ratio_not_classifier"] == "false"
                    for row in channel_rows
                )
                + sum(
                    row["historical_ratio_not_classifier"] == "false"
                    for row in denominator_rows
                )
            ),
            "must remain zero; historical rows are context only",
        )
    )
    return rows


def comparable_model_status_rows(
    *,
    source_method_dir: str | Path = DEFAULT_SOURCE_METHOD_DIR,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
    forecast_hardening_dir: str | Path = DEFAULT_FORECAST_HARDENING_DIR,
    current_overlay_dir: str | Path = DEFAULT_CURRENT_OVERLAY_DIR,
    historical_provisional_dir: str | Path = DEFAULT_HISTORICAL_PROVISIONAL_DIR,
) -> list[dict[str, str]]:
    """Return a plain status row for each live model surface."""

    source_rows = _read_required(
        Path(source_method_dir) / "ratewall_source_method_matrix.csv"
    )
    source_by_block = {row["block_id"]: row for row in source_rows}
    forecast_rows = _read_required(
        Path(forecast_readout_dir) / "ratewall_forecast_central_scenario_surface.csv"
    )
    assumption_rows = _read_required(
        Path(forecast_hardening_dir)
        / "ratewall_forecast_central_assumption_ledger.csv"
    )
    current_rows = _read_required(
        Path(current_overlay_dir) / "ratewall_current_assumption_benchmark.csv"
    )
    current_candidates = _read_required(
        Path(current_overlay_dir) / "ratewall_current_observed_overlay_candidate.csv"
    )
    historical_rows = _read_required(
        Path(historical_provisional_dir) / "ratewall_historical_provisional_rw_panel.csv"
    )
    historical_gates = _read_required(
        Path(historical_provisional_dir)
        / "ratewall_historical_provisional_classifier_gate.csv"
    )

    forecast = _representative_forecast_status_row(forecast_rows)
    current = _selected_current_benchmark_row(current_rows)
    historical = _representative_historical_status_row(historical_rows)
    selected_n_rule = _assumption_value(assumption_rows, "forecast_selected_n_rule")
    selected_d_rule = _assumption_value(assumption_rows, "forecast_selected_D_rule")
    blocked_historical_gates = [
        row["check_id"]
        for row in historical_gates
        if row["gate_status"].startswith("blocked")
    ]
    historical_blocker = (
        ";".join(blocked_historical_gates)
        if blocked_historical_gates
        else "R37_historical_context_accepted_nonclassifier"
    )
    current_overlay_blockers = sorted(
        {
            row["candidate_status"]
            for row in current_candidates
            if row["benchmark_replacement_allowed"] == "false"
        }
    )
    return [
        _model_status_row(
            surface_id="forecast_central_tdcsim_cbo",
            surface_family="forecast",
            status_role="selected_forecast_model_surface",
            object_role="selected_n",
            period=forecast["fiscal_year"],
            case=forecast["scenario_id"],
            n_value=forecast["central_n_bil"],
            d_value=forecast["central_moving_denominator_bil"],
            ratio=forecast["central_ratewall_ratio"],
            numerator_method=selected_n_rule,
            denominator_method=selected_d_rule,
            source_status=_surface_source_status(
                source_by_block,
                ["forecast_tdc_support", "forecast_public_interest_net_block"],
            ),
            final_classifier_allowed="false",
            headline_allowed="false",
            blocker="model_readout_not_canonical_headline_or_evidence_mode",
        ),
        _model_status_row(
            surface_id="current_assumption_runtime",
            surface_family="current_or_static",
            status_role="selected_current_benchmark_recast",
            object_role="selected_benchmark_recast",
            period=current["forecast_year"],
            case=current["benchmark_id"],
            n_value=current["benchmark_numerator_bil"],
            d_value=current["fixed_D_bil"],
            ratio=current["benchmark_ratewall_ratio"],
            numerator_method="existing assumption runtime recast unchanged",
            denominator_method="fixed current D benchmark",
            source_status=_surface_source_status(
                source_by_block,
                ["current_public_interest_runtime", "current_denominator"],
            ),
            final_classifier_allowed="false",
            headline_allowed="false",
            blocker="observed_overlay_not_admitted;benchmark_replacement_disallowed",
        ),
        _model_status_row(
            surface_id="current_observed_overlay_candidate",
            surface_family="current_or_static",
            status_role="overlay_candidate_gate",
            object_role="candidate_replacement",
            period=current["forecast_year"],
            case=f"{len(current_candidates)} candidate rows",
            n_value="",
            d_value="",
            ratio="",
            numerator_method="source-led current replacements are candidates only",
            denominator_method="inherits current benchmark D if ever admitted",
            source_status=";".join(current_overlay_blockers),
            final_classifier_allowed="false",
            headline_allowed="false",
            blocker="silent_current_benchmark_replacement_blocked",
        ),
        _model_status_row(
            surface_id="historical_path_context",
            surface_family="historical",
            status_role="provisional_historical_comparison",
            object_role="diagnostic_context",
            period=historical["period"],
            case=historical["assumption_case"],
            n_value=historical["provisional_n_bil"],
            d_value=historical["historical_path_D_bil"],
            ratio=historical["provisional_historical_ratewall_ratio"],
            numerator_method="partial source-backed historical components only",
            denominator_method="CBO quarterly GDP times fed funds path D",
            source_status=_surface_source_status(
                source_by_block,
                ["historical_public_interest_net_block", "historical_denominator"],
            ),
            final_classifier_allowed=historical["final_classifier_allowed"],
            headline_allowed="false",
            blocker=historical_blocker,
        ),
    ]


def comparable_gap_priority_rows(
    *,
    source_method_dir: str | Path = DEFAULT_SOURCE_METHOD_DIR,
    current_overlay_dir: str | Path = DEFAULT_CURRENT_OVERLAY_DIR,
    realized_safe_yield_dir: str | Path = DEFAULT_REALIZED_SAFE_YIELD_DIR,
    historical_provisional_dir: str | Path = DEFAULT_HISTORICAL_PROVISIONAL_DIR,
) -> list[dict[str, str]]:
    """Return a ranked list of remaining model gaps to avoid roadmap drift."""

    source_rows = _read_required(
        Path(source_method_dir) / "ratewall_source_method_matrix.csv"
    )
    current_candidates = _read_required(
        Path(current_overlay_dir) / "ratewall_current_observed_overlay_candidate.csv"
    )
    current_admission = _read_required(
        Path(current_overlay_dir) / "ratewall_current_observed_overlay_admission.csv"
    )
    safe_yield_gaps = _read_required(
        Path(realized_safe_yield_dir) / "ratewall_realized_safe_yield_income_gap.csv"
    )
    safe_yield_admission = _read_optional(
        Path(realized_safe_yield_dir)
        / "ratewall_realized_safe_yield_payer_flow_admission.csv"
    )
    historical_gates = _read_required(
        Path(historical_provisional_dir)
        / "ratewall_historical_provisional_classifier_gate.csv"
    )
    source_by_block = {row["block_id"]: row for row in source_rows}

    specs: list[dict[str, str]] = []
    specs.append(
        _manual_gap_spec(
            gap_id="R37_historical_context_nonclassifier_closure",
            surface_id="historical_path_context",
            model_area="historical_classifier",
            object_role="diagnostic_context",
            priority_bucket="closed_context_not_active_model_gap",
            materiality_status="historical_context_accepted_not_wall_hit_classifier",
            feasibility_status="R37_resolved_nonclassifier_policy_decision",
            current_source_status=_blocked_gate_summary(historical_gates),
            central_allowed="false",
            gap_description="historical technical gates pass, but rows remain context/validation by design",
            next_action="keep historical rows nonclassifier; active work has moved to realized safe-yield/deposit",
            do_not_do="do_not_quote_R30_ratios_as_final_historical_classifiers",
        )
    )
    specs.append(
        _manual_gap_spec(
            gap_id="D2_current_object_bridge_freeze_now",
            surface_id="current_assumption_runtime",
            model_area="current_overlay",
            object_role="selected_benchmark_recast",
            priority_bucket="medium_current_adjudication_after_R39",
            materiality_status="source_filled_current_overlay_changes_N_not_selected",
            feasibility_status=current_admission[0]["replacement_gate_status"],
            current_source_status=(
                _current_overlay_summary(current_candidates)
                + ";"
                + current_admission[0]["candidate_minus_benchmark_n_bil"]
            ),
            central_allowed="false",
            gap_description="R38 built current public-interest/TDC/D overlay candidates; benchmark still selected",
            next_action="keep selected benchmark frozen unless a named current replacement surface passes",
            do_not_do="do_not_silently_replace_current_benchmark",
        )
    )
    for gap in safe_yield_gaps:
        admission_status = (
            safe_yield_admission[0]["blocked_reason"]
            if safe_yield_admission
            else gap["required_to_unpark"]
        )
        specs.append(
            _manual_gap_spec(
                gap_id=gap["source_channel_id"],
                surface_id="current_and_historical_overlay",
                model_area="realized_safe_yield",
                object_role="blocked_source_or_method",
                priority_bucket="medium_candidate_only",
                materiality_status="unknown_until_payer_flow_and_recipient_mapping",
                feasibility_status=gap["build_status"],
                current_source_status=admission_status,
                central_allowed=gap["central_n_delta_bil_allowed"],
                gap_description="realized safe-yield composite remains parked",
                next_action="build payer-flow, recipient allocation, tax timing, conversion, D, and overlap proof",
                do_not_do="do_not_use_raw_stock_times_shortcut_or_tdc_substitute",
            )
        )
    specs.append(
        _gap_spec_from_source_row(
            source_by_block["forecast_remittance_baseline_path"],
            "forecast_remittance_scenario_delta_model",
            "forecast_public_interest",
            "lower_priority_context_already_sourced",
            "low_for_current_central_forecast_until_scenario_delta_model_exists",
            "baseline_csv_extracted_delta_model_not_admitted",
            "only build a remittance scenario-delta model if future forecast scenarios require it",
            "do_not_convert_CBO_baseline_remittances_to_private_demand_support",
        )
    )
    return [
        _gap_priority_row(index + 1, spec)
        for index, spec in enumerate(sorted(specs, key=_gap_sort_key))
    ]


def comparable_model_readout_markdown(
    channel_rows: Sequence[Mapping[str, str]],
    denominator_rows: Sequence[Mapping[str, str]],
    summary_rows: Sequence[Mapping[str, str]],
    model_status_rows: Sequence[Mapping[str, str]] = (),
    gap_priority_rows: Sequence[Mapping[str, str]] = (),
) -> str:
    """Return a concise economist-facing readout for R24."""

    by_surface = Counter(row["surface_id"] for row in channel_rows)
    central_forecast = [
        row
        for row in channel_rows
        if row["surface_id"] == "forecast_central_tdcsim_cbo"
        and row["model_treatment_status"] in {"central", "central_block_input"}
    ]
    historical_source = [
        row
        for row in channel_rows
        if row["surface_id"] == "historical_path_context"
        and row["representative_numerator_value_bil"] != ""
    ]
    denominator_selected = [
        row
        for row in denominator_rows
        if row["selected_variant"] == "true"
        or row["surface_id"] == "current_assumption_runtime"
    ]
    lines = [
        "# Comparable Model Surface",
        "",
        "This is a review surface only. It does not change RateWall N, D, beta, chi, or headline status.",
        "",
        "## What It Shows",
        "",
        f"- Channel rows: {len(channel_rows)} across {len(by_surface)} surfaces.",
        f"- Forecast central/block-input rows: {len(central_forecast)}.",
        f"- Historical rows with explicit component values: {len(historical_source)}.",
        f"- Denominator rows: {len(denominator_rows)}; selected/current reference rows: {len(denominator_selected)}.",
        "",
        "## Main Interpretation",
        "",
        "- Forecast is the only surface with a complete central numeric model path.",
        "- Historical is useful as context where explicit component columns exist, but it is not a classifier.",
        "- Current/static rows remain useful for runtime comparison, but they are not the forecast path model.",
        "- Fixed D, path D, moving D, and historical D labels are kept separate.",
        "",
        "## Current Model Status",
        "",
    ]
    if model_status_rows:
        for row in model_status_rows:
            ratio = row["selected_or_provisional_ratewall_ratio"] or "not numeric"
            lines.append(
                f"- {row['surface_id']}: {row['status_role']}; "
                f"period/case {row['representative_period']} / "
                f"{row['representative_case']}; RW {ratio}; blocker "
                f"{row['main_blocker']}."
            )
    else:
        lines.append("- No model-status rows supplied.")
    lines.extend(
        [
            "",
            "## Next Model Gaps",
            "",
        ]
    )
    if gap_priority_rows:
        for row in gap_priority_rows[:8]:
            lines.append(
                f"- R{row['priority_rank']} {row['gap_id']}: "
                f"{row['priority_bucket']}; next: {row['next_model_action']}."
            )
    else:
        lines.append("- No gap-priority rows supplied.")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- No missing historical value is filled from forecast assumptions.",
            "- Direct and bank Treasury interest remain replacement-block inputs, not extra add-ons.",
            "- Residual channels remain sensitivity, replacement, sidecar, or gap rows unless a later source-backed basis admits them.",
            "- Historical rows remain `historical_ratio_not_classifier=true`.",
            "",
            "## Summary Rows",
            "",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"- {row['surface_id']} / {row['metric_id']}: {row['metric_value']} "
            f"({row['interpretation']})"
        )
    lines.append("")
    return "\n".join(lines)


def write_comparable_model_surface_outputs(
    output_dir: str | Path,
    *,
    channel_rows: Sequence[Mapping[str, str]],
    denominator_rows: Sequence[Mapping[str, str]],
    summary_rows: Sequence[Mapping[str, str]],
    model_status_rows: Sequence[Mapping[str, str]] = (),
    gap_priority_rows: Sequence[Mapping[str, str]] = (),
    readout_markdown: str,
) -> dict[str, Path]:
    """Write R24 comparable model surface outputs."""

    root = Path(output_dir)
    outputs = {
        "channel_csv": root / "ratewall_comparable_channel_surface.csv",
        "denominator_csv": root / "ratewall_comparable_denominator_surface.csv",
        "summary_csv": root / "ratewall_comparable_review_summary.csv",
        "model_status_csv": root / "ratewall_comparable_model_status.csv",
        "gap_priority_csv": root / "ratewall_comparable_gap_priority.csv",
        "readout_md": root / "comparable_model_surface_readout.md",
    }
    write_rows(
        outputs["channel_csv"], list(channel_rows), COMPARABLE_CHANNEL_SURFACE_FIELDS
    )
    write_rows(
        outputs["denominator_csv"],
        list(denominator_rows),
        COMPARABLE_DENOMINATOR_SURFACE_FIELDS,
    )
    write_rows(
        outputs["summary_csv"], list(summary_rows), COMPARABLE_REVIEW_SUMMARY_FIELDS
    )
    write_rows(
        outputs["model_status_csv"],
        list(model_status_rows),
        COMPARABLE_MODEL_STATUS_FIELDS,
    )
    write_rows(
        outputs["gap_priority_csv"],
        list(gap_priority_rows),
        COMPARABLE_GAP_PRIORITY_FIELDS,
    )
    root.mkdir(parents=True, exist_ok=True)
    outputs["readout_md"].write_text(readout_markdown, encoding="utf-8")
    return outputs


def _forecast_channel_value(
    *,
    channel_id: str,
    tdc_representative: Mapping[str, str],
    tdc_row_count: int,
    public_representative: Mapping[str, str],
    public_row_count: int,
    fallback_status: str,
) -> tuple[str, str, str, str]:
    if channel_id == "tdc_ex_overlap_current_demand_support":
        return (
            tdc_representative["fiscal_year"],
            tdc_representative["tdc_current_demand_support_bil"],
            str(tdc_row_count),
            "source_backed_shared_tdc_ex_overlap_support",
        )
    value_column = PUBLIC_INTEREST_VALUE_COLUMNS.get(channel_id)
    if value_column is not None:
        return (
            public_representative["fiscal_year"],
            public_representative[value_column],
            str(public_row_count),
            f"source_backed_public_interest_net_block::{value_column}",
        )
    return "", "", "", fallback_status


def _representative_row(rows: Sequence[Mapping[str, str]]) -> Mapping[str, str]:
    if not rows:
        raise ComparableModelSurfaceError("cannot choose representative from empty rows")
    baselines = [
        row
        for row in rows
        if row.get("scenario_id") == row.get("baseline_scenario_id")
        and row.get("fiscal_year") == "2036"
    ]
    if baselines:
        return baselines[0]
    return rows[-1]


def _representative_historical_values(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for row in rows:
        key = row["channel_id"]
        if key not in out and row["historical_numerator_value_bil"] != "":
            out[key] = (row["period"], row["historical_numerator_value_bil"])
    return out


def _representative_forecast_denominator_variants(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Mapping[str, str]]:
    variants: dict[str, Mapping[str, str]] = {}
    for row in rows:
        if row["fiscal_year"] == "2036" and row["scenario_id"] == "cbo_baseline_noop_v1":
            variants[row["denominator_variant"]] = row
    if set(variants) == {"fixed_D", "path_D", "moving_D"}:
        return variants
    for row in rows:
        variants.setdefault(row["denominator_variant"], row)
    return variants


def _denominator_row(
    *,
    surface_id: str,
    surface_family: str,
    variant: str,
    role: str,
    selected: str,
    period: str,
    value: str,
    fixed_anchor: str,
    rate_status: str,
    source_row_count: str,
    historical_not_classifier: str,
    source_status: str,
) -> dict[str, str]:
    return {
        "comparable_denominator_surface_row_id": (
            f"comparable_denominator_surface::{surface_id}::{variant}"
        ),
        "surface_id": surface_id,
        "surface_family": surface_family,
        "denominator_variant": variant,
        "denominator_role": role,
        "object_role": "denominator_only",
        "selected_variant": selected,
        "representative_period": period,
        "representative_denominator_value_bil": value,
        "fixed_anchor_component_pp_gdp": fixed_anchor,
        "rate_response_status": rate_status,
        "source_row_count": source_row_count,
        "historical_ratio_not_classifier": historical_not_classifier,
        "source_status": source_status,
        "allowed_use": "forecast_current_historical_denominator_review",
        "blocked_use": "canonical_headline_promotion;evidence_mode_claim;model_D_change",
        "claim_boundary": "comparable_review_surface_no_n_d_beta_chi_change",
    }


def _summary(
    surface_id: str,
    metric_id: str,
    value: str,
    interpretation: str,
) -> dict[str, str]:
    return {
        "comparable_review_summary_row_id": (
            f"comparable_review_summary::{surface_id}::{metric_id}"
        ),
        "summary_scope": "comparable_model_surface",
        "surface_id": surface_id,
        "metric_id": metric_id,
        "metric_value": value,
        "interpretation": interpretation,
        "allowed_use": "model_review_status_summary",
        "blocked_use": "canonical_headline_promotion;evidence_mode_claim",
    }


def _model_status_row(
    *,
    surface_id: str,
    surface_family: str,
    status_role: str,
    object_role: str,
    period: str,
    case: str,
    n_value: str,
    d_value: str,
    ratio: str,
    numerator_method: str,
    denominator_method: str,
    source_status: str,
    final_classifier_allowed: str,
    headline_allowed: str,
    blocker: str,
) -> dict[str, str]:
    return {
        "comparable_model_status_row_id": f"comparable_model_status::{surface_id}",
        "surface_id": surface_id,
        "surface_family": surface_family,
        "status_role": status_role,
        "object_role": object_role,
        "representative_period": period,
        "representative_case": case,
        "selected_or_provisional_n_bil": n_value,
        "selected_or_provisional_d_bil": d_value,
        "selected_or_provisional_ratewall_ratio": ratio,
        "numerator_method_plain": numerator_method,
        "denominator_method_plain": denominator_method,
        "source_method_status": source_status,
        "final_classifier_allowed": final_classifier_allowed,
        "headline_promotion_allowed": headline_allowed,
        "main_blocker": blocker,
        "allowed_use": "comparable_model_status_readout",
        "blocked_use": "canonical_headline_promotion;evidence_mode_claim",
        "claim_boundary": "comparable_status_no_model_value_change",
    }


def _gap_spec_from_source_row(
    row: Mapping[str, str],
    gap_id: str,
    model_area: str,
    priority_bucket: str,
    materiality_status: str,
    feasibility_status: str,
    next_action: str,
    do_not_do: str,
) -> dict[str, str]:
    return _manual_gap_spec(
        gap_id=gap_id,
        surface_id=row["surface_id"],
        model_area=model_area,
        object_role=row.get("object_role", _source_row_object_role(row)),
        priority_bucket=priority_bucket,
        materiality_status=materiality_status,
        feasibility_status=feasibility_status,
        current_source_status=row["local_source_status"],
        central_allowed=row["central_n_delta_bil_allowed"],
        gap_description=row["known_gap"],
        next_action=next_action,
        do_not_do=do_not_do,
    )


def _manual_gap_spec(
    *,
    gap_id: str,
    surface_id: str,
    model_area: str,
    object_role: str,
    priority_bucket: str,
    materiality_status: str,
    feasibility_status: str,
    current_source_status: str,
    central_allowed: str,
    gap_description: str,
    next_action: str,
    do_not_do: str,
) -> dict[str, str]:
    return {
        "gap_id": gap_id,
        "surface_id": surface_id,
        "model_area": model_area,
        "object_role": object_role,
        "priority_bucket": priority_bucket,
        "materiality_status": materiality_status,
        "feasibility_status": feasibility_status,
        "current_source_status": current_source_status,
        "central_n_delta_bil_allowed": central_allowed,
        "gap_description": gap_description,
        "next_model_action": next_action,
        "do_not_do": do_not_do,
    }


def _gap_priority_row(index: int, spec: Mapping[str, str]) -> dict[str, str]:
    return {
        "comparable_gap_priority_row_id": (
            f"comparable_gap_priority::{index:02d}::{spec['gap_id']}"
        ),
        "priority_rank": str(index),
        "gap_id": spec["gap_id"],
        "surface_id": spec["surface_id"],
        "model_area": spec["model_area"],
        "object_role": spec["object_role"],
        "priority_bucket": spec["priority_bucket"],
        "materiality_status": spec["materiality_status"],
        "feasibility_status": spec["feasibility_status"],
        "current_source_status": spec["current_source_status"],
        "central_n_delta_bil_allowed": spec["central_n_delta_bil_allowed"],
        "gap_description": spec["gap_description"],
        "next_model_action": spec["next_model_action"],
        "do_not_do": spec["do_not_do"],
        "allowed_use": "model_gap_priority_queue",
        "blocked_use": "release_chore_queue;canonical_headline_promotion",
        "claim_boundary": "gap_priority_no_model_value_change",
    }


def _gap_sort_key(row: Mapping[str, str]) -> tuple[int, str]:
    explicit = {
        "realized_deposit_mmf_tbill_income_gap": 0,
        "D1_deposit_safe_yield_route": 0,
        "D2_current_object_bridge_freeze_now": 1,
        "R37_historical_context_nonclassifier_closure": 2,
        "forecast_remittance_scenario_delta_model": 3,
    }
    if row["gap_id"] in explicit:
        return explicit[row["gap_id"]], row["gap_id"]
    bucket = row["priority_bucket"]
    if bucket.startswith("high_impact_model"):
        rank = 3
    elif bucket.startswith("high_impact"):
        rank = 4
    elif bucket.startswith("medium_high"):
        rank = 5
    elif bucket.startswith("medium"):
        rank = 6
    else:
        rank = 7
    return rank, row["gap_id"]


def _representative_forecast_status_row(
    rows: Sequence[Mapping[str, str]],
) -> Mapping[str, str]:
    baselines = [
        row
        for row in rows
        if row["scenario_id"] == row["baseline_scenario_id"]
        and row["fiscal_year"] == "2036"
    ]
    if baselines:
        return baselines[0]
    return _representative_row(rows)


def _selected_current_benchmark_row(
    rows: Sequence[Mapping[str, str]],
) -> Mapping[str, str]:
    selected = [row for row in rows if row["selected_current_row"] == "true"]
    if selected:
        return selected[0]
    return rows[0]


def _representative_historical_status_row(
    rows: Sequence[Mapping[str, str]],
) -> Mapping[str, str]:
    base_rows = [row for row in rows if row["assumption_case"] == "base"]
    candidates = base_rows or list(rows)
    return sorted(candidates, key=lambda row: _period_key(row["period"]))[-1]


def _assumption_value(rows: Sequence[Mapping[str, str]], assumption_id: str) -> str:
    for row in rows:
        if row["assumption_id"] == assumption_id:
            return row["assumption_value"]
    raise ComparableModelSurfaceError(f"missing assumption row: {assumption_id}")


def _surface_source_status(
    source_by_block: Mapping[str, Mapping[str, str]], block_ids: Sequence[str]
) -> str:
    return ";".join(
        f"{block_id}={source_by_block[block_id]['local_source_status']}"
        for block_id in block_ids
    )


def _blocked_gate_summary(rows: Sequence[Mapping[str, str]]) -> str:
    blocked = [
        row["check_id"]
        for row in rows
        if row["gate_status"].startswith("blocked")
    ]
    return ";".join(blocked)


def _current_overlay_summary(rows: Sequence[Mapping[str, str]]) -> str:
    statuses = sorted({row["candidate_status"] for row in rows})
    return ";".join(statuses)


def _period_key(period: str) -> tuple[int, int]:
    return int(period[:4]), int(period[-1])


def _central_n_treatment(row: Mapping[str, str]) -> str:
    if row["centrality"] == "central":
        return "central_N_term"
    if row["centrality"] == "central_block_input":
        return "replacement_block_input_not_standalone"
    if row["centrality"] == "sensitivity":
        return "sensitivity_not_central_N"
    if row["surface_id"] == "historical_path_context":
        return "historical_context_not_central_N"
    return "not_in_central_N"


def _channel_object_role(row: Mapping[str, str]) -> str:
    if row["surface_id"] == "historical_path_context":
        return "diagnostic_context"
    if row["surface_id"] == "current_assumption_runtime":
        return "selected_benchmark_recast"
    if row["centrality"] == "central":
        return "selected_n"
    if row["centrality"] == "central_block_input":
        return "selected_block_input"
    if row["centrality"] == "sensitivity":
        return "sensitivity_only"
    if row["centrality"] == "not_ready":
        return "blocked_source_or_method"
    return "diagnostic_context"


def _source_row_object_role(row: Mapping[str, str]) -> str:
    if row["block_id"] in {"forecast_tdc_support", "forecast_public_interest_net_block"}:
        return "selected_n"
    if row["block_id"] == "forecast_remittance_baseline_path":
        return "selected_block_input"
    if row["surface_id"] == "current_assumption_runtime":
        return "selected_benchmark_recast"
    if row["surface_id"] == "historical_path_context":
        return "diagnostic_context"
    return "blocked_source_or_method"


def _shared_channel_family(channel_id: str) -> str:
    if channel_id == "tdc_ex_overlap_current_demand_support":
        return "tdc_ex_overlap_support"
    if channel_id in PUBLIC_INTEREST_VALUE_COLUMNS or channel_id in {
        "foreign_treasury_holder_leakage_drag",
    }:
        return "public_interest_net_block"
    return "residual_replacement_channel"


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ComparableModelSurfaceError(f"missing required input: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_optional(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

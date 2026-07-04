from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.comparable_model_surface import (
    COMPARABLE_CHANNEL_SURFACE_FIELDS,
    COMPARABLE_DENOMINATOR_SURFACE_FIELDS,
    COMPARABLE_GAP_PRIORITY_FIELDS,
    COMPARABLE_MODEL_STATUS_FIELDS,
    COMPARABLE_REVIEW_SUMMARY_FIELDS,
    comparable_channel_surface_rows,
    comparable_denominator_surface_rows,
    comparable_gap_priority_rows,
    comparable_model_readout_markdown,
    comparable_model_status_rows,
    comparable_review_summary_rows,
    write_comparable_model_surface_outputs,
)


def test_comparable_channel_surface_preserves_surface_roles(tmp_path: Path) -> None:
    dirs = _write_fixture(tmp_path)

    rows = _channel_rows(dirs)

    assert {field for row in rows for field in row} == set(
        COMPARABLE_CHANNEL_SURFACE_FIELDS
    )
    by_key = {(row["surface_id"], row["channel_id"]): row for row in rows}
    forecast_tdc = by_key[
        ("forecast_central_tdcsim_cbo", "tdc_ex_overlap_current_demand_support")
    ]
    assert forecast_tdc["representative_numerator_value_bil"] == "2.5"
    assert forecast_tdc["source_row_count"] == "1"
    assert forecast_tdc["central_N_treatment"] == "central_N_term"
    assert forecast_tdc["object_role"] == "selected_n"

    direct = by_key[
        ("forecast_central_tdcsim_cbo", "direct_treasury_interest_support")
    ]
    assert direct["central_N_treatment"] == (
        "replacement_block_input_not_standalone"
    )
    assert direct["object_role"] == "selected_block_input"
    assert direct["representative_numerator_value_bil"] == "10"

    residual = by_key[("forecast_sensitivity_tdcsim_cbo", "firm_cash_attenuation")]
    assert residual["central_N_treatment"] == "not_in_central_N"
    assert residual["object_role"] == "sensitivity_only"
    assert residual["sensitivity_treatment"] == "admitted_as_bounded_sensitivity"
    assert residual["replacement_group"] == "firm_liquidity"

    historical = by_key[
        ("historical_path_context", "tdc_ex_overlap_current_demand_support")
    ]
    assert historical["historical_ratio_not_classifier"] == "true"
    assert historical["object_role"] == "diagnostic_context"
    assert historical["representative_numerator_value_bil"] == "100"
    assert "forecast_assumption_backfill" not in historical["source_status"]

    historical_gap = by_key[
        ("historical_path_context", "bank_treasury_interest_support")
    ]
    assert historical_gap["source_status"] == "not_source_backed_in_current_adapter"
    assert historical_gap["object_role"] == "diagnostic_context"
    assert historical_gap["representative_numerator_value_bil"] == ""


def test_comparable_denominator_surface_separates_d_variants(tmp_path: Path) -> None:
    dirs = _write_fixture(tmp_path)

    rows = comparable_denominator_surface_rows(
        methodology_parity_dir=dirs["methodology_parity_dir"],
        denominator_parity_dir=dirs["denominator_parity_dir"],
        historical_adapter_dir=dirs["historical_adapter_dir"],
    )

    assert {field for row in rows for field in row} == set(
        COMPARABLE_DENOMINATOR_SURFACE_FIELDS
    )
    by_key = {(row["surface_id"], row["denominator_variant"]): row for row in rows}
    assert by_key[("current_assumption_runtime", "fixed_runtime_D")][
        "selected_variant"
    ] == "true"
    assert by_key[("current_assumption_runtime", "fixed_runtime_D")][
        "object_role"
    ] == "denominator_only"
    assert by_key[("forecast_central_tdcsim_cbo", "path_D")][
        "selected_variant"
    ] == "true"
    assert by_key[("forecast_central_tdcsim_cbo", "fixed_D")][
        "selected_variant"
    ] == "false"
    assert by_key[("historical_path_context", "historical_path_D")][
        "historical_ratio_not_classifier"
    ] == "true"
    assert by_key[("historical_path_context", "moving_D_not_applicable")][
        "source_status"
    ] == "not_applicable_historical_rate_path_is_not_forecast_scenario"


def test_comparable_summary_readout_and_outputs(tmp_path: Path) -> None:
    dirs = _write_fixture(tmp_path)
    channel_rows = _channel_rows(dirs)
    denominator_rows = comparable_denominator_surface_rows(
        methodology_parity_dir=dirs["methodology_parity_dir"],
        denominator_parity_dir=dirs["denominator_parity_dir"],
        historical_adapter_dir=dirs["historical_adapter_dir"],
    )
    summary_rows = comparable_review_summary_rows(channel_rows, denominator_rows)
    status_rows = _model_status_rows(dirs)
    gap_rows = _gap_priority_rows(dirs)
    readout = comparable_model_readout_markdown(
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
        summary_rows=summary_rows,
        model_status_rows=status_rows,
        gap_priority_rows=gap_rows,
    )

    assert {field for row in summary_rows for field in row} == set(
        COMPARABLE_REVIEW_SUMMARY_FIELDS
    )
    assert {field for row in status_rows for field in row} == set(
        COMPARABLE_MODEL_STATUS_FIELDS
    )
    assert {field for row in gap_rows for field in row} == set(
        COMPARABLE_GAP_PRIORITY_FIELDS
    )
    assert "does not change RateWall N, D, beta, chi" in readout
    assert "## Current Model Status" in readout
    assert "## Next Model Gaps" in readout
    assert "historical_ratio_not_classifier=true" in readout
    outputs = write_comparable_model_surface_outputs(
        tmp_path / "out",
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
        summary_rows=summary_rows,
        model_status_rows=status_rows,
        gap_priority_rows=gap_rows,
        readout_markdown=readout,
    )
    assert outputs["channel_csv"].read_text(encoding="utf-8").startswith(
        "comparable_channel_surface_row_id,"
    )
    assert outputs["denominator_csv"].read_text(encoding="utf-8").startswith(
        "comparable_denominator_surface_row_id,"
    )
    assert outputs["summary_csv"].read_text(encoding="utf-8").startswith(
        "comparable_review_summary_row_id,"
    )
    assert outputs["model_status_csv"].read_text(encoding="utf-8").startswith(
        "comparable_model_status_row_id,"
    )
    assert outputs["gap_priority_csv"].read_text(encoding="utf-8").startswith(
        "comparable_gap_priority_row_id,"
    )
    assert outputs["readout_md"].read_text(encoding="utf-8") == readout


def test_comparable_model_status_and_gap_priority_use_r26_r30_artifacts(
    tmp_path: Path,
) -> None:
    dirs = _write_fixture(tmp_path)

    status_rows = _model_status_rows(dirs)
    gap_rows = _gap_priority_rows(dirs)

    by_surface = {row["surface_id"]: row for row in status_rows}
    forecast = by_surface["forecast_central_tdcsim_cbo"]
    assert forecast["object_role"] == "selected_n"
    assert forecast["selected_or_provisional_n_bil"] == "21"
    assert forecast["selected_or_provisional_d_bil"] == "120"
    assert forecast["main_blocker"] == (
        "model_readout_not_canonical_headline_or_evidence_mode"
    )
    historical = by_surface["historical_path_context"]
    assert historical["object_role"] == "diagnostic_context"
    assert historical["representative_period"] == "2024Q1"
    assert historical["final_classifier_allowed"] == "false"
    assert "numerator_dollars" in historical["main_blocker"]

    by_gap = {row["gap_id"]: row for row in gap_rows}
    assert by_gap["realized_deposit_mmf_tbill_income_gap"][
        "priority_rank"
    ] == "1"
    assert by_gap["D2_current_object_bridge_freeze_now"][
        "priority_rank"
    ] == "2"
    assert by_gap["D2_current_object_bridge_freeze_now"]["object_role"] == (
        "selected_benchmark_recast"
    )
    assert by_gap["realized_deposit_mmf_tbill_income_gap"]["object_role"] == (
        "blocked_source_or_method"
    )
    assert by_gap["R37_historical_context_nonclassifier_closure"][
        "feasibility_status"
    ] == "R37_resolved_nonclassifier_policy_decision"
    assert by_gap["forecast_remittance_scenario_delta_model"][
        "priority_bucket"
    ] == "lower_priority_context_already_sourced"
    assert by_gap["realized_deposit_mmf_tbill_income_gap"][
        "do_not_do"
    ] == "do_not_use_raw_stock_times_shortcut_or_tdc_substitute"
    assert "blocked_missing_fdic_ffiec_or_ncua_payer_flow" in by_gap[
        "realized_deposit_mmf_tbill_income_gap"
    ]["current_source_status"]


def _write_fixture(tmp_path: Path) -> dict[str, Path]:
    methodology = tmp_path / "methodology"
    core = tmp_path / "core"
    denominator = tmp_path / "denominator"
    residual = tmp_path / "residual"
    historical = tmp_path / "historical"
    source_method = tmp_path / "source_method"
    forecast = tmp_path / "forecast"
    hardening = tmp_path / "hardening"
    current = tmp_path / "current"
    safe_yield = tmp_path / "safe_yield"
    historical_provisional = tmp_path / "historical_provisional"
    for path in [
        methodology,
        core,
        denominator,
        residual,
        historical,
        source_method,
        forecast,
        hardening,
        current,
        safe_yield,
        historical_provisional,
    ]:
        path.mkdir()

    _write_csv(
        methodology / "ratewall_methodology_parity_channels.csv",
        [
            _method_channel(
                "current_assumption_runtime",
                "current_or_static",
                "tdc_ex_overlap_current_demand_support",
                "TDC",
                "sidecar",
                "sidecar",
            ),
            _method_channel(
                "forecast_central_tdcsim_cbo",
                "forecast",
                "tdc_ex_overlap_current_demand_support",
                "TDC",
                "standalone_final_n_term",
                "central",
            ),
            _method_channel(
                "forecast_central_tdcsim_cbo",
                "forecast",
                "direct_treasury_interest_support",
                "Direct interest",
                "replacement_block_input_not_standalone",
                "central_block_input",
            ),
            _method_channel(
                "forecast_sensitivity_tdcsim_cbo",
                "forecast",
                "firm_cash_attenuation",
                "Firm cash",
                "sensitivity",
                "sensitivity",
            ),
            _method_channel(
                "historical_path_context",
                "historical",
                "tdc_ex_overlap_current_demand_support",
                "TDC",
                "historical_context_not_classifier",
                "context",
            ),
            _method_channel(
                "historical_path_context",
                "historical",
                "bank_treasury_interest_support",
                "Bank interest",
                "not_ready",
                "not_ready",
            ),
        ],
    )
    _write_csv(
        methodology / "ratewall_methodology_parity_denominators.csv",
        [
            _method_denominator(
                "current_assumption_runtime",
                "primary_runtime_default",
                "0.77600",
                "none_fixed_runtime_object",
            ),
            _method_denominator(
                "forecast_central_tdcsim_cbo",
                "primary_forecast_path_denominator",
                "0.77600",
                "selected_frbus_structural_term_premium_c_D_1.1198692004749646",
            ),
        ],
    )
    _write_csv(
        core / "ratewall_tdc_ex_overlap_support_shared.csv",
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "cbo_baseline_noop_v1",
                "baseline_scenario_id": "cbo_baseline_noop_v1",
                "tdc_current_demand_support_bil": "2.5",
            }
        ],
    )
    _write_csv(
        core / "ratewall_public_interest_net_block_shared.csv",
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "cbo_baseline_noop_v1",
                "baseline_scenario_id": "cbo_baseline_noop_v1",
                "direct_treasury_current_demand_support_bil": "10",
                "bank_treasury_current_demand_support_bil": "1",
                "net_interest_after_fiscal_tga_offsets_bil": "7",
                "projected_current_remittance_demand_offset_bil": "0",
                "projected_future_remittance_drag_demand_offset_bil": "0",
                "projected_iorb_current_demand_support_bil": "2",
                "projected_on_rrp_current_demand_support_bil": "0",
                "fiscal_offset_bil": "1",
                "tga_liquidity_offset_bil": "1",
                "interest_income_tax_timing_drag_bil": "2",
            }
        ],
    )
    _write_csv(
        denominator / "ratewall_denominator_variant_surface.csv",
        [
            _variant("fixed_D", "100", "false", "comparison_only_fixed_reference"),
            _variant("path_D", "110", "true", "cbo_gdp_scaled_path_reference"),
            _variant("moving_D", "110", "false", "rate_response_variant"),
        ],
    )
    _write_csv(
        residual / "ratewall_residual_channel_admission_matrix.csv",
        [
            {
                "channel_id": "firm_cash_attenuation",
                "central_N_treatment": "not_in_central_N",
                "sensitivity_treatment": "admitted_as_bounded_sensitivity",
                "replacement_group": "firm_liquidity",
                "source_or_calibration_status": "source_backed_context",
            }
        ],
    )
    _write_csv(
        historical / "ratewall_historical_channel_adapter_status.csv",
        [
            {
                "channel_id": "tdc_ex_overlap_current_demand_support",
                "historical_source_row_count": "1",
                "source_status": "source_backed_noncanonical_historical_column::tdc",
            },
            {
                "channel_id": "bank_treasury_interest_support",
                "historical_source_row_count": "0",
                "source_status": "not_source_backed_in_current_adapter",
            },
        ],
    )
    _write_csv(
        historical / "ratewall_historical_comparable_surface.csv",
        [
            {
                "period": "2024Q1",
                "channel_id": "tdc_ex_overlap_current_demand_support",
                "historical_numerator_value_bil": "100",
            }
        ],
    )
    _write_csv(
        historical / "ratewall_historical_denominator_variant_bridge.csv",
        [
            _historical_variant(
                "fixed_D_comparison",
                "false",
                "comparison_only",
                "source_backed_fixed_anchor_component_not_bil_D",
            ),
            _historical_variant(
                "historical_path_D",
                "true",
                "historical_context_primary",
                "source_backed_historical_denominator_contract_no_bil_export",
            ),
            _historical_variant(
                "moving_D_not_applicable",
                "false",
                "not_applicable_to_historical_context",
                "not_applicable_historical_rate_path_is_not_forecast_scenario",
            ),
        ],
    )
    _write_r31_fixture_artifacts(
        source_method=source_method,
        forecast=forecast,
        hardening=hardening,
        current=current,
        safe_yield=safe_yield,
        historical_provisional=historical_provisional,
    )
    return {
        "methodology_parity_dir": methodology,
        "core_support_dir": core,
        "denominator_parity_dir": denominator,
        "residual_closure_dir": residual,
        "historical_adapter_dir": historical,
        "source_method_dir": source_method,
        "forecast_readout_dir": forecast,
        "forecast_hardening_dir": hardening,
        "current_overlay_dir": current,
        "realized_safe_yield_dir": safe_yield,
        "historical_provisional_dir": historical_provisional,
    }


def _channel_rows(dirs: dict[str, Path]) -> list[dict[str, str]]:
    return comparable_channel_surface_rows(
        methodology_parity_dir=dirs["methodology_parity_dir"],
        core_support_dir=dirs["core_support_dir"],
        residual_closure_dir=dirs["residual_closure_dir"],
        historical_adapter_dir=dirs["historical_adapter_dir"],
    )


def _model_status_rows(dirs: dict[str, Path]) -> list[dict[str, str]]:
    return comparable_model_status_rows(
        source_method_dir=dirs["source_method_dir"],
        forecast_readout_dir=dirs["forecast_readout_dir"],
        forecast_hardening_dir=dirs["forecast_hardening_dir"],
        current_overlay_dir=dirs["current_overlay_dir"],
        historical_provisional_dir=dirs["historical_provisional_dir"],
    )


def _gap_priority_rows(dirs: dict[str, Path]) -> list[dict[str, str]]:
    return comparable_gap_priority_rows(
        source_method_dir=dirs["source_method_dir"],
        current_overlay_dir=dirs["current_overlay_dir"],
        realized_safe_yield_dir=dirs["realized_safe_yield_dir"],
        historical_provisional_dir=dirs["historical_provisional_dir"],
    )


def _write_r31_fixture_artifacts(
    *,
    source_method: Path,
    forecast: Path,
    hardening: Path,
    current: Path,
    safe_yield: Path,
    historical_provisional: Path,
) -> None:
    _write_csv(
        source_method / "ratewall_source_method_matrix.csv",
        [
            _source_method("forecast_tdc_support", "forecast_central_tdcsim_cbo"),
            _source_method(
                "forecast_public_interest_net_block",
                "forecast_central_tdcsim_cbo",
            ),
            _source_method(
                "current_public_interest_runtime",
                "current_assumption_runtime",
            ),
            _source_method("current_denominator", "current_assumption_runtime"),
            _source_method(
                "historical_public_interest_net_block",
                "historical_path_context",
                local_status="source_to_acquire",
                gap="bank_fed_liability_remittance_tax_fiscal_tga_subchannels_incomplete",
            ),
            _source_method(
                "historical_denominator",
                "historical_path_context",
                local_status="present_local",
                gap="rate_path_convention_needs_review",
            ),
            _source_method(
                "forecast_remittance_baseline_path",
                "forecast_central_tdcsim_cbo",
                local_status="present_local",
                gap="scenario_remittance_delta_model_not_admitted",
            ),
        ],
    )
    _write_csv(
        forecast / "ratewall_forecast_central_scenario_surface.csv",
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "cbo_baseline_noop_v1",
                "baseline_scenario_id": "cbo_baseline_noop_v1",
                "central_n_bil": "21",
                "central_moving_denominator_bil": "120",
                "central_ratewall_ratio": "0.175",
            }
        ],
    )
    _write_csv(
        hardening / "ratewall_forecast_central_assumption_ledger.csv",
        [
            {
                "assumption_id": "forecast_selected_n_rule",
                "assumption_value": "public_interest_net_block + forecast_tdc_support",
            },
            {
                "assumption_id": "forecast_selected_D_rule",
                "assumption_value": "moving_D_for_rate_scenarios_else_path_D",
            },
        ],
    )
    _write_csv(
        current / "ratewall_current_assumption_benchmark.csv",
        [
            {
                "forecast_year": "2026",
                "benchmark_id": "current_assumption_benchmark",
                "benchmark_numerator_bil": "83",
                "fixed_D_bil": "247",
                "benchmark_ratewall_ratio": "0.336",
                "selected_current_row": "true",
            }
        ],
    )
    _write_csv(
        current / "ratewall_current_observed_overlay_candidate.csv",
        [
            {
                "candidate_status": "blocked_requires_source_led_current_overlay_gate",
                "benchmark_replacement_allowed": "false",
            }
        ],
    )
    _write_csv(
        current / "ratewall_current_observed_overlay_admission.csv",
        [
            {
                "replacement_gate_status": (
                    "blocked_candidate_changes_current_N_requires_R40_current_object_decision"
                ),
                "candidate_minus_benchmark_n_bil": "-8",
            }
        ],
    )
    _write_csv(
        safe_yield / "ratewall_realized_safe_yield_income_gap.csv",
        [
            {
                "source_channel_id": "realized_deposit_mmf_tbill_income_gap",
                "build_status": "R39_candidate_built_sources_missing_for_admission",
                "required_to_unpark": "payer_flow;recipient_allocation",
                "central_n_delta_bil_allowed": "false",
            }
        ],
    )
    _write_csv(
        safe_yield / "ratewall_realized_safe_yield_payer_flow_admission.csv",
        [
            {
                "blocked_reason": (
                    "blocked_missing_fdic_ffiec_or_ncua_payer_flow;"
                    "blocked_no_final_recipient_allocation"
                )
            }
        ],
    )
    _write_csv(
        historical_provisional / "ratewall_historical_provisional_rw_panel.csv",
        [
            {
                "period": "2024Q1",
                "quarter": "2024Q1",
                "assumption_case": "base",
                "provisional_n_bil": "15",
                "historical_path_D_bil": "97",
                "fixed_D_comparison_bil": "194",
                "provisional_historical_ratewall_ratio": "0.154639",
                "final_classifier_allowed": "false",
            }
        ],
    )
    _write_csv(
        historical_provisional / "ratewall_historical_provisional_classifier_gate.csv",
        [
            {"check_id": "numerator_dollars", "gate_status": "blocked_partial"},
            {"check_id": "denominator_dollars", "gate_status": "pass"},
            {"check_id": "overlap", "gate_status": "blocked_unproven"},
            {"check_id": "remittance_on_rrp", "gate_status": "blocked_unproven"},
        ],
    )


def _source_method(
    block_id: str,
    surface_id: str,
    *,
    local_status: str = "present_local",
    gap: str = "fixture_gap",
) -> dict[str, str]:
    return {
        "block_id": block_id,
        "surface_id": surface_id,
        "local_source_status": local_status,
        "central_n_delta_bil_allowed": "false",
        "known_gap": gap,
    }


def _method_channel(
    surface_id: str,
    family: str,
    channel_id: str,
    label: str,
    role: str,
    centrality: str,
) -> dict[str, str]:
    return {
        "surface_id": surface_id,
        "surface_family": family,
        "channel_id": channel_id,
        "channel_label": label,
        "surface_entry_role": role,
        "centrality": centrality,
        "denominator_treatment": "selected_or_context_D",
        "parity_status": "fixture_status",
    }


def _method_denominator(
    surface_id: str, role: str, anchor: str, rate_response: str
) -> dict[str, str]:
    return {
        "surface_id": surface_id,
        "denominator_role": role,
        "fixed_anchor_component": anchor,
        "moving_rate_response": rate_response,
    }


def _variant(
    variant: str, value: str, selected: str, role: str
) -> dict[str, str]:
    return {
        "fiscal_year": "2036",
        "scenario_id": "cbo_baseline_noop_v1",
        "denominator_variant": variant,
        "denominator_value_bil": value,
        "selected_variant": selected,
        "variant_role": role,
    }


def _historical_variant(
    variant: str, selected: str, role: str, source_status: str
) -> dict[str, str]:
    return {
        "denominator_variant": variant,
        "selected_variant": selected,
        "variant_role": role,
        "fixed_anchor_component_pp_gdp": "0.77600",
        "historical_path_D_bil": "",
        "fixed_D_comparison_bil": "",
        "moving_D_bil": "",
        "historical_ratio_not_classifier": "true",
        "source_status": source_status,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

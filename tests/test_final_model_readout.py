from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.final_model_readout import (
    FINAL_FORECAST_BETA_SHOCK_TIME_SERIES_FIELDS,
    FINAL_FORECAST_SCENARIO_TIME_SERIES_FIELDS,
    FINAL_FORECAST_TDC_TIME_SERIES_FIELDS,
    FINAL_MODEL_READOUT_LEDGER_FIELDS,
    FINAL_MODEL_RATIO_SNAPSHOT_FIELDS,
    FINAL_MODEL_RATIO_TIME_SERIES_FIELDS,
    final_forecast_beta_shock_time_series_rows,
    final_forecast_scenario_time_series_rows,
    final_forecast_tdc_time_series_rows,
    final_model_readiness_ledger_rows,
    final_model_ratio_snapshot_rows,
    final_model_ratio_time_series_rows,
    final_model_readout_markdown,
    write_final_model_readout_outputs,
)


def test_final_model_readout_contains_required_sections_and_anti_claims(
    tmp_path: Path,
) -> None:
    root = _write_fixture(tmp_path)

    readout = final_model_readout_markdown(preliminary_dir=root)
    ledger = final_model_readiness_ledger_rows(preliminary_dir=root)
    ratio_rows = final_model_ratio_snapshot_rows(preliminary_dir=root)
    time_series_rows = final_model_ratio_time_series_rows(preliminary_dir=root)
    forecast_rows = final_forecast_scenario_time_series_rows(preliminary_dir=root)
    beta_shock_rows = final_forecast_beta_shock_time_series_rows(preliminary_dir=root)
    tdc_rows = final_forecast_tdc_time_series_rows(preliminary_dir=root, extreme_count=1)

    for heading in [
        "## Object Definition And Claim Mode",
        "## Selected Forecast Estimate",
        "## Selected Current Benchmark",
        "## Historical Context And Coverage",
        "## Diagnostics And Sensitivities",
        "## Source-Blocked Theoretical Channels",
        "## Denominator-Only Routes",
        "## Completion/Readiness Ledger",
    ]:
        assert heading in readout
    for required_text in [
        "not a fully source-identified causal/evidence-mode estimate",
        "No selected central safe-yield unless all D1 gates pass",
        "BEA/IRS do not substitute for payer-flow panels",
        "`Y001RC1Q027SBEA` is not personal-interest context",
        "MMF/T-bill diagnostics are not additive central `N` on top of public-interest",
        "R38 did not replace the selected current benchmark",
        "D1 fallback did not alter the current benchmark",
        "Historical rows are context and validation, not final wall-hit classifiers",
        "Direct Treasury interest, IORB, ON RRP, and bank Treasury split are inputs inside the public-interest block",
        "Denominator drag is never booked as a numerator offset",
        "Raw stock times MPC is not an accepted central route",
        "Bounded deposit fallback is not release/report-grade central evidence",
        "No major theoretical channel remains unclassified",
    ]:
        assert required_text in readout
    by_gate = {row["roadmap_gate_id"]: row for row in ledger}
    assert by_gate["D1"]["gate_status"] == "pass_source_gate_fail_closed_central"
    assert all(row["selected_value_change"] == "false" for row in ledger)
    assert [row["ratio_row_id"] for row in ratio_rows] == [
        "past_historical_context",
        "current_selected_benchmark",
        "forecast_selected_2036",
    ]
    assert ratio_rows[0]["selection_status"] == "historical_context_not_classifier"
    assert {row["series_id"] for row in time_series_rows} == {
        "historical_context_base",
        "current_selected_benchmark",
        "forecast_selected_baseline",
    }
    assert {
        row["series_role"]
        for row in time_series_rows
        if row["series_id"] == "historical_context_base"
    } == {"historical_root_public_interest_context"}
    assert len({row["scenario_id"] for row in forecast_rows}) <= 8
    assert forecast_rows[0]["scenario_id"] == "cbo_baseline_noop_v1"
    assert {row["shock_id"] for row in beta_shock_rows} == {
        "baseline_beta_0_342",
        "peak_beta_0_500",
        "peak_beta_0_700",
    }
    peak_row = next(
        row
        for row in beta_shock_rows
        if row["shock_id"] == "peak_beta_0_700" and row["fiscal_year"] == "2031"
    )
    assert peak_row["tdc_beta"] == "0.7"
    assert float(peak_row["delta_ratewall_ratio_vs_baseline"]) < 0
    assert {row["scenario_id"] for row in tdc_rows} == {
        "cbo_baseline_noop_v1",
        "tdcsim_rate_down_25bp_v1",
        "tdcsim_private_holder_low_v1",
    }


def test_final_model_readout_outputs_write_markdown_and_ledger(tmp_path: Path) -> None:
    root = _write_fixture(tmp_path)

    outputs = write_final_model_readout_outputs(tmp_path / "out", preliminary_dir=root)

    assert outputs["readout_md"].read_text(encoding="utf-8").startswith(
        "# RateWall Final Economist-Facing Readout"
    )
    with outputs["readiness_ledger_csv"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {field for row in rows for field in row} == set(
        FINAL_MODEL_READOUT_LEDGER_FIELDS
    )
    assert len(rows) == 6
    with outputs["ratio_snapshot_csv"].open(newline="", encoding="utf-8") as handle:
        ratio_rows = list(csv.DictReader(handle))
    assert {field for row in ratio_rows for field in row} == set(
        FINAL_MODEL_RATIO_SNAPSHOT_FIELDS
    )
    assert outputs["ratio_snapshot_png"].read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with outputs["ratio_time_series_csv"].open(newline="", encoding="utf-8") as handle:
        time_series_rows = list(csv.DictReader(handle))
    assert {field for row in time_series_rows for field in row} == set(
        FINAL_MODEL_RATIO_TIME_SERIES_FIELDS
    )
    assert outputs["ratio_time_series_png"].read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with outputs["forecast_scenario_time_series_csv"].open(
        newline="", encoding="utf-8"
    ) as handle:
        forecast_rows = list(csv.DictReader(handle))
    assert {field for row in forecast_rows for field in row} == set(
        FINAL_FORECAST_SCENARIO_TIME_SERIES_FIELDS
    )
    assert len({row["scenario_id"] for row in forecast_rows}) <= 8
    assert outputs["forecast_scenario_time_series_png"].read_bytes().startswith(
        b"\x89PNG\r\n\x1a\n"
    )
    with outputs["forecast_beta_shock_time_series_csv"].open(
        newline="", encoding="utf-8"
    ) as handle:
        beta_shock_rows = list(csv.DictReader(handle))
    assert {field for row in beta_shock_rows for field in row} == set(
        FINAL_FORECAST_BETA_SHOCK_TIME_SERIES_FIELDS
    )
    assert outputs["forecast_beta_shock_time_series_png"].read_bytes().startswith(
        b"\x89PNG\r\n\x1a\n"
    )
    with outputs["forecast_tdc_time_series_csv"].open(
        newline="", encoding="utf-8"
    ) as handle:
        tdc_rows = list(csv.DictReader(handle))
    assert {field for row in tdc_rows for field in row} == set(
        FINAL_FORECAST_TDC_TIME_SERIES_FIELDS
    )
    assert outputs["forecast_tdc_time_series_png"].read_bytes().startswith(
        b"\x89PNG\r\n\x1a\n"
    )


def _write_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "prelim"
    _write_csv(
        root / "comparable_model_surface/ratewall_comparable_model_status.csv",
        [
            "surface_id",
            "representative_period",
            "representative_case",
            "selected_or_provisional_n_bil",
            "selected_or_provisional_d_bil",
            "selected_or_provisional_ratewall_ratio",
            "numerator_method_plain",
            "denominator_method_plain",
            "main_blocker",
            "object_role",
            "claim_boundary",
        ],
        [
            [
                "forecast_central_tdcsim_cbo",
                "2036",
                "cbo_baseline_noop_v1",
                "43.2",
                "176.9",
                "0.244",
                "public_interest_net_block + forecast_tdc_support",
                "moving_D_for_rate_scenarios_else_path_D",
                "model_readout_not_canonical_headline_or_evidence_mode",
                "selected_n",
                "comparable_status_no_model_value_change",
            ],
            [
                "current_assumption_runtime",
                "2026",
                "current_assumption_benchmark",
                "83.5",
                "247.5",
                "0.337",
                "existing assumption runtime recast unchanged",
                "fixed current D benchmark",
                "observed_overlay_not_admitted;benchmark_replacement_disallowed",
                "selected_benchmark_recast",
                "comparable_status_no_model_value_change",
            ],
            [
                "historical_path_context",
                "2026Q2",
                "base",
                "38.2",
                "844.2",
                "0.045",
                "partial source-backed historical components only",
                "CBO quarterly GDP times fed funds path D",
                "R37_historical_context_accepted_nonclassifier",
                "diagnostic_context",
                "comparable_status_no_model_value_change",
            ],
        ],
    )
    _write_csv(
        root / "current_object_bridge/ratewall_current_object_freeze_decision.csv",
        [
            "selected_current_object_id",
            "selected_n_bil",
            "selected_d_bil",
            "selected_rw",
            "selection_status",
            "replacement_gate_status",
        ],
        [
            [
                "current_assumption_benchmark::2026",
                "83.5",
                "247.5",
                "0.337",
                "freeze_selected_runtime_benchmark",
                "closed_no_named_replacement_surface",
            ]
        ],
    )
    _write_csv(
        root / "current_object_bridge/ratewall_current_object_bridge.csv",
        [
            "current_object_bridge_row_id",
            "rw",
            "claim_boundary",
        ],
        [
            [
                "current_object_bridge::selected_runtime_benchmark",
                "0.337",
                "current_selected_values_frozen",
            ]
        ],
    )
    _write_csv(
        root / "historical_coverage_contract/ratewall_historical_coverage_contract.csv",
        [
            "route_id",
            "coverage_window_start",
            "coverage_window_end",
            "final_classifier_status",
            "classifier_allowed",
            "historical_n_formula",
            "nonadditive_decomposition_terms",
        ],
        [
            [
                "implemented_short_panel",
                "2021Q4",
                "2026Q2",
                "closed_nonclassifier",
                "false",
                "tdc_ex_overlap_support_bil + public_interest_net_block_partial_bil",
                "direct_treasury_interest_bil_inside_public_interest_context",
            ]
        ],
    )
    _write_csv(
        root / "historical_coverage_contract/ratewall_historical_extension_feasibility.csv",
        [
            "route_id",
            "target_window_start",
            "target_window_end",
            "feasibility_status",
        ],
        [
            [
                "implemented_short_panel",
                "2021Q4",
                "2026Q2",
                "pass_context_available_not_classifier",
            ]
        ],
    )
    _write_csv(
        root
        / "historical_provisional_estimate/ratewall_historical_provisional_rw_panel.csv",
        [
            "period",
            "assumption_case",
            "provisional_historical_ratewall_ratio",
            "claim_boundary",
        ],
        [
            ["2025Q4", "base", "0.050", "historical_provisional_ratio_nonfinal"],
            ["2026Q1", "base", "0.047", "historical_provisional_ratio_nonfinal"],
            ["2026Q2", "base", "0.045", "historical_provisional_ratio_nonfinal"],
        ],
    )
    _write_csv(
        root
        / "historical_provisional_estimate/ratewall_historical_root_public_interest_rw_panel.csv",
        [
            "period",
            "assumption_case",
            "root_public_interest_ratewall_ratio",
            "claim_boundary",
        ],
        [
            ["2003Q1", "base", "0.021", "historical_root_public_interest_context_not_classifier"],
            ["2021Q4", "base", "0.002690", "historical_root_public_interest_context_not_classifier"],
            ["2022Q1", "base", "0.059011", "historical_root_public_interest_context_not_classifier"],
        ],
    )
    _write_csv(
        root / "forecast_10y/ratewall_forecast_central_scenario_surface.csv",
        [
            "fiscal_year",
            "scenario_id",
            "central_n_bil",
            "central_moving_denominator_bil",
            "central_ratewall_ratio",
            "delta_central_ratewall_ratio_vs_baseline",
            "wall_hit_under_central_forecast",
            "sensitivity_rule",
        ],
        [
            ["2027", "cbo_baseline_noop_v1", "15", "100", "0.15", "0", "false", "sensitivity"],
            ["2028", "cbo_baseline_noop_v1", "16", "100", "0.16", "0", "false", "sensitivity"],
            ["2029", "cbo_baseline_noop_v1", "17", "100", "0.17", "0", "false", "sensitivity"],
            ["2030", "cbo_baseline_noop_v1", "18", "100", "0.18", "0", "false", "sensitivity"],
            ["2031", "cbo_baseline_noop_v1", "19", "100", "0.19", "0", "false", "sensitivity"],
            ["2032", "cbo_baseline_noop_v1", "20", "100", "0.20", "0", "false", "sensitivity"],
            ["2033", "cbo_baseline_noop_v1", "21", "100", "0.21", "0", "false", "sensitivity"],
            ["2034", "cbo_baseline_noop_v1", "22", "100", "0.22", "0", "false", "sensitivity"],
            ["2035", "cbo_baseline_noop_v1", "23", "100", "0.23", "0", "false", "sensitivity"],
            ["2036", "cbo_baseline_noop_v1", "24", "100", "0.24", "0", "false", "sensitivity"],
            ["2027", "tdcsim_rate_down_25bp_v1", "19", "100", "0.19", "0.04", "false", "sensitivity"],
            ["2028", "tdcsim_rate_down_25bp_v1", "22", "100", "0.22", "0.06", "false", "sensitivity"],
            ["2029", "tdcsim_rate_down_25bp_v1", "20", "100", "0.20", "0.03", "false", "sensitivity"],
            ["2030", "tdcsim_rate_down_25bp_v1", "20", "100", "0.20", "0.02", "false", "sensitivity"],
            ["2031", "tdcsim_rate_down_25bp_v1", "20", "100", "0.20", "0.01", "false", "sensitivity"],
            ["2032", "tdcsim_rate_down_25bp_v1", "20", "100", "0.20", "0", "false", "sensitivity"],
            ["2033", "tdcsim_rate_down_25bp_v1", "20", "100", "0.20", "-0.01", "false", "sensitivity"],
            ["2034", "tdcsim_rate_down_25bp_v1", "20", "100", "0.20", "-0.02", "false", "sensitivity"],
            ["2035", "tdcsim_rate_down_25bp_v1", "20", "100", "0.20", "-0.03", "false", "sensitivity"],
            ["2036", "tdcsim_rate_down_25bp_v1", "20", "100", "0.20", "-0.04", "false", "sensitivity"],
            ["2027", "tdcsim_private_holder_low_v1", "12", "100", "0.12", "-0.03", "false", "sensitivity"],
            ["2028", "tdcsim_private_holder_low_v1", "11", "100", "0.11", "-0.05", "false", "sensitivity"],
            ["2029", "tdcsim_private_holder_low_v1", "30", "100", "0.30", "0.13", "false", "sensitivity"],
            ["2030", "tdcsim_private_holder_low_v1", "30", "100", "0.30", "0.12", "false", "sensitivity"],
            ["2031", "tdcsim_private_holder_low_v1", "30", "100", "0.30", "0.11", "false", "sensitivity"],
            ["2032", "tdcsim_private_holder_low_v1", "30", "100", "0.30", "0.10", "false", "sensitivity"],
            ["2033", "tdcsim_private_holder_low_v1", "30", "100", "0.30", "0.09", "false", "sensitivity"],
            ["2034", "tdcsim_private_holder_low_v1", "30", "100", "0.30", "0.08", "false", "sensitivity"],
            ["2035", "tdcsim_private_holder_low_v1", "30", "100", "0.30", "0.07", "false", "sensitivity"],
            ["2036", "tdcsim_private_holder_low_v1", "30", "100", "0.30", "0.06", "false", "sensitivity"],
        ],
    )
    _write_csv(
        root / "forecast_10y/ratewall_forecast_public_interest_net_block.csv",
        [
            "fiscal_year",
            "scenario_id",
            "net_interest_after_fiscal_tga_offsets_bil",
        ],
        (
            [[str(year), "cbo_baseline_noop_v1", "35"] for year in range(2027, 2037)]
            + [[str(year), "tdcsim_rate_down_25bp_v1", "25"] for year in range(2027, 2037)]
            + [[str(year), "tdcsim_private_holder_low_v1", "10"] for year in range(2027, 2037)]
        ),
    )
    _write_csv(
        root / "realized_safe_yield_income/ratewall_safe_yield_sublane_status.csv",
        [
            "source_gate_status",
            "accepted_current_rows",
            "eligible_current_rows",
            "gross_realized_income_bil",
        ],
        [["pass_source_panels_shape_coverage_and_flow", "10", "10", "20"]],
    )
    _write_csv(
        root
        / "realized_safe_yield_income/ratewall_realized_safe_yield_payer_flow_admission.csv",
        [
            "central_n_delta_bil_allowed",
            "central_n_delta_bil",
            "blocked_reason",
        ],
        [
            [
                "false",
                "0",
                "blocked_no_final_recipient_allocation;blocked_public_interest_tdc_and_firm_cash_overlap_unproven",
            ]
        ],
    )
    _write_csv(
        root / "demand_translation_ledger/ratewall_object_role_matrix.csv",
        [
            "source_channel_id",
            "channel_label",
            "object_role",
            "promotion_requirements_remaining",
            "same_period_denominator_status",
        ],
        [
            ["public_interest_net_block", "Public interest", "selected_n", "none", "pass_forecast_selected_D"],
            ["tdc_ex_overlap_beta_chi", "TDC", "selected_n", "none", "pass_forecast_selected_D"],
            ["deposit_safe_yield", "Deposit safe-yield", "blocked_source_or_method", "recipient and overlap gates", "blocked_current_D"],
            ["moving_d", "Moving D", "denominator_only", "none", "pass_forecast_selected_D"],
            ["fallback", "Fallback", "sensitivity_only", "none", "not_applicable"],
        ],
    )
    return root


def _write_csv(path: Path, fields: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)

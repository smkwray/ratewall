from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ratewall.databook.forecast_model_readout import (
    CENTRAL_FORECAST_SURFACE_FIELDS,
    CENTRAL_SCENARIO_INTERPRETATION_FIELDS,
    FORECAST_CHANNEL_CLASSIFICATION_FIELDS,
    FORECAST_COMPOSITION_SURFACE_FIELDS,
    FORECAST_NUMERATOR_CHANNEL_PLAN_FIELDS,
    FORECAST_SCENARIO_SUFFICIENCY_FIELDS,
    PUBLIC_INTEREST_NET_BLOCK_FIELDS,
    RESIDUAL_NUMERATOR_SENSITIVITY_FIELDS,
    RESIDUAL_SENSITIVITY_SOURCE_FIELDS,
    TIMED_BETA_PATH_FIELDS,
    ZERO_LOW_APR_CREDIT_MATERIALITY_FIELDS,
    central_forecast_surface_rows,
    central_scenario_interpretation_rows,
    forecast_channel_classification_rows,
    forecast_composition_surface_rows,
    forecast_model_readout_markdown,
    forecast_numerator_channel_plan_rows,
    forecast_public_interest_net_block_rows,
    forecast_residual_numerator_sensitivity_rows,
    forecast_scenario_sufficiency_rows,
    PRIVATE_DEPOSIT_USER_TDC_ROUTE_HOLDER_TYPES,
    RESERVE_USER_TDC_ROUTE_HOLDER_TYPES,
    timed_beta_path_rows,
    write_forecast_model_readout_outputs,
    zero_low_apr_credit_materiality_rows,
)


def test_timed_beta_paths_transition_without_changing_non_tdc_channels() -> None:
    rows = timed_beta_path_rows(
        effect_rows=_effect_rows(),
        summary_rows=_summary_rows(),
        synthesis_rows=_synthesis_rows(),
        materiality_rows=_materiality_rows(),
    )

    assert {field for row in rows for field in row} == set(TIMED_BETA_PATH_FIELDS)
    by_key = {
        (row["beta_path_id"], row["fiscal_year"], row["scenario_id"]): row
        for row in rows
    }
    normal_2032 = by_key[("normal_forward_constant", "2032", "scenario_high_tdc")]
    latest_2032 = by_key[(
        "latest_rolling_from_fy2032",
        "2032",
        "scenario_high_tdc",
    )]
    latest_2031 = by_key[(
        "latest_rolling_from_fy2032",
        "2031",
        "scenario_high_tdc",
    )]

    assert latest_2031["tdc_materialization_beta_scenario"] == "normal_forward"
    assert latest_2032["tdc_materialization_beta_scenario"] == (
        "latest_rolling_persistence"
    )
    assert latest_2032["delta_direct_treasury_current_demand_support_bil_fixed"] == (
        normal_2032["delta_direct_treasury_current_demand_support_bil_fixed"]
    )
    assert latest_2032["delta_bank_treasury_current_demand_support_bil_fixed"] == (
        normal_2032["delta_bank_treasury_current_demand_support_bil_fixed"]
    )
    assert Decimal(latest_2032["delta_ratewall_ratio_vs_normal_forward_path"]) > 0


def test_forecast_channel_classification_keeps_deferred_channels_visible() -> None:
    rows = forecast_channel_classification_rows()

    assert {field for row in rows for field in row} == set(
        FORECAST_CHANNEL_CLASSIFICATION_FIELDS
    )
    by_channel = {row["channel_id"]: row for row in rows}
    assert by_channel["tdc_ex_overlap_current_demand_support"][
        "classification"
    ] == "included"
    assert by_channel["tdc_ex_overlap_current_demand_support"][
        "selected_central_entry_role"
    ] == "standalone_final_n_term"
    assert by_channel["direct_treasury_interest_support"][
        "first_forecast_entry_role"
    ] == "standalone_final_n_term"
    assert by_channel["direct_treasury_interest_support"][
        "selected_central_entry_role"
    ] == "replacement_block_input_not_standalone"
    assert by_channel["bank_treasury_interest_support"][
        "selected_central_entry_role"
    ] == "replacement_block_input_not_standalone"
    assert by_channel["deposit_mmf_substitution_drag"]["classification"] == (
        "projection_required_as_paired_bounded_sensitivity"
    )
    assert by_channel["deposit_mmf_substitution_drag"]["blocked_use"] == (
        "credit_drag_double_count_against_moving_D"
    )
    assert by_channel["net_interest_after_fiscal_tga_offsets"][
        "classification"
    ] == "included_as_public_interest_replacement_block"
    assert by_channel["net_interest_after_fiscal_tga_offsets"][
        "selected_central_entry_role"
    ] == "standalone_final_n_term"
    assert by_channel["future_remittance_drag_demand_offset"][
        "public_interest_block_role"
    ] == "signed_future_remittance_timing_subchannel"


def test_remaining_numerator_channel_plan_gates_final_admission() -> None:
    channel_rows = forecast_channel_classification_rows()
    rows = forecast_numerator_channel_plan_rows(channel_rows)

    assert {field for row in rows for field in row} == set(
        FORECAST_NUMERATOR_CHANNEL_PLAN_FIELDS
    )
    assert {row["channel_id"] for row in rows} == {
        "safe_asset_allocation_drag",
        "zero_interest_credit_attenuation",
        "firm_liquid_asset_cushion",
        "firm_rollover_pressure_drag",
    }
    by_channel = {row["channel_id"]: row for row in rows}
    assert by_channel["safe_asset_allocation_drag"]["final_central_status"] == (
        "not_admitted_pending_disjoint_basis"
    )
    assert "household_safe_yield_capture" in by_channel[
        "safe_asset_allocation_drag"
    ]["double_count_guard"]
    assert by_channel["firm_liquid_asset_cushion"]["final_central_status"] == (
        "replacement_candidate_not_additive"
    )
    assert by_channel["firm_liquid_asset_cushion"]["blocked_use"] == (
        "additive_firm_cash_plus_firm_cushion"
    )
    assert by_channel["zero_interest_credit_attenuation"]["materiality_tier"] == (
        "bnpl_likely_low_total_zero_low_apr_promotional_credit_unproven"
    )
    assert by_channel["zero_interest_credit_attenuation"]["next_model_action"] == (
        "run_product_specific_zero_low_apr_credit_materiality_screen"
    )
    assert by_channel["firm_rollover_pressure_drag"]["final_central_status"] == (
        "not_a_current_numerator_channel_without_new_credit_model"
    )


def test_zero_low_apr_credit_screen_blocks_originations_and_central_n() -> None:
    rows = zero_low_apr_credit_materiality_rows()

    assert {field for row in rows for field in row} == set(
        ZERO_LOW_APR_CREDIT_MATERIALITY_FIELDS
    )
    assert {row["central_n_treatment"] for row in rows} == {"not_in_central_n"}
    by_segment = {row["product_segment"]: row for row in rows}
    assert Decimal(
        by_segment["bnpl_pay_in_4_average_outstanding"]["screen_relief_bil"]
    ) > Decimal("0")
    assert by_segment["broader_bnpl_zero_apr_originations"]["screen_relief_bil"] == ""
    assert by_segment["broader_bnpl_zero_apr_originations"]["blocked_use"] == (
        "originations_as_current_outstanding_stock"
    )
    assert by_segment["credit_card_introductory_promo_apr_balances"][
        "screen_status"
    ] == "potentially_material_but_historical_share_not_current_path"
    assert by_segment["deferred_interest_retail_credit"]["screen_status"] == (
        "missing_required_stock_and_duration"
    )


def test_public_interest_net_block_replaces_legacy_direct_bank_rows() -> None:
    rows, source_rows = forecast_public_interest_net_block_rows(
        effect_rows=_effect_rows(),
        cbo_macro_rows=_cbo_macro_rows(),
        fed_source_rows=_fed_source_rows(),
    )

    assert {field for row in rows for field in row} == set(
        PUBLIC_INTEREST_NET_BLOCK_FIELDS
    )
    assert len(source_rows) == 3
    by_key = {(row["fiscal_year"], row["scenario_id"]): row for row in rows}
    baseline = by_key[("2031", "cbo_baseline_noop_v1")]
    assert baseline["legacy_interest_support_bil"] == "11"
    assert baseline["projected_iorb_current_demand_support_bil"] == "1.5"
    assert baseline["projected_on_rrp_current_demand_support_bil"] == "1.2"
    assert baseline["projected_current_remittance_demand_offset_bil"] == "0"
    assert baseline["projected_future_remittance_drag_demand_offset_bil"] == "0"
    assert baseline["remittance_timing_treatment"].startswith(
        "cbo_baseline_remittance_budget_context_only"
    )
    assert Decimal(baseline["net_interest_after_fiscal_tga_offsets_bil"]) < Decimal(
        baseline["legacy_interest_support_bil"]
    )
    assert baseline["composition_rule"] == (
        "final_interest_block_replaces_legacy_direct_plus_bank_rows_never_add_both"
    )
    assert baseline["blocked_use"].startswith(
        "add_on_top_of_direct_and_bank_interest_rows"
    )


def test_cbo_remittance_projection_is_budget_context_not_numerator() -> None:
    rows, _source_rows = forecast_public_interest_net_block_rows(
        effect_rows=_effect_rows(),
        cbo_macro_rows=_cbo_macro_rows(),
        fed_source_rows=_fed_source_rows(),
        remittance_projection_rows=[
            {
                "fiscal_year": "2031",
                "cbo_federal_reserve_remittance_bil": "9999",
            }
        ],
    )

    baseline = {
        (row["fiscal_year"], row["scenario_id"]): row for row in rows
    }[("2031", "cbo_baseline_noop_v1")]
    assert baseline["projected_current_remittance_state_bil"] == "9999"
    assert baseline["projected_current_remittance_demand_offset_bil"] == "0"
    assert baseline["remittance_projection_status"] == (
        "cbo_remittance_projection_baseline_budget_context_not_numerator"
    )


def test_residual_numerator_sensitivities_use_residual_basis_and_overlap_guard() -> None:
    public_interest_rows, _source_rows = forecast_public_interest_net_block_rows(
        effect_rows=_effect_rows(),
        cbo_macro_rows=_cbo_macro_rows(),
        fed_source_rows=_fed_source_rows(),
    )
    rows, source_rows = forecast_residual_numerator_sensitivity_rows(
        effect_rows=_effect_rows(),
        synthesis_rows=_synthesis_rows(),
        public_interest_rows=public_interest_rows,
        cbo_macro_rows=_cbo_macro_rows(),
        residual_source_rows=_residual_source_rows(),
    )

    assert {field for row in rows for field in row} == set(
        RESIDUAL_NUMERATOR_SENSITIVITY_FIELDS
    )
    assert {field for row in source_rows for field in row} == set(
        RESIDUAL_SENSITIVITY_SOURCE_FIELDS
    )
    by_key = {
        (row["assumption_set"], row["fiscal_year"], row["scenario_id"]): row
        for row in rows
    }
    base = by_key[("literature_calibrated_base", "2032", "scenario_high_tdc")]
    paired = by_key[(
        "assumption_mode_deposit_mmf_paired_entry",
        "2032",
        "scenario_high_tdc",
    )]
    assert base["firm_liquid_asset_stock_source_status"] == (
        "source_backed_latest_4q_average_z1_fred_components_held_constant"
    )
    assert Decimal(base["firm_cash_attenuation_bil"]) < 0
    assert base["household_safe_yield_capture_bil"] == "0"
    assert Decimal(paired["public_interest_residual_cashflow_basis_bil"]) > 0
    assert Decimal(paired["household_safe_yield_capture_bil"]) > 0
    assert Decimal(paired["deposit_mmf_substitution_offset_bil"]) > 0
    assert Decimal(paired["deposit_mmf_substitution_drag_bil"]) < 0
    assert Decimal(
        paired["delta_total_residual_sensitivity_vs_baseline_bil"]
    ) != Decimal("0")
    assert paired["baseline_firm_cash_attenuation_bil"] == "0"
    assert Decimal(
        paired["delta_firm_cash_attenuation_vs_baseline_bil"]
    ) < Decimal("0")
    assert paired["deposit_mmf_pairing_status"] == (
        "paired_offset_and_drag_never_unpaired_offset"
    )
    assert paired["denominator_overlap_status"] == (
        "credit_drag_has_moving_D_overlap_not_added_to_main_n"
    )
    assert paired["blocked_use"].endswith("credit_drag_double_count_against_moving_D")


def test_composition_surface_replaces_interest_and_adds_residual_deltas_only() -> None:
    timed_rows = timed_beta_path_rows(
        effect_rows=_effect_rows(),
        summary_rows=_summary_rows(),
        synthesis_rows=_synthesis_rows(),
        materiality_rows=_materiality_rows(),
    )
    public_interest_rows, _ = forecast_public_interest_net_block_rows(
        effect_rows=_effect_rows(),
        cbo_macro_rows=_cbo_macro_rows(),
        fed_source_rows=_fed_source_rows(),
    )
    residual_rows, _ = (
        forecast_residual_numerator_sensitivity_rows(
            effect_rows=_effect_rows(),
            synthesis_rows=_synthesis_rows(),
            public_interest_rows=public_interest_rows,
            cbo_macro_rows=_cbo_macro_rows(),
            residual_source_rows=_residual_source_rows(),
        )
    )

    rows = forecast_composition_surface_rows(
        timed_beta_rows=timed_rows,
        public_interest_rows=public_interest_rows,
        residual_sensitivity_rows=residual_rows,
    )

    assert {field for row in rows for field in row} == set(
        FORECAST_COMPOSITION_SURFACE_FIELDS
    )
    by_key = {
        (
            row["composition_case_id"],
            row["beta_path_id"],
            row["fiscal_year"],
            row["scenario_id"],
        ): row
        for row in rows
    }
    current = by_key[(
        "first_forecast_current",
        "normal_forward_constant",
        "2032",
        "scenario_high_tdc",
    )]
    replacement = by_key[(
        "public_interest_replacement",
        "normal_forward_constant",
        "2032",
        "scenario_high_tdc",
    )]
    residual = by_key[(
        "public_interest_plus_residual_delta::assumption_mode_deposit_mmf_paired_entry",
        "normal_forward_constant",
        "2032",
        "scenario_high_tdc",
    )]
    residual_baseline = by_key[(
        "public_interest_plus_residual_delta::assumption_mode_deposit_mmf_paired_entry",
        "normal_forward_constant",
        "2032",
        "cbo_baseline_noop_v1",
    )]

    assert current["composition_n_bil"] == current["first_forecast_n_bil"]
    assert Decimal(replacement["composition_n_bil"]) == (
        Decimal(replacement["tdc_current_demand_support_bil"])
        + Decimal(replacement["public_interest_net_support_bil"])
    )
    assert Decimal(replacement["composition_n_bil"]) != Decimal(
        current["composition_n_bil"]
    )
    assert residual_baseline["residual_sensitivity_delta_bil"] == "0"
    assert Decimal(residual["composition_n_bil"]) == (
        Decimal(replacement["composition_n_bil"])
        + Decimal(residual["residual_sensitivity_delta_bil"])
    )
    assert Decimal(residual["delta_composition_ratewall_ratio_vs_baseline"]) != 0
    assert residual["selected_moving_denominator_bil"] == "1080"
    assert residual["canonical_ratio_entry"] == "false"


def test_central_forecast_surface_selects_replacement_and_normal_beta() -> None:
    composition_rows = _composition_rows()

    rows = central_forecast_surface_rows(composition_rows)

    assert {field for row in rows for field in row} == set(
        CENTRAL_FORECAST_SURFACE_FIELDS
    )
    by_key = {(row["fiscal_year"], row["scenario_id"]): row for row in rows}
    high = by_key[("2032", "scenario_high_tdc")]
    assert high["central_beta_path_id"] == "normal_forward_constant"
    assert high["central_composition_case_id"] == "public_interest_replacement"
    assert high["central_choice_status"] == (
        "selected_model_surface_public_interest_replacement_normal_forward_beta"
    )
    assert Decimal(high["delta_central_ratewall_ratio_vs_baseline"]) != 0
    assert Decimal(high["delta_first_forecast_ratewall_ratio_vs_central"]) != 0
    assert Decimal(high["delta_residual_paired_ratewall_ratio_vs_central"]) != 0
    assert Decimal(high["delta_latest_rolling_beta_ratewall_ratio_vs_central"]) > 0
    assert high["canonical_ratio_entry"] == "false"


def test_central_scenario_interpretation_summarizes_mechanisms() -> None:
    central_rows = central_forecast_surface_rows(_composition_rows())

    rows = central_scenario_interpretation_rows(central_rows)

    assert {field for row in rows for field in row} == set(
        CENTRAL_SCENARIO_INTERPRETATION_FIELDS
    )
    by_key = {(row["fiscal_year"], row["scenario_id"]): row for row in rows}
    baseline = by_key[("2032", "cbo_baseline_noop_v1")]
    high = by_key[("2032", "scenario_high_tdc")]
    assert baseline["primary_driver"] == "baseline_or_zero_delta"
    assert high["scenario_direction"] in {"raises_ratewall", "lowers_ratewall"}
    assert high["primary_driver"] in {
        "numerator_driven",
        "denominator_driven",
        "mixed_numerator_and_denominator",
    }
    assert "N-only delta" in high["mechanism_summary"]
    assert Decimal(high["sensitivity_width_ratewall_ratio"]) > 0
    assert high["largest_sensitivity_case"] in {
        "first_forecast",
        "residual_base",
        "residual_paired",
        "latest_rolling_beta",
        "pooled_full_beta",
    }
    assert high["canonical_ratio_entry"] == "false"


def test_scenario_sufficiency_marks_private_holder_rows_as_ru_route_shifts() -> None:
    central_rows = [
        {
            "fiscal_year": "2036",
            "scenario_id": "cbo_baseline_noop_v1",
            "baseline_scenario_id": "cbo_baseline_noop_v1",
            "delta_central_ratewall_ratio_vs_baseline": "0",
            "primary_driver": "baseline_or_zero_delta",
        },
        {
            "fiscal_year": "2036",
            "scenario_id": "tdcsim_private_holder_high_v1",
            "baseline_scenario_id": "cbo_baseline_noop_v1",
            "delta_central_ratewall_ratio_vs_baseline": "0.04",
            "primary_driver": "numerator_driven",
        },
        {
            "fiscal_year": "2036",
            "scenario_id": "tdcsim_rate_up_25bp_v1",
            "baseline_scenario_id": "cbo_baseline_noop_v1",
            "delta_central_ratewall_ratio_vs_baseline": "-0.03",
            "primary_driver": "denominator_driven",
        },
    ]
    rows = forecast_scenario_sufficiency_rows(
        effect_rows=[
            _effect_row("cbo_baseline_noop_v1", "2036", "0", "10", "1"),
            _effect_row("tdcsim_private_holder_high_v1", "2036", "5", "10", "1"),
            _effect_row("tdcsim_rate_up_25bp_v1", "2036", "0", "10", "1"),
            _effect_row("tdcsim_issuance_shorter_v1", "2036", "1", "10", "1"),
        ],
        scenario_config_rows=[
            {
                "scenario_id": "cbo_baseline_noop_v1",
                "scenario_title": "Baseline",
                "scenario_axis": "baseline",
                "provenance_kind": "user_stress_assumption",
            },
            {
                "scenario_id": "tdcsim_private_holder_high_v1",
                "scenario_title": "Higher private holder share",
                "scenario_axis": "holder_mix_reserve_user_private",
                "provenance_kind": "user_stress_assumption",
            },
            {
                "scenario_id": "tdcsim_rate_up_25bp_v1",
                "scenario_title": "Rate up",
                "scenario_axis": "rate_curve",
                "provenance_kind": "user_stress_assumption",
            },
            {
                "scenario_id": "tdcsim_issuance_shorter_v1",
                "scenario_title": "Generic shorter issuance",
                "scenario_axis": "issuance_generic_superseded",
                "provenance_kind": "user_stress_assumption",
            },
            {
                "scenario_id": "tdcsim_primary_deficit_up_1pct_v1",
                "scenario_title": "Primary deficit up",
                "scenario_axis": "primary_deficit",
                "provenance_kind": "user_stress_assumption",
            },
        ],
        central_interpretation_rows=central_rows,
    )

    assert {field for row in rows for field in row} == set(
        FORECAST_SCENARIO_SUFFICIENCY_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    assert by_scenario["tdcsim_rate_up_25bp_v1"]["coverage_status"] == (
        "active_central_surface"
    )
    assert by_scenario["tdcsim_rate_up_25bp_v1"]["fy2036_primary_driver"] == (
        "denominator_driven"
    )
    assert by_scenario["tdcsim_private_holder_high_v1"]["sufficiency_decision"] == (
        "covered_as_reserve_user_vs_private_tdc_route_shift"
    )
    assert by_scenario["tdcsim_private_holder_high_v1"]["next_model_action"] == (
        "interpret_as_reserve_user_like_absorption_shift_with_fed_reserve_creation_deferred"
    )
    assert "Foreign" in by_scenario["tdcsim_private_holder_high_v1"][
        "tdc_route_taxonomy"
    ]
    assert "fed_cb_reserve_creation_channel_deferred" in by_scenario[
        "tdcsim_private_holder_high_v1"
    ]["tdc_route_taxonomy"]
    assert not any(
        row["coverage_status"] == "required_missing"
        for row in by_scenario.values()
    )
    assert by_scenario["tdcsim_issuance_shorter_v1"]["sufficiency_decision"] == (
        "superseded_by_empirical_issuance_surface"
    )
    assert by_scenario["tdcsim_primary_deficit_up_1pct_v1"]["coverage_status"] == (
        "configured_not_run"
    )
    assert set(RESERVE_USER_TDC_ROUTE_HOLDER_TYPES) == {
        "Banks",
        "Foreign",
        "CB",
        "FedInternal",
    }
    assert PRIVATE_DEPOSIT_USER_TDC_ROUTE_HOLDER_TYPES == ("Private",)


def test_forecast_model_outputs_write_csv_png_and_readout(tmp_path: Path) -> None:
    timed_rows = timed_beta_path_rows(
        effect_rows=_effect_rows(),
        summary_rows=_summary_rows(),
        synthesis_rows=_synthesis_rows(),
        materiality_rows=_materiality_rows(),
    )
    channel_rows = forecast_channel_classification_rows()
    numerator_channel_plan_rows = forecast_numerator_channel_plan_rows(channel_rows)
    zero_low_apr_credit_rows = zero_low_apr_credit_materiality_rows()
    public_interest_rows, fed_source_rows = forecast_public_interest_net_block_rows(
        effect_rows=_effect_rows(),
        cbo_macro_rows=_cbo_macro_rows(),
        fed_source_rows=_fed_source_rows(),
    )
    residual_sensitivity_rows, residual_source_rows = (
        forecast_residual_numerator_sensitivity_rows(
            effect_rows=_effect_rows(),
            synthesis_rows=_synthesis_rows(),
            public_interest_rows=public_interest_rows,
            cbo_macro_rows=_cbo_macro_rows(),
            residual_source_rows=_residual_source_rows(),
        )
    )
    composition_surface_rows = forecast_composition_surface_rows(
        timed_beta_rows=timed_rows,
        public_interest_rows=public_interest_rows,
        residual_sensitivity_rows=residual_sensitivity_rows,
    )
    central_forecast_rows = central_forecast_surface_rows(composition_surface_rows)
    central_interpretation_rows = central_scenario_interpretation_rows(
        central_forecast_rows
    )
    scenario_sufficiency_rows = forecast_scenario_sufficiency_rows(
        effect_rows=_effect_rows(),
        scenario_config_rows=[
            {
                "scenario_id": "cbo_baseline_noop_v1",
                "scenario_title": "Baseline",
                "scenario_axis": "baseline",
                "provenance_kind": "test",
            },
            {
                "scenario_id": "scenario_high_tdc",
                "scenario_title": "High TDC",
                "scenario_axis": "holder_mix_reserve_user_private",
                "provenance_kind": "test",
            },
        ],
        central_interpretation_rows=central_interpretation_rows,
    )

    outputs = write_forecast_model_readout_outputs(
        tmp_path / "out",
        timed_beta_rows=timed_rows,
        channel_rows=channel_rows,
        numerator_channel_plan_rows=numerator_channel_plan_rows,
        zero_low_apr_credit_rows=zero_low_apr_credit_rows,
        public_interest_rows=public_interest_rows,
        fed_source_rows=fed_source_rows,
        residual_sensitivity_rows=residual_sensitivity_rows,
        residual_source_rows=residual_source_rows,
        composition_surface_rows=composition_surface_rows,
        central_forecast_rows=central_forecast_rows,
        central_interpretation_rows=central_interpretation_rows,
        scenario_sufficiency_rows=scenario_sufficiency_rows,
    )

    assert outputs["timed_beta_csv"].read_text(encoding="utf-8").startswith(
        "forecast_timed_beta_path_row_id,"
    )
    assert outputs["channel_classification_csv"].read_text(
        encoding="utf-8"
    ).startswith("forecast_channel_classification_row_id,")
    assert outputs["numerator_channel_plan_csv"].read_text(
        encoding="utf-8"
    ).startswith("forecast_numerator_channel_plan_row_id,")
    assert outputs["zero_low_apr_credit_materiality_csv"].read_text(
        encoding="utf-8"
    ).startswith("zero_low_apr_credit_materiality_row_id,")
    assert outputs["public_interest_net_block_csv"].read_text(
        encoding="utf-8"
    ).startswith("forecast_public_interest_net_block_row_id,")
    assert outputs["fed_liability_sources_csv"].read_text(
        encoding="utf-8"
    ).startswith("forecast_fed_liability_source_row_id,")
    assert outputs["residual_numerator_sensitivity_csv"].read_text(
        encoding="utf-8"
    ).startswith("forecast_residual_numerator_sensitivity_row_id,")
    assert outputs["residual_sensitivity_sources_csv"].read_text(
        encoding="utf-8"
    ).startswith("forecast_residual_sensitivity_source_row_id,")
    assert outputs["composition_surface_csv"].read_text(
        encoding="utf-8"
    ).startswith("forecast_composition_surface_row_id,")
    assert outputs["central_forecast_surface_csv"].read_text(
        encoding="utf-8"
    ).startswith("central_forecast_surface_row_id,")
    assert outputs["central_interpretation_csv"].read_text(
        encoding="utf-8"
    ).startswith("central_scenario_interpretation_row_id,")
    assert outputs["scenario_sufficiency_csv"].read_text(
        encoding="utf-8"
    ).startswith("forecast_scenario_sufficiency_row_id,")
    readout = forecast_model_readout_markdown(timed_rows, channel_rows)
    readout_with_net_block = forecast_model_readout_markdown(
        timed_rows,
        channel_rows,
        numerator_channel_plan_rows=numerator_channel_plan_rows,
        zero_low_apr_credit_rows=zero_low_apr_credit_rows,
        public_interest_rows=public_interest_rows,
        residual_sensitivity_rows=residual_sensitivity_rows,
        composition_surface_rows=composition_surface_rows,
        central_forecast_rows=central_forecast_rows,
        central_interpretation_rows=central_interpretation_rows,
        scenario_sufficiency_rows=scenario_sufficiency_rows,
    )
    assert outputs["readout_md"].read_text(encoding="utf-8") == readout_with_net_block
    assert "Preliminary Economist Summary" in readout_with_net_block
    assert "Central Forecast Choice" in readout_with_net_block
    assert "Plain Mechanism Readout" in readout_with_net_block
    assert "Scenario Coverage" in readout_with_net_block
    assert "reserve-user-like versus private/deposit-user shifts" in (
        readout_with_net_block
    )
    assert "Public-Interest Net Block" in readout_with_net_block
    assert "Residual Numerator Sensitivities" in readout_with_net_block
    assert "Remaining Numerator Channel Plan" in readout_with_net_block
    assert "Remaining unresolved deferred channels: `4`" in readout_with_net_block
    assert "Zero/Low-APR Credit Materiality Screen" in readout_with_net_block
    assert "This is a materiality screen only" in readout_with_net_block
    assert "Forecast Composition Surface" in readout_with_net_block
    assert "Deferred channels classified" in readout
    assert "Settled deferred channels outside the remaining-plan table" in (
        readout_with_net_block
    )
    assert "Remaining final-central admission/parking plan rows: `4`" in (
        readout_with_net_block
    )
    for key in (
        "png_ratewall_paths",
        "png_timed_beta_effect",
        "png_components",
        "png_channel_scope",
        "png_composition_surface",
        "png_central_surface",
        "png_central_baseline_path",
        "png_central_sensitivity_spread",
        "png_scenario_sufficiency",
    ):
        assert outputs[key].read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def _composition_rows() -> list[dict[str, str]]:
    timed_rows = timed_beta_path_rows(
        effect_rows=_effect_rows(),
        summary_rows=_summary_rows(),
        synthesis_rows=_synthesis_rows(),
        materiality_rows=_materiality_rows(),
    )
    public_interest_rows, _ = forecast_public_interest_net_block_rows(
        effect_rows=_effect_rows(),
        cbo_macro_rows=_cbo_macro_rows(),
        fed_source_rows=_fed_source_rows(),
    )
    residual_rows, _ = forecast_residual_numerator_sensitivity_rows(
        effect_rows=_effect_rows(),
        synthesis_rows=_synthesis_rows(),
        public_interest_rows=public_interest_rows,
        cbo_macro_rows=_cbo_macro_rows(),
        residual_source_rows=_residual_source_rows(),
    )
    return forecast_composition_surface_rows(
        timed_beta_rows=timed_rows,
        public_interest_rows=public_interest_rows,
        residual_sensitivity_rows=residual_rows,
    )


def _summary_rows() -> list[dict[str, str]]:
    return [
        _summary_row("cbo_baseline_noop_v1", "2031"),
        _summary_row("scenario_high_tdc", "2031"),
        _summary_row("cbo_baseline_noop_v1", "2032"),
        _summary_row("scenario_high_tdc", "2032"),
    ]


def _effect_rows() -> list[dict[str, str]]:
    return [
        _effect_row("cbo_baseline_noop_v1", "2031", "100", "10", "1"),
        _effect_row("scenario_high_tdc", "2031", "200", "8", "2"),
        _effect_row("cbo_baseline_noop_v1", "2032", "110", "11", "1"),
        _effect_row("scenario_high_tdc", "2032", "220", "9", "2"),
    ]


def _cbo_macro_rows() -> list[dict[str, str]]:
    return [
        {
            "fiscal_year": "2031",
            "cbo_nominal_gdp_bil": "1000",
            "cbo_short_rate_pct": "4",
        },
        {
            "fiscal_year": "2032",
            "cbo_nominal_gdp_bil": "1100",
            "cbo_short_rate_pct": "5",
        },
    ]


def _fed_source_rows() -> list[dict[str, str]]:
    return [
        _fed_source_row("WRBWFRBL", "1000000"),
        _fed_source_row("IORB", "5"),
        _fed_source_row("RRPONTSYD", "500000"),
    ]


def _residual_source_rows() -> list[dict[str, str]]:
    return [
        _residual_source_row("NCBCDCA", "100000"),
        _residual_source_row("TSDABSNNCB", "200000"),
        _residual_source_row("TSABSNNCB", "300000"),
        _residual_source_row("BOGZ1FL103034000Q", "400000"),
        _residual_source_row("SRPSABSNNCB", "500000"),
    ]


def _synthesis_rows() -> list[dict[str, str]]:
    return [
        _synthesis_row("cbo_baseline_noop_v1", "2031", "1000", "0", "0"),
        _synthesis_row("scenario_high_tdc", "2031", "1000", "0", "0"),
        _synthesis_row("cbo_baseline_noop_v1", "2032", "1100", "0", "0"),
        _synthesis_row("scenario_high_tdc", "2032", "1080", "-20", "-25"),
    ]


def _materiality_rows() -> list[dict[str, str]]:
    return [
        _materiality_row("cbo_baseline_noop_v1", "2031", "baseline"),
        _materiality_row("scenario_high_tdc", "2031", "holder_only"),
        _materiality_row("cbo_baseline_noop_v1", "2032", "baseline"),
        _materiality_row("scenario_high_tdc", "2032", "holder_only"),
    ]


def _summary_row(scenario_id: str, fiscal_year: str) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "fiscal_year": fiscal_year,
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "comparison_group": "test_group",
    }


def _effect_row(
    scenario_id: str,
    fiscal_year: str,
    tdc: str,
    direct: str,
    bank: str,
) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "fiscal_year": fiscal_year,
        "tdc_change_ex_overlap_bil": tdc,
        "direct_treasury_current_demand_support_bil": direct,
        "bank_treasury_current_demand_support_bil": bank,
    }


def _synthesis_row(
    scenario_id: str,
    fiscal_year: str,
    denominator: str,
    delta_d: str,
    curve_bp: str,
) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "fiscal_year": fiscal_year,
        "selected_moving_denominator_bil": denominator,
        "selected_delta_denominator_bil": delta_d,
        "curve_effective_overlay_bp": curve_bp,
    }


def _materiality_row(
    scenario_id: str,
    fiscal_year: str,
    scenario_family: str,
) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "fiscal_year": fiscal_year,
        "scenario_family": scenario_family,
        "model_relevance_class": "test",
    }


def _fed_source_row(series_id: str, latest_average_value: str) -> dict[str, str]:
    return {
        "forecast_fed_liability_source_row_id": f"source::{series_id}",
        "series_id": series_id,
        "series_label": series_id,
        "source_url": "",
        "source_cache_path": "",
        "observation_count": "13",
        "latest_observation_date": "2026-06-24",
        "latest_observation_value": latest_average_value,
        "latest_average_window_observation_count": "13",
        "latest_average_value": latest_average_value,
        "unit": "test",
        "projection_use": "test",
        "source_status": "test_fixture",
    }


def _residual_source_row(series_id: str, latest_average_value: str) -> dict[str, str]:
    return {
        "forecast_residual_sensitivity_source_row_id": f"source::{series_id}",
        "series_id": series_id,
        "series_label": series_id,
        "source_url": "",
        "source_cache_path": "",
        "observation_count": "4",
        "latest_observation_date": "2026-06-24",
        "latest_observation_value": latest_average_value,
        "latest_average_window_observation_count": "4",
        "latest_average_value": latest_average_value,
        "unit": "test",
        "projection_use": "test",
        "source_status": "test_fixture",
    }

from ratewall.databook.build import (
    RATEWALL_CORPORATE_NET_INTEREST_CASHFLOW_BRIDGE_FIELDS,
    RATEWALL_DENOMINATOR_CROSS_SOURCE_DESIGN_VALIDATION_FIELDS,
    RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_BLOCKER_RESOLUTION_MATRIX_FIELDS,
    RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_BLOCKER_STATUS_ROLLUP_FIELDS,
    RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_PRIORITY_QUEUE_FIELDS,
    RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_SOURCE_DESIGN_REQUIREMENT_FIELDS,
    RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_TIER1_WORKPLAN_FIELDS,
    RATEWALL_DENOMINATOR_OUTLIER_WINDOW_ROBUSTNESS_DIAGNOSTIC_FIELDS,
    RATEWALL_DENOMINATOR_PRETREND_PLACEBO_DIAGNOSTIC_FIELDS,
    RATEWALL_DENOMINATOR_RESPONSE_ESTIMATE_DIAGNOSTIC_FIELDS,
    RATEWALL_DENOMINATOR_FORMAL_DESIGN_TEST_RESULT_FIELDS,
    RATEWALL_TDSP_SUPPORTED_HORIZON_RESPONSE_PROFILE_FIELDS,
    RATEWALL_DYNAMIC_OFFSET_RATIO_PATH_FIELDS,
    RATEWALL_DYNAMIC_SCENARIO_PATH_FIELDS,
    RATEWALL_HIGHER_RATE_CHANNEL_REGISTRY_FIELDS,
    RATEWALL_ASSUMPTION_MODE_POST_CLOSURE_BOUNDARY_FIELDS,
    RATEWALL_PRICE_CHANNEL_DIAGNOSTIC_FIELDS,
    RATEWALL_RESTRICTED_DATA_GATE_SPEC_FIELDS,
    RATEWALL_SCENARIO_CROSSING_DIAGNOSTIC_FIELDS,
    RATEWALL_SOURCE_GATE_EXHAUSTION_CLOSURE_FIELDS,
    SOURCE_SPECIFIC_EVIDENCE_MAP,
    _dynamic_path_claim_defaults,
    _ratewall_corporate_net_interest_cashflow_bridge_rows,
    _ratewall_denominator_cross_source_design_validation_rows,
    _ratewall_denominator_evidence_upgrade_blocker_resolution_matrix_rows,
    _ratewall_denominator_evidence_upgrade_blocker_status_rollup_rows,
    _ratewall_denominator_evidence_upgrade_priority_queue_rows,
    _ratewall_denominator_evidence_upgrade_source_design_requirement_rows,
    _ratewall_denominator_evidence_upgrade_tier1_workplan_rows,
    _ratewall_denominator_formal_design_test_result_rows,
    _ratewall_denominator_outlier_window_robustness_diagnostic_rows,
    _ratewall_denominator_pretrend_placebo_diagnostic_rows,
    _ratewall_tdsp_supported_horizon_response_profile_rows,
    _ratewall_higher_rate_channel_registry_rows,
    _ratewall_interest_channel_module_registry_rows,
    _ratewall_main_ratio_inclusion_status,
    _ratewall_assumption_mode_post_closure_boundary_rows,
    _ratewall_source_gate_exhaustion_closure_rows,
    _ratewall_restricted_data_gate_spec_rows,
    _ratewall_source_gate_prior_narrowing_decision_rows,
    _ratewall_term_structure_pricing_carry_diagnostic_rows,
    _ratewall_working_capital_cost_channel_diagnostic_rows,
    _disabled_claim_switches,
)
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot


def test_public_liability_status_distinguishes_bucket_gate_from_full_ladder() -> None:
    modules = {
        row["module_name"]: row
        for row in _ratewall_interest_channel_module_registry_rows()
    }

    assert SOURCE_SPECIFIC_EVIDENCE_MAP["public_liability_repricing_ladder"][
        "status"
    ] == (
        "source_specific_context_treasury_bucket_repricing_gate_passed_"
        "full_ladder_blocked"
    )
    assert (
        "treasury_bucket_repricing_only"
        in modules["public_liability_repricing_ladder"]["source_status"]
    )
    assert (
        "main_ratio_unchanged"
        in modules["public_liability_repricing_ladder"]["source_status"]
    )


def test_passed_mspd_bucket_gate_uses_existing_bridge_fail_closed() -> None:
    rows = _ratewall_source_gate_prior_narrowing_decision_rows(
        evidence_queue_rows=[
            {
                "channel_module": "public_liability_repricing_ladder",
                "priority_rank": "1",
                "model_layer": "core_public_interest_cashflow",
                "next_backend_action": "stale_queue_action_should_not_win",
            }
        ],
        mspd_table3_bucket_repricing_gate_rows=[
            {
                "gate_block": "mspd_table3_gate_summary",
                "horizon": "all_required",
                "diagnostic_scope": "overall_mspd_table3_bucket_repricing_gate",
                "source_status": "live_source_reconciled_bucket_repricing_gate_passed",
                "source_snapshot_kind": "live",
                "bucket_repricing_handle_candidate": (
                    "treasury_repricing_speed_share_bucket_candidate"
                ),
                "promotion_readiness": "gate_passed_formula_context_only",
                "exact_blocker_before_formula_replacement": (
                    "none_bucket_repricing_source_gate_passed"
                ),
                "evidence_needed": "recipient/leakage and reset-calendar gates",
                "evidence_needed_before_prior_narrowing": (
                    "explicit solver opt-in and nonpromotion tests"
                ),
                "evidence_needed_before_promotion": (
                    "explicit solver opt-in and nonpromotion tests"
                ),
                "promotion_gate": "mspd_bucket_repricing_source_gate",
                "prior_narrowing_allowed": "true",
                "formula_replacement_allowed": "true",
                "main_offset_ratio_changed_this_tranche": "false",
            }
        ],
        treasury_recipient_leakage_source_gate_rows=[],
        conventional_drag_source_design_gate_rows=[],
        public_finance_timing_evidence_gap_rows=[],
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["candidate_bridge_table"] == (
        "ratewall_treasury_bucket_repricing_prior_bridge.csv"
    )
    assert row["bridge_action"] == (
        "use_existing_source_specific_formula_context_bridge_"
        "fail_closed_until_explicit_solver_opt_in"
    )
    assert row["source_bridge_created_this_tranche"] == "false"
    assert "no_new_table_or_solver_opt_in" in row["why_no_bridge_created"]
    assert "explicit nonpromotion tests" in row["next_backend_action"]
    assert row["main_offset_ratio_changed_this_tranche"] == "false"
    assert row["aggregate_assumption_behavior_preserved"] == "true"


def test_source_gate_exhaustion_closure_rows_are_fail_closed_invariants() -> None:
    rows = _ratewall_source_gate_exhaustion_closure_rows(snapshots=[])

    assert rows
    assert [int(row["priority_rank"]) for row in rows] == list(range(1, len(rows) + 1))
    assert len({row["gate_id"] for row in rows}) == len(rows)
    for row in rows:
        assert set(row) == set(RATEWALL_SOURCE_GATE_EXHAUSTION_CLOSURE_FIELDS)
        assert row["gate_id"].endswith("_promotion_gate")
        assert row["gate_family"]
        assert row["target_promotion_step"]
        assert row["audited_required_evidence"]
        assert row["final_blocker_type"]
        assert row["exact_final_blocker"]
        assert row["source_or_schema_blocker"]
        assert row["claim_boundary_blocker"]
        assert row["promotion_grade_source_available"] == "false"
        assert row["promotion_gate_passed"] == "false"
        assert (
            row["stage_exhausted_for_current_public_official_local_artifacts"] == "true"
        )
        assert row["no_further_source_mining_goal_recommended"] == "true"
        assert row["source_gate_mining_phase_status"] == (
            "stage_exhausted_no_concrete_promotion_grade_next_step"
        )
        assert row["prior_narrowing_allowed"] == "false"
        assert row["formula_replacement_allowed"] == "false"
        assert row["main_offset_ratio_changed_this_tranche"] == "false"
        assert row["dynamic_equation_changed_this_tranche"] == "false"
        assert row["split_denominator_promotion_allowed"] == "false"
        assert row["empirical_claim_enabled"] == "false"
        assert row["policy_failure_claim_enabled"] == "false"
        assert row["pricing_output_enabled"] == "false"
        assert row["incidence_claim_enabled"] == "false"
        assert row["welfare_claim_enabled"] == "false"
        assert row["tax_output_enabled"] == "false"
        assert row["mpc_output_enabled"] == "false"
        assert row["holder_allocation_enabled"] == "false"
        assert row["reset_calendar_construction_enabled"] == "false"
        assert row["raw_rate_shock_enabled"] == "false"
        assert row["causal_financialization_claim_enabled"] == "false"


def test_restricted_data_gate_spec_rows_are_nonpromoting_contracts() -> None:
    closure_rows = _ratewall_source_gate_exhaustion_closure_rows(snapshots=[])
    rows = _ratewall_restricted_data_gate_spec_rows(
        source_gate_exhaustion_closure_rows=closure_rows
    )

    assert rows
    assert {row["gate_id"] for row in rows} == {
        row["gate_id"] for row in closure_rows
    }
    assert [int(row["priority_rank"]) for row in rows] == list(range(1, len(rows) + 1))
    for row in rows:
        assert set(row) == set(RATEWALL_RESTRICTED_DATA_GATE_SPEC_FIELDS)
        assert row["gate_id"].endswith("_promotion_gate")
        assert row["required_artifact_or_method_bridge"]
        assert row["access_class"]
        assert row["unit_of_observation"]
        assert row["must_have_schema_fields"]
        assert row["minimal_bridge_test"]
        assert row["explicit_abandonment_condition"]
        assert row["promotion_gate_passed"] == "false"
        assert row["prior_narrowing_allowed"] == "false"
        assert row["formula_replacement_allowed"] == "false"
        assert row["main_offset_ratio_changed_this_tranche"] == "false"
        assert row["dynamic_equation_changed_this_tranche"] == "false"
        assert row["split_denominator_promotion_allowed"] == "false"
        assert row["forbidden_switches_remain_disabled"] == "true"
        assert row["linked_closure_surface"] == (
            "ratewall_source_gate_exhaustion_closure.csv"
        )


def test_assumption_mode_post_closure_boundary_map_separates_layers() -> None:
    closure_rows = _ratewall_source_gate_exhaustion_closure_rows(snapshots=[])
    restricted_rows = _ratewall_restricted_data_gate_spec_rows(
        source_gate_exhaustion_closure_rows=closure_rows
    )
    rows = _ratewall_assumption_mode_post_closure_boundary_rows(
        source_gate_exhaustion_closure_rows=closure_rows,
        restricted_data_gate_spec_rows=restricted_rows,
        assumption_rows=[
            {"assumption_set": "base"},
            {"assumption_set": "upper_bound"},
        ],
        scenario_ladder_rows=[
            {"chapter_regime_use_label": "robust_non_hit"},
            {"chapter_regime_use_label": "wall_hit_under_assumptions"},
        ],
    )

    assert len(rows) == 5
    assert {row["boundary_layer"] for row in rows} == {
        "evidence_mode_admitted_context",
        "stage_exhausted_public_source_blockers",
        "restricted_or_licensed_data_requirements",
        "explicit_assumption_mode_scenario_parameters",
        "disabled_claims_and_forbidden_outputs",
    }
    for row in rows:
        assert set(row) == set(
            RATEWALL_ASSUMPTION_MODE_POST_CLOSURE_BOUNDARY_FIELDS
        )
        assert row["prior_narrowing_allowed"] == "false"
        assert row["formula_replacement_allowed"] == "false"
        assert row["main_offset_ratio_changed_this_tranche"] == "false"
        assert row["dynamic_equation_changed_this_tranche"] == "false"
        assert row["split_denominator_promotion_allowed"] == "false"
        assert row["forbidden_switches_remain_disabled"] == "true"

    by_layer = {row["boundary_layer"]: row for row in rows}
    assert by_layer["stage_exhausted_public_source_blockers"][
        "public_source_mining_status"
    ] == "stage_exhausted_no_general_mining_goal"
    assert (
        "not_current_evidence"
        in by_layer["restricted_or_licensed_data_requirements"]["claim_boundary"]
    )
    assert "2_assumption_sets" in by_layer[
        "explicit_assumption_mode_scenario_parameters"
    ]["assumption_mode_status"]


def test_existing_scalar_terms_are_not_labeled_outside_main_ratio() -> None:
    modules = {
        row["module_name"]: row
        for row in _ratewall_interest_channel_module_registry_rows()
    }

    assert "existing_main_ratio_scalar_firm_cash_attenuation_term" in (
        _ratewall_main_ratio_inclusion_status(
            name="firm_cash_debt_maturity_heterogeneity",
            enters_main=False,
            module=modules["firm_cash_debt_maturity_heterogeneity"],
        )
    )
    assert "existing_main_ratio_paired_safe_yield_offset_and_drag_terms" in (
        _ratewall_main_ratio_inclusion_status(
            name="safe_yield_offset_drag_pairing",
            enters_main=False,
            module=modules["safe_yield_offset_drag_pairing"],
        )
    )
    assert "existing_minor_main_ratio_zero_interest_credit_attenuation_term" in (
        _ratewall_main_ratio_inclusion_status(
            name="bnpl_zero_interest_float",
            enters_main=False,
            module=modules["bnpl_zero_interest_float"],
        )
    )
    assert "optional_pro_forma_amplifier_outside_main_ratio" in (
        _ratewall_main_ratio_inclusion_status(
            name="household_yield_optimization_financialized_balance_sheet",
            enters_main=False,
            module=modules["household_yield_optimization_financialized_balance_sheet"],
        )
    )


def test_higher_rate_channel_registry_separates_cashflow_and_price_channels() -> None:
    rows = {
        row["channel_name"]: row
        for row in _ratewall_higher_rate_channel_registry_rows()
    }

    assert set(rows) == {
        "corporate_net_interest_cashflow_offset",
        "interest_income_tax_clawback_leakage",
        "foreign_treasury_holder_leakage",
        "fast_repricing_consumer_credit_drag",
        "cre_refinancing_bank_exposure_drag",
        "private_credit_ndfi_funding_drag",
        "mortgage_lockin_payment_shield_shelter_sidecar",
        "working_capital_cost_pass_through_pressure",
        "state_local_cash_interest_spendback",
        "pension_insurance_reinvestment_spread",
        "utility_wacc_ratecase_pass_through",
        "bnpl_merchant_fee_price_pass_through",
        "term_structure_pricing_carry_pressure",
    }
    assert set(rows["corporate_net_interest_cashflow_offset"]) == set(
        RATEWALL_HIGHER_RATE_CHANNEL_REGISTRY_FIELDS
    )
    assert (
        rows["corporate_net_interest_cashflow_offset"]["channel_role"]
        == "cashflow_support"
    )
    assert (
        rows["corporate_net_interest_cashflow_offset"]["cashflow_support_channel"]
        == "true"
    )
    assert (
        rows["corporate_net_interest_cashflow_offset"]["enters_main_offset_ratio"]
        == "false"
    )

    assert (
        rows["interest_income_tax_clawback_leakage"][
            "recipient_leakage_wrapper_channel"
        ]
        == "true"
    )
    assert (
        rows["foreign_treasury_holder_leakage"]["recipient_leakage_wrapper_channel"]
        == "true"
    )
    assert (
        rows["fast_repricing_consumer_credit_drag"]["denominator_drag_channel"]
        == "true"
    )
    assert (
        rows["cre_refinancing_bank_exposure_drag"]["denominator_drag_channel"] == "true"
    )
    assert (
        rows["private_credit_ndfi_funding_drag"]["denominator_drag_channel"] == "true"
    )
    assert (
        rows["pension_insurance_reinvestment_spread"]["dynamic_horizon_sidecar_channel"]
        == "true"
    )

    for channel_name in (
        "working_capital_cost_pass_through_pressure",
        "term_structure_pricing_carry_pressure",
        "utility_wacc_ratecase_pass_through",
        "bnpl_merchant_fee_price_pass_through",
    ):
        row = rows[channel_name]
        assert row["channel_role"] == "price_channel_sidecar"
        assert row["price_channel"] == "true"
        assert row["cashflow_support_channel"] == "false"
        assert row["enters_main_offset_ratio"] == "false"
        assert (
            row["main_offset_ratio_role"]
            == "excluded_price_channel_not_cashflow_support"
        )
        assert row["main_offset_ratio_changed_this_tranche"] == "false"
        for switch in (
            "forward_price_output_enabled",
            "commodity_price_forecast_enabled",
            "cpi_forecast_enabled",
            "inflation_forecast_enabled",
            "empirical_threshold_date_enabled",
            "pricing_output_enabled",
            "incidence_claim_enabled",
            "welfare_claim_enabled",
            "tax_output_enabled",
            "mpc_output_enabled",
            "holder_allocation_enabled",
            "reset_calendar_construction_enabled",
            "raw_rate_shock_enabled",
            "causal_financialization_claim_enabled",
        ):
            assert row[switch] == "false"


def test_higher_rate_bridges_are_fail_closed_outside_main_ratio() -> None:
    corporate_rows = _ratewall_corporate_net_interest_cashflow_bridge_rows(snapshots=[])
    working_rows = _ratewall_working_capital_cost_channel_diagnostic_rows(snapshots=[])
    carry_rows = _ratewall_term_structure_pricing_carry_diagnostic_rows(snapshots=[])

    assert len(corporate_rows) == 3
    assert set(corporate_rows[0]) == set(
        RATEWALL_CORPORATE_NET_INTEREST_CASHFLOW_BRIDGE_FIELDS
    )
    assert {row["enters_main_offset_ratio"] for row in corporate_rows} == {"false"}
    assert {
        row["main_offset_ratio_changed_this_tranche"] for row in corporate_rows
    } == {"false"}
    assert {
        row["source_admission_attempted_this_tranche"] for row in corporate_rows
    } == {"true"}
    assert {row["corporate_cashflow_gate_passed"] for row in corporate_rows} == {
        "false"
    }
    assert {row["can_narrow_prior"] for row in corporate_rows} == {"false"}
    assert {row["formula_replacement_allowed"] for row in corporate_rows} == {"false"}
    assert {row["interest_paid_source_status"] for row in corporate_rows} == {
        "registered_fred_z1_candidate_not_in_current_snapshot"
    }
    assert {row["interest_received_source_status"] for row in corporate_rows} == {
        "registered_fred_z1_candidate_not_in_current_snapshot"
    }
    assert {
        "fixed_floating_maturity_refinancing_overlap_snapshot"
        in row["source_admission_result"]
        for row in corporate_rows
    } == {True}
    assert {row["formula_handle_candidate"] for row in corporate_rows} == {
        "corporate_cash_interest_income_offset_share",
        "corporate_debt_refinancing_drag_share",
        "corporate_net_interest_cashflow_offset_share",
    }

    for rows in (working_rows, carry_rows):
        assert rows
        assert set(rows[0]) == set(RATEWALL_PRICE_CHANNEL_DIAGNOSTIC_FIELDS)
        assert {row["channel_role"] for row in rows} == {"price_channel"}
        assert {row["cashflow_support_channel"] for row in rows} == {"false"}
        assert {row["enters_main_offset_ratio"] for row in rows} == {"false"}
        assert {row["main_offset_ratio_changed_this_tranche"] for row in rows} == {
            "false"
        }

    for row in corporate_rows + working_rows + carry_rows:
        for switch in (
            "forward_price_output_enabled",
            "commodity_price_forecast_enabled",
            "cpi_forecast_enabled",
            "inflation_forecast_enabled",
            "empirical_threshold_date_enabled",
            "empirical_claim_enabled",
            "policy_failure_claim_enabled",
            "pricing_output_enabled",
            "incidence_claim_enabled",
            "welfare_claim_enabled",
            "tax_output_enabled",
            "mpc_output_enabled",
            "holder_allocation_enabled",
            "reset_calendar_construction_enabled",
            "raw_rate_shock_enabled",
            "causal_financialization_claim_enabled",
        ):
            assert row[switch] == "false"


def test_corporate_net_interest_paid_received_snapshots_do_not_promote_gate() -> None:
    snapshots = [
        SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id="fred",
                series_id=series_id,
                source_url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
                units="millions_of_dollars",
                frequency="quarterly",
                transform="transactions_context",
                retrieved_at="2026-05-16T00:00:00Z",
                source_release_at="2025-10-01",
            ),
            records=[{"date": "2025-10-01", "value": "1"}],
        )
        for series_id in ("BOGZ1FU106130001Q", "BOGZ1FU106130101Q")
    ]

    rows = _ratewall_corporate_net_interest_cashflow_bridge_rows(snapshots=snapshots)

    assert {row["source_backed_partial_evidence_status"] for row in rows} == {
        "partial_paid_received_snapshot_available_but_gate_still_blocked"
    }
    assert {row["interest_paid_source_status"] for row in rows} == {
        "source_backed_snapshot_available"
    }
    assert {row["interest_received_source_status"] for row in rows} == {
        "source_backed_snapshot_available"
    }
    assert {row["interest_paid_source_record_count"] for row in rows} == {"1"}
    assert {row["interest_received_source_record_count"] for row in rows} == {"1"}
    assert {row["corporate_cashflow_gate_passed"] for row in rows} == {"false"}
    assert {row["can_narrow_prior"] for row in rows} == {"false"}
    assert {row["formula_replacement_allowed"] for row in rows} == {"false"}


def test_corporate_net_interest_stock_context_still_does_not_promote_gate() -> None:
    series_ids = (
        "BOGZ1FU106130001Q",
        "BOGZ1FU106130101Q",
        "NCBCDCA",
        "TSDABSNNCB",
        "TSABSNNCB",
        "BOGZ1FL103034000Q",
        "SRPSABSNNCB",
        "CBLBSNNCB",
        "NCBDBIQ027S",
        "NCBLL",
        "CPLBSNNCB",
    )
    snapshots = [
        SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id="fred",
                series_id=series_id,
                source_url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
                units="millions_of_dollars",
                frequency="quarterly",
                transform="level",
                retrieved_at="2026-05-16T00:00:00Z",
                source_release_at="2025-10-01",
            ),
            records=[{"date": "2025-10-01", "value": "1"}],
        )
        for series_id in series_ids
    ]

    rows = _ratewall_corporate_net_interest_cashflow_bridge_rows(snapshots=snapshots)

    assert {row["source_backed_partial_evidence_status"] for row in rows} == {
        "partial_paid_received_cash_short_asset_and_debt_stock_context_"
        "available_but_gate_still_blocked"
    }
    assert {row["cash_short_asset_source_status"] for row in rows} == {
        "source_backed_z1_cash_short_asset_stock_context_available_no_"
        "cash_income_or_overlap_bridge"
    }
    assert {row["debt_maturity_source_status"] for row in rows} == {
        "source_backed_z1_debt_stock_context_available_but_no_admitted_"
        "fixed_floating_maturity_refinancing_snapshot"
    }
    assert {row["refinancing_drag_source_status"] for row in rows} == {
        "blocked_no_admitted_qfr_compustat_or_public_refinancing_timing_"
        "overlap_artifact"
    }
    assert {row["corporate_cashflow_gate_passed"] for row in rows} == {"false"}
    assert {row["can_narrow_prior"] for row in rows} == {"false"}
    assert {row["formula_replacement_allowed"] for row in rows} == {"false"}


def test_higher_rate_modules_are_registered_without_main_ratio_entry() -> None:
    modules = {
        row["module_name"]: row
        for row in _ratewall_interest_channel_module_registry_rows()
    }

    for module_name in (
        "corporate_net_interest_cashflow_bridge",
        "working_capital_cost_pass_through",
        "term_structure_pricing_carry",
    ):
        assert modules[module_name]["enters_main_offset_ratio"] == "false"
        assert modules[module_name]["promotion_gate"]
        assert modules[module_name]["pricing_output_enabled"] == "false"
        assert modules[module_name]["raw_rate_shock_enabled"] == "false"


def test_dynamic_path_scale_semantics_are_machine_visible() -> None:
    defaults = _dynamic_path_claim_defaults({"defaults": {}})

    assert "not_a_second_rate_path" in defaults["policy_rate_bps_role"]
    assert "not_raw_rate_shock" in defaults["rate_path_bps_year_role"]
    assert (
        "amplitude_times_duration_exposure"
        in defaults["joint_policy_rate_rate_path_guard"]
    )
    for field_name in (
        "policy_rate_bps_role",
        "rate_path_bps_year_role",
        "joint_policy_rate_rate_path_guard",
    ):
        assert field_name in RATEWALL_DYNAMIC_SCENARIO_PATH_FIELDS
        assert field_name in RATEWALL_DYNAMIC_OFFSET_RATIO_PATH_FIELDS
    for field_name in (
        "state_period_frequency",
        "evaluation_horizon",
        "base_safe_asset_allocation_offset_share",
        "tdc_liquidity_effect_offset_bil",
        "tdc_adjusted_safe_asset_allocation_offset_share",
        "crossing_semantics",
    ):
        assert field_name in RATEWALL_DYNAMIC_OFFSET_RATIO_PATH_FIELDS
    for field_name in ("evaluation_horizon", "crossing_semantics"):
        assert field_name in RATEWALL_SCENARIO_CROSSING_DIAGNOSTIC_FIELDS


def test_denominator_response_estimate_gate_metadata_is_machine_visible() -> None:
    for field_name in (
        "shock_admissibility_status",
        "unit_conversion_to_gdp_share_status",
        "robust_uncertainty_status",
        "confidence_interval_status",
        "p_value_status",
        "placebo_pretrend_gate_status",
        "sign_horizon_stability_status",
        "outlier_window_robustness_gate_status",
        "cross_source_replication_status",
        "component_aggregation_status",
        "state_dependence_status",
        "denominator_prior_calibration_grade",
    ):
        assert field_name in RATEWALL_DENOMINATOR_RESPONSE_ESTIMATE_DIAGNOSTIC_FIELDS


def test_denominator_tdsp_window_diagnostics_report_source_boundary_blockers() -> None:
    design = {
        "design_test_diagnostic_id": (
            "denominator_panel_design_test::pretrend_placebo::tdsp_boundary"
        ),
        "panel_value_diagnostic_id": "denominator_event_outcome_value::tdsp_boundary",
        "cell_diagnostic_id": "cell::tdsp_boundary",
        "panel_cell_id": "panel_cell::tdsp_boundary",
        "denominator_component": "conventional_drag_borrowing_cost",
        "horizon_bucket": "10y",
        "horizon_months": "120",
        "shock_source_id": "shock_boundary",
        "shock_frequency": "annual",
        "shock_value_field": "value",
        "shock_units": "percentage_points",
        "outcome_series_id": "TDSP",
        "outcome_frequency": "annual",
        "outcome_units": "percent",
        "design_test_family": "pretrend_placebo",
        "minimum_support_threshold": "2",
        "constructible_event_outcome_cell_count": "2",
        "event_outcome_values_available": "true",
        "promotion_gate": "split denominator remains prototype",
        "source_specific_artifacts": "source_provenance.json",
        "source_specific_series_or_table_ids": "shock_boundary;TDSP",
        "source_specific_urls_or_docs": "official_source_urls",
        "source_specific_citation_or_design_handles": "diagnostic_design",
        "source_specific_evidence_status": "diagnostic_only",
        "source_snapshot_kind_summary": "shock_boundary:fixture;TDSP:fixture",
    }
    snapshots = [
        SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id="fixture",
                series_id="shock_boundary",
                source_url="fixture://shock",
                units="percentage_points",
                frequency="annual",
                transform="level",
                retrieved_at="2026-06-07T00:00:00Z",
                source_release_at="2026-06-07",
            ),
            records=[
                {"date": "2015-01-01", "value": "1"},
                {"date": "2016-01-01", "value": "1"},
            ],
        ),
        SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id="fixture",
                series_id="TDSP",
                source_url="fixture://tdsp",
                units="percent",
                frequency="annual",
                transform="level",
                retrieved_at="2026-06-07T00:00:00Z",
                source_release_at="2026-06-07",
            ),
            records=[
                {"date": f"{year}-01-01", "value": str(year - 1999)}
                for year in range(2000, 2031)
            ],
        ),
    ]

    pretrend_rows = _ratewall_denominator_pretrend_placebo_diagnostic_rows(
        design_rows=[design],
        snapshots=snapshots,
    )

    assert set(pretrend_rows[0]) == set(
        RATEWALL_DENOMINATOR_PRETREND_PLACEBO_DIAGNOSTIC_FIELDS
    )
    assert pretrend_rows[0]["pretrend_window_support_count"] == "2"
    assert pretrend_rows[0]["placebo_window_support_count"] == "0"
    assert pretrend_rows[0]["outcome_first_date"] == "2000-01-01"
    assert pretrend_rows[0]["earliest_required_placebo_start_date"] == "1995-01-01"
    assert pretrend_rows[0]["pretrend_placebo_support_boundary_status"] == (
        "blocked_placebo_window_requires_pre_source_history"
    )
    assert pretrend_rows[0]["pretrend_placebo_available"] == "false"
    assert pretrend_rows[0]["prior_narrowing_allowed"] == "false"

    outlier_design = {
        **design,
        "design_test_diagnostic_id": (
            "denominator_panel_design_test::outlier_window_robustness::tdsp_boundary"
        ),
        "design_test_family": "outlier_window_robustness",
    }
    outlier_rows = _ratewall_denominator_outlier_window_robustness_diagnostic_rows(
        design_rows=[outlier_design],
        snapshots=snapshots,
    )

    assert set(outlier_rows[0]) == set(
        RATEWALL_DENOMINATOR_OUTLIER_WINDOW_ROBUSTNESS_DIAGNOSTIC_FIELDS
    )
    assert outlier_rows[0]["base_window_support_count"] == "2"
    assert outlier_rows[0]["long_window_months"] == "240"
    assert outlier_rows[0]["long_window_support_count"] == "0"
    assert outlier_rows[0]["missing_long_window_support_count"] == "2"
    assert outlier_rows[0]["outcome_last_date"] == "2030-01-01"
    assert outlier_rows[0]["latest_required_long_window_future_date"] == "2036-01-01"
    assert outlier_rows[0]["outlier_window_support_boundary_status"] == (
        "blocked_long_window_extends_beyond_source_end"
    )
    assert outlier_rows[0]["outlier_window_robustness_available"] == "false"
    assert outlier_rows[0]["prior_narrowing_allowed"] == "false"


def test_tdsp_supported_horizon_response_profile_stays_diagnostic_only() -> None:
    base = {
        "denominator_component": "conventional_drag_borrowing_cost",
        "outcome_series_id": "TDSP",
        "outcome_frequency": "quarterly",
        "outcome_units": "percent",
        "shock_frequency": "event",
        "shock_value_field": "value",
        "shock_units": "percentage_points",
        "source_specific_artifacts": "source_provenance.json",
        "source_specific_series_or_table_ids": "TDSP;shock",
        "source_specific_urls_or_docs": "official_source_urls",
        "source_specific_citation_or_design_handles": "diagnostic_design",
        "source_specific_evidence_status": "diagnostic_only",
        "source_snapshot_kind_summary": "fixture",
    }
    rows = _ratewall_tdsp_supported_horizon_response_profile_rows(
        [
            {
                **base,
                "horizon_bucket": "1y",
                "horizon_months": "12",
                "shock_source_id": "fed_brw_monetary_policy_shocks",
                "response_estimate_available": "true",
                "usable_observation_count": "100",
                "response_coefficient": "1.5",
                "response_t_statistic": "2.0",
            },
            {
                **base,
                "horizon_bucket": "1y",
                "horizon_months": "12",
                "shock_source_id": "sf_fed_monetary_policy_surprises",
                "response_estimate_available": "true",
                "usable_observation_count": "50",
                "response_coefficient": "0.5",
                "response_t_statistic": "1.0",
            },
            {
                **base,
                "horizon_bucket": "1y",
                "horizon_months": "12",
                "shock_source_id": "romer_romer_2004",
                "response_estimate_available": "false",
                "usable_observation_count": "0",
                "formal_response_estimate_decision": (
                    "blocked_missing_formal_diagnostic_objects"
                ),
            },
            {
                **base,
                "horizon_bucket": "10y",
                "horizon_months": "120",
                "shock_source_id": "fed_brw_monetary_policy_shocks",
                "response_estimate_available": "false",
                "usable_observation_count": "30",
                "formal_response_estimate_decision": (
                    "blocked_missing_formal_diagnostic_objects"
                ),
            },
        ]
    )

    assert {row["horizon_bucket"] for row in rows} == {"1y", "10y"}
    assert all(
        set(row) == set(RATEWALL_TDSP_SUPPORTED_HORIZON_RESPONSE_PROFILE_FIELDS)
        for row in rows
    )
    by_horizon = {row["horizon_bucket"]: row for row in rows}
    assert by_horizon["1y"]["available_response_source_count"] == "2"
    assert by_horizon["1y"]["response_coefficient_min"] == "0.5"
    assert by_horizon["1y"]["response_coefficient_max"] == "1.5"
    assert by_horizon["1y"]["response_sign_pattern"] == "all_available_sources_positive"
    assert by_horizon["1y"]["supported_horizon_profile_decision"] == (
        "usable_as_supported_horizon_diagnostic_evidence_not_10y_prior"
    )
    assert by_horizon["10y"]["available_response_source_count"] == "0"
    assert by_horizon["10y"]["ten_year_admissibility_status"] == (
        "blocked_10y_pretrend_placebo_and_long_window_robustness_support"
    )
    for row in rows:
        assert row["prior_narrowing_allowed"] == "false"
        assert row["split_denominator_promotion_allowed"] == "false"
        assert row["formula_replacement_allowed"] == "false"
        assert row["raw_rate_shock_enabled"] == "false"


def test_formal_denominator_diagnostic_runner_stays_nonpromotional() -> None:
    scaffold = {
        "formal_design_test_result_scaffold_id": "scaffold::x",
        "denominator_design_readiness_decision_id": "decision::x",
        "panel_value_diagnostic_id": "panel::x",
        "cell_diagnostic_id": "cell::x",
        "panel_cell_id": "panel_cell::x",
        "denominator_component": "conventional_drag_credit_supply",
        "horizon_bucket": "1y",
        "horizon_months": "12",
        "shock_source_id": "fed_brw_monetary_policy_shocks",
        "shock_frequency": "monthly_and_fomc_event",
        "shock_value_field": "monthly_shock_pctpt",
        "shock_units": "percentage_points",
        "outcome_series_id": "BUSLOANS",
        "outcome_frequency": "weekly",
        "outcome_units": "billions_of_dollars",
        "formal_runner_eligible": "true",
        "formal_result_blocker": "",
        "missing_diagnostic_families": "",
        "evidence_needed_before_prior_narrowing": (
            "registered response estimate and non-promotion review"
        ),
        "evidence_needed_before_promotion": (
            "source-backed denominator evidence and non-promotion review"
        ),
        "promotion_gate": "split denominator remains prototype",
        "source_specific_artifacts": "source_provenance.json",
        "source_specific_series_or_table_ids": (
            "fed_brw_monetary_policy_shocks;BUSLOANS"
        ),
        "source_specific_urls_or_docs": "official_source_urls",
        "source_specific_citation_or_design_handles": (
            "admissible_shock_denominator_design"
        ),
        "source_specific_evidence_status": "diagnostic_only",
        "source_snapshot_kind_summary": "fed_brw_monetary_policy_shocks:live",
    }

    rows = _ratewall_denominator_formal_design_test_result_rows(
        scaffold_rows=[scaffold],
        panel_value_rows=[
            {
                "panel_value_diagnostic_id": "panel::x",
                "constructible_event_outcome_cell_count": "42",
                "first_event_date": "2000-01-01",
                "first_baseline_outcome_date": "1999-12-01",
                "first_future_outcome_date": "2000-12-01",
                "last_event_date": "2020-01-01",
                "last_baseline_outcome_date": "2019-12-01",
                "last_future_outcome_date": "2020-12-01",
            }
        ],
        pretrend_placebo_rows=[
            {
                "panel_value_diagnostic_id": "panel::x",
                "pretrend_window_support_count": "42",
                "placebo_window_support_count": "42",
                "pretrend_mean_transformed_change": "1.0",
                "placebo_mean_transformed_change": "0.5",
                "diagnostic_status": "pretrend_placebo_statistics_available_diagnostic_only",
            }
        ],
        shock_relevance_rows=[
            {
                "panel_value_diagnostic_id": "panel::x",
                "nonzero_shock_count": "40",
                "shock_mean": "0.01",
                "shock_stddev": "0.02",
                "shock_min": "-0.03",
                "shock_max": "0.04",
                "diagnostic_status": "shock_relevance_statistics_available_diagnostic_only",
            }
        ],
        sign_consistency_rows=[
            {
                "panel_value_diagnostic_id": "panel::x",
                "expected_directional_check": "higher_outcome_is_tightening_drag",
                "classified_direction_count": "42",
                "direction_match_count": "30",
                "direction_mismatch_count": "12",
                "direction_match_share": "0.7142857143",
                "diagnostic_status": "sign_consistency_statistics_available_diagnostic_only",
            }
        ],
        horizon_sensitivity_rows=[
            {
                "panel_value_diagnostic_id": "panel::x",
                "horizon_peer_available_count": "5",
                "horizon_peer_supported_count": "5",
                "current_horizon_mean_transformed_change": "1.0",
                "peer_mean_range_transformed_change": "0.7",
                "diagnostic_status": "horizon_sensitivity_statistics_available_diagnostic_only",
            }
        ],
        outlier_window_robustness_rows=[
            {
                "panel_value_diagnostic_id": "panel::x",
                "base_window_support_count": "42",
                "base_mean_transformed_change": "1.0",
                "base_stddev_transformed_change": "0.4",
                "base_outlier_count_two_stddev": "2",
                "leave_one_out_mean_range": "0.1",
                "diagnostic_status": "outlier_window_statistics_available_diagnostic_only",
            }
        ],
    )
    assert set(rows[0]) == set(RATEWALL_DENOMINATOR_FORMAL_DESIGN_TEST_RESULT_FIELDS)
    assert rows[0]["formal_runner_executed"] == "true"
    assert rows[0]["formal_diagnostic_result_available"] == "true"
    assert rows[0]["formal_response_diagnostic_object_available"] == "true"
    assert rows[0]["event_outcome_support_count"] == "42"
    assert "pretrend_mean=1.0" in rows[0]["pretrend_placebo_statistic_summary"]
    assert "nonzero_shocks=40" in rows[0]["shock_relevance_statistic_summary"]
    assert "matches=30" in rows[0]["sign_consistency_statistic_summary"]
    assert "peer_count=5" in rows[0]["horizon_sensitivity_statistic_summary"]
    assert "outliers_2sd=2" in rows[0]["outlier_window_robustness_statistic_summary"]
    assert rows[0]["response_estimate_available"] == "false"
    assert rows[0]["response_estimate_used_for_prior"] == "false"
    assert rows[0]["formal_test_result_available"] == "false"
    assert rows[0]["test_result_available"] == "false"
    assert rows[0]["prior_narrowing_allowed"] == "false"
    assert rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rows[0]["formula_replacement_allowed"] == "false"
    assert rows[0]["main_offset_ratio_changed_this_tranche"] == "false"
    assert rows[0]["raw_rate_shock_enabled"] == "false"


def test_denominator_formal_and_cross_source_rows_preserve_partial_family_status() -> None:
    scaffold = {
        "formal_design_test_result_scaffold_id": "scaffold::tdsp_10y",
        "denominator_design_readiness_decision_id": "readiness::tdsp_10y",
        "panel_value_diagnostic_id": "panel::tdsp_10y",
        "cell_diagnostic_id": "cell::tdsp",
        "panel_cell_id": "panel_cell::tdsp",
        "denominator_component": "conventional_drag_borrowing_cost",
        "horizon_bucket": "10y",
        "horizon_months": "120",
        "shock_source_id": "fed_brw_monetary_policy_shocks",
        "shock_frequency": "monthly_and_fomc_event",
        "shock_value_field": "monthly_shock_pctpt",
        "shock_units": "percentage_points",
        "outcome_series_id": "TDSP",
        "outcome_frequency": "quarterly",
        "outcome_units": "percent",
        "all_required_diagnostics_available": "false",
        "diagnostic_family_available_count": "3",
        "missing_diagnostic_families": "pretrend_placebo;outlier_window_robustness",
        "formal_runner_eligible": "false",
        "formal_result_blocker": (
            "Missing required diagnostic families: "
            "pretrend_placebo;outlier_window_robustness"
        ),
        "evidence_needed_before_prior_narrowing": "keep blocked",
        "evidence_needed_before_promotion": "keep blocked",
        "promotion_gate": "split denominator remains prototype",
        "next_backend_action": "fill_missing_denominator_design_diagnostic_families",
        "source_specific_artifacts": "source_provenance.json",
        "source_specific_series_or_table_ids": "fed_brw_monetary_policy_shocks;TDSP",
        "source_specific_urls_or_docs": "official_source_urls",
        "source_specific_citation_or_design_handles": "diagnostic_design",
        "source_specific_evidence_status": "diagnostic_only",
        "source_snapshot_kind_summary": "fed_brw_monetary_policy_shocks:live",
    }

    formal_rows = _ratewall_denominator_formal_design_test_result_rows(
        scaffold_rows=[scaffold],
        panel_value_rows=[
            {
                "panel_value_diagnostic_id": "panel::tdsp_10y",
                "constructible_event_outcome_cell_count": "130",
            }
        ],
        pretrend_placebo_rows=[
            {
                "panel_value_diagnostic_id": "panel::tdsp_10y",
                "pretrend_placebo_available": "false",
                "diagnostic_status": "blocked_insufficient_pretrend_or_placebo_support",
            }
        ],
        shock_relevance_rows=[
            {
                "panel_value_diagnostic_id": "panel::tdsp_10y",
                "shock_relevance_available": "true",
                "diagnostic_status": "shock_relevance_statistics_available_diagnostic_only",
            }
        ],
        sign_consistency_rows=[
            {
                "panel_value_diagnostic_id": "panel::tdsp_10y",
                "sign_check_available": "true",
                "diagnostic_status": "sign_consistency_statistics_available_diagnostic_only",
            }
        ],
        horizon_sensitivity_rows=[
            {
                "panel_value_diagnostic_id": "panel::tdsp_10y",
                "horizon_sensitivity_available": "true",
                "diagnostic_status": "horizon_sensitivity_statistics_available_diagnostic_only",
            }
        ],
        outlier_window_robustness_rows=[
            {
                "panel_value_diagnostic_id": "panel::tdsp_10y",
                "outlier_window_robustness_available": "false",
                "diagnostic_status": "outlier_window_statistics_blocked",
            }
        ],
    )

    formal = formal_rows[0]
    assert formal["formal_diagnostic_result_available"] == "false"
    assert (
        formal["formal_pretrend_placebo_result"]
        == "blocked_missing_required_diagnostic_family"
    )
    assert (
        formal["formal_shock_relevance_result"]
        == "support_qualified_diagnostic_family_available"
    )
    assert (
        formal["formal_sign_consistency_result"]
        == "support_qualified_diagnostic_family_available"
    )
    assert (
        formal["formal_horizon_sensitivity_result"]
        == "support_qualified_diagnostic_family_available"
    )
    assert (
        formal["formal_outlier_window_robustness_result"]
        == "blocked_missing_required_diagnostic_family"
    )

    response = {
        "response_estimate_diagnostic_id": "denominator_response_estimate_diagnostic::tdsp_10y",
        "formal_design_test_result_id": formal["formal_design_test_result_id"],
        "panel_value_diagnostic_id": "panel::tdsp_10y",
        "cell_diagnostic_id": "cell::tdsp",
        "panel_cell_id": "panel_cell::tdsp",
        "denominator_component": "conventional_drag_borrowing_cost",
        "horizon_bucket": "10y",
        "horizon_months": "120",
        "shock_source_id": "fed_brw_monetary_policy_shocks",
        "shock_frequency": "monthly_and_fomc_event",
        "shock_value_field": "monthly_shock_pctpt",
        "shock_units": "percentage_points",
        "outcome_series_id": "TDSP",
        "outcome_frequency": "quarterly",
        "outcome_units": "percent",
        "response_estimate_available": "false",
        "response_estimate_used_for_prior": "false",
        "formal_test_result_available": "false",
        "test_result_available": "false",
        "test_passed": "false",
        "prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_offset_ratio_changed_this_tranche": "false",
        "aggregate_assumption_behavior_preserved": "true",
        "promotion_gate": "split denominator remains prototype",
        "source_specific_artifacts": "source_provenance.json",
        "source_specific_series_or_table_ids": "fed_brw_monetary_policy_shocks;TDSP",
        "source_specific_urls_or_docs": "official_source_urls",
        "source_specific_citation_or_design_handles": "diagnostic_design",
        "source_specific_evidence_status": "diagnostic_only",
        "source_snapshot_kind_summary": "fed_brw_monetary_policy_shocks:live",
        **_disabled_claim_switches(),
    }

    cross_rows = _ratewall_denominator_cross_source_design_validation_rows(
        formal_result_rows=formal_rows,
        response_estimate_rows=[response],
    )

    assert cross_rows[0]["diagnostic_family_available_count"] == "3"
    assert cross_rows[0]["missing_or_blocked_diagnostic_families"] == (
        "pretrend_placebo;outlier_window_robustness"
    )
    assert (
        "shock_relevance" not in cross_rows[0]["missing_or_blocked_diagnostic_families"]
    )
    assert "formal_diagnostic_result_unavailable" in cross_rows[0]["exact_blocker"]


def test_denominator_cross_source_design_validation_stays_fail_closed() -> None:
    formal = {
        "formal_design_test_result_id": "formal::x",
        "panel_value_diagnostic_id": "panel::x",
        "cell_diagnostic_id": "cell::x",
        "panel_cell_id": "panel_cell::x",
        "denominator_component": "conventional_drag_credit_supply",
        "horizon_bucket": "1y",
        "horizon_months": "12",
        "shock_source_id": "fed_brw_monetary_policy_shocks",
        "shock_frequency": "monthly_and_fomc_event",
        "shock_value_field": "monthly_shock_pctpt",
        "shock_units": "percentage_points",
        "outcome_series_id": "BUSLOANS",
        "outcome_frequency": "weekly",
        "outcome_units": "billions_of_dollars",
        "formal_diagnostic_result_available": "true",
        "formal_pretrend_placebo_result": "support_qualified_diagnostic_family_available",
        "formal_shock_relevance_result": "support_qualified_diagnostic_family_available",
        "formal_sign_consistency_result": "support_qualified_diagnostic_family_available",
        "formal_horizon_sensitivity_result": "support_qualified_diagnostic_family_available",
        "formal_outlier_window_robustness_result": (
            "support_qualified_diagnostic_family_available"
        ),
    }
    response = {
        "response_estimate_diagnostic_id": "denominator_response_estimate_diagnostic::x",
        "formal_design_test_result_id": "formal::x",
        "panel_value_diagnostic_id": "panel::x",
        "cell_diagnostic_id": "cell::x",
        "panel_cell_id": "panel_cell::x",
        "denominator_component": "conventional_drag_credit_supply",
        "horizon_bucket": "1y",
        "horizon_months": "12",
        "shock_source_id": "fed_brw_monetary_policy_shocks",
        "shock_frequency": "monthly_and_fomc_event",
        "shock_value_field": "monthly_shock_pctpt",
        "shock_units": "percentage_points",
        "outcome_series_id": "BUSLOANS",
        "outcome_frequency": "weekly",
        "outcome_units": "billions_of_dollars",
        "response_estimate_available": "true",
        "response_estimate_used_for_prior": "false",
        "formal_test_result_available": "false",
        "test_result_available": "false",
        "test_passed": "false",
        "prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_offset_ratio_changed_this_tranche": "false",
        "aggregate_assumption_behavior_preserved": "true",
        "promotion_gate": "no promotion without independent validation",
        "source_specific_artifacts": "source_provenance.json",
        "source_specific_series_or_table_ids": (
            "fed_brw_monetary_policy_shocks;BUSLOANS"
        ),
        "source_specific_urls_or_docs": "official_source_urls",
        "source_specific_citation_or_design_handles": (
            "admissible_shock_denominator_design"
        ),
        "source_specific_evidence_status": "diagnostic_only",
        "source_snapshot_kind_summary": "fed_brw_monetary_policy_shocks:live",
        **_disabled_claim_switches(),
    }

    rows = _ratewall_denominator_cross_source_design_validation_rows(
        formal_result_rows=[formal],
        response_estimate_rows=[response],
    )

    assert set(rows[0]) == set(
        RATEWALL_DENOMINATOR_CROSS_SOURCE_DESIGN_VALIDATION_FIELDS
    )
    assert rows[0]["cell_validation_status"] == "blocked"
    assert rows[0]["chain_key_alignment_status"] == "pass"
    assert rows[0]["diagnostic_family_alignment_status"] == "pass"
    assert rows[0]["formal_response_alignment_status"] == "pass"
    assert rows[0]["promotion_switch_lock_status"] == "pass"
    assert (
        rows[0]["cross_source_replication_validation_status"]
        == "blocked_no_second_independent_consistent_source_design"
    )
    assert rows[0]["peer_consistent_source_count"] == "1"
    assert rows[0]["prior_narrowing_allowed"] == "false"
    assert rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rows[0]["formula_replacement_allowed"] == "false"
    assert rows[0]["main_offset_ratio_changed_this_tranche"] == "false"
    assert rows[0]["raw_rate_shock_enabled"] == "false"

    requirement_rows = (
        _ratewall_denominator_evidence_upgrade_source_design_requirement_rows(rows)
    )

    assert set(requirement_rows[0]) == set(
        RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_SOURCE_DESIGN_REQUIREMENT_FIELDS
    )
    assert requirement_rows[0]["denominator_component"] == (
        "conventional_drag_credit_supply"
    )
    assert requirement_rows[0]["horizon_bucket"] == "1y"
    assert requirement_rows[0]["outcome_series_id"] == "BUSLOANS"
    assert requirement_rows[0]["blocked_validation_cell_count"] == "1"
    assert requirement_rows[0]["additional_peer_source_designs_required"] == "1"
    assert "missing_second_independent_consistent_source_design" in (
        requirement_rows[0]["missing_source_or_design_evidence"]
    )
    assert requirement_rows[0]["requirement_status"] == (
        "blocked_diagnostic_only_evidence_upgrade_required"
    )
    assert requirement_rows[0]["enters_main_ratio"] == "false"
    assert requirement_rows[0]["evidence_mode_enabled"] == "false"
    assert requirement_rows[0]["canonical_ratio_entry"] == "false"
    assert requirement_rows[0]["prior_narrowing_allowed"] == "false"
    assert requirement_rows[0]["split_denominator_promotion_allowed"] == "false"
    assert requirement_rows[0]["formula_replacement_allowed"] == "false"
    assert requirement_rows[0]["main_offset_ratio_changed_this_tranche"] == "false"
    assert requirement_rows[0]["raw_rate_shock_enabled"] == "false"

    priority_rows = _ratewall_denominator_evidence_upgrade_priority_queue_rows(
        requirement_rows
    )

    assert set(priority_rows[0]) == set(
        RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_PRIORITY_QUEUE_FIELDS
    )
    assert priority_rows[0]["priority_rank"] == "1"
    assert priority_rows[0]["priority_surface_status"] == (
        "blocked_diagnostic_only_priority_queue"
    )
    assert priority_rows[0]["primary_blocker_type"] == (
        "missing_second_independent_consistent_source_design"
    )
    assert priority_rows[0]["affected_cross_source_design_validation_ids"] == (
        "denominator_cross_source_design_validation::x"
    )
    assert priority_rows[0]["chain_key_alignment_status_summary"] == "pass:1"
    assert priority_rows[0]["formal_response_alignment_status_summary"] == "pass:1"
    assert (
        priority_rows[0]["cross_source_replication_validation_status_summary"]
        == "blocked_no_second_independent_consistent_source_design:1"
    )
    assert int(priority_rows[0]["priority_score"]) > 0
    assert priority_rows[0]["enters_main_ratio"] == "false"
    assert priority_rows[0]["evidence_mode_enabled"] == "false"
    assert priority_rows[0]["canonical_ratio_entry"] == "false"
    assert priority_rows[0]["prior_narrowing_allowed"] == "false"
    assert priority_rows[0]["split_denominator_promotion_allowed"] == "false"
    assert priority_rows[0]["formula_replacement_allowed"] == "false"
    assert priority_rows[0]["main_offset_ratio_changed_this_tranche"] == "false"
    assert priority_rows[0]["raw_rate_shock_enabled"] == "false"

    workplan_rows = _ratewall_denominator_evidence_upgrade_tier1_workplan_rows(
        priority_rows
    )

    assert set(workplan_rows[0]) == set(
        RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_TIER1_WORKPLAN_FIELDS
    )
    assert workplan_rows[0]["source_priority_rank"] == "1"
    assert workplan_rows[0]["source_priority_bucket"] == (
        "tier_1_highest_review_priority"
    )
    assert workplan_rows[0]["workplan_surface_status"] == (
        "blocked_diagnostic_only_tier1_workplan"
    )
    assert "resolve_missing_evidence=" in workplan_rows[0][
        "missing_evidence_contract"
    ]
    assert "no_candidate_source_is_admitted" in workplan_rows[0][
        "candidate_peer_source_design_requirement"
    ]
    assert "remain_blocked_unless" in workplan_rows[0][
        "fail_closed_admission_gate"
    ]
    assert workplan_rows[0]["linked_cross_source_design_validation_ids"] == (
        "denominator_cross_source_design_validation::x"
    )
    assert workplan_rows[0]["linked_chain_key_alignment_status_summary"] == "pass:1"
    assert workplan_rows[0]["linked_formal_response_alignment_status_summary"] == (
        "pass:1"
    )
    assert workplan_rows[0]["source_design_execution_status"] == (
        "current_source_design_inputs_linked_but_promotion_evidence_incomplete"
    )
    assert "linked_cross_source_replication_status=" in workplan_rows[0][
        "source_design_execution_blocker"
    ]
    assert workplan_rows[0]["enters_main_ratio"] == "false"
    assert workplan_rows[0]["evidence_mode_enabled"] == "false"
    assert workplan_rows[0]["canonical_ratio_entry"] == "false"
    assert workplan_rows[0]["prior_narrowing_allowed"] == "false"
    assert workplan_rows[0]["split_denominator_promotion_allowed"] == "false"
    assert workplan_rows[0]["formula_replacement_allowed"] == "false"
    assert workplan_rows[0]["main_offset_ratio_changed_this_tranche"] == "false"
    assert workplan_rows[0]["raw_rate_shock_enabled"] == "false"

    matrix_rows = (
        _ratewall_denominator_evidence_upgrade_blocker_resolution_matrix_rows(
            workplan_rows
        )
    )

    assert set(matrix_rows[0]) == set(
        RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_BLOCKER_RESOLUTION_MATRIX_FIELDS
    )
    assert {
        "missing_evidence_contract_item",
        "diagnostic_family_repair_item",
        "candidate_peer_source_design_prerequisite",
        "provenance_prerequisite",
        "fail_closed_admission_status",
    }.issubset({row["resolution_category"] for row in matrix_rows})
    assert matrix_rows[0]["source_tier1_workplan_id"] == workplan_rows[0][
        "tier1_workplan_id"
    ]
    assert matrix_rows[0]["admission_gate_status"] == "blocked_no_source_admission"
    assert matrix_rows[0]["resolution_surface_status"] == (
        "blocked_diagnostic_only_blocker_resolution_matrix"
    )
    assert matrix_rows[0]["enters_main_ratio"] == "false"
    assert matrix_rows[0]["evidence_mode_enabled"] == "false"
    assert matrix_rows[0]["canonical_ratio_entry"] == "false"
    assert matrix_rows[0]["prior_narrowing_allowed"] == "false"
    assert matrix_rows[0]["split_denominator_promotion_allowed"] == "false"
    assert matrix_rows[0]["formula_replacement_allowed"] == "false"
    assert matrix_rows[0]["main_offset_ratio_changed_this_tranche"] == "false"
    assert matrix_rows[0]["raw_rate_shock_enabled"] == "false"

    rollup_rows = (
        _ratewall_denominator_evidence_upgrade_blocker_status_rollup_rows(
            matrix_rows
        )
    )

    assert set(rollup_rows[0]) == set(
        RATEWALL_DENOMINATOR_EVIDENCE_UPGRADE_BLOCKER_STATUS_ROLLUP_FIELDS
    )
    assert rollup_rows[0]["source_tier1_workplan_id"] == workplan_rows[0][
        "tier1_workplan_id"
    ]
    assert rollup_rows[0]["resolution_category"] == (
        "missing_evidence_contract_item"
    )
    assert int(rollup_rows[0]["blocker_item_count"]) > 0
    assert rollup_rows[0]["unresolved_item_count"] == rollup_rows[0][
        "blocker_item_count"
    ]
    assert rollup_rows[0]["required_action_coverage_status"] == (
        "all_required_actions_populated"
    )
    assert rollup_rows[0]["admission_gate_status"] == "blocked_no_source_admission"
    assert rollup_rows[0]["rollup_surface_status"] == (
        "blocked_diagnostic_only_blocker_status_rollup"
    )
    assert rollup_rows[0]["enters_main_ratio"] == "false"
    assert rollup_rows[0]["evidence_mode_enabled"] == "false"
    assert rollup_rows[0]["canonical_ratio_entry"] == "false"
    assert rollup_rows[0]["prior_narrowing_allowed"] == "false"
    assert rollup_rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rollup_rows[0]["formula_replacement_allowed"] == "false"
    assert rollup_rows[0]["main_offset_ratio_changed_this_tranche"] == "false"
    assert rollup_rows[0]["raw_rate_shock_enabled"] == "false"

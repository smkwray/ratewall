from __future__ import annotations

from pathlib import Path

from ratewall.databook.realized_safe_yield_income import (
    CONSTRUCTED_SAFE_YIELD_DIAGNOSTIC_FIELDS,
    DEPOSIT_FALLBACK_RATE_SERIES,
    DEPOSIT_SAFE_YIELD_FALLBACK_BASIS_FIELDS,
    DEPOSIT_PAYER_FLOW_CANDIDATE_FIELDS,
    REALIZED_SAFE_YIELD_AUDIT_FIELDS,
    REALIZED_SAFE_YIELD_BOUNDED_SENSITIVITY_FIELDS,
    SAFE_YIELD_PAYER_FLOW_ADMISSION_FIELDS,
    SAFE_YIELD_GAP_FIELDS,
    SAFE_YIELD_LANE_DECISION_FIELDS,
    SAFE_YIELD_SOURCE_INVENTORY_FIELDS,
    constructed_safe_yield_flow_diagnostic_rows,
    deposit_safe_yield_fallback_basis_rows,
    deposit_interest_payer_flow_candidate_rows,
    realized_safe_yield_bounded_sensitivity_rows,
    realized_safe_yield_audit_rows,
    realized_safe_yield_gap_rows,
    realized_safe_yield_lane_decision_rows,
    realized_safe_yield_payer_flow_admission_rows,
    realized_safe_yield_source_inventory_rows,
    write_realized_safe_yield_outputs,
)


def test_realized_safe_yield_inventory_and_decision_fail_closed(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "sec_nmfp").mkdir()
    (raw / "sec_nmfp/latest_nmfp.zip").write_bytes(b"placeholder")

    inventory = realized_safe_yield_source_inventory_rows(raw_dir=raw)
    decision = realized_safe_yield_lane_decision_rows(inventory)

    assert {field for row in inventory for field in row} == set(
        SAFE_YIELD_SOURCE_INVENTORY_FIELDS
    )
    assert {field for row in decision for field in row} == set(
        SAFE_YIELD_LANE_DECISION_FIELDS
    )
    by_candidate = {row["candidate_id"]: row for row in inventory}
    assert by_candidate["deposit_payer_flow_fdic_ffiec"][
        "admission_status"
    ] == "missing_required_source"
    assert by_candidate["mmf_holdings_sec_nmfp"]["admission_status"] == (
        "diagnostic_context_constructed_flow"
    )
    assert by_candidate["raw_safe_asset_stocks"]["admission_status"] == (
        "stock_context_only"
    )
    assert decision[0]["decision"] == (
        "deposit_required_bounded_noncentral_now_source_backed_candidate_later"
    )
    assert decision[0]["central_forecast_addition_bil"] == "0"
    assert decision[0]["central_current_benchmark_addition_bil"] == "0"
    assert decision[0]["deposit_candidate_status"] == (
        "bounded_noncentral_fallback_required_until_payer_flow_sources_pass"
    )


def test_deposit_candidate_and_diagnostics_have_no_central_effect(
    tmp_path: Path,
) -> None:
    inventory = realized_safe_yield_source_inventory_rows(raw_dir=tmp_path / "raw")
    decision = realized_safe_yield_lane_decision_rows(inventory)
    deposit = deposit_interest_payer_flow_candidate_rows(inventory)
    admission = realized_safe_yield_payer_flow_admission_rows(
        inventory,
        deposit,
        raw_dir=tmp_path / "raw",
        current_overlay_dir=tmp_path / "current",
    )
    diagnostic = constructed_safe_yield_flow_diagnostic_rows()
    gap = realized_safe_yield_gap_rows()
    audit = realized_safe_yield_audit_rows(
        decision_rows=decision,
        deposit_rows=deposit,
        admission_rows=admission,
        diagnostic_rows=diagnostic,
        gap_rows=gap,
    )

    assert {field for row in deposit for field in row} == set(
        DEPOSIT_PAYER_FLOW_CANDIDATE_FIELDS
    )
    assert {field for row in admission for field in row} == set(
        SAFE_YIELD_PAYER_FLOW_ADMISSION_FIELDS
    )
    assert {field for row in diagnostic for field in row} == set(
        CONSTRUCTED_SAFE_YIELD_DIAGNOSTIC_FIELDS
    )
    assert {field for row in gap for field in row} == set(SAFE_YIELD_GAP_FIELDS)
    assert {field for row in audit for field in row} == set(
        REALIZED_SAFE_YIELD_AUDIT_FIELDS
    )
    assert deposit[0]["overlap_guard_id"] == "bank_first_vs_recipient_flow_xor"
    assert deposit[0]["demand_support_bil"] == "0"
    assert admission[0]["all_required_gates_pass"] == "false"
    assert admission[0]["object_role"] == "blocked_source_or_method"
    assert admission[0]["central_n_delta_bil_allowed"] == "false"
    assert admission[0]["central_n_delta_bil"] == "0"
    assert admission[0]["period_cashflow_gate"] == (
        "blocked_missing_fdic_ffiec_or_ncua_payer_flow"
    )
    assert admission[0]["tax_timing_gate"] == (
        "pass_approved_leakage_handles_available_0_08_0_18_0_30"
    )
    assert admission[0]["demand_conversion_gate"] == (
        "pass_approved_current_spend_handles_available_0_04_0_08_0_13"
    )
    assert admission[0]["denominator_alignment_gate"] == (
        "blocked_missing_current_D_reference"
    )
    assert all(row["central_n_delta_bil_allowed"] == "false" for row in diagnostic)
    assert all(row["object_role"] == "diagnostic_context" for row in diagnostic)
    assert gap[0]["surface_role"] == "bounded_noncentral_reopen_lane"
    assert gap[0]["object_role"] == "blocked_source_or_method"
    assert gap[0]["build_status"] == (
        "D1_required_route_bounded_fallback_now_source_backed_central_candidate_later"
    )
    assert {row["check_status"] for row in audit} == {"pass"}


def test_context_sources_do_not_unlock_safe_yield_admission(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    current = tmp_path / "current"
    (
        raw
        / "current_demand_gdp_share/fspdp_official_component_sources/fred_csv"
    ).mkdir(parents=True)
    (raw / "irs_soi").mkdir(parents=True)
    (raw / "fdic_bank_margin_distribution").mkdir(parents=True)
    current.mkdir()
    (
        raw
        / "current_demand_gdp_share/fspdp_official_component_sources/fred_csv/"
        "A064RC1Q027SBEA.csv"
    ).write_text("observation_date,A064RC1Q027SBEA\n2024-01-01,1\n")
    (
        raw
        / "current_demand_gdp_share/fspdp_official_component_sources/fred_csv/"
        "Y001RC1Q027SBEA.csv"
    ).write_text("observation_date,Y001RC1Q027SBEA\n2024-01-01,1\n")
    (raw / "irs_soi/irs_soi_2023_table_1_4_taxable_interest.csv").write_text(
        "date,taxable_interest_amount_thousand_usd\n2023-01-01,1\n"
    )
    (
        raw
        / "fdic_bank_margin_distribution/fdic_bank_margin_distribution_panel.csv"
    ).write_text("quarter,retention_share_proxy\n2024Q1,0.1\n")
    (current / "ratewall_current_assumption_benchmark.csv").write_text(
        "forecast_year,benchmark_id,benchmark_numerator_bil,fixed_D_bil,"
        "benchmark_ratewall_ratio,selected_current_row\n"
        "2026,current_assumption_benchmark,83,247,0.336,true\n"
    )

    inventory = realized_safe_yield_source_inventory_rows(raw_dir=raw)
    by_candidate = {row["candidate_id"]: row for row in inventory}
    assert by_candidate["bea_personal_interest_reconciliation"]["source_artifact"] == (
        "data/raw/current_demand_gdp_share/fspdp_official_component_sources/fred_csv/"
        "A064RC1Q027SBEA.csv"
    )
    assert by_candidate["bea_y001_disposable_personal_income_blocked"][
        "admission_status"
    ] == "blocked_wrong_bea_series_not_personal_interest_context"
    deposit = deposit_interest_payer_flow_candidate_rows(inventory)
    admission = realized_safe_yield_payer_flow_admission_rows(
        inventory,
        deposit,
        raw_dir=raw,
        current_overlay_dir=current,
    )

    row = admission[0]
    assert row["bea_personal_interest_context_status"] == (
        "present_context_not_instrument_specific"
    )
    assert row["irs_taxable_interest_context_status"] == (
        "present_tax_context_not_timing_conversion"
    )
    assert row["bank_margin_context_status"] == (
        "present_bank_context_not_deposit_payer_flow"
    )
    assert row["current_denominator_reference_status"] == (
        "present_current_benchmark_D_reference"
    )
    assert row["all_required_gates_pass"] == "false"
    assert row["central_n_delta_bil_allowed"] == "false"
    assert row["period_cashflow_gate"] == (
        "blocked_missing_fdic_ffiec_or_ncua_payer_flow"
    )
    assert row["denominator_alignment_gate"] == (
        "blocked_candidate_cashflow_not_aligned_to_current_D_period"
    )


def test_all_safe_yield_gates_compute_nonzero_central_delta(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    current = tmp_path / "current"
    (raw / "ffiec_fdic").mkdir(parents=True)
    (raw / "ncua").mkdir(parents=True)
    current.mkdir()
    (raw / "ffiec_fdic/deposit_interest_expense_panel.csv").write_text(
        "report_date,rssd_id,RIAD4508,RIAD0093,RIADHK03,RIADHK04\n"
        "2024-03-31,1001,1,1,1,1\n",
        encoding="utf-8",
    )
    (raw / "ncua/share_deposit_interest_panel.csv").write_text(
        "report_date,charter_number,380,381\n2024-03-31,2001,1,1\n",
        encoding="utf-8",
    )
    _write_current_benchmark(current)

    inventory = realized_safe_yield_source_inventory_rows(raw_dir=raw)
    deposit = deposit_interest_payer_flow_candidate_rows(inventory)
    admission = realized_safe_yield_payer_flow_admission_rows(
        inventory,
        deposit,
        raw_dir=raw,
        current_overlay_dir=current,
        payer_flow_source_gate={
            "source_gate_status": "pass_source_panels_shape_coverage_and_flow",
            "accepted_current_row_share": "1",
            "gross_realized_income_bil": "27",
        },
        central_gate_inputs={
            "gross_realized_income_bil": "27",
            "recipient_share": "1",
            "coverage_alignment_factor": "1",
            "public_interest_overlap_share": "0",
            "tdc_overlap_share": "0",
            "firm_cash_overlap_share": "0",
            "tax_timing_leakage_share": "0.18",
            "current_spend_conversion_share": "0.08",
            "recipient_allocation_gate": "pass_recipient_allocation_proven",
            "denominator_alignment_gate": "pass_same_period_current_D_alignment",
            "overlap_gate": "pass_public_tdc_and_firm_cash_overlap_proven",
            "owner_gate": "pass_owner_approved_selected_overlay",
        },
    )

    row = admission[0]
    assert row["all_required_gates_pass"] == "true"
    assert row["object_role"] == "selected_n"
    assert row["central_n_delta_bil_allowed"] == "true"
    assert row["candidate_gross_flow_bil"] == "27"
    assert row["central_n_delta_bil"] == "1.7712"
    assert row["candidate_demand_support_bil"] == "1.7712"


def test_owner_gate_alone_cannot_unlock_missing_source_panel(tmp_path: Path) -> None:
    inventory = realized_safe_yield_source_inventory_rows(raw_dir=tmp_path / "raw")
    deposit = deposit_interest_payer_flow_candidate_rows(inventory)
    admission = realized_safe_yield_payer_flow_admission_rows(
        inventory,
        deposit,
        raw_dir=tmp_path / "raw",
        current_overlay_dir=tmp_path / "current",
        central_gate_inputs={
            "gross_realized_income_bil": "27",
            "recipient_share": "1",
            "coverage_alignment_factor": "1",
            "recipient_allocation_gate": "pass_recipient_allocation_proven",
            "denominator_alignment_gate": "pass_same_period_current_D_alignment",
            "overlap_gate": "pass_public_tdc_and_firm_cash_overlap_proven",
            "owner_gate": "pass_owner_approved_selected_overlay",
        },
    )

    row = admission[0]
    assert row["all_required_gates_pass"] == "false"
    assert row["object_role"] == "blocked_source_or_method"
    assert row["central_n_delta_bil_allowed"] == "false"
    assert row["central_n_delta_bil"] == "0"
    assert row["period_cashflow_gate"] == (
        "blocked_missing_fdic_ffiec_or_ncua_payer_flow"
    )


def test_deposit_safe_yield_bounded_fallback_uses_official_stock_rate_chain(
    tmp_path: Path,
) -> None:
    source = tmp_path / "fred"
    current = tmp_path / "current"
    source.mkdir()
    current.mkdir()
    _write_current_benchmark(current)
    _write_series(
        source / "TSDABSHNO.csv",
        "TSDABSHNO",
        [
            ("2025-01-01", "1000000"),
            ("2025-04-01", "1100000"),
            ("2025-07-01", "1200000"),
            ("2025-10-01", "1300000"),
            ("2026-01-01", "1400000"),
        ],
    )
    _write_series(
        source / "GDP.csv",
        "GDP",
        [
            ("2025-04-01", "30000"),
            ("2025-07-01", "31000"),
            ("2025-10-01", "32000"),
            ("2026-01-01", "33000"),
        ],
    )
    for index, series in enumerate(DEPOSIT_FALLBACK_RATE_SERIES, start=1):
        _write_series(
            source / f"{series}.csv",
            series,
            [
                ("2025-04-01", str(index)),
                ("2025-07-01", str(index)),
                ("2025-10-01", str(index)),
                ("2026-01-01", str(index)),
            ],
        )

    basis = deposit_safe_yield_fallback_basis_rows(
        source_dir=source,
        current_overlay_dir=current,
    )
    sensitivity = realized_safe_yield_bounded_sensitivity_rows(basis)

    assert {field for row in basis for field in row} == set(
        DEPOSIT_SAFE_YIELD_FALLBACK_BASIS_FIELDS
    )
    assert {field for row in sensitivity for field in row} == set(
        REALIZED_SAFE_YIELD_BOUNDED_SENSITIVITY_FIELDS
    )
    assert len(basis) == 4
    assert len(sensitivity) == 3
    assert all(row["central_n_delta_bil_allowed"] == "false" for row in basis)
    assert all(row["object_role"] == "sensitivity_only" for row in basis)
    assert all(row["central_n_delta_bil"] == "0" for row in sensitivity)
    assert all(row["object_role"] == "sensitivity_only" for row in sensitivity)
    assert {row["scenario"] for row in sensitivity} == {"low", "base", "high"}
    latest = basis[-1]
    assert latest["stock_source_series"] == "FL153030005|TSDABSHNO"
    assert latest["product_mix_numeric_used"] == "false"
    assert latest["paid_rate_low_annual_percent"] == "1"
    assert latest["paid_rate_base_annual_percent"] == "5.5"
    assert latest["paid_rate_high_annual_percent"] == "10"
    by_scenario = {row["scenario"]: row for row in sensitivity}
    assert by_scenario["low"]["tax_timing_leakage_share"] == "0.3"
    assert by_scenario["low"]["current_spend_conversion_share"] == "0.04"
    assert by_scenario["base"]["tax_timing_leakage_share"] == "0.18"
    assert by_scenario["base"]["current_spend_conversion_share"] == "0.08"
    assert by_scenario["high"]["tax_timing_leakage_share"] == "0.08"
    assert by_scenario["high"]["current_spend_conversion_share"] == "0.13"
    low = by_scenario["low"]
    assert float(low["eligible_deposit_safe_yield_flow_bil"]) > 0
    assert float(low["safe_yield_support_bil"]) < float(
        low["eligible_deposit_safe_yield_flow_bil"]
    )
    assert (
        float(by_scenario["low"]["safe_yield_support_bil"])
        <= float(by_scenario["base"]["safe_yield_support_bil"])
        <= float(by_scenario["high"]["safe_yield_support_bil"])
    )


def test_deposit_safe_yield_fallback_missing_sources_produces_no_numeric_rows(
    tmp_path: Path,
) -> None:
    current = tmp_path / "current"
    current.mkdir()
    _write_current_benchmark(current)

    basis = deposit_safe_yield_fallback_basis_rows(
        source_dir=tmp_path / "missing",
        current_overlay_dir=current,
    )
    sensitivity = realized_safe_yield_bounded_sensitivity_rows(basis)

    assert basis == []
    assert sensitivity == []


def test_realized_safe_yield_outputs_are_written(tmp_path: Path) -> None:
    inventory = realized_safe_yield_source_inventory_rows(raw_dir=tmp_path / "raw")
    decision = realized_safe_yield_lane_decision_rows(inventory)
    deposit = deposit_interest_payer_flow_candidate_rows(inventory)
    admission = realized_safe_yield_payer_flow_admission_rows(
        inventory,
        deposit,
        raw_dir=tmp_path / "raw",
        current_overlay_dir=tmp_path / "current",
    )
    diagnostic = constructed_safe_yield_flow_diagnostic_rows()
    gap = realized_safe_yield_gap_rows()
    audit = realized_safe_yield_audit_rows(
        decision_rows=decision,
        deposit_rows=deposit,
        admission_rows=admission,
        diagnostic_rows=diagnostic,
        gap_rows=gap,
    )
    fallback_basis = deposit_safe_yield_fallback_basis_rows(
        source_dir=tmp_path / "fred",
        current_overlay_dir=tmp_path / "current",
    )
    bounded_sensitivity = realized_safe_yield_bounded_sensitivity_rows(fallback_basis)

    outputs = write_realized_safe_yield_outputs(
        tmp_path / "out",
        inventory_rows=inventory,
        decision_rows=decision,
        deposit_rows=deposit,
        admission_rows=admission,
        diagnostic_rows=diagnostic,
        gap_rows=gap,
        audit_rows=audit,
        fallback_basis_rows=fallback_basis,
        bounded_sensitivity_rows=bounded_sensitivity,
    )

    assert outputs["inventory_csv"].read_text(encoding="utf-8").startswith(
        "candidate_id,"
    )
    assert outputs["decision_csv"].read_text(encoding="utf-8").startswith(
        "decision_row_id,"
    )
    assert outputs["payer_flow_admission_csv"].read_text(
        encoding="utf-8"
    ).startswith("admission_row_id,")
    assert outputs["audit_csv"].read_text(encoding="utf-8").startswith(
        "realized_safe_yield_audit_row_id,"
    )
    assert outputs["deposit_fallback_basis_csv"].read_text(
        encoding="utf-8"
    ).startswith("basis_row_id,")
    assert outputs["bounded_sensitivity_csv"].read_text(
        encoding="utf-8"
    ).startswith("sensitivity_row_id,")


def _write_series(path: Path, series_id: str, rows: list[tuple[str, str]]) -> None:
    path.write_text(
        "observation_date," + series_id + "\n"
        + "".join(f"{date_value},{value}\n" for date_value, value in rows),
        encoding="utf-8",
    )


def _write_current_benchmark(path: Path) -> None:
    (path / "ratewall_current_assumption_benchmark.csv").write_text(
        "forecast_year,benchmark_id,benchmark_numerator_bil,fixed_D_bil,"
        "benchmark_ratewall_ratio,selected_current_row\n"
        "2026,current_assumption_benchmark,83.542224868775,247.55956656,"
        "0.337463124652,true\n",
        encoding="utf-8",
    )

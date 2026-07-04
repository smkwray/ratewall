"""Realized safe-yield income lane gates for current and historical RateWall."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_CURRENT_OVERLAY_DIR = Path(
    "var/preliminary_scenario_results/current_observed_overlay"
)
DEFAULT_SAFE_YIELD_FRED_DIR = Path("data/raw/safe_yield/fred_csv")

APPROVED_SAFE_YIELD_LEAKAGE = {
    "low": Decimal("0.30"),
    "base": Decimal("0.18"),
    "high": Decimal("0.08"),
}
APPROVED_SAFE_YIELD_SPEND = {
    "low": Decimal("0.04"),
    "base": Decimal("0.08"),
    "high": Decimal("0.13"),
}
DEPOSIT_FALLBACK_STOCK_SERIES = "TSDABSHNO"
DEPOSIT_FALLBACK_RATE_SERIES = [
    "SNDR",
    "MMNDR",
    "NDR1MCD",
    "NDR3MCD",
    "NDR6MCD",
    "NDR12MCD",
    "NDR24MCD",
    "NDR36MCD",
    "NDR48MCD",
    "NDR60MCD",
]
DEPOSIT_FALLBACK_EXCLUDED_RATE_SERIES = "ICNDR|ICNRNJ|rate_caps|Treasury_yields|MMF_yields"

SAFE_YIELD_SOURCE_INVENTORY_FIELDS = [
    "candidate_id",
    "candidate_label",
    "source_family",
    "source_artifact",
    "instrument_scope",
    "recipient_scope",
    "period_coverage_start",
    "period_coverage_end",
    "frequency",
    "is_realized_income_flow",
    "is_constructed_flow",
    "requires_stock_to_flow_rule",
    "recipient_basis_available",
    "public_interest_overlap_risk",
    "tdc_overlap_risk",
    "tax_scope_limitation",
    "admission_status",
    "next_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DEPOSIT_SAFE_YIELD_FALLBACK_BASIS_FIELDS = [
    "basis_row_id",
    "object_role",
    "period_id",
    "period_start_date",
    "period_end_date",
    "period_frequency",
    "period_days",
    "period_fraction_of_year",
    "denominator_object_id",
    "current_D_bil",
    "nominal_gdp_bil",
    "gdp_source_id",
    "stock_source_family",
    "stock_source_table",
    "stock_source_series",
    "stock_source_label",
    "stock_source_units",
    "stock_source_frequency",
    "stock_source_timing",
    "stock_eop_start_bil",
    "stock_eop_end_bil",
    "stock_avg_bil",
    "included_stock_scope",
    "excluded_checkable_currency_series",
    "excluded_noninterest_bearing_deposit_rule",
    "excluded_other_deposits_series",
    "excluded_public_balance_series",
    "excluded_foreign_balance_series",
    "excluded_financial_sector_balance_series",
    "excluded_firm_cash_balance_series",
    "household_sector_residual_limitation",
    "tdc_applicability",
    "tdc_created_deposit_stock_start_bil",
    "tdc_created_deposit_stock_end_bil",
    "tdc_created_deposit_stock_avg_subtracted_bil",
    "tdc_subtraction_source",
    "eligible_interest_bearing_household_private_deposit_stock_bil",
    "paid_rate_source_family",
    "paid_rate_source_release",
    "paid_rate_methodology_version",
    "paid_rate_period_aggregation",
    "eligible_paid_rate_series_set",
    "excluded_paid_rate_series_set",
    "paid_rate_low_rule",
    "paid_rate_base_rule",
    "paid_rate_high_rule",
    "paid_rate_low_annual_percent",
    "paid_rate_base_annual_percent",
    "paid_rate_high_annual_percent",
    "period_rate_low_decimal",
    "period_rate_base_decimal",
    "period_rate_high_decimal",
    "eligible_deposit_safe_yield_flow_low_bil",
    "eligible_deposit_safe_yield_flow_base_bil",
    "eligible_deposit_safe_yield_flow_high_bil",
    "product_mix_source_status",
    "product_mix_numeric_used",
    "holder_allocation_source_status",
    "overlap_guard_status",
    "centrality",
    "central_n_delta_bil_allowed",
    "central_n_delta_bil",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "source_status",
]

REALIZED_SAFE_YIELD_BOUNDED_SENSITIVITY_FIELDS = [
    "sensitivity_row_id",
    "object_role",
    "support_period_id",
    "support_period_type",
    "support_period_start_date",
    "support_period_end_date",
    "scenario",
    "basis_row_ids",
    "basis_period_count",
    "rate_basis_rule",
    "paid_rate_annual_percent",
    "period_rate_decimal_sum_check",
    "eligible_interest_bearing_household_private_deposit_stock_avg_bil",
    "tdc_created_deposit_stock_avg_subtracted_bil",
    "eligible_deposit_safe_yield_flow_bil",
    "tax_timing_leakage_handle_id",
    "tax_timing_leakage_share",
    "post_tax_timing_safe_yield_flow_bil",
    "current_spend_conversion_handle_id",
    "current_spend_conversion_share",
    "safe_yield_support_bil",
    "denominator_object_id",
    "current_D_bil",
    "support_to_current_D_ratio",
    "nominal_gdp_bil",
    "support_to_gdp_share",
    "centrality",
    "central_n_delta_bil_allowed",
    "central_n_delta_bil",
    "source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

SAFE_YIELD_LANE_DECISION_FIELDS = [
    "decision_row_id",
    "decision",
    "central_forecast_addition_bil",
    "central_current_benchmark_addition_bil",
    "full_composite_current_addition_bil",
    "full_composite_historical_addition_bil",
    "deposit_payer_flow_candidate_required",
    "diagnostic_output",
    "owner_gate_required_for_selected_overlay",
    "deposit_candidate_status",
    "full_composite_headline_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DEPOSIT_PAYER_FLOW_CANDIDATE_FIELDS = [
    "period_id",
    "instrument_family",
    "gross_realized_income_bil",
    "recipient_basis",
    "eligible_domestic_private_share",
    "tax_timing_or_leakage_share",
    "translation_family",
    "current_demand_conversion_share",
    "demand_support_bil",
    "overlap_guard_id",
    "source_status",
    "recipient_share_quality",
    "coverage_alignment_factor",
    "owner_gate_status",
    "centrality",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

SAFE_YIELD_PAYER_FLOW_ADMISSION_FIELDS = [
    "admission_row_id",
    "candidate_family",
    "object_role",
    "period_id",
    "fdic_ffiec_payer_flow_status",
    "ncua_payer_flow_status",
    "bea_personal_interest_context_status",
    "irs_taxable_interest_context_status",
    "bank_margin_context_status",
    "current_denominator_reference_status",
    "period_cashflow_gate",
    "recipient_allocation_gate",
    "tax_timing_gate",
    "demand_conversion_gate",
    "denominator_alignment_gate",
    "overlap_gate",
    "owner_gate",
    "all_required_gates_pass",
    "candidate_gross_flow_bil",
    "candidate_demand_support_bil",
    "central_n_delta_bil_allowed",
    "central_n_delta_bil",
    "blocked_reason",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

CONSTRUCTED_SAFE_YIELD_DIAGNOSTIC_FIELDS = [
    "diagnostic_row_id",
    "object_role",
    "instrument_family",
    "balance_source",
    "yield_or_passthrough_source",
    "periodization",
    "stock_to_flow_rule",
    "recipient_basis",
    "overlap_risks",
    "constructed_flow_bil",
    "central_n_delta_bil_allowed",
    "diagnostic_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

SAFE_YIELD_GAP_FIELDS = [
    "source_channel_id",
    "object_role",
    "surface_role",
    "build_status",
    "claim_boundary",
    "central_n_delta_bil_allowed",
    "required_to_unpark",
    "allowed_use",
    "blocked_use",
]

REALIZED_SAFE_YIELD_AUDIT_FIELDS = [
    "realized_safe_yield_audit_row_id",
    "check_id",
    "check_status",
    "row_count",
    "required_rule",
    "allowed_use",
    "blocked_use",
]


def realized_safe_yield_source_inventory_rows(
    *,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
) -> list[dict[str, str]]:
    """Inventory safe-yield sources without admitting a composite income channel."""

    raw = Path(raw_dir)
    return [
        _inventory_row(
            candidate_id="deposit_payer_flow_fdic_ffiec",
            label="Bank deposit-interest expense from Call Report fields",
            family="ffiec_fdic_call_report_deposit_interest_expense",
            artifact="data/raw/ffiec_fdic/deposit_interest_expense_panel.csv",
            instrument="deposits",
            recipient="payer_side_not_recipient_allocated",
            start="",
            end="",
            frequency="quarterly",
            realized_flow=True,
            constructed=False,
            stock_rule=False,
            recipient_basis=False,
            public_overlap=True,
            tdc_overlap=True,
            tax_limited=False,
            status=(
                "owner_gated_candidate_deposit_only"
                if (raw / "ffiec_fdic/deposit_interest_expense_panel.csv").exists()
                else "missing_required_source"
            ),
            next_action="acquire_or_build_domestic_deposit_interest_expense_panel",
        ),
        _inventory_row(
            candidate_id="deposit_payer_flow_ncua",
            label="Credit-union share/deposit interest expense",
            family="ncua_credit_union_share_interest",
            artifact="data/raw/ncua/share_deposit_interest_panel.csv",
            instrument="deposits",
            recipient="payer_side_not_recipient_allocated",
            start="",
            end="",
            frequency="quarterly",
            realized_flow=True,
            constructed=False,
            stock_rule=False,
            recipient_basis=False,
            public_overlap=True,
            tdc_overlap=True,
            tax_limited=False,
            status=(
                "owner_gated_candidate_deposit_only"
                if (raw / "ncua/share_deposit_interest_panel.csv").exists()
                else "missing_required_source"
            ),
            next_action="acquire_or_build_credit_union_share_interest_panel",
        ),
        _inventory_row(
            candidate_id="mmf_holdings_sec_nmfp",
            label="SEC N-MFP MMF portfolio holdings",
            family="sec_nmfp_mmf_holdings_flatfiles",
            artifact="data/raw/sec_nmfp/latest_nmfp.zip",
            instrument="money_market_funds",
            recipient="fund_type_context_not_final_investor",
            start="2010Q4",
            end="2026Q2",
            frequency="monthly_quarterly_context",
            realized_flow=False,
            constructed=True,
            stock_rule=True,
            recipient_basis=False,
            public_overlap=True,
            tdc_overlap=True,
            tax_limited=False,
            status=(
                "diagnostic_context_constructed_flow"
                if (raw / "sec_nmfp/latest_nmfp.zip").exists()
                else "missing_required_source"
            ),
            next_action="add_realized_yield_and_final_investor_recipient_basis",
        ),
        _inventory_row(
            candidate_id="bea_personal_interest_reconciliation",
            label="BEA personal interest income reconciliation",
            family="bea_personal_interest_income_payments",
            artifact="data/raw/current_demand_gdp_share/fspdp_official_component_sources/fred_csv/A064RC1Q027SBEA.csv",
            instrument="all_personal_interest_income",
            recipient="household_top_down_broad",
            start="",
            end="",
            frequency="quarterly",
            realized_flow=True,
            constructed=False,
            stock_rule=False,
            recipient_basis=True,
            public_overlap=True,
            tdc_overlap=False,
            tax_limited=False,
            status="reconciliation_context_only",
            next_action="use_as_scale_check_not_instrument_complete_channel",
        ),
        _inventory_row(
            candidate_id="bea_y001_disposable_personal_income_blocked",
            label="BEA disposable personal income series blocked for D1",
            family="bea_disposable_personal_income_wrong_safe_yield_context",
            artifact="data/raw/current_demand_gdp_share/fspdp_official_component_sources/fred_csv/Y001RC1Q027SBEA.csv",
            instrument="not_personal_interest_income",
            recipient="broad_personal_income_not_safe_yield_recipient_basis",
            start="",
            end="",
            frequency="quarterly",
            realized_flow=True,
            constructed=False,
            stock_rule=False,
            recipient_basis=False,
            public_overlap=True,
            tdc_overlap=False,
            tax_limited=False,
            status="blocked_wrong_bea_series_not_personal_interest_context",
            next_action="do_not_use_Y001_for_safe_yield_context_or_payer_flow",
        ),
        _inventory_row(
            candidate_id="irs_taxable_interest_context",
            label="IRS taxable interest context",
            family="irs_soi_taxable_interest",
            artifact="data/raw/irs_soi/irs_soi_2023_table_1_4_taxable_interest.csv",
            instrument="taxable_interest",
            recipient="tax_filers_only",
            start="2023",
            end="2023",
            frequency="annual",
            realized_flow=True,
            constructed=False,
            stock_rule=False,
            recipient_basis=True,
            public_overlap=True,
            tdc_overlap=False,
            tax_limited=True,
            status="tax_context_only",
            next_action="use_as_tax_timing_or_leakage_context_only",
        ),
        _inventory_row(
            candidate_id="raw_safe_asset_stocks",
            label="Deposit/MMF/Treasury stock context",
            family="z1_dfa_scf_h8_stock_context",
            artifact="candidate_source_family_not_single_flow_artifact",
            instrument="deposits_mmf_treasuries",
            recipient="stock_holder_context",
            start="",
            end="",
            frequency="mixed",
            realized_flow=False,
            constructed=False,
            stock_rule=True,
            recipient_basis=True,
            public_overlap=True,
            tdc_overlap=True,
            tax_limited=False,
            status="stock_context_only",
            next_action="do_not_apply_mpc_until_stock_is_converted_to_period_flow",
        ),
    ]


def realized_safe_yield_lane_decision_rows(
    inventory_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return the required single lane decision row."""

    deposit_ready = any(
        row["candidate_id"].startswith("deposit_payer_flow_")
        and row["admission_status"] == "owner_gated_candidate_deposit_only"
        for row in inventory_rows
    )
    return [
        {
            "decision_row_id": "realized_safe_yield_lane_decision::selected",
            "decision": "deposit_required_bounded_noncentral_now_source_backed_candidate_later",
            "central_forecast_addition_bil": "0",
            "central_current_benchmark_addition_bil": "0",
            "full_composite_current_addition_bil": "0",
            "full_composite_historical_addition_bil": "0",
            "deposit_payer_flow_candidate_required": "true",
            "diagnostic_output": "ratewall_constructed_safe_yield_flow_diagnostic.csv",
            "owner_gate_required_for_selected_overlay": "true",
            "deposit_candidate_status": (
                "payer_flow_source_present_owner_gate_required"
                if deposit_ready
                else "bounded_noncentral_fallback_required_until_payer_flow_sources_pass"
            ),
            "full_composite_headline_status": "not_headline_central_addition_zero",
            "allowed_use": "realized_safe_yield_lane_decision",
            "blocked_use": (
                "forecast_central_N_addition;current_benchmark_replacement;"
                "historical_final_classifier;raw_stock_mpc_shortcut"
            ),
            "claim_boundary": "realized_safe_yield_decision_no_selected_value_change",
        }
    ]


def deposit_interest_payer_flow_candidate_rows(
    inventory_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return the deposit-only candidate row, admitted only when source gates pass."""

    fdic = _by_candidate(inventory_rows, "deposit_payer_flow_fdic_ffiec")
    ncua = _by_candidate(inventory_rows, "deposit_payer_flow_ncua")
    sources_present = (
        fdic["admission_status"] == "owner_gated_candidate_deposit_only"
        and ncua["admission_status"] == "owner_gated_candidate_deposit_only"
    )
    return [
        {
            "period_id": "current_overlay_candidate",
            "instrument_family": "deposits",
            "gross_realized_income_bil": "",
            "recipient_basis": "",
            "eligible_domestic_private_share": "",
            "tax_timing_or_leakage_share": "",
            "translation_family": "realized_household_safe_yield_income",
            "current_demand_conversion_share": "",
            "demand_support_bil": "0",
            "overlap_guard_id": "bank_first_vs_recipient_flow_xor",
            "source_status": (
                "payer_flow_sources_present_but_owner_gate_required"
                if sources_present
                else "missing_deposit_payer_side_realized_flow"
            ),
            "recipient_share_quality": "not_allocated_to_eligible_recipients",
            "coverage_alignment_factor": "0",
            "owner_gate_status": "blocked_until_payer_flow_recipient_overlap_gates_pass",
            "centrality": "candidate_diagnostic_not_selected",
            "allowed_use": "current_overlay_candidate_after_owner_gate",
            "blocked_use": (
                "central_current_benchmark_addition;forecast_central_N;"
                "historical_final_classifier;raw_stock_mpc_shortcut"
            ),
            "claim_boundary": "deposit_payer_flow_candidate_no_selected_value_change",
        }
    ]


def realized_safe_yield_payer_flow_admission_rows(
    inventory_rows: Sequence[Mapping[str, str]],
    deposit_rows: Sequence[Mapping[str, str]],
    *,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    current_overlay_dir: str | Path = DEFAULT_CURRENT_OVERLAY_DIR,
    payer_flow_source_gate: Mapping[str, str] | None = None,
    central_gate_inputs: Mapping[str, str] | None = None,
) -> list[dict[str, str]]:
    """Return the proof gates required before safe-yield income can enter N."""

    if len(deposit_rows) != 1:
        raise ValueError("expected exactly one deposit payer-flow candidate row")

    raw = Path(raw_dir)
    current = Path(current_overlay_dir)
    fdic = _by_candidate(inventory_rows, "deposit_payer_flow_fdic_ffiec")
    ncua = _by_candidate(inventory_rows, "deposit_payer_flow_ncua")
    deposit = deposit_rows[0]
    payer_sources_present = (
        fdic["admission_status"] == "owner_gated_candidate_deposit_only"
        and ncua["admission_status"] == "owner_gated_candidate_deposit_only"
    )
    source_gate_status = (
        payer_flow_source_gate.get("source_gate_status", "")
        if payer_flow_source_gate is not None
        else ""
    )
    source_gate_pass = _gate_passes(source_gate_status)
    source_gross_flow = (
        payer_flow_source_gate.get("gross_realized_income_bil", "")
        if payer_flow_source_gate is not None
        else ""
    )
    context = _safe_yield_context_statuses(raw)
    current_d_present = (
        current / "ratewall_current_assumption_benchmark.csv"
    ).exists()

    period_gate = (
        "pass_deposit_payer_flow_source_panels_shape_coverage_and_flow"
        if source_gate_pass
        else "blocked_missing_fdic_ffiec_or_ncua_payer_flow"
    )
    if payer_sources_present and not source_gate_pass:
        period_gate = "blocked_deposit_payer_flow_source_gate_failed"
    recipient_gate = (
        "blocked_no_final_recipient_allocation"
        if deposit["recipient_share_quality"] == "not_allocated_to_eligible_recipients"
        else "pass"
    )
    tax_gate = "pass_approved_leakage_handles_available_0_08_0_18_0_30"
    demand_gate = "pass_approved_current_spend_handles_available_0_04_0_08_0_13"
    denominator_gate = (
        "blocked_candidate_cashflow_not_aligned_to_current_D_period"
        if current_d_present
        else "blocked_missing_current_D_reference"
    )
    overlap_gate = "blocked_public_interest_tdc_and_firm_cash_overlap_unproven"
    owner_gate = "blocked_until_all_required_safe_yield_gates_pass"
    central_inputs = central_gate_inputs or {}
    if _gate_passes(central_inputs.get("recipient_allocation_gate", "")):
        recipient_gate = central_inputs["recipient_allocation_gate"]
    if _gate_passes(central_inputs.get("denominator_alignment_gate", "")):
        denominator_gate = central_inputs["denominator_alignment_gate"]
    if _gate_passes(central_inputs.get("overlap_gate", "")):
        overlap_gate = central_inputs["overlap_gate"]
    if _gate_passes(central_inputs.get("owner_gate", "")):
        owner_gate = central_inputs["owner_gate"]
    gate_values = [
        period_gate,
        recipient_gate,
        tax_gate,
        demand_gate,
        denominator_gate,
        overlap_gate,
        owner_gate,
    ]
    all_pass = all(_gate_passes(value) for value in gate_values)
    gross_flow = central_inputs.get(
        "gross_realized_income_bil",
        source_gross_flow or deposit["gross_realized_income_bil"],
    )
    central_delta = "0"
    if all_pass:
        central_delta = _safe_yield_central_delta_bil(
            gross_flow_bil=gross_flow,
            recipient_share=central_inputs.get("recipient_share", "1"),
            coverage_alignment_factor=central_inputs.get(
                "coverage_alignment_factor",
                payer_flow_source_gate.get("accepted_current_row_share", "1")
                if payer_flow_source_gate is not None
                else "1",
            ),
            public_interest_overlap_share=central_inputs.get(
                "public_interest_overlap_share", "0"
            ),
            tdc_overlap_share=central_inputs.get("tdc_overlap_share", "0"),
            firm_cash_overlap_share=central_inputs.get("firm_cash_overlap_share", "0"),
            leakage_share=central_inputs.get(
                "tax_timing_leakage_share",
                str(APPROVED_SAFE_YIELD_LEAKAGE["base"]),
            ),
            current_spend_share=central_inputs.get(
                "current_spend_conversion_share",
                str(APPROVED_SAFE_YIELD_SPEND["base"]),
            ),
        )
        if Decimal(central_delta) == 0:
            all_pass = False
            gate_values.append("blocked_central_delta_zero")
    blocked_reason = (
        "all_required_gates_passed"
        if all_pass
        else ";".join(value for value in gate_values if not _gate_passes(value))
    )
    return [
        {
            "admission_row_id": "realized_safe_yield_payer_flow_admission::deposit",
            "candidate_family": "deposit_interest_payer_flow",
            "object_role": "blocked_source_or_method" if not all_pass else "selected_n",
            "period_id": deposit["period_id"],
            "fdic_ffiec_payer_flow_status": fdic["admission_status"],
            "ncua_payer_flow_status": ncua["admission_status"],
            "bea_personal_interest_context_status": context[
                "bea_personal_interest"
            ],
            "irs_taxable_interest_context_status": context["irs_taxable_interest"],
            "bank_margin_context_status": context["bank_margin"],
            "current_denominator_reference_status": (
                "present_current_benchmark_D_reference"
                if current_d_present
                else "missing_current_benchmark_D_reference"
            ),
            "period_cashflow_gate": period_gate,
            "recipient_allocation_gate": recipient_gate,
            "tax_timing_gate": tax_gate,
            "demand_conversion_gate": demand_gate,
            "denominator_alignment_gate": denominator_gate,
            "overlap_gate": overlap_gate,
            "owner_gate": owner_gate,
            "all_required_gates_pass": str(all_pass).lower(),
            "candidate_gross_flow_bil": gross_flow,
            "candidate_demand_support_bil": central_delta if all_pass else "0",
            "central_n_delta_bil_allowed": str(all_pass).lower(),
            "central_n_delta_bil": central_delta if all_pass else "0",
            "blocked_reason": blocked_reason,
            "allowed_use": "safe_yield_payer_flow_admission_gate",
            "blocked_use": (
                "central_N_addition;current_benchmark_replacement;"
                "forecast_backfill;historical_classifier"
            ),
            "claim_boundary": "R39_safe_yield_admission_fail_closed_no_value_change",
        }
    ]


def deposit_safe_yield_fallback_basis_rows(
    *,
    source_dir: str | Path = DEFAULT_SAFE_YIELD_FRED_DIR,
    current_overlay_dir: str | Path = DEFAULT_CURRENT_OVERLAY_DIR,
) -> list[dict[str, str]]:
    """Build official-stock x official-paid-rate D1 bounded basis rows.

    Missing required official stock/rate/GDP/current-D sources produce no numeric
    rows. That is intentional: D1 may continue as a documented noncentral route,
    but not as a numeric sensitivity without the official inputs.
    """

    source = Path(source_dir)
    current = _current_denominator_reference(Path(current_overlay_dir))
    stock = _read_series_csv(source, DEPOSIT_FALLBACK_STOCK_SERIES)
    gdp = _read_series_csv(source, "GDP")
    rates = {
        series: _read_series_csv(source, series)
        for series in DEPOSIT_FALLBACK_RATE_SERIES
    }
    if (
        current is None
        or not stock
        or not gdp
        or any(not series_rows for series_rows in rates.values())
    ):
        return []

    stock_dates = sorted(stock)
    out: list[dict[str, str]] = []
    for index, observation_date in enumerate(stock_dates[1:], start=1):
        period_start = _quarter_start(observation_date)
        period_end = _quarter_end(period_start)
        period_id = _period_id(period_start)
        gdp_value = gdp.get(period_start)
        if gdp_value is None:
            continue
        quarter_rates = [
            _period_average_rate(series_rows, period_start, period_end)
            for series_rows in rates.values()
        ]
        if any(value is None for value in quarter_rates):
            continue
        sorted_rates = sorted(value for value in quarter_rates if value is not None)
        low_rate = sorted_rates[0]
        high_rate = sorted_rates[-1]
        base_rate = _median(sorted_rates)
        prior_stock = stock[stock_dates[index - 1]] / Decimal("1000")
        current_stock = stock[observation_date] / Decimal("1000")
        stock_avg = (prior_stock + current_stock) / Decimal("2")
        days = (period_end - period_start).days + 1
        fraction = Decimal(days) / Decimal("365.25")
        flows = {
            "low": stock_avg * (low_rate / Decimal("100")) * fraction,
            "base": stock_avg * (base_rate / Decimal("100")) * fraction,
            "high": stock_avg * (high_rate / Decimal("100")) * fraction,
        }
        out.append(
            {
                "basis_row_id": f"deposit_safe_yield_fallback_basis::{period_id}",
                "object_role": "sensitivity_only",
                "period_id": period_id,
                "period_start_date": period_start.isoformat(),
                "period_end_date": period_end.isoformat(),
                "period_frequency": "quarter",
                "period_days": str(days),
                "period_fraction_of_year": _fmt(fraction),
                "denominator_object_id": current["denominator_object_id"],
                "current_D_bil": current["current_D_bil"],
                "nominal_gdp_bil": _fmt(gdp_value),
                "gdp_source_id": "FRED::GDP",
                "stock_source_family": "Federal_Reserve_Z1_F2_3_s_FRED",
                "stock_source_table": "F2.3.s/L.101/L.205",
                "stock_source_series": "FL153030005|TSDABSHNO",
                "stock_source_label": "Households and nonprofit organizations time and savings deposits",
                "stock_source_units": "millions_usd_converted_to_billions_usd",
                "stock_source_frequency": "quarterly",
                "stock_source_timing": "end_of_period",
                "stock_eop_start_bil": _fmt(prior_stock),
                "stock_eop_end_bil": _fmt(current_stock),
                "stock_avg_bil": _fmt(stock_avg),
                "included_stock_scope": "household_HNO_time_and_savings_deposits_only",
                "excluded_checkable_currency_series": "FL153020005",
                "excluded_noninterest_bearing_deposit_rule": "excluded_by_time_and_savings_stock_boundary",
                "excluded_other_deposits_series": "LM153030505",
                "excluded_public_balance_series": "federal_government;state_local_government",
                "excluded_foreign_balance_series": "rest_of_world",
                "excluded_financial_sector_balance_series": "domestic_financial_sectors",
                "excluded_firm_cash_balance_series": "nonfinancial_business",
                "household_sector_residual_limitation": "HNO_includes_nonprofit_organizations",
                "tdc_applicability": "static_current_object_no_tdc_term",
                "tdc_created_deposit_stock_start_bil": "0",
                "tdc_created_deposit_stock_end_bil": "0",
                "tdc_created_deposit_stock_avg_subtracted_bil": "0",
                "tdc_subtraction_source": "not_applicable_static_current_object",
                "eligible_interest_bearing_household_private_deposit_stock_bil": _fmt(
                    stock_avg
                ),
                "paid_rate_source_family": "FDIC_National_Rates_and_Rate_Caps_FRED",
                "paid_rate_source_release": "national_deposit_rates_not_caps",
                "paid_rate_methodology_version": "post_2021_current_product_set",
                "paid_rate_period_aggregation": "mean_observed_annual_percent_inside_quarter",
                "eligible_paid_rate_series_set": "|".join(DEPOSIT_FALLBACK_RATE_SERIES),
                "excluded_paid_rate_series_set": DEPOSIT_FALLBACK_EXCLUDED_RATE_SERIES,
                "paid_rate_low_rule": "min_eligible_FDIC_product_paid_rate",
                "paid_rate_base_rule": "median_eligible_FDIC_product_paid_rate",
                "paid_rate_high_rule": "max_eligible_FDIC_product_paid_rate",
                "paid_rate_low_annual_percent": _fmt(low_rate),
                "paid_rate_base_annual_percent": _fmt(base_rate),
                "paid_rate_high_annual_percent": _fmt(high_rate),
                "period_rate_low_decimal": _fmt((low_rate / Decimal("100")) * fraction),
                "period_rate_base_decimal": _fmt((base_rate / Decimal("100")) * fraction),
                "period_rate_high_decimal": _fmt((high_rate / Decimal("100")) * fraction),
                "eligible_deposit_safe_yield_flow_low_bil": _fmt(flows["low"]),
                "eligible_deposit_safe_yield_flow_base_bil": _fmt(flows["base"]),
                "eligible_deposit_safe_yield_flow_high_bil": _fmt(flows["high"]),
                "product_mix_source_status": "no_clean_official_household_holder_product_mix",
                "product_mix_numeric_used": "false",
                "holder_allocation_source_status": "direct_Z1_holder_line_used_no_total_allocation",
                "overlap_guard_status": "static_current_no_tdc_term_noncentral_only",
                "centrality": "noncentral_bounded_sensitivity",
                "central_n_delta_bil_allowed": "false",
                "central_n_delta_bil": "0",
                "allowed_use": "bounded_sensitivity_only",
                "blocked_use": "central_N_selected_RW_release_reporting",
                "claim_boundary": "assumption_backed_bounded_sensitivity_candidate",
                "source_status": "source_present_official_stock_and_paid_rate_envelope",
            }
        )
    return out


def realized_safe_yield_bounded_sensitivity_rows(
    basis_rows: Sequence[Mapping[str, str]],
    *,
    trailing_quarters: int = 4,
) -> list[dict[str, str]]:
    """Aggregate bounded basis rows into low/base/high noncentral support rows."""

    if len(basis_rows) < trailing_quarters:
        return []
    selected = sorted(basis_rows, key=lambda row: row["period_start_date"])[
        -trailing_quarters:
    ]
    period_start = selected[0]["period_start_date"]
    period_end = selected[-1]["period_end_date"]
    support_period_id = f"TTM_{selected[-1]['period_id']}"
    stock_avg = _mean_decimal(
        row["eligible_interest_bearing_household_private_deposit_stock_bil"]
        for row in selected
    )
    tdc_subtracted = sum(
        Decimal(row["tdc_created_deposit_stock_avg_subtracted_bil"])
        for row in selected
    ) / Decimal(len(selected))
    gdp = _mean_decimal(row["nominal_gdp_bil"] for row in selected)
    current_d = Decimal(selected[-1]["current_D_bil"])
    out: list[dict[str, str]] = []
    for scenario, rule, rate_field, period_rate_field, flow_field in [
        (
            "low",
            "min_eligible_FDIC_product_paid_rate",
            "paid_rate_low_annual_percent",
            "period_rate_low_decimal",
            "eligible_deposit_safe_yield_flow_low_bil",
        ),
        (
            "base",
            "median_eligible_FDIC_product_paid_rate",
            "paid_rate_base_annual_percent",
            "period_rate_base_decimal",
            "eligible_deposit_safe_yield_flow_base_bil",
        ),
        (
            "high",
            "max_eligible_FDIC_product_paid_rate",
            "paid_rate_high_annual_percent",
            "period_rate_high_decimal",
            "eligible_deposit_safe_yield_flow_high_bil",
        ),
    ]:
        flow = sum(Decimal(row[flow_field]) for row in selected)
        leakage = APPROVED_SAFE_YIELD_LEAKAGE[scenario]
        spend = APPROVED_SAFE_YIELD_SPEND[scenario]
        post_tax = flow * (Decimal("1") - leakage)
        support = post_tax * spend
        out.append(
            {
                "sensitivity_row_id": f"realized_safe_yield_bounded::{support_period_id}::{scenario}",
                "object_role": "sensitivity_only",
                "support_period_id": support_period_id,
                "support_period_type": "trailing_four_complete_quarters",
                "support_period_start_date": period_start,
                "support_period_end_date": period_end,
                "scenario": scenario,
                "basis_row_ids": "|".join(row["basis_row_id"] for row in selected),
                "basis_period_count": str(len(selected)),
                "rate_basis_rule": rule,
                "paid_rate_annual_percent": _fmt(
                    _mean_decimal(row[rate_field] for row in selected)
                ),
                "period_rate_decimal_sum_check": _fmt(
                    sum(Decimal(row[period_rate_field]) for row in selected)
                ),
                "eligible_interest_bearing_household_private_deposit_stock_avg_bil": _fmt(
                    stock_avg
                ),
                "tdc_created_deposit_stock_avg_subtracted_bil": _fmt(tdc_subtracted),
                "eligible_deposit_safe_yield_flow_bil": _fmt(flow),
                "tax_timing_leakage_handle_id": "interest_income_tax_timing_leakage_share",
                "tax_timing_leakage_share": _fmt(leakage),
                "post_tax_timing_safe_yield_flow_bil": _fmt(post_tax),
                "current_spend_conversion_handle_id": "household_safe_yield_current_spend_share",
                "current_spend_conversion_share": _fmt(spend),
                "safe_yield_support_bil": _fmt(support),
                "denominator_object_id": selected[-1]["denominator_object_id"],
                "current_D_bil": _fmt(current_d),
                "support_to_current_D_ratio": _fmt(support / current_d),
                "nominal_gdp_bil": _fmt(gdp),
                "support_to_gdp_share": _fmt(support / gdp),
                "centrality": "noncentral_bounded_sensitivity",
                "central_n_delta_bil_allowed": "false",
                "central_n_delta_bil": "0",
                "source_status": selected[-1]["source_status"],
                "allowed_use": "bounded_sensitivity_only",
                "blocked_use": "central_N_selected_RW_release_reporting",
                "claim_boundary": "assumption_backed_bounded_sensitivity_candidate",
            }
        )
    return out


def constructed_safe_yield_flow_diagnostic_rows() -> list[dict[str, str]]:
    """Return diagnostic constructed-flow rows with no central admission."""

    specs = [
        (
            "deposits",
            "H8_or_Z1_deposit_balances",
            "FDIC_or_FRED_SNDR_product_rates",
            "annualized_or_quarterly_period_flow_required",
            "balance * realized deposit yield * period timing",
        ),
        (
            "money_market_funds",
            "SEC_NMFP_or_OFR_or_ICI_MMF_assets",
            "MMF portfolio yield/pass-through source required",
            "monthly_to_quarterly_or_annual_flow_required",
            "aum * realized yield/pass-through * period timing",
        ),
        (
            "treasury_bills",
            "Treasury_or_Z1_bill_holdings",
            "bill_yield_or_discount_income_source_required",
            "auction_or_holding_period_income_required",
            "bill holdings * realized yield * period timing",
        ),
    ]
    return [
        {
            "diagnostic_row_id": f"constructed_safe_yield_flow::{instrument}",
            "object_role": "diagnostic_context",
            "instrument_family": instrument,
            "balance_source": balance_source,
            "yield_or_passthrough_source": yield_source,
            "periodization": periodization,
            "stock_to_flow_rule": stock_rule,
            "recipient_basis": "not_sufficient_for_selected_overlay",
            "overlap_risks": "public_interest;on_rrp_mmf;tdc;firm_cash",
            "constructed_flow_bil": "",
            "central_n_delta_bil_allowed": "false",
            "diagnostic_status": "diagnostic_context_constructed_flow_not_admitted",
            "allowed_use": "diagnostic_context_and_future_owner_gate_inputs",
            "blocked_use": (
                "selected_current_row;forecast_central_N;historical_final_classifier;"
                "raw_stock_mpc_shortcut"
            ),
            "claim_boundary": "constructed_safe_yield_diagnostic_no_selected_value_change",
        }
        for instrument, balance_source, yield_source, periodization, stock_rule in specs
    ]


def realized_safe_yield_gap_rows() -> list[dict[str, str]]:
    """Return the explicit D1 route row."""

    return [
        {
            "source_channel_id": "D1_deposit_safe_yield_route",
            "object_role": "blocked_source_or_method",
            "surface_role": "bounded_noncentral_reopen_lane",
            "build_status": "D1_required_route_bounded_fallback_now_source_backed_central_candidate_later",
            "claim_boundary": "D1_explicit_route_no_selected_value_change",
            "central_n_delta_bil_allowed": "false",
            "required_to_unpark": (
                "FFIEC_FDIC_and_NCUA_payer_flow_panels;recipient_allocation;"
                "same_period_D_alignment;overlap_proof;named_current_replacement_surface"
            ),
            "allowed_use": "bounded_noncentral_sensitivity_and_reopen_trigger",
            "blocked_use": "central_N_addition;current_benchmark_replacement",
        }
    ]


def realized_safe_yield_audit_rows(
    *,
    decision_rows: Sequence[Mapping[str, str]],
    deposit_rows: Sequence[Mapping[str, str]],
    admission_rows: Sequence[Mapping[str, str]],
    diagnostic_rows: Sequence[Mapping[str, str]],
    gap_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    checks = [
        (
            "single_required_decision",
            len(decision_rows) == 1
            and decision_rows[0]["decision"]
            == "deposit_required_bounded_noncentral_now_source_backed_candidate_later",
            len(decision_rows),
            "exactly one required safe-yield lane decision is emitted",
        ),
        (
            "central_additions_zero",
            all(
                decision_rows[0][field] == "0"
                for field in [
                    "central_forecast_addition_bil",
                    "central_current_benchmark_addition_bil",
                    "full_composite_current_addition_bil",
                    "full_composite_historical_addition_bil",
                ]
            ),
            len(decision_rows),
            "full composite and central additions stay zero",
        ),
        (
            "bank_first_guard_present",
            all(
                row["overlap_guard_id"] == "bank_first_vs_recipient_flow_xor"
                for row in deposit_rows
            ),
            len(deposit_rows),
            "deposit candidate uses bank-first versus recipient-flow XOR guard",
        ),
        (
            "diagnostics_not_central",
            all(
                row["central_n_delta_bil_allowed"] == "false"
                for row in diagnostic_rows
            ),
            len(diagnostic_rows),
            "constructed-flow diagnostics cannot affect central N",
        ),
        (
            "payer_flow_admission_fail_closed",
            len(admission_rows) == 1
            and admission_rows[0]["all_required_gates_pass"] == "false"
            and admission_rows[0]["central_n_delta_bil_allowed"] == "false"
            and admission_rows[0]["central_n_delta_bil"] == "0",
            len(admission_rows),
            "safe-yield payer-flow admission blocks central N until all gates pass",
        ),
        (
            "context_sources_not_substitutes",
            all(
                "context" in admission_rows[0][field]
                or admission_rows[0][field].startswith("missing")
                for field in [
                    "bea_personal_interest_context_status",
                    "irs_taxable_interest_context_status",
                    "bank_margin_context_status",
                ]
            ),
            len(admission_rows),
            "BEA, IRS, and bank-margin context cannot substitute for payer flow",
        ),
        (
            "denominator_alignment_required",
            len(admission_rows) == 1
            and admission_rows[0]["denominator_alignment_gate"].startswith("blocked_"),
            len(admission_rows),
            "candidate cashflow must align to the denominator period before admission",
        ),
        (
            "d1_route_not_parked",
            len(gap_rows) == 1
            and gap_rows[0]["build_status"]
            == "D1_required_route_bounded_fallback_now_source_backed_central_candidate_later",
            len(gap_rows),
            "D1 deposit route is explicit and not parked as the only treatment",
        ),
    ]
    return [
        {
            "realized_safe_yield_audit_row_id": f"realized_safe_yield_audit::{check_id}",
            "check_id": check_id,
            "check_status": "pass" if passed else "fail",
            "row_count": str(row_count),
            "required_rule": rule,
            "allowed_use": "realized_safe_yield_gate_audit",
            "blocked_use": "central_N_change_without_owner_gate",
        }
        for check_id, passed, row_count, rule in checks
    ]


def write_realized_safe_yield_outputs(
    output_dir: str | Path,
    *,
    inventory_rows: list[dict[str, str]],
    decision_rows: list[dict[str, str]],
    deposit_rows: list[dict[str, str]],
    admission_rows: list[dict[str, str]],
    diagnostic_rows: list[dict[str, str]],
    gap_rows: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
    fallback_basis_rows: list[dict[str, str]] | None = None,
    bounded_sensitivity_rows: list[dict[str, str]] | None = None,
) -> dict[str, Path]:
    out = Path(output_dir)
    outputs = {
        "inventory_csv": out / "ratewall_realized_safe_yield_income_source_inventory.csv",
        "decision_csv": out / "ratewall_realized_safe_yield_income_lane_decision.csv",
        "deposit_candidate_csv": out
        / "ratewall_deposit_interest_payer_flow_candidate.csv",
        "payer_flow_admission_csv": out
        / "ratewall_realized_safe_yield_payer_flow_admission.csv",
        "diagnostic_csv": out / "ratewall_constructed_safe_yield_flow_diagnostic.csv",
        "gap_csv": out / "ratewall_realized_safe_yield_income_gap.csv",
        "audit_csv": out / "ratewall_realized_safe_yield_income_audit.csv",
        "deposit_fallback_basis_csv": out
        / "ratewall_deposit_safe_yield_fallback_basis.csv",
        "bounded_sensitivity_csv": out
        / "ratewall_realized_safe_yield_bounded_sensitivity.csv",
    }
    write_rows(outputs["inventory_csv"], inventory_rows, SAFE_YIELD_SOURCE_INVENTORY_FIELDS)
    write_rows(outputs["decision_csv"], decision_rows, SAFE_YIELD_LANE_DECISION_FIELDS)
    write_rows(
        outputs["deposit_candidate_csv"],
        deposit_rows,
        DEPOSIT_PAYER_FLOW_CANDIDATE_FIELDS,
    )
    write_rows(
        outputs["payer_flow_admission_csv"],
        admission_rows,
        SAFE_YIELD_PAYER_FLOW_ADMISSION_FIELDS,
    )
    write_rows(
        outputs["diagnostic_csv"],
        diagnostic_rows,
        CONSTRUCTED_SAFE_YIELD_DIAGNOSTIC_FIELDS,
    )
    write_rows(outputs["gap_csv"], gap_rows, SAFE_YIELD_GAP_FIELDS)
    write_rows(outputs["audit_csv"], audit_rows, REALIZED_SAFE_YIELD_AUDIT_FIELDS)
    write_rows(
        outputs["deposit_fallback_basis_csv"],
        fallback_basis_rows or [],
        DEPOSIT_SAFE_YIELD_FALLBACK_BASIS_FIELDS,
    )
    write_rows(
        outputs["bounded_sensitivity_csv"],
        bounded_sensitivity_rows or [],
        REALIZED_SAFE_YIELD_BOUNDED_SENSITIVITY_FIELDS,
    )
    return outputs


def _inventory_row(
    *,
    candidate_id: str,
    label: str,
    family: str,
    artifact: str,
    instrument: str,
    recipient: str,
    start: str,
    end: str,
    frequency: str,
    realized_flow: bool,
    constructed: bool,
    stock_rule: bool,
    recipient_basis: bool,
    public_overlap: bool,
    tdc_overlap: bool,
    tax_limited: bool,
    status: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "candidate_id": candidate_id,
        "candidate_label": label,
        "source_family": family,
        "source_artifact": artifact,
        "instrument_scope": instrument,
        "recipient_scope": recipient,
        "period_coverage_start": start,
        "period_coverage_end": end,
        "frequency": frequency,
        "is_realized_income_flow": str(realized_flow).lower(),
        "is_constructed_flow": str(constructed).lower(),
        "requires_stock_to_flow_rule": str(stock_rule).lower(),
        "recipient_basis_available": str(recipient_basis).lower(),
        "public_interest_overlap_risk": str(public_overlap).lower(),
        "tdc_overlap_risk": str(tdc_overlap).lower(),
        "tax_scope_limitation": str(tax_limited).lower(),
        "admission_status": status,
        "next_action": next_action,
        "allowed_use": "realized_safe_yield_source_inventory",
        "blocked_use": "central_N_addition_without_period_flow_and_owner_gate",
        "claim_boundary": "safe_yield_inventory_no_selected_value_change",
    }


def _safe_yield_context_statuses(raw: Path) -> dict[str, str]:
    return {
        "bea_personal_interest": (
            "present_context_not_instrument_specific"
            if (
                raw
                / "current_demand_gdp_share/fspdp_official_component_sources/"
                "fred_csv/A064RC1Q027SBEA.csv"
            ).exists()
            else "missing_context_source"
        ),
        "irs_taxable_interest": (
            "present_tax_context_not_timing_conversion"
            if (raw / "irs_soi/irs_soi_2023_table_1_4_taxable_interest.csv").exists()
            else "missing_context_source"
        ),
        "bank_margin": (
            "present_bank_context_not_deposit_payer_flow"
            if (
                raw / "fdic_bank_margin_distribution/"
                "fdic_bank_margin_distribution_panel.csv"
            ).exists()
            else "missing_context_source"
        ),
    }


def _by_candidate(
    rows: Sequence[Mapping[str, str]], candidate_id: str
) -> Mapping[str, str]:
    for row in rows:
        if row["candidate_id"] == candidate_id:
            return row
    raise ValueError(f"missing safe-yield candidate row: {candidate_id}")


def _read_series_csv(source_dir: Path, series_id: str) -> dict[date, Decimal]:
    path = source_dir / f"{series_id}.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return {}
        date_col = _first_present(reader.fieldnames, ["observation_date", "DATE", "date"])
        value_col = _first_present(reader.fieldnames, [series_id, "value", "VALUE"])
        if value_col is None:
            value_col = next(
                (
                    field
                    for field in reader.fieldnames
                    if field.lower().startswith(series_id.lower() + "_")
                ),
                None,
            )
        if date_col is None or value_col is None:
            return {}
        rows: dict[date, Decimal] = {}
        for row in reader:
            parsed_date = _parse_date(row.get(date_col, ""))
            parsed_value = _parse_decimal(row.get(value_col, ""))
            if parsed_date is not None and parsed_value is not None:
                rows[parsed_date] = parsed_value
        return rows


def _period_average_rate(
    rows: Mapping[date, Decimal],
    period_start: date,
    period_end: date,
) -> Decimal | None:
    values = [
        value
        for observation_date, value in rows.items()
        if period_start <= observation_date <= period_end
    ]
    if not values:
        return None
    return sum(values) / Decimal(len(values))


def _current_denominator_reference(current_overlay_dir: Path) -> dict[str, str] | None:
    path = current_overlay_dir / "ratewall_current_assumption_benchmark.csv"
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get("selected_current_row") == "true":
                current_d = row.get("fixed_D_bil") or row.get("benchmark_D_bil")
                if current_d:
                    return {
                        "denominator_object_id": "current_assumption_benchmark::2026",
                        "current_D_bil": current_d,
                    }
    return None


def _quarter_start(value: date) -> date:
    month = ((value.month - 1) // 3) * 3 + 1
    return date(value.year, month, 1)


def _quarter_end(value: date) -> date:
    next_month = value.month + 3
    year = value.year + (next_month - 1) // 12
    month = ((next_month - 1) % 12) + 1
    return date(year, month, 1) - timedelta(days=1)


def _period_id(value: date) -> str:
    return f"{value.year}Q{((value.month - 1) // 3) + 1}"


def _median(values: Sequence[Decimal]) -> Decimal:
    midpoint = len(values) // 2
    if len(values) % 2:
        return values[midpoint]
    return (values[midpoint - 1] + values[midpoint]) / Decimal("2")


def _mean_decimal(values: Sequence[str] | Sequence[Decimal]) -> Decimal:
    parsed = [Decimal(value) for value in values]
    return sum(parsed) / Decimal(len(parsed))


def _first_present(options: Sequence[str], candidates: Sequence[str]) -> str | None:
    option_set = {option.lower(): option for option in options}
    for candidate in candidates:
        found = option_set.get(candidate.lower())
        if found is not None:
            return found
    return None


def _gate_passes(value: str) -> bool:
    return value == "pass" or value.startswith("pass_")


def _safe_yield_central_delta_bil(
    *,
    gross_flow_bil: str,
    recipient_share: str,
    coverage_alignment_factor: str,
    public_interest_overlap_share: str,
    tdc_overlap_share: str,
    firm_cash_overlap_share: str,
    leakage_share: str,
    current_spend_share: str,
) -> str:
    gross = _parse_decimal(gross_flow_bil) or Decimal("0")
    recipient = _parse_decimal(recipient_share) or Decimal("0")
    coverage = _parse_decimal(coverage_alignment_factor) or Decimal("0")
    public_overlap = _parse_decimal(public_interest_overlap_share) or Decimal("0")
    tdc_overlap = _parse_decimal(tdc_overlap_share) or Decimal("0")
    firm_overlap = _parse_decimal(firm_cash_overlap_share) or Decimal("0")
    leakage = _parse_decimal(leakage_share) or Decimal("0")
    spend = _parse_decimal(current_spend_share) or Decimal("0")
    overlap_share = public_overlap + tdc_overlap + firm_overlap
    nonoverlap = max(Decimal("0"), Decimal("1") - overlap_share)
    eligible = gross * recipient * coverage
    central = eligible * nonoverlap * (Decimal("1") - leakage) * spend
    return _fmt(central)


def _parse_date(raw: str | None) -> date | None:
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return None


def _parse_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    text = raw.strip().replace(",", "")
    if text in {"", "."}:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _fmt(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")

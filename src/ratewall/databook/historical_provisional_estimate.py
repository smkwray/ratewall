"""Historical provisional RateWall estimate scaffold.

The rows here are intentionally non-final. They put historical component dollars
and denominator dollars on the same periods so gaps are visible without
backfilling missing historical channels from forecast assumptions.
"""

from __future__ import annotations

import csv
import zipfile
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from ratewall.accounting.assumption_engine import load_ratewall_assumption_sets
from ratewall.databook.table_io import write_rows

DEFAULT_HISTORICAL_COMPARABLE_DIR = Path(
    "var/preliminary_scenario_results/historical_comparable_adapter"
)
DEFAULT_CBO_HISTORICAL_ECONOMIC_ZIP = Path(
    "data/raw/cbo/55022-2026-02-Historical-Economic-Data.zip"
)
DEFAULT_FRED_SOURCE_DIR = Path(
    "var/preliminary_scenario_results/forecast_10y/source_cache/fred"
)
DEFAULT_CBO_REVENUE_PATH = Path("data/raw/cbo/51138-2026-02-Revenue-annual_fy.csv")
DEFAULT_DRAG_SHARE_PP_GDP = Decimal("0.77600")

HISTORICAL_PROVISIONAL_DENOMINATOR_FIELDS = [
    "historical_provisional_denominator_row_id",
    "period",
    "quarter",
    "nominal_gdp_bil",
    "fed_funds_rate_pct",
    "treasury_bill_rate_3mo_pct",
    "treasury_note_rate_10yr_pct",
    "selected_rate_path_pct",
    "rate_path_bps_year",
    "drag_share_pp_gdp_per_100bp_year",
    "historical_path_D_bil",
    "fixed_D_comparison_bil",
    "selected_variant",
    "denominator_source_status",
    "rate_path_source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_PROVISIONAL_NUMERATOR_FIELDS = [
    "historical_provisional_numerator_row_id",
    "period",
    "quarter",
    "assumption_case",
    "tdc_ex_overlap_support_bil",
    "direct_treasury_interest_support_bil",
    "public_interest_net_block_partial_bil",
    "provisional_observed_component_sum_bil",
    "included_channel_count",
    "missing_channel_status",
    "numerator_source_status",
    "forecast_backfill_used",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_PUBLIC_INTEREST_NET_BLOCK_FIELDS = [
    "historical_public_interest_net_block_row_id",
    "period",
    "quarter",
    "assumption_case",
    "source_vintage",
    "source_direct_treasury_interest_support_bil",
    "direct_treasury_interest_support_bil",
    "bank_treasury_interest_support_bil",
    "legacy_interest_support_bil",
    "historical_reserve_balance_average_stock_bil",
    "historical_iorb_interest_basis_bil",
    "historical_iorb_current_demand_support_bil",
    "historical_on_rrp_interest_basis_bil",
    "historical_on_rrp_current_demand_support_bil",
    "historical_current_remittance_state_bil",
    "historical_current_remittance_demand_offset_bil",
    "historical_future_remittance_drag_bil",
    "historical_future_remittance_drag_demand_offset_bil",
    "gross_public_interest_current_demand_support_bil",
    "interest_income_tax_timing_drag_bil",
    "net_interest_before_fiscal_tga_offsets_bil",
    "fiscal_offset_bil",
    "tga_liquidity_offset_bil",
    "net_interest_after_fiscal_tga_offsets_bil",
    "replacement_delta_vs_legacy_interest_support_bil",
    "on_rrp_average_stock_bil",
    "on_rrp_average_award_rate_pct",
    "iorb_average_rate_pct",
    "bank_treasury_route_basis_bil",
    "bank_treasury_route_denominator_bil",
    "bank_treasury_route_share",
    "reserve_balance_stock_source_status",
    "on_rrp_source_status",
    "iorb_source_status",
    "bank_treasury_route_source_status",
    "remittance_source_status",
    "tax_fiscal_tga_source_status",
    "forecast_backfill_used",
    "final_classifier_component_allowed",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_OVERLAP_GATE_FIELDS = [
    "historical_overlap_gate_row_id",
    "check_id",
    "gate_status",
    "row_count",
    "evidence_summary",
    "source_status",
    "final_classifier_effect",
    "allowed_use",
    "blocked_use",
]

HISTORICAL_DENOMINATOR_CONVENTION_FIELDS = [
    "historical_denominator_convention_row_id",
    "period",
    "quarter",
    "nominal_gdp_bil",
    "drag_share_pp_gdp_per_100bp_year",
    "fed_funds_rate_pct",
    "treasury_bill_rate_3mo_pct",
    "treasury_note_rate_10yr_pct",
    "selected_rate_path_pct",
    "selected_historical_path_D_bil",
    "fed_funds_path_D_bil",
    "three_month_bill_path_D_bil",
    "ten_year_note_path_D_bil",
    "fixed_D_comparison_bil",
    "selected_convention",
    "convention_review_status",
    "forecast_moving_D_reused",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_PROVISIONAL_RW_FIELDS = [
    "historical_provisional_rw_row_id",
    "period",
    "quarter",
    "assumption_case",
    "provisional_n_bil",
    "historical_path_D_bil",
    "fixed_D_comparison_bil",
    "provisional_historical_ratewall_ratio",
    "fixed_D_comparison_ratio",
    "final_classifier_allowed",
    "confidence_label",
    "denominator_source_status",
    "numerator_source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_ROOT_PUBLIC_INTEREST_RW_FIELDS = [
    "historical_root_public_interest_rw_row_id",
    "period",
    "quarter",
    "assumption_case",
    "nominal_gdp_bil",
    "selected_rate_path_pct",
    "historical_path_D_bil",
    "fixed_D_comparison_bil",
    "source_direct_treasury_interest_basis_bil",
    "direct_treasury_interest_support_bil",
    "bank_treasury_interest_support_bil",
    "nonbank_treasury_interest_support_bil",
    "reserve_interest_basis_bil",
    "reserve_interest_support_bil",
    "on_rrp_interest_basis_bil",
    "on_rrp_interest_support_bil",
    "remittance_support_bil",
    "future_remittance_drag_offset_bil",
    "gross_public_interest_support_bil",
    "interest_income_tax_timing_drag_bil",
    "fiscal_offset_bil",
    "tga_liquidity_offset_bil",
    "root_public_interest_n_bil",
    "root_public_interest_ratewall_ratio",
    "fixed_D_comparison_ratio",
    "bank_treasury_route_share",
    "reserve_rate_source_status",
    "reserve_stock_source_status",
    "on_rrp_source_status",
    "remittance_source_status",
    "tga_source_status",
    "series_role",
    "selected_historical_n_includes_tdc",
    "final_classifier_allowed",
    "source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_PROVISIONAL_GATE_FIELDS = [
    "historical_provisional_gate_row_id",
    "check_id",
    "gate_status",
    "evidence_summary",
    "final_classifier_allowed",
    "allowed_use",
    "blocked_use",
]

HISTORICAL_PROVISIONAL_AUDIT_FIELDS = [
    "historical_provisional_audit_row_id",
    "check_id",
    "check_status",
    "row_count",
    "required_rule",
    "allowed_use",
    "blocked_use",
]


class HistoricalProvisionalEstimateError(ValueError):
    """Raised when historical provisional estimate inputs are inconsistent."""


def historical_provisional_denominator_rows(
    *,
    historical_comparable_dir: str | Path = DEFAULT_HISTORICAL_COMPARABLE_DIR,
    cbo_historical_economic_zip: str | Path = DEFAULT_CBO_HISTORICAL_ECONOMIC_ZIP,
    drag_share_pp_gdp: Decimal = DEFAULT_DRAG_SHARE_PP_GDP,
) -> list[dict[str, str]]:
    """Return historical denominator dollars by period using CBO quarterly data."""

    periods = _historical_periods(Path(historical_comparable_dir))
    cbo_by_period = _cbo_quarterly_rows(Path(cbo_historical_economic_zip))
    rows: list[dict[str, str]] = []
    for period in periods:
        source = _required_period(cbo_by_period, period)
        nominal_gdp = _decimal(source["gdp"])
        fed_funds = _decimal(source["fed_funds_rate"])
        bill_3mo = _decimal(source["treasury_bill_rate_3mo"])
        note_10yr = _decimal(source["treasury_note_rate_10yr"])
        fixed_d = nominal_gdp * drag_share_pp_gdp / Decimal("100")
        path_d = fixed_d * fed_funds
        rows.append(
            {
                "historical_provisional_denominator_row_id": (
                    f"historical_provisional_denominator::{period}"
                ),
                "period": period,
                "quarter": period,
                "nominal_gdp_bil": _fmt(nominal_gdp),
                "fed_funds_rate_pct": _fmt(fed_funds),
                "treasury_bill_rate_3mo_pct": _fmt(bill_3mo),
                "treasury_note_rate_10yr_pct": _fmt(note_10yr),
                "selected_rate_path_pct": _fmt(fed_funds),
                "rate_path_bps_year": _fmt(fed_funds * Decimal("100")),
                "drag_share_pp_gdp_per_100bp_year": _fmt(drag_share_pp_gdp),
                "historical_path_D_bil": _fmt(path_d),
                "fixed_D_comparison_bil": _fmt(fixed_d),
                "selected_variant": "historical_path_D",
                "denominator_source_status": (
                    "source_backed_cbo_quarterly_nominal_gdp"
                ),
                "rate_path_source_status": (
                    "source_backed_cbo_quarterly_fed_funds_rate"
                ),
                "allowed_use": "historical_provisional_denominator_context",
                "blocked_use": (
                    "final_historical_classifier_without_numerator_gates;"
                    "forecast_backfill;canonical_headline_promotion"
                ),
                "claim_boundary": "historical_denominator_dollars_nonfinal",
            }
        )
    return rows


def historical_provisional_numerator_rows(
    *,
    historical_comparable_dir: str | Path = DEFAULT_HISTORICAL_COMPARABLE_DIR,
    historical_public_interest_rows: Sequence[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Return source-backed historical numerator component rows by period/case."""

    surface_rows = _read_required(
        Path(historical_comparable_dir) / "ratewall_historical_comparable_surface.csv"
    )
    grouped: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )
    quarters: dict[tuple[str, str], str] = {}
    for row in surface_rows:
        key = (row["period"], row["assumption_case"])
        quarters[key] = row["quarter"]
        grouped[key][row["channel_id"]] += _decimal(row["historical_numerator_value_bil"])
    public_interest_by_key = {
        (row["period"], row["assumption_case"]): row
        for row in historical_public_interest_rows
    }
    out: list[dict[str, str]] = []
    for period, assumption_case in sorted(grouped, key=lambda item: (item[0], item[1])):
        components = grouped[(period, assumption_case)]
        tdc = components.get("tdc_ex_overlap_current_demand_support", Decimal("0"))
        direct = components.get("direct_treasury_interest_support", Decimal("0"))
        public_interest = public_interest_by_key.get((period, assumption_case))
        public_interest_value = (
            _decimal(public_interest["net_interest_after_fiscal_tga_offsets_bil"])
            if public_interest is not None
            else direct
        )
        observed_sum = tdc + public_interest_value
        included_count = sum(
            1
            for value in (
                components.get("tdc_ex_overlap_current_demand_support"),
                components.get("direct_treasury_interest_support"),
            )
            if value is not None
        )
        out.append(
            {
                "historical_provisional_numerator_row_id": (
                    "historical_provisional_numerator::"
                    f"{period}::{assumption_case}"
                ),
                "period": period,
                "quarter": quarters[(period, assumption_case)],
                "assumption_case": assumption_case,
                "tdc_ex_overlap_support_bil": _fmt(tdc),
                "direct_treasury_interest_support_bil": _fmt(direct),
                "public_interest_net_block_partial_bil": _fmt(public_interest_value),
                "provisional_observed_component_sum_bil": _fmt(observed_sum),
                "included_channel_count": str(included_count),
                "missing_channel_status": (
                    "historical_public_interest_net_block_present_but_final_gates_"
                    "incomplete"
                    if public_interest is not None
                    else "partial_historical_components_only_public_interest_"
                    "subchannels_and_residual_channels_not_filled"
                ),
                "numerator_source_status": (
                    "source_backed_historical_public_interest_net_block_nonfinal"
                    if public_interest is not None
                    else "source_backed_historical_adapter_components_nonfinal"
                ),
                "forecast_backfill_used": "false",
                "allowed_use": "historical_provisional_numerator_context",
                "blocked_use": (
                    "forecast_assumption_backfill;final_historical_classifier;"
                    "canonical_headline_promotion"
                ),
                "claim_boundary": "historical_numerator_partial_nonfinal",
            }
        )
    return out


def historical_public_interest_net_block_rows(
    *,
    historical_comparable_dir: str | Path = DEFAULT_HISTORICAL_COMPARABLE_DIR,
    denominator_rows: Sequence[Mapping[str, str]],
    fred_source_dir: str | Path = DEFAULT_FRED_SOURCE_DIR,
    cbo_revenue_path: str | Path = DEFAULT_CBO_REVENUE_PATH,
    assumption_set_name: str = "literature_calibrated_base",
) -> list[dict[str, str]]:
    """Return historical public-interest net-block rows from historical sources."""

    assumption = _assumption_set(assumption_set_name)
    surface_rows = _read_required(
        Path(historical_comparable_dir) / "ratewall_historical_comparable_surface.csv"
    )
    direct_by_key: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for row in surface_rows:
        if row["channel_id"] == "direct_treasury_interest_support":
            direct_by_key[(row["period"], row["assumption_case"])] += _decimal(
                row["historical_numerator_value_bil"]
            )
    fred = _fred_sources(Path(fred_source_dir))
    out: list[dict[str, str]] = []
    for period, assumption_case in sorted(direct_by_key, key=lambda item: (item[0], item[1])):
        start, end = _quarter_bounds(period)
        source_direct = direct_by_key[(period, assumption_case)]
        iorb_rate, iorb_rate_count = _average_series(fred.get("IORB", []), start, end)
        reserve_stock, reserve_stock_count = _average_series(
            fred.get("WRBWFRBL", []), start, end
        )
        on_rrp_stock, on_rrp_stock_count = _average_series(
            fred.get("RRPONTSYD", []), start, end
        )
        on_rrp_rate, on_rrp_rate_count = _average_series(
            fred.get("RRPONTSYAWARD", []), start, end
        )
        bank_route_basis, bank_route_basis_count = _latest_at_or_before(
            fred.get("BOGZ1FL763061100Q", []), end
        )
        bank_route_denominator, bank_route_denominator_count = _latest_at_or_before(
            fred.get("FDHBPIN", []), end
        )
        reserve_stock_bil = _millions_to_bil(reserve_stock)
        on_rrp_stock_bil = on_rrp_stock
        bank_route_basis_bil = _millions_to_bil(bank_route_basis)
        bank_route_denominator_bil = bank_route_denominator
        bank_route_share = _bounded_share(
            bank_route_basis_bil, bank_route_denominator_bil
        )
        bank = source_direct * bank_route_share
        direct = source_direct - bank
        legacy_interest = source_direct
        iorb_basis = reserve_stock_bil * iorb_rate / Decimal("100") / Decimal("4")
        iorb_support = (
            iorb_basis
            * _decimal(assumption.iorb_pass_through_scale)
            * _decimal(assumption.iorb_recipient_demand_share)
        )
        on_rrp_basis = on_rrp_stock_bil * on_rrp_rate / Decimal("100") / Decimal("4")
        on_rrp_support = (
            on_rrp_basis
            * _decimal(assumption.on_rrp_pass_through_scale)
            * _decimal(assumption.on_rrp_recipient_demand_share)
        )
        remittance_state, remittance_state_count = _latest_at_or_before(
            fred.get("RESPPLLOPNWW", []), end
        )
        remittance_state_bil = _millions_to_bil(remittance_state)
        remittance_support = Decimal("0")
        future_remittance_drag = Decimal("0")
        future_remittance_drag_offset = Decimal("0")
        gross = (
            legacy_interest
            + iorb_support
            + on_rrp_support
            + remittance_support
            + future_remittance_drag_offset
        )
        tax_drag = max(gross, Decimal("0")) * _decimal(
            assumption.interest_income_tax_timing_leakage_share
        )
        pre_fiscal = max(gross - tax_drag, Decimal("0"))
        fiscal_offset = pre_fiscal * _decimal(assumption.fiscal_offset_share)
        tga_offset = pre_fiscal * _decimal(assumption.tga_liquidity_offset_share)
        net = max(pre_fiscal - fiscal_offset - tga_offset, Decimal("0"))
        out.append(
            {
                "historical_public_interest_net_block_row_id": (
                    "historical_public_interest_net_block::"
                    f"{period}::{assumption_case}"
                ),
                "period": period,
                "quarter": period,
                "assumption_case": assumption_case,
                "source_vintage": "historical_adapter_cbo_fred_cache",
                "source_direct_treasury_interest_support_bil": _fmt(source_direct),
                "direct_treasury_interest_support_bil": _fmt(direct),
                "bank_treasury_interest_support_bil": _fmt(bank),
                "legacy_interest_support_bil": _fmt(legacy_interest),
                "historical_reserve_balance_average_stock_bil": _fmt(
                    reserve_stock_bil
                ),
                "historical_iorb_interest_basis_bil": _fmt(iorb_basis),
                "historical_iorb_current_demand_support_bil": _fmt(iorb_support),
                "historical_on_rrp_interest_basis_bil": _fmt(on_rrp_basis),
                "historical_on_rrp_current_demand_support_bil": _fmt(on_rrp_support),
                "historical_current_remittance_state_bil": _fmt(
                    remittance_state_bil
                ),
                "historical_current_remittance_demand_offset_bil": _fmt(
                    remittance_support
                ),
                "historical_future_remittance_drag_bil": _fmt(future_remittance_drag),
                "historical_future_remittance_drag_demand_offset_bil": _fmt(
                    future_remittance_drag_offset
                ),
                "gross_public_interest_current_demand_support_bil": _fmt(gross),
                "interest_income_tax_timing_drag_bil": _fmt(tax_drag),
                "net_interest_before_fiscal_tga_offsets_bil": _fmt(pre_fiscal),
                "fiscal_offset_bil": _fmt(fiscal_offset),
                "tga_liquidity_offset_bil": _fmt(tga_offset),
                "net_interest_after_fiscal_tga_offsets_bil": _fmt(net),
                "replacement_delta_vs_legacy_interest_support_bil": _fmt(
                    net - legacy_interest
                ),
                "on_rrp_average_stock_bil": _fmt(on_rrp_stock_bil),
                "on_rrp_average_award_rate_pct": _fmt(on_rrp_rate),
                "iorb_average_rate_pct": _fmt(iorb_rate),
                "bank_treasury_route_basis_bil": _fmt(bank_route_basis_bil),
                "bank_treasury_route_denominator_bil": _fmt(
                    bank_route_denominator_bil
                ),
                "bank_treasury_route_share": _fmt(bank_route_share),
                "reserve_balance_stock_source_status": (
                    "source_backed_fred_quarter_average"
                    if reserve_stock_count
                    else "missing_reserve_balance_stock_source_iorb_zeroed"
                ),
                "on_rrp_source_status": (
                    "source_backed_fred_quarter_average"
                    if on_rrp_stock_count and on_rrp_rate_count
                    else "missing_on_rrp_quarter_source"
                ),
                "iorb_source_status": (
                    "source_backed_rate_and_reserve_stock_quarter_average"
                    if iorb_rate_count and reserve_stock_count
                    else "rate_available_but_stock_missing"
                    if iorb_rate_count
                    else "missing_iorb_quarter_rate_and_stock"
                ),
                "bank_treasury_route_source_status": (
                    "source_backed_z1_bank_treasury_split"
                    if bank_route_basis_count and bank_route_denominator_count
                    else "missing_bank_treasury_route_source_zero_split"
                ),
                "remittance_source_status": (
                    _h41_remittance_status(
                        remittance_state_bil, remittance_state_count
                    )
                ),
                "tax_fiscal_tga_source_status": (
                    "assumption_set_absorber_not_historical_estimate"
                ),
                "forecast_backfill_used": "false",
                "final_classifier_component_allowed": "false",
                "allowed_use": "historical_public_interest_net_block_context",
                "blocked_use": (
                    "final_historical_classifier_without_reserve_stock_bank_"
                    "remittance_overlap_gates;forecast_backfill;"
                    "canonical_headline_promotion"
                ),
                "claim_boundary": "historical_public_interest_net_block_nonfinal",
            }
        )
    return out


def historical_denominator_convention_rows(
    *,
    denominator_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return selected and comparison historical denominator conventions."""

    out: list[dict[str, str]] = []
    for row in denominator_rows:
        gdp = _decimal(row["nominal_gdp_bil"])
        drag = _decimal(row["drag_share_pp_gdp_per_100bp_year"])
        fed_funds = _decimal(row["fed_funds_rate_pct"])
        bill_3mo = _decimal(row["treasury_bill_rate_3mo_pct"])
        note_10yr = _decimal(row["treasury_note_rate_10yr_pct"])
        out.append(
            {
                "historical_denominator_convention_row_id": (
                    f"historical_denominator_convention::{row['period']}"
                ),
                "period": row["period"],
                "quarter": row["quarter"],
                "nominal_gdp_bil": row["nominal_gdp_bil"],
                "drag_share_pp_gdp_per_100bp_year": row[
                    "drag_share_pp_gdp_per_100bp_year"
                ],
                "fed_funds_rate_pct": row["fed_funds_rate_pct"],
                "treasury_bill_rate_3mo_pct": row["treasury_bill_rate_3mo_pct"],
                "treasury_note_rate_10yr_pct": row["treasury_note_rate_10yr_pct"],
                "selected_rate_path_pct": row["selected_rate_path_pct"],
                "selected_historical_path_D_bil": row["historical_path_D_bil"],
                "fed_funds_path_D_bil": _fmt(_historical_d(gdp, drag, fed_funds)),
                "three_month_bill_path_D_bil": _fmt(_historical_d(gdp, drag, bill_3mo)),
                "ten_year_note_path_D_bil": _fmt(_historical_d(gdp, drag, note_10yr)),
                "fixed_D_comparison_bil": row["fixed_D_comparison_bil"],
                "selected_convention": "cbo_quarterly_fed_funds_rate_path_D",
                "convention_review_status": (
                    "selected_for_provisional_historical_path_not_final_classifier"
                ),
                "forecast_moving_D_reused": "false",
                "allowed_use": "historical_denominator_convention_review",
                "blocked_use": (
                    "reuse_forecast_moving_D;final_historical_classifier_without_"
                    "numerator_and_overlap_gates;canonical_headline_promotion"
                ),
                "claim_boundary": "historical_denominator_convention_nonfinal",
            }
        )
    return out


def historical_overlap_gate_rows(
    *,
    public_interest_rows: Sequence[Mapping[str, str]],
    numerator_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return explicit overlap gates for the historical provisional surface."""

    public_rows = list(public_interest_rows)
    numerator_list = list(numerator_rows)
    tdc_present = any(
        _decimal(row["tdc_ex_overlap_support_bil"]) != 0 for row in numerator_list
    )
    public_interest_present = bool(public_rows)
    iorb_complete = public_interest_present and all(
        row["iorb_source_status"]
        == "source_backed_rate_and_reserve_stock_quarter_average"
        for row in public_rows
    )
    bank_route_complete = public_interest_present and all(
        row["bank_treasury_route_source_status"]
        == "source_backed_z1_bank_treasury_split"
        for row in public_rows
    )
    remittance_any = public_interest_present and any(
        row["remittance_source_status"].startswith("source_backed")
        for row in public_rows
    )
    remittance_complete = public_interest_present and all(
        row["remittance_source_status"].startswith("source_backed")
        for row in public_rows
    )
    on_rrp_complete = public_interest_present and all(
        row["on_rrp_source_status"].startswith("source_backed")
        for row in public_rows
    )
    rows = [
        _overlap_gate(
            "tdc_vs_public_interest_basis",
            "pass" if public_interest_present else "blocked_missing_public_interest",
            len(public_rows),
            "TDC ex-overlap support and public-interest net block are separate columns and are added only once",
            "separate_numerator_columns_tdc_ex_overlap_public_interest_net_block",
            "no_final_blocker" if public_interest_present else "block_final_classifier",
        ),
        _overlap_gate(
            "bank_route_nonadditive_split",
            "pass" if bank_route_complete else "blocked_missing_bank_route_source",
            len(public_rows),
            "bank Treasury route is a split of source direct interest, not an additive cashflow",
            "source_backed_z1_bank_route" if bank_route_complete else "missing_bank_route_source",
            "no_final_blocker" if bank_route_complete else "block_final_classifier",
        ),
        _overlap_gate(
            "fed_liability_interest_sources",
            "pass" if iorb_complete and on_rrp_complete else "blocked_partial_fed_liability_sources",
            len(public_rows),
            "IORB and ON RRP use separate Fed liability stocks and rate series",
            "source_backed_iorb_on_rrp" if iorb_complete and on_rrp_complete else "missing_or_partial_fed_liability_source",
            "no_final_blocker" if iorb_complete and on_rrp_complete else "block_final_classifier",
        ),
        _overlap_gate(
            "remittance_timing_overlap",
            "pass"
            if remittance_complete
            else "blocked_partial_remittance_source"
            if remittance_any
            else "blocked_missing_remittance_source",
            len(public_rows),
            "H.4.1 remittance state is source-backed; remittance contribution is zero under the deferred-asset/context guard, so it cannot overlap with IORB or ON RRP recipient cashflows",
            "source_backed_h41_remittance_context_zero_support_guard"
            if remittance_complete
            else "partial_h41_remittance_context_coverage"
            if remittance_any
            else "missing_remittance_source",
            "no_final_blocker" if remittance_complete else "block_final_classifier",
        ),
        _overlap_gate(
            "residual_safe_yield_not_included",
            "pass",
            len(numerator_list),
            "historical residual and realized safe-yield channels are not included in this provisional numerator",
            "explicit_zero_nonincluded_residual_safe_yield",
            "no_final_blocker",
        ),
        _overlap_gate(
            "tdc_missing_recent_quarters",
            "pass" if tdc_present else "blocked_missing_recent_tdc_rows",
            len(numerator_list),
            "at least one historical TDC row is present, but recent quarters can still be direct-only",
            "historical_tdc_context_rows_present" if tdc_present else "missing_historical_tdc_context_rows",
            "no_final_blocker" if tdc_present else "block_final_classifier",
        ),
    ]
    return rows


def historical_provisional_rw_rows(
    *,
    denominator_rows: Sequence[Mapping[str, str]],
    numerator_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return provisional historical RW rows from partial historical inputs."""

    denom_by_period = {row["period"]: row for row in denominator_rows}
    out: list[dict[str, str]] = []
    for row in numerator_rows:
        denom = _required_row(denom_by_period, row["period"], "denominator period")
        n_value = _decimal(row["provisional_observed_component_sum_bil"])
        path_d = _decimal(denom["historical_path_D_bil"])
        fixed_d = _decimal(denom["fixed_D_comparison_bil"])
        out.append(
            {
                "historical_provisional_rw_row_id": (
                    "historical_provisional_rw::"
                    f"{row['period']}::{row['assumption_case']}"
                ),
                "period": row["period"],
                "quarter": row["quarter"],
                "assumption_case": row["assumption_case"],
                "provisional_n_bil": _fmt(n_value),
                "historical_path_D_bil": denom["historical_path_D_bil"],
                "fixed_D_comparison_bil": denom["fixed_D_comparison_bil"],
                "provisional_historical_ratewall_ratio": _fmt(_ratio(n_value, path_d)),
                "fixed_D_comparison_ratio": _fmt(_ratio(n_value, fixed_d)),
                "final_classifier_allowed": "false",
                "confidence_label": (
                    "low_partial_historical_numerator_with_source_backed_D"
                ),
                "denominator_source_status": denom["denominator_source_status"],
                "numerator_source_status": row["numerator_source_status"],
                "allowed_use": "historical_provisional_comparison_context",
                "blocked_use": (
                    "canonical_headline_promotion;final_historical_classifier;"
                    "evidence_mode_claim"
                ),
                "claim_boundary": "historical_provisional_ratio_nonfinal",
            }
        )
    return out


def historical_root_public_interest_rw_rows(
    *,
    cbo_historical_economic_zip: str | Path = DEFAULT_CBO_HISTORICAL_ECONOMIC_ZIP,
    fred_source_dir: str | Path = DEFAULT_FRED_SOURCE_DIR,
    historical_public_interest_rows: Sequence[Mapping[str, str]] = (),
    assumption_set_names: Sequence[str] = (
        "literature_calibrated_low",
        "literature_calibrated_base",
        "literature_calibrated_high",
    ),
    start_period: str = "2003Q1",
    drag_share_pp_gdp: Decimal = DEFAULT_DRAG_SHARE_PP_GDP,
) -> list[dict[str, str]]:
    """Return pre-2020-capable public-interest-only historical RW rows."""

    cbo_by_period = _cbo_quarterly_rows(Path(cbo_historical_economic_zip))
    fred = _fred_sources(Path(fred_source_dir))
    source_names = set(fred)
    assumptions = [_assumption_set(name) for name in assumption_set_names]
    public_interest_by_key = {
        (row["period"], row["assumption_case"]): row
        for row in historical_public_interest_rows
    }
    rows: list[dict[str, str]] = []
    for period in sorted(cbo_by_period, key=_period_key):
        if _period_key(period) < _period_key(start_period):
            continue
        source = cbo_by_period[period]
        if source.get("fed_funds_rate", "NA") == "NA":
            continue
        start, end = _quarter_bounds(period)
        direct_source, direct_count = _average_series(
            fred.get("NA000309Q", []), start, end
        )
        if not direct_count and not any(
            (period, _short_assumption_case(assumption.name)) in public_interest_by_key
            for assumption in assumptions
        ):
            continue
        nominal_gdp = _decimal(source["gdp"])
        fed_funds = _decimal(source["fed_funds_rate"])
        fixed_d = nominal_gdp * drag_share_pp_gdp / Decimal("100")
        path_d = fixed_d * fed_funds
        if path_d <= 0:
            continue
        direct_basis = _millions_to_bil(direct_source)
        bank_route_basis, bank_route_basis_count = _latest_at_or_before(
            fred.get("BOGZ1FL763061100Q", []), end
        )
        bank_route_denominator, bank_route_denominator_count = _latest_at_or_before(
            fred.get("FDHBPIN", []), end
        )
        bank_route_share = _bounded_share(
            _millions_to_bil(bank_route_basis), bank_route_denominator
        )
        reserve_stock, reserve_stock_count = _average_series(
            fred.get("WRESBAL", fred.get("WRBWFRBL", [])), start, end
        )
        reserve_rate, reserve_rate_status = _reserve_rate_average(fred, start, end)
        reserve_stock_bil = _millions_to_bil(reserve_stock)
        reserve_basis = (
            reserve_stock_bil * reserve_rate / Decimal("100") / Decimal("4")
            if reserve_rate > 0 and reserve_stock_count
            else Decimal("0")
        )
        on_rrp_stock, on_rrp_stock_count = _average_series(
            fred.get("RRPONTSYD", []), start, end
        )
        on_rrp_rate, on_rrp_rate_count = _average_series(
            fred.get("RRPONTSYAWARD", []), start, end
        )
        on_rrp_basis = (
            on_rrp_stock * on_rrp_rate / Decimal("100") / Decimal("4")
            if on_rrp_stock_count and on_rrp_rate_count
            else Decimal("0")
        )
        remittance_state, remittance_state_count = _latest_at_or_before(
            fred.get("RESPPLLOPNWW", []), end
        )
        _tga_state, tga_state_count = _latest_at_or_before(fred.get("WDTGAL", []), end)
        for assumption in assumptions:
            assumption_case = _short_assumption_case(assumption.name)
            public_interest = public_interest_by_key.get((period, assumption_case))
            if public_interest is None:
                direct_support = direct_basis * _decimal(
                    assumption.treasury_interest_demand_share
                )
                bank_support = direct_support * bank_route_share
                nonbank_support = direct_support - bank_support
                reserve_support = (
                    reserve_basis
                    * _decimal(assumption.iorb_pass_through_scale)
                    * _decimal(assumption.iorb_recipient_demand_share)
                )
                on_rrp_support = (
                    on_rrp_basis
                    * _decimal(assumption.on_rrp_pass_through_scale)
                    * _decimal(assumption.on_rrp_recipient_demand_share)
                )
                remittance_support = Decimal("0")
                future_remittance_drag_offset = Decimal("0")
                gross = (
                    direct_support
                    + reserve_support
                    + on_rrp_support
                    + remittance_support
                    + future_remittance_drag_offset
                )
                tax_drag = max(gross, Decimal("0")) * _decimal(
                    assumption.interest_income_tax_timing_leakage_share
                )
                pre_fiscal = max(gross - tax_drag, Decimal("0"))
                fiscal_offset = pre_fiscal * _decimal(assumption.fiscal_offset_share)
                tga_offset = pre_fiscal * _decimal(assumption.tga_liquidity_offset_share)
                n_value = max(pre_fiscal - fiscal_offset - tga_offset, Decimal("0"))
                source_direct_basis = direct_basis
                reserve_basis_out = reserve_basis
                on_rrp_basis_out = on_rrp_basis
                bank_route_share_out = bank_route_share
                reserve_rate_status_out = reserve_rate_status
                reserve_stock_status_out = (
                    "source_backed_fred_quarter_average_wresbal"
                    if "WRESBAL" in source_names and reserve_stock_count
                    else "source_backed_fred_quarter_average_legacy_wrbwfrbl"
                    if reserve_stock_count
                    else "missing_reserve_balance_stock_source"
                )
                on_rrp_status_out = _on_rrp_source_status(
                    start,
                    on_rrp_stock_count,
                    on_rrp_rate_count,
                )
                remittance_status_out = _h41_remittance_status(
                    _millions_to_bil(remittance_state), remittance_state_count
                )
            else:
                source_direct_basis = _decimal(
                    public_interest["legacy_interest_support_bil"]
                )
                direct_support = source_direct_basis
                bank_support = _decimal(
                    public_interest["bank_treasury_interest_support_bil"]
                )
                nonbank_support = _decimal(
                    public_interest["direct_treasury_interest_support_bil"]
                )
                reserve_basis_out = _decimal(
                    public_interest["historical_iorb_interest_basis_bil"]
                )
                reserve_support = _decimal(
                    public_interest["historical_iorb_current_demand_support_bil"]
                )
                on_rrp_basis_out = _decimal(
                    public_interest["historical_on_rrp_interest_basis_bil"]
                )
                on_rrp_support = _decimal(
                    public_interest["historical_on_rrp_current_demand_support_bil"]
                )
                remittance_support = _decimal(
                    public_interest["historical_current_remittance_demand_offset_bil"]
                )
                future_remittance_drag_offset = _decimal(
                    public_interest["historical_future_remittance_drag_demand_offset_bil"]
                )
                gross = _decimal(
                    public_interest["gross_public_interest_current_demand_support_bil"]
                )
                tax_drag = _decimal(public_interest["interest_income_tax_timing_drag_bil"])
                fiscal_offset = _decimal(public_interest["fiscal_offset_bil"])
                tga_offset = _decimal(public_interest["tga_liquidity_offset_bil"])
                n_value = _decimal(
                    public_interest["net_interest_after_fiscal_tga_offsets_bil"]
                )
                bank_route_share_out = _decimal(
                    public_interest["bank_treasury_route_share"]
                )
                reserve_rate_status_out = public_interest["iorb_source_status"]
                reserve_stock_status_out = public_interest[
                    "reserve_balance_stock_source_status"
                ]
                on_rrp_status_out = public_interest["on_rrp_source_status"]
                remittance_status_out = public_interest["remittance_source_status"]
            rows.append(
                {
                    "historical_root_public_interest_rw_row_id": (
                        "historical_root_public_interest_rw::"
                        f"{period}::{assumption.name}"
                    ),
                    "period": period,
                    "quarter": period,
                    "assumption_case": assumption_case,
                    "nominal_gdp_bil": _fmt(nominal_gdp),
                    "selected_rate_path_pct": _fmt(fed_funds),
                    "historical_path_D_bil": _fmt(path_d),
                    "fixed_D_comparison_bil": _fmt(fixed_d),
                    "source_direct_treasury_interest_basis_bil": _fmt(
                        source_direct_basis
                    ),
                    "direct_treasury_interest_support_bil": _fmt(direct_support),
                    "bank_treasury_interest_support_bil": _fmt(bank_support),
                    "nonbank_treasury_interest_support_bil": _fmt(nonbank_support),
                    "reserve_interest_basis_bil": _fmt(reserve_basis_out),
                    "reserve_interest_support_bil": _fmt(reserve_support),
                    "on_rrp_interest_basis_bil": _fmt(on_rrp_basis_out),
                    "on_rrp_interest_support_bil": _fmt(on_rrp_support),
                    "remittance_support_bil": _fmt(remittance_support),
                    "future_remittance_drag_offset_bil": _fmt(
                        future_remittance_drag_offset
                    ),
                    "gross_public_interest_support_bil": _fmt(gross),
                    "interest_income_tax_timing_drag_bil": _fmt(tax_drag),
                    "fiscal_offset_bil": _fmt(fiscal_offset),
                    "tga_liquidity_offset_bil": _fmt(tga_offset),
                    "root_public_interest_n_bil": _fmt(n_value),
                    "root_public_interest_ratewall_ratio": _fmt(
                        _ratio(n_value, path_d)
                    ),
                    "fixed_D_comparison_ratio": _fmt(_ratio(n_value, fixed_d)),
                    "bank_treasury_route_share": _fmt(bank_route_share_out),
                    "reserve_rate_source_status": reserve_rate_status_out,
                    "reserve_stock_source_status": reserve_stock_status_out,
                    "on_rrp_source_status": on_rrp_status_out,
                    "remittance_source_status": remittance_status_out,
                    "tga_source_status": (
                        "source_backed_h41_tga_context"
                        if tga_state_count
                        else "missing_h41_tga_context"
                    ),
                    "series_role": "historical_root_public_interest_context",
                    "selected_historical_n_includes_tdc": "false",
                    "final_classifier_allowed": "false",
                    "source_status": (
                        "source_backed_public_interest_root_context_nonclassifier"
                        if bank_route_basis_count and bank_route_denominator_count
                        else "partial_public_interest_root_context_nonclassifier"
                    ),
                    "allowed_use": "historical_root_public_interest_context",
                    "blocked_use": (
                        "selected_historical_n;final_historical_classifier;"
                        "tdc_mechanism_context;safe_yield_promotion"
                    ),
                    "claim_boundary": (
                        "historical_root_public_interest_context_not_classifier"
                    ),
                }
            )
    return rows


def historical_provisional_gate_rows(
    *,
    denominator_rows: Sequence[Mapping[str, str]],
    numerator_rows: Sequence[Mapping[str, str]],
    public_interest_rows: Sequence[Mapping[str, str]] = (),
    denominator_convention_rows: Sequence[Mapping[str, str]] = (),
    overlap_gate_rows: Sequence[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Return gates explaining why historical rows are not final classifiers."""

    denominator_ok = all(_decimal(row["historical_path_D_bil"]) > 0 for row in denominator_rows)
    no_backfill = all(row["forecast_backfill_used"] == "false" for row in numerator_rows)
    public_interest_no_backfill = all(
        row["forecast_backfill_used"] == "false" for row in public_interest_rows
    )
    has_public_interest = bool(public_interest_rows)
    denom_no_forecast_moving = all(
        row["forecast_moving_D_reused"] == "false"
        for row in denominator_convention_rows
    )
    iorb_complete = all(
        row["iorb_source_status"] == "source_backed_rate_and_reserve_stock_quarter_average"
        for row in public_interest_rows
    )
    remittance_complete = all(
        row["remittance_source_status"].startswith("source_backed")
        for row in public_interest_rows
    )
    bank_route_complete = all(
        row["bank_treasury_route_source_status"] == "source_backed_z1_bank_treasury_split"
        for row in public_interest_rows
    )
    overlap_complete = bool(overlap_gate_rows) and all(
        row["final_classifier_effect"] == "no_final_blocker"
        for row in overlap_gate_rows
    )
    specs = [
        (
            "numerator_dollars",
            "pass"
            if has_public_interest and iorb_complete and bank_route_complete
            else "blocked_partial_public_interest_net_block_nonfinal"
            if has_public_interest
            else "blocked_partial",
            "historical public-interest net block exists; technical numerator gates pass under the R37 nonclassifier policy"
            if has_public_interest
            else "only TDC context and direct Treasury interest are source-backed here",
        ),
        (
            "denominator_dollars",
            "pass" if denominator_ok else "fail",
            "CBO quarterly GDP and fed funds rate produce positive D",
        ),
        ("periodization", "pass", "periods are quarterly historical rows"),
        (
            "overlap",
            "pass" if overlap_complete else "blocked_unproven",
            "historical public-interest, TDC, residual, safe-yield, and remittance overlap gates are explicit",
        ),
        (
            "no_forecast_backfill",
            "pass" if no_backfill and public_interest_no_backfill else "fail",
            "historical numerator and public-interest rows do not use forecast backfill",
        ),
        (
            "denominator_convention",
            "pass" if denom_no_forecast_moving else "fail",
            "historical D uses CBO fed funds path and does not reuse forecast moving D",
        ),
        (
            "remittance_on_rrp",
            "pass" if remittance_complete else "blocked_unproven",
            "H.4.1 remittance contribution is zero under the deferred-asset/context guard and cannot overlap with ON RRP support",
        ),
        (
            "iorb_reserve_stock",
            "pass" if iorb_complete else "blocked_missing_reserve_stock",
            "IORB rate and reserve-balance stock are source-backed where local rows exist",
        ),
        (
            "bank_treasury_route",
            "pass" if bank_route_complete else "blocked_missing_bank_route_source",
            "bank Treasury route is source-backed as a non-additive split of direct interest",
        ),
        (
            "final_classifier",
            "closed_nonclassifier",
            "R37 resolved: technical gates pass, but historical remains context/validation rather than a final wall-hit classifier",
        ),
    ]
    return [
        {
            "historical_provisional_gate_row_id": (
                f"historical_provisional_gate::{check_id}"
            ),
            "check_id": check_id,
            "gate_status": status,
            "evidence_summary": evidence,
            "final_classifier_allowed": "false",
            "allowed_use": "historical_provisional_gate",
            "blocked_use": "canonical_headline_promotion;evidence_mode_claim",
        }
        for check_id, status, evidence in specs
    ]


def historical_provisional_audit_rows(
    *,
    denominator_rows: Sequence[Mapping[str, str]],
    numerator_rows: Sequence[Mapping[str, str]],
    rw_rows: Sequence[Mapping[str, str]],
    gate_rows: Sequence[Mapping[str, str]],
    public_interest_rows: Sequence[Mapping[str, str]] = (),
    denominator_convention_rows: Sequence[Mapping[str, str]] = (),
    overlap_gate_rows: Sequence[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Return machine checks for the provisional historical scaffold."""

    return [
        _audit(
            "denominator_rows_positive",
            all(_decimal(row["historical_path_D_bil"]) > 0 for row in denominator_rows),
            len(denominator_rows),
            "every denominator row must have positive historical_path_D_bil",
        ),
        _audit(
            "no_forecast_backfill",
            all(row["forecast_backfill_used"] == "false" for row in numerator_rows),
            len(numerator_rows),
            "historical numerator rows must not use forecast backfill",
        ),
        _audit(
            "rw_rows_not_final_classifier",
            all(row["final_classifier_allowed"] == "false" for row in rw_rows),
            len(rw_rows),
            "provisional RW rows cannot be final classifiers",
        ),
        _audit(
            "final_gate_closed_nonclassifier",
            any(
                row["check_id"] == "final_classifier"
                and row["gate_status"] == "closed_nonclassifier"
                for row in gate_rows
            ),
            len(gate_rows),
            "R37 must close final classifier as an intentional nonclassifier policy decision",
        ),
        _audit(
            "public_interest_no_forecast_backfill",
            all(
                row["forecast_backfill_used"] == "false"
                for row in public_interest_rows
            ),
            len(public_interest_rows),
            "historical public-interest rows must not use forecast backfill",
        ),
        _audit(
            "denominator_convention_no_forecast_moving_D",
            all(
                row["forecast_moving_D_reused"] == "false"
                for row in denominator_convention_rows
            ),
            len(denominator_convention_rows),
            "historical denominator convention rows cannot reuse forecast moving D",
        ),
        _audit(
            "overlap_gate_blocks_final_when_needed",
            bool(overlap_gate_rows)
            and all(
                row["final_classifier_effect"]
                in {"block_final_classifier", "no_final_blocker"}
                for row in overlap_gate_rows
            ),
            len(overlap_gate_rows),
            "overlap gate rows must explicitly mark whether each check blocks final promotion",
        ),
    ]


def write_historical_provisional_estimate_outputs(
    output_dir: str | Path,
    *,
    denominator_rows: Sequence[Mapping[str, str]],
    numerator_rows: Sequence[Mapping[str, str]],
    rw_rows: Sequence[Mapping[str, str]],
    gate_rows: Sequence[Mapping[str, str]],
    audit_rows: Sequence[Mapping[str, str]],
    public_interest_rows: Sequence[Mapping[str, str]] = (),
    root_public_interest_rw_rows: Sequence[Mapping[str, str]] = (),
    denominator_convention_rows: Sequence[Mapping[str, str]] = (),
    overlap_gate_rows: Sequence[Mapping[str, str]] = (),
) -> dict[str, Path]:
    """Write historical provisional estimate outputs."""

    root = Path(output_dir)
    outputs = {
        "denominator_csv": root
        / "ratewall_historical_provisional_denominator_panel.csv",
        "public_interest_csv": root
        / "ratewall_historical_public_interest_net_block.csv",
        "root_public_interest_rw_csv": root
        / "ratewall_historical_root_public_interest_rw_panel.csv",
        "denominator_convention_csv": root
        / "ratewall_historical_denominator_convention_review.csv",
        "overlap_gate_csv": root / "ratewall_historical_overlap_gate.csv",
        "numerator_csv": root / "ratewall_historical_provisional_numerator_ledger.csv",
        "rw_csv": root / "ratewall_historical_provisional_rw_panel.csv",
        "gate_csv": root / "ratewall_historical_provisional_classifier_gate.csv",
        "audit_csv": root / "ratewall_historical_provisional_audit.csv",
    }
    write_rows(
        outputs["denominator_csv"],
        list(denominator_rows),
        HISTORICAL_PROVISIONAL_DENOMINATOR_FIELDS,
    )
    write_rows(
        outputs["public_interest_csv"],
        list(public_interest_rows),
        HISTORICAL_PUBLIC_INTEREST_NET_BLOCK_FIELDS,
    )
    write_rows(
        outputs["root_public_interest_rw_csv"],
        list(root_public_interest_rw_rows),
        HISTORICAL_ROOT_PUBLIC_INTEREST_RW_FIELDS,
    )
    write_rows(
        outputs["denominator_convention_csv"],
        list(denominator_convention_rows),
        HISTORICAL_DENOMINATOR_CONVENTION_FIELDS,
    )
    write_rows(
        outputs["overlap_gate_csv"],
        list(overlap_gate_rows),
        HISTORICAL_OVERLAP_GATE_FIELDS,
    )
    write_rows(
        outputs["numerator_csv"],
        list(numerator_rows),
        HISTORICAL_PROVISIONAL_NUMERATOR_FIELDS,
    )
    write_rows(outputs["rw_csv"], list(rw_rows), HISTORICAL_PROVISIONAL_RW_FIELDS)
    write_rows(
        outputs["gate_csv"], list(gate_rows), HISTORICAL_PROVISIONAL_GATE_FIELDS
    )
    write_rows(
        outputs["audit_csv"], list(audit_rows), HISTORICAL_PROVISIONAL_AUDIT_FIELDS
    )
    return outputs


def _historical_periods(historical_comparable_dir: Path) -> list[str]:
    rows = _read_required(
        historical_comparable_dir / "ratewall_historical_comparable_surface.csv"
    )
    return sorted({row["period"] for row in rows}, key=_period_key)


def _assumption_set(name: str):
    for assumption in load_ratewall_assumption_sets():
        if assumption.name == name:
            return assumption
    raise HistoricalProvisionalEstimateError(f"missing assumption set: {name}")


def _historical_d(gdp: Decimal, drag_share_pp_gdp: Decimal, rate_pct: Decimal) -> Decimal:
    return gdp * drag_share_pp_gdp / Decimal("100") * rate_pct


def _fred_sources(source_dir: Path) -> dict[str, list[tuple[date, Decimal]]]:
    out: dict[str, list[tuple[date, Decimal]]] = {}
    for series_id in [
        "NA000309Q",
        "IOER",
        "IORB",
        "WRESBAL",
        "WRBWFRBL",
        "RRPONTSYD",
        "RRPONTSYAWARD",
        "RESPPLLOPNWW",
        "BOGZ1FL763061100Q",
        "FDHBPIN",
        "WDTGAL",
    ]:
        path = source_dir / f"{series_id}.csv"
        if not path.exists():
            out[series_id] = []
            continue
        rows: list[tuple[date, Decimal]] = []
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                value = row.get(series_id, "")
                if value in {"", "."}:
                    continue
                rows.append((date.fromisoformat(row["observation_date"]), Decimal(value)))
        out[series_id] = rows
    return out


def _reserve_rate_average(
    fred: Mapping[str, Sequence[tuple[date, Decimal]]], start: date, end: date
) -> tuple[Decimal, str]:
    values: list[tuple[str, Decimal]] = []
    for observed, value in fred.get("IOER", []):
        if start <= observed <= end and observed <= date(2021, 7, 28):
            values.append(("IOER", value))
    for observed, value in fred.get("IORB", []):
        if start <= observed <= end and observed >= date(2021, 7, 29):
            values.append(("IORB", value))
    if not values:
        if end < date(2008, 10, 9):
            return Decimal("0"), "reserve_interest_not_applicable_zero_pre_ioer"
        return Decimal("0"), "missing_ioer_iorb_quarter_rate"
    average = sum((value for _source, value in values), Decimal("0")) / Decimal(
        len(values)
    )
    sources = {source for source, _value in values}
    if sources == {"IOER", "IORB"}:
        status = "source_backed_ioer_to_iorb_splice_quarter"
    elif sources == {"IOER"}:
        status = "source_backed_ioer_quarter_average"
    else:
        status = "source_backed_iorb_quarter_average"
    return average, status


def _on_rrp_source_status(start: date, stock_count: int, rate_count: int) -> str:
    if start < date(2013, 7, 1):
        return "on_rrp_interest_not_applicable_zero_pre_fixed_rate_facility"
    if stock_count and rate_count:
        if start == date(2013, 7, 1):
            return "source_backed_on_rrp_partial_quarter"
        return "source_backed_on_rrp_stock_and_award_rate"
    return "missing_on_rrp_stock_or_award_rate_source"


def _short_assumption_case(name: str) -> str:
    prefix = "literature_calibrated_"
    return name.removeprefix(prefix) if name.startswith(prefix) else name


def _average_series(
    rows: Sequence[tuple[date, Decimal]], start: date, end: date
) -> tuple[Decimal, int]:
    values = [value for observed, value in rows if start <= observed <= end]
    if not values:
        return Decimal("0"), 0
    return sum(values, Decimal("0")) / Decimal(len(values)), len(values)


def _latest_at_or_before(
    rows: Sequence[tuple[date, Decimal]], end: date
) -> tuple[Decimal, int]:
    values = [item for item in rows if item[0] <= end]
    if not values:
        return Decimal("0"), 0
    return max(values, key=lambda item: item[0])[1], 1


def _cbo_remittance_by_fiscal_year(path: Path) -> dict[int, Decimal]:
    if not path.exists():
        return {}
    out: dict[int, Decimal] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("variable") != "rev_fed_reserve":
                continue
            fiscal_year = row.get("date", "")
            if fiscal_year.startswith("FY") and row.get("value"):
                out[int(fiscal_year.removeprefix("FY"))] = Decimal(row["value"])
    return out


def _quarterly_remittance_state(
    remittance_by_fy: Mapping[int, Decimal], period: str
) -> Decimal:
    return remittance_by_fy.get(_fiscal_year_for_quarter(period), Decimal("0"))


def _fiscal_year_for_quarter(period: str) -> int:
    year = int(period[:4])
    quarter = int(period[-1])
    return year + 1 if quarter == 4 else year


def _quarter_bounds(period: str) -> tuple[date, date]:
    year = int(period[:4])
    quarter = int(period[-1])
    starts = {
        1: (1, 1, 3, 31),
        2: (4, 1, 6, 30),
        3: (7, 1, 9, 30),
        4: (10, 1, 12, 31),
    }
    start_month, start_day, end_month, end_day = starts[quarter]
    return date(year, start_month, start_day), date(year, end_month, end_day)


def _cbo_quarterly_rows(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise HistoricalProvisionalEstimateError(f"missing required input: {path}")
    with zipfile.ZipFile(path) as archive:
        with archive.open("Quarterly_February2026.csv") as handle:
            text_rows = (line.decode("utf-8") for line in handle)
            rows = list(csv.DictReader(text_rows))
    return {row["date"].upper().replace("Q", "Q"): row for row in rows}


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise HistoricalProvisionalEstimateError(f"missing required input: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _required_period(
    rows: Mapping[str, Mapping[str, str]], period: str
) -> Mapping[str, str]:
    try:
        return rows[period.upper()]
    except KeyError as exc:
        raise HistoricalProvisionalEstimateError(
            f"missing CBO quarterly row for historical period: {period}"
        ) from exc


def _required_row(
    rows: Mapping[str, Mapping[str, str]], key: str, label: str
) -> Mapping[str, str]:
    try:
        return rows[key]
    except KeyError as exc:
        raise HistoricalProvisionalEstimateError(f"missing {label}: {key}") from exc


def _period_key(period: str) -> tuple[int, int]:
    year = int(period[:4])
    quarter = int(period[-1])
    return year, quarter


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator if denominator else Decimal("0")


def _millions_to_bil(value: Decimal) -> Decimal:
    return value / Decimal("1000")


def _bounded_share(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0 or numerator <= 0:
        return Decimal("0")
    return min(numerator / denominator, Decimal("1"))


def _h41_remittance_status(state_bil: Decimal, observation_count: int) -> str:
    if not observation_count:
        return "missing_h41_remittance_state_source"
    if state_bil < 0:
        return "source_backed_h41_deferred_asset_context_zero_support"
    if state_bil == 0:
        return "source_backed_h41_zero_state_zero_support"
    return "source_backed_h41_positive_weekly_remittance_due_context_not_support"


def _decimal(value: str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value == "" or value.upper() == "NA":
        raise HistoricalProvisionalEstimateError(f"missing numeric value: {value!r}")
    return Decimal(value)


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _audit(
    check_id: str,
    passed: bool,
    row_count: int,
    required_rule: str,
) -> dict[str, str]:
    return {
        "historical_provisional_audit_row_id": (
            f"historical_provisional_audit::{check_id}"
        ),
        "check_id": check_id,
        "check_status": "pass" if passed else "fail",
        "row_count": str(row_count),
        "required_rule": required_rule,
        "allowed_use": "historical_provisional_audit",
        "blocked_use": "canonical_headline_promotion;evidence_mode_claim",
    }


def _overlap_gate(
    check_id: str,
    status: str,
    row_count: int,
    evidence: str,
    source_status: str,
    final_effect: str,
) -> dict[str, str]:
    return {
        "historical_overlap_gate_row_id": f"historical_overlap_gate::{check_id}",
        "check_id": check_id,
        "gate_status": status,
        "row_count": str(row_count),
        "evidence_summary": evidence,
        "source_status": source_status,
        "final_classifier_effect": final_effect,
        "allowed_use": "historical_overlap_gate",
        "blocked_use": "canonical_headline_promotion;evidence_mode_claim",
    }

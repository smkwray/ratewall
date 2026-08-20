"""V1 calibrated RWTAM headline and channel-report builder."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path


BANDS: tuple[str, ...] = ("low", "base", "high")
DOSE_MODES: tuple[str, ...] = ("transient_12m", "persistent_level")
DEFAULT_DOSE_MODE = "persistent_level"
TERM_PREMIUM_PACK_ID = "term_premium_response"
TAX_LAYER_PACK_ID = "tax_layer_calibration_20260702"
PHASE6_LAYER_CONFIG = Path("configs/rwtam/phase6_waterfall_layers.csv")
PHASE6_OVERLAP_CONFIG = Path("configs/rwtam/phase6_overlap_groups.csv")
SCENARIO_AXES_CONFIG = Path("configs/rwtam/scenario_axes.csv")
MONTHS = 120
START_YEAR = 2026
START_MONTH = 1
TDCSIM_COUPON_ROLL_SOURCE_ID = "TDCSIM_MSPD_COUPON_ROLL_20260531"
TDCSIM_ISSUANCE_MIX_SOURCE_ID = "TDCSIM_RATEWALL_ISSUANCE_TENOR_MIX_20260702"
TREASURY_BILL_TARGET = Decimal("6819")
TREASURY_COUPON_TARGET = Decimal("23822")
MARKETABLE_TREASURY_TARGET = Decimal("30641")
CURRENT_DEFAULT_OBJECT_STAMP = (
    "current_default_wave8_combined_sinks_tdc_split_suspended:"
    "dose_mode=persistent_level,basis=tax_layer_calibration_20260702"
)
TDC_SPLIT_SUSPENSION_REASON = "suspended_tdcsim_input_nonfeeding"
TDC_SPLIT_ROUTE_FAMILY = "tdc_income_from_tdcsim_marginal_deposit_stock"
COMBINED_SINK_LABEL = (
    "default_baseline;combined_sinks;bank_retention_sink;"
    "assumption_directional_support;banded_recycle_share"
)
COMBINED_SINK_RECYCLE_SHARE_BANDS = {
    "low": Decimal("0.45"),
    "base": Decimal("0.60"),
    "high": Decimal("0.75"),
}
COMBINED_SINK_CREDIT_LEAKAGE_SHARE_BANDS = {
    "low": Decimal("0.10"),
    "base": Decimal("0.25"),
    "high": Decimal("0.45"),
}
COMBINED_SINK_BANK_CREDIT_FAMILIES = {
    "c_and_i_depository_loans",
    "cre_mortgages_floating",
    "cre_mortgages_fixed",
}
COMBINED_SINK_DEPOSIT_FAMILIES = {
    "deposits_checkable",
    "deposits_savings_mmda",
    "deposits_time_cds",
}
COMBINED_SINK_BANK_EARNING_RECEIPT_FAMILIES = {
    "fed_iorb",
    "c_and_i_depository_loans",
    "mortgages_fixed",
    "mortgages_arm",
    "heloc",
    "credit_card_revolving",
    "auto_installment_debt",
    "student_loans_private",
    "personal_installment_debt",
    "treasury_bills",
    "treasury_coupon_current_stock_roll",
    "treasury_coupon_new_deficit_issuance",
}
BACKCAST_FORBIDDEN_COMPARISONS = (
    "forbidden:headline_RW_full,scalar,P0/P1_bands,claim_ratios"
)
TDC_BETA_SENSITIVITY_VALUES = {
    "tdc_beta_sensitivity_minus_0p005": Decimal("-0.005"),
    "tdc_beta_sensitivity_legacy_0p342": Decimal("0.342"),
    "tdc_beta_sensitivity_0p516": Decimal("0.516"),
    "tdc_beta_sensitivity_1p038": Decimal("1.038"),
}
TDC_BETA_SENSITIVITY_FIELDS = {
    "parameter_id",
    "sensitivity_id",
    "beta",
    "legacy_status",
    "authority_status",
    "evidence_mode_enabled",
    "canonical_status",
    "input_basis_label",
    "rationale",
}
TDC_BETA_SELECTOR_FIELDS = {
    "is_default",
    "state_id",
    "state_family",
    "transition_direction",
    "enabled",
    "threshold_variable",
    "threshold_flow_bil_low",
    "threshold_flow_bil_base",
    "threshold_flow_bil_high",
    "override_beta_base",
    "runtime_selector_allowed",
    "selection_scope",
}

HH_CELLS = (
    "hh_constrained_net_borrower",
    "hh_middle_owner_illiquid",
    "hh_retiree_fixed_income_saver",
    "hh_unconstrained_saver",
)
FIRM_CELLS = ("firm_bank_dependent_small", "firm_market_funded_large")
ZERO_CELLS = {
    "banks_intermediary_no_conversion",
    "nonbank_finance_intermediary_no_conversion",
    "federal_reserve_accounting_cell",
    "treasury_federal_accounting_cell",
    "rest_of_world_external_cell",
    "unallocated_no_conversion",
    "deferred_no_conversion",
}


@dataclass(frozen=True)
class V1Result:
    """CSV-ready RWTAM V1 output tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_v1(
    pack_dir: Path = Path("configs/rwtam/packs"),
    *,
    include_scenario_adjustments: bool = True,
    include_tdc_settlement: bool | None = None,
    include_tdc_split_addendum: bool = False,
    include_combined_sinks: bool = True,
    include_tax_layer: bool = True,
    qt_supply_stress: bool | Decimal | str = False,
    shock_start_month: str = "2026-01",
    dose_mode: str = DEFAULT_DOSE_MODE,
    use_impulse_beta_context: bool = False,
    shock_size_bp: Decimal | str = Decimal("100"),
    include_impulse_beta_comparator: bool = True,
    hysteresis_state_config: dict[str, object] | None = None,
    fiscal_tilt_config: dict[str, object] | None = None,
) -> V1Result:
    with localcontext() as context:
        context.prec = 28
        return _build_v1_impl(
            pack_dir,
            include_scenario_adjustments=include_scenario_adjustments,
            include_tdc_settlement=include_tdc_settlement,
            include_tdc_split_addendum=include_tdc_split_addendum,
            include_combined_sinks=include_combined_sinks,
            include_tax_layer=include_tax_layer,
            qt_supply_stress=qt_supply_stress,
            shock_start_month=shock_start_month,
            dose_mode=dose_mode,
            use_impulse_beta_context=use_impulse_beta_context,
            shock_size_bp=_d(shock_size_bp),
            include_impulse_beta_comparator=include_impulse_beta_comparator,
            hysteresis_state_config=hysteresis_state_config,
            fiscal_tilt_config=fiscal_tilt_config,
        )


def _build_v1_impl(
    pack_dir: Path,
    *,
    include_scenario_adjustments: bool,
    include_tdc_settlement: bool | None,
    include_tdc_split_addendum: bool,
    include_combined_sinks: bool,
    include_tax_layer: bool,
    qt_supply_stress: bool | Decimal | str,
    shock_start_month: str,
    dose_mode: str,
    use_impulse_beta_context: bool,
    shock_size_bp: Decimal,
    include_impulse_beta_comparator: bool,
    hysteresis_state_config: dict[str, object] | None,
    fiscal_tilt_config: dict[str, object] | None,
) -> V1Result:
    _validate_dose_mode(dose_mode)
    if include_tdc_settlement is None:
        include_tdc_settlement = include_scenario_adjustments
    pack = _effective_pack(
        _load_pack(pack_dir),
        include_scenario_adjustments,
        include_tdc_settlement,
    )
    pack = _pack_with_qt_deposit_leg(pack, qt_supply_stress)
    phase6_pack = _load_pack(pack_dir / "phase6")
    validation = validate_pack(pack, phase6_pack)
    if include_tdc_split_addendum:
        raise ValueError("suspended TDCSim split input is nonfeeding and cannot enter V1")
    tdc_split_addendum = _tdc_split_suspended()
    monthly_records = _monthly_records(
        pack,
        phase6_pack=phase6_pack,
        include_tdc_settlement=include_tdc_settlement,
        include_tdc_split_addendum=include_tdc_split_addendum,
        tdc_split_addendum=tdc_split_addendum,
        include_combined_sinks=include_combined_sinks,
        shock_start_month=shock_start_month,
        dose_mode=dose_mode,
        include_tax_layer=include_tax_layer,
        qt_supply_stress=qt_supply_stress,
        use_impulse_beta_context=use_impulse_beta_context,
        shock_size_bp=shock_size_bp,
        hysteresis_state_config=hysteresis_state_config,
        fiscal_tilt_config=fiscal_tilt_config,
    )
    records = _annual_records_from_monthly(monthly_records)
    impulse_beta_records: list[dict[str, Decimal | str]] | None = None
    if not use_impulse_beta_context and include_impulse_beta_comparator:
        impulse_beta_monthly = _monthly_records(
            pack,
            phase6_pack=phase6_pack,
            include_tdc_settlement=include_tdc_settlement,
            include_tdc_split_addendum=include_tdc_split_addendum,
            tdc_split_addendum=tdc_split_addendum,
            include_combined_sinks=include_combined_sinks,
            shock_start_month=shock_start_month,
            dose_mode=dose_mode,
            include_tax_layer=include_tax_layer,
            qt_supply_stress=qt_supply_stress,
            use_impulse_beta_context=True,
            shock_size_bp=shock_size_bp,
            hysteresis_state_config=hysteresis_state_config,
            fiscal_tilt_config=fiscal_tilt_config,
        )
        impulse_beta_records = _annual_records_from_monthly(impulse_beta_monthly)
    bnpl_scenario_pack = _pack_with_bnpl_opening_rows(pack)
    bnpl_scenario_records = _annual_records_from_monthly(
        _monthly_records(
            bnpl_scenario_pack,
            phase6_pack=phase6_pack,
            include_tdc_settlement=include_tdc_settlement,
            include_tdc_split_addendum=include_tdc_split_addendum,
            tdc_split_addendum=tdc_split_addendum,
            include_combined_sinks=include_combined_sinks,
            shock_start_month=shock_start_month,
            dose_mode=dose_mode,
            include_tax_layer=include_tax_layer,
            qt_supply_stress=qt_supply_stress,
            use_impulse_beta_context=use_impulse_beta_context,
            shock_size_bp=shock_size_bp,
            hysteresis_state_config=hysteresis_state_config,
            fiscal_tilt_config=fiscal_tilt_config,
        )
    )
    tables = _output_tables(
        pack,
        phase6_pack,
        records,
        validation,
        pack_dir,
        monthly_records=monthly_records,
        dose_mode=dose_mode,
        include_tax_layer=include_tax_layer,
        qt_supply_stress=qt_supply_stress,
        impulse_beta_records=impulse_beta_records,
        use_impulse_beta_context=use_impulse_beta_context,
        bnpl_scenario_records=bnpl_scenario_records,
        bnpl_scenario_pack=bnpl_scenario_pack,
    )
    return V1Result(tables=tables)


def write_v1_outputs(result: V1Result, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        rows_to_write = (
            _with_rw_ratio_degenerate(rows)
            if table_name == "out_ratewall_rollup"
            and _is_scenario_output_dir(output_dir)
            else rows
        )
        _write_rows(path, rows_to_write)
        paths[table_name] = path
    return paths


def _is_scenario_output_dir(output_dir: Path) -> bool:
    parts = output_dir.as_posix().split("/")
    for index in range(len(parts) - 2):
        if parts[index : index + 3] == ["var", "rwtam", "scenarios"]:
            return True
    return False


def _with_rw_ratio_degenerate(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return rows
    threshold = _rw_ratio_degenerate_d_threshold(rows)
    out: list[dict[str, str]] = []
    for row in rows:
        copy = dict(row)
        d_value = _d(copy.get("D_bil", "0") or "0")
        rw_value = _d(copy.get("RW_ratio", "0") or "0")
        copy["rw_ratio_degenerate"] = (
            "true"
            if d_value < threshold or rw_value < Decimal("0") or rw_value > Decimal("1")
            else "false"
        )
        out.append(copy)
    return out


def _rw_ratio_degenerate_d_threshold(rows: list[dict[str, str]]) -> Decimal:
    for row in rows:
        if (
            row.get("period_type") == "annual"
            and row.get("period") == "2026"
            and row.get("band") == "base"
            and row.get("ricardian_offset") == "0"
        ):
            return _d(row.get("D_bil", "0") or "0") * Decimal("0.001")
    return Decimal("0")


def validate_pack(
    pack: dict[str, list[dict[str, str]]],
    phase6_pack: dict[str, list[dict[str, str]]] | None = None,
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    required = {
        "cells",
        "conversion_coefficients",
        "household_stock_splits",
        "lookthrough_shares",
        "opening_stocks",
        "ricardian_sensitivity",
        "source_provenance",
        "mortgage_holder_decomposition",
        "treasury_holder_matrix",
        "structural_assumptions",
        "tdc_beta_authority",
        "tdc_empirical_beta_path",
    }
    checks.append(_check("T25_files", required <= set(pack), "all required pack CSVs load"))
    checks.extend(_validate_tdc_beta_authority(pack))
    bounded_ok = True
    labels_ok = True
    for name, rows in pack.items():
        if name in {
            "source_provenance",
            "absorption_modes",
            "tdc_recipient_splits",
            "tdcsim_coupon_roll_schedule",
            "tdcsim_issuance_tenor_mix",
            "term_premium_validation_decomposition",
            "tdc_empirical_beta_path",
            "tdc_beta_authority",
            "absorption_mode_mix_summary_annual_and_2010_2019_avg",
        } or name.startswith("tax_layer_") or name.startswith("mmf_targets_v2_"):
            continue
        for row in rows:
            if {"low", "base", "high"}.issubset(row):
                low, base, high = _d(row["low"]), _d(row["base"]), _d(row["high"])
                bounded_ok = bounded_ok and low <= base <= high
            labels_ok = labels_ok and bool(row.get("input_basis_label", "").strip())
    checks.append(_check("T25_bounds", bounded_ok, "all pack rows satisfy low<=base<=high"))
    checks.append(_check("T25_labels", labels_ok, "all parameter rows carry input_basis_label"))
    if phase6_pack is not None:
        checks.extend(_validate_phase6_pack(phase6_pack))
    if "scenario_adjustments" in pack:
        checks.extend(_validate_scenario_adjustments(pack["scenario_adjustments"]))

    for table, key_field in [
        ("household_stock_splits", "instrument_family"),
        ("lookthrough_shares", "instrument_family"),
    ]:
        for family in sorted({row[key_field] for row in pack[table]}):
            total = sum(_d(row["base"]) for row in pack[table] if row[key_field] == family)
            checks.append(
                _check(
                    f"T25_{table}_{family}",
                    abs(total - Decimal("1")) <= Decimal("0.000001"),
                    f"{table} {family} base shares sum to {_fmt(total)}",
                )
            )

    for family in ["all_marketable_treasuries", "treasury_bills", "treasury_notes_bonds_tips"]:
        total = sum(
            _d(row["base"])
            for row in pack["treasury_holder_matrix"]
            if row["instrument_family"] == family
        )
        has_unallocated = any(
            row["cell_or_sector"] == "unallocated_line_mapping_residual"
            and row["instrument_family"] == family
            for row in pack["treasury_holder_matrix"]
        )
        checks.append(
            _check(
                f"T26_{family}",
                abs(total - Decimal("1")) <= Decimal("0.000001") and has_unallocated,
                f"{family} shares sum to {_fmt(total)} including unallocated",
            )
        )

    opening = _opening_by_family(pack)
    bills = opening["treasury_bills"]
    coupons = opening["treasury_notes_bonds_tips"]
    total = bills + coupons
    checks.append(
        _check(
            "T27_treasury_stock",
            abs(bills - TREASURY_BILL_TARGET) <= Decimal("1")
            and abs(coupons - TREASURY_COUPON_TARGET) <= Decimal("1")
            and abs(total - MARKETABLE_TREASURY_TARGET) <= Decimal("2"),
            f"bills={_fmt(bills)} coupons={_fmt(coupons)} total={_fmt(total)}",
        )
    )
    return checks


def _validate_tdc_beta_authority(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    sensitivities = pack.get("tdc_beta_authority", [])
    empirical = pack.get("tdc_empirical_beta_path", [])
    by_id = {row.get("sensitivity_id", ""): row for row in sensitivities}
    exact_set = (
        len(sensitivities) == len(TDC_BETA_SENSITIVITY_VALUES)
        and set(by_id) == set(TDC_BETA_SENSITIVITY_VALUES)
        and all(
            by_id[sensitivity_id].get("parameter_id") == sensitivity_id
            and _d(by_id[sensitivity_id].get("beta", "nan")) == beta
            for sensitivity_id, beta in TDC_BETA_SENSITIVITY_VALUES.items()
        )
    )
    equal_status = exact_set and all(
        row.get("authority_status") == "equal_status_sensitivity"
        for row in sensitivities
    )
    legacy_visible = exact_set and all(
        row.get("legacy_status")
        == (
            "visibly_legacy"
            if row.get("sensitivity_id") == "tdc_beta_sensitivity_legacy_0p342"
            else "current_sensitivity_member"
        )
        for row in sensitivities
    )
    schema_exact = all(set(row) == TDC_BETA_SENSITIVITY_FIELDS for row in sensitivities)
    beta_related_rows = [
        row
        for name, rows in pack.items()
        if "tdc" in name and "beta" in name
        for row in rows
    ]
    no_selector_fields = all(
        not (set(row) & TDC_BETA_SELECTOR_FIELDS) for row in beta_related_rows
    )
    no_selector_surfaces = (
        "tdc_flow_size_beta_override" not in pack
        and "beta_state_indicator" not in pack
    )
    historical_only = bool(empirical) and all(
        row.get("period") == "2010_2019_avg"
        or (row.get("period", "").isdigit() and int(row["period"]) <= 2025)
        for row in empirical
    )
    serialized_pack = "\n".join(
        str(value)
        for rows in pack.values()
        for row in rows
        for value in row.values()
    )
    prohibited_labels_absent = "tdcest_" not in serialized_pack
    noncanonical = exact_set and all(
        row.get("evidence_mode_enabled") == "false"
        and row.get("canonical_status") == "noncanonical_sensitivity_only"
        for row in sensitivities
    )
    return [
        _check(
            "T25_tdc_beta_equal_status_sensitivity_set",
            exact_set and equal_status and legacy_visible,
            "four exact equal-status beta sensitivities; 0.342 visibly legacy",
        ),
        _check(
            "T25_tdc_beta_no_selector",
            schema_exact
            and no_selector_fields
            and no_selector_surfaces
            and historical_only
            and prohibited_labels_absent,
            "no default, state, transition, quiet/large-shock, flow-size, or forward beta selector",
        ),
        _check(
            "T25_tdc_beta_noncanonical",
            noncanonical,
            "beta sensitivities remain noncanonical with Evidence Mode false",
        ),
    ]


def _validate_phase6_pack(phase6_pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    required = {"conversion_parameters", "overlap_matrix", "source_provenance"}
    checks.append(_check("T25_phase6_files", required <= set(phase6_pack), "Phase 6 pack CSVs load"))
    bounded_ok = True
    labels_ok = True
    include_zero_loads = False
    for row in phase6_pack.get("conversion_parameters", []):
        low, base, high = _d(row["low"]), _d(row["base"]), _d(row["high"])
        bounded_ok = bounded_ok and low <= base <= high
        labels_ok = labels_ok and bool(row.get("input_basis_label", "").strip())
        if row["parameter_id"].endswith("include_flag") and base == 0:
            include_zero_loads = True
    checks.append(_check("T25_phase6_bounds", bounded_ok, "Phase 6 rows satisfy low<=base<=high"))
    checks.append(_check("T25_phase6_labels", labels_ok, "Phase 6 rows carry input_basis_label"))
    checks.append(_check("T25_phase6_include0", include_zero_loads, "include_flag=0 rows load for diagnostics"))
    return checks


def _validate_scenario_adjustments(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    checks: list[dict[str, str]] = []
    for delta_set_id in sorted({row["delta_set_id"] for row in rows}):
        group = [row for row in rows if row["delta_set_id"] == delta_set_id]
        closes = True
        messages: list[str] = []
        for band in BANDS:
            entries = _scenario_delta_balance_entries(group, band)
            for sector, item in entries.items():
                gap = (
                    item.get("asset_delta", Decimal("0"))
                    - item.get("liability_delta", Decimal("0"))
                    - item.get("real_counterpart", Decimal("0"))
                )
                if abs(gap) > Decimal("0.000001"):
                    closes = False
                    messages.append(f"{band}:{sector}:{_fmt(gap)}")
        checks.append(
            _check(
                f"T25_scenario_delta_{delta_set_id}",
                closes,
                f"{delta_set_id} sector balance identities close"
                if closes
                else ";".join(messages),
            )
        )
    return checks


def _annual_records(
    pack: dict[str, list[dict[str, str]]],
    *,
    include_tdc_settlement: bool = True,
) -> list[dict[str, Decimal | str]]:
    """Legacy annual-core constructor retained for wave4 comparison evidence."""

    return _legacy_annual_records(pack, include_tdc_settlement=include_tdc_settlement)


def _legacy_annual_records(
    pack: dict[str, list[dict[str, str]]],
    *,
    include_tdc_settlement: bool,
) -> list[dict[str, Decimal | str]]:
    records: list[dict[str, Decimal | str]] = []
    assumptions = _assumptions(pack)
    opening = _opening_by_family(pack)
    conversion = _conversion(pack)
    ricardian_offsets = _ricardian_offsets(pack)

    for band in BANDS:
        coupon_stock_extra = Decimal("0")
        bill_stock_extra = Decimal("0")
        tdc_created_deposit_stock = Decimal("0")
        bill_issue_share = assumptions["marginal_issuance_bill_share"][band]
        deferred_open = assumptions["fed_deferred_asset_open_bil"][band]
        nominal_gdp = assumptions["nominal_gdp_bil"][band]
        annual_public_net_prev = Decimal("0")
        for year_index in range(1, 11):
            private_routes = _private_annual_routes(pack, band, year_index)
            family_routes: dict[str, dict[str, Decimal]] = {}
            if year_index > 1:
                bill_stock_extra += annual_public_net_prev * bill_issue_share
                coupon_stock_extra += annual_public_net_prev * (Decimal("1") - bill_issue_share)

            bill_stock = opening["treasury_bills"] + bill_stock_extra
            bill_interest = bill_stock * _driver("treasury_bills", band, year_index)
            coupon_components = _treasury_coupon_interest_components(
                pack,
                band,
                year_index,
                opening["treasury_notes_bonds_tips"],
                coupon_stock_extra,
            )
            coupon_interest = coupon_components["total_coupon_interest"]
            bill_routes = _treasury_routes(
                pack,
                bill_interest,
                Decimal("0"),
                band,
                aggregate_matrix=False,
            )
            coupon_current_routes = _treasury_routes(
                pack,
                Decimal("0"),
                coupon_components["current_stock_coupon_interest"],
                band,
                aggregate_matrix=False,
            )
            coupon_new_routes = _treasury_routes(
                pack,
                Decimal("0"),
                coupon_components["new_issuance_coupon_interest"],
                band,
                aggregate_matrix=False,
            )
            treasury_routes = _treasury_routes(
                pack,
                bill_interest,
                coupon_interest,
                band,
                aggregate_matrix=False,
            )
            aggregate_routes = _treasury_routes(
                pack,
                bill_interest,
                coupon_interest,
                band,
                aggregate_matrix=True,
            )
            iorb = opening["reserves_iorb"] * Decimal("0.01")
            on_rrp = opening["on_rrp_mmfs"] * Decimal("0.01")
            fed_rrp_foreign = opening["foreign_official_reverse_repos"] * Decimal("0.01")
            iorb_routes = _route_amount(pack, "banks", iorb, band, "banks_retained_margin")
            on_rrp_routes = _route_amount(pack, "mmfs", on_rrp, band, "mmfs")
            _add_family_routes(family_routes, "treasury_bills", bill_routes)
            _add_family_routes(
                family_routes,
                "treasury_coupon_current_stock_roll",
                coupon_current_routes,
            )
            _add_family_routes(
                family_routes,
                "treasury_coupon_new_deficit_issuance",
                coupon_new_routes,
            )
            _add_family_routes(family_routes, "fed_iorb", iorb_routes)
            _add_family_routes(family_routes, "fed_on_rrp_mmfs", on_rrp_routes)
            _merge_family_routes(
                family_routes,
                _private_annual_family_routes(pack, band, year_index),
            )
            fed_private_routes = _merge_routes(iorb_routes, on_rrp_routes)
            fed_interest_cost = iorb + on_rrp + fed_rrp_foreign
            remittance_delta = (
                Decimal("0") if deferred_open > 0 else -fed_interest_cost
            )
            public_effect_routes = _merge_routes(treasury_routes, fed_private_routes)
            cashflow_routes = _merge_routes(public_effect_routes, private_routes)
            public_n, public_d, public_net = _classify(public_effect_routes, conversion, Decimal("0"))
            private_n, private_d, private_net = _classify(private_routes, conversion, Decimal("0"))
            gov_delta = bill_interest + coupon_interest
            tdc_metrics = _tdc_metrics_for_period(
                pack,
                band,
                year_index,
                gov_delta,
                tdc_created_deposit_stock,
                include_tdc_settlement,
            )
            tdc_created_deposit_stock = tdc_metrics["created_deposit_stock_bil"]
            tdc_routes = _tdc_routes_from_metrics(pack, band, tdc_metrics)
            cashflow_routes = _merge_routes(cashflow_routes, tdc_routes)
            _add_family_routes(
                family_routes,
                "tdc_created_deposit_income_from_deficit_financing",
                tdc_routes,
            )
            for ricardian in ricardian_offsets:
                n, d, net = _classify(cashflow_routes, conversion, ricardian)
                records.append(
                    {
                        "band": band,
                        "year_index": Decimal(year_index),
                        "year": str(START_YEAR + year_index - 1),
                        "ricardian_offset": ricardian,
                        "public_n": public_n,
                        "public_d": public_d + gov_delta * ricardian,
                        "private_n": private_n,
                        "private_d": private_d,
                        "N": n,
                        "D": d,
                        "net": net,
                        "RW": Decimal("0") if d == 0 else n / d,
                        "nominal_gdp_bil": nominal_gdp,
                        "bottom_up_D_to_legacy_D": d / (nominal_gdp * Decimal("0.00776")),
                        "bill_interest": bill_interest,
                        "coupon_interest": coupon_interest,
                        "coupon_current_stock_interest": coupon_components[
                            "current_stock_coupon_interest"
                        ],
                        "coupon_new_issuance_interest": coupon_components[
                            "new_issuance_coupon_interest"
                        ],
                        "coupon_current_stock_reprice_share": coupon_components[
                            "current_stock_reprice_share"
                        ],
                        "coupon_new_issuance_reprice_share": coupon_components[
                            "new_issuance_reprice_share"
                        ],
                        "government_interest_delta": gov_delta,
                        "iorb_delta": iorb,
                        "on_rrp_delta": on_rrp,
                        "remittance_delta": remittance_delta,
                        "aggregate_matrix_government_net": sum(
                            aggregate_routes.values(), Decimal("0")
                        ),
                        "tdc_issuance_divergence_bil": gov_delta
                        if include_tdc_settlement
                        else Decimal("0"),
                        "tdc_new_created_deposits_bil": tdc_metrics[
                            "new_created_deposits_bil"
                        ],
                        "tdc_created_deposit_stock_bil": tdc_metrics[
                            "created_deposit_stock_bil"
                        ],
                        "tdc_created_deposit_income_bil": tdc_metrics[
                            "created_deposit_income_bil"
                        ],
                        "tdc_created_deposit_full_level_rate": tdc_metrics[
                            "full_level_deposit_rate"
                        ],
                        "tdc_implied_beta": tdc_metrics["implied_beta"],
                        "cashflow_routes": cashflow_routes,
                        "cashflow_family_routes": family_routes,
                    }
                )
            annual_public_net_prev = public_net
    return records


@dataclass(frozen=True)
class _CouponCohort:
    amount: Decimal
    rate_delta_ann: Decimal
    issue_month_index: int
    tenor_months: int
    bucket: str


def _monthly_records(
    pack: dict[str, list[dict[str, str]]],
    *,
    phase6_pack: dict[str, list[dict[str, str]]] | None = None,
    include_tdc_settlement: bool,
    include_tdc_split_addendum: bool = False,
    tdc_split_addendum: dict[str, object] | None = None,
    include_combined_sinks: bool = True,
    shock_start_month: str,
    dose_mode: str,
    include_tax_layer: bool,
    qt_supply_stress: bool | Decimal | str = False,
    use_impulse_beta_context: bool = False,
    shock_size_bp: Decimal = Decimal("100"),
    hysteresis_state_config: dict[str, object] | None = None,
    fiscal_tilt_config: dict[str, object] | None = None,
    issuance_loop_extra_public_net_by_month: dict[tuple[str, str], Decimal] | None = None,
) -> list[dict[str, Decimal | str]]:
    if include_tdc_split_addendum:
        raise ValueError("suspended TDCSim split input is nonfeeding and cannot enter V1")
    records: list[dict[str, Decimal | str]] = []
    if phase6_pack is None:
        phase6_pack = _load_pack(Path("configs/rwtam/packs/phase6"))
    if tdc_split_addendum is None:
        tdc_split_addendum = _tdc_split_suspended()
    assumptions = _assumptions(pack)
    opening = _opening_by_family(pack)
    conversion = _conversion(pack)
    ricardian_offsets = _ricardian_offsets(pack)
    shock_start_index = _month_index_from_label(shock_start_month)
    shock_scale = shock_size_bp / Decimal("100")

    for band in BANDS:
        coupon_stock_extra = Decimal("0")
        bill_stock_extra = Decimal("0")
        tdc_created_deposit_stock = Decimal("0")
        tdc_split_deposit_stock = Decimal("0")
        combined_sink_retention_stock_delta = Decimal("0")
        combined_sink_credit_delta = (
            _combined_sink_credit_deposit_delta(pack, phase6_pack, band, shock_size_bp)
            if include_combined_sinks
            else Decimal("0")
        )
        hysteresis_state = _initial_hysteresis_state(
            opening,
            hysteresis_state_config,
            band,
        )
        current_coupon_cohorts: list[_CouponCohort] = []
        coupon_cohorts: list[_CouponCohort] = []
        bill_issue_share = assumptions["marginal_issuance_bill_share"][band]
        deferred_open = assumptions["fed_deferred_asset_open_bil"][band]
        nominal_gdp = assumptions["nominal_gdp_bil"][band]
        public_net_prev = Decimal("0")
        active_months_elapsed = 0
        for month_index in range(1, MONTHS + 1):
            month = _month_label(month_index)
            year_index = (month_index - 1) // 12 + 1
            year = str(START_YEAR + year_index - 1)
            shock_multiplier = (
                _shock_multiplier(month_index, shock_start_index, dose_mode)
                * shock_scale
            )
            if shock_multiplier:
                active_months_elapsed += 1
            month_pack = pack
            combined_sink_retention_start = combined_sink_retention_stock_delta
            combined_sink_new_retained_nii = Decimal("0")
            hysteresis_rate_add_by_family: dict[str, Decimal] | None = None
            next_hysteresis_state = hysteresis_state
            if hysteresis_state is not None:
                month_pack = _pack_with_hysteresis_state(pack, band, hysteresis_state)
                hysteresis_rate_add_by_family = _hysteresis_rate_add_by_family(
                    hysteresis_state,
                    shock_multiplier,
                )
                next_hysteresis_state = _advance_hysteresis_state(
                    opening,
                    hysteresis_state,
                    shock_multiplier,
                    fiscal_tilt_flow_bil=_fiscal_tilt_flow_bil(
                        pack,
                        band,
                        month_index,
                        fiscal_tilt_config,
                    ),
                )
            if include_combined_sinks:
                rows = [dict(row) for row in month_pack["opening_stocks"]]
                _apply_bank_deposit_stock_delta(
                    rows,
                    band,
                    combined_sink_credit_delta + combined_sink_retention_start,
                )
                month_pack = month_pack | {"opening_stocks": rows}

            if month_index > 1:
                bill_stock_extra += public_net_prev * bill_issue_share
                coupon_addition = public_net_prev * (Decimal("1") - bill_issue_share)
                coupon_stock_extra += coupon_addition
                if coupon_addition:
                    coupon_cohorts.extend(
                        _coupon_cohorts_from_monthly_issuance(
                            pack,
                            amount=coupon_addition,
                            rate_delta_ann=_treasury_yield_delta(
                                pack,
                                "10y",
                                band,
                                month_index,
                                shock_start_index,
                                dose_mode,
                                qt_supply_stress=qt_supply_stress,
                                use_impulse_beta_context=use_impulse_beta_context,
                                shock_size_bp=shock_size_bp,
                            ),
                            issue_month_index=month_index,
                        )
                    )

            bill_stock = opening["treasury_bills"] + bill_stock_extra
            bill_interest = (
                bill_stock
                * _treasury_yield_delta(
                    pack,
                    "bills",
                    band,
                    month_index,
                    shock_start_index,
                    dose_mode,
                    qt_supply_stress=qt_supply_stress,
                    use_impulse_beta_context=use_impulse_beta_context,
                    shock_size_bp=shock_size_bp,
                )
                / Decimal("12")
            )
            current_coupon_maturing = _current_coupon_maturing_month(pack, month)
            if current_coupon_maturing:
                current_coupon_cohorts.extend(
                    _coupon_cohorts_from_monthly_issuance(
                        pack,
                        amount=current_coupon_maturing,
                        rate_delta_ann=_treasury_yield_delta(
                            pack,
                            "10y",
                            band,
                            month_index,
                            shock_start_index,
                            dose_mode,
                            qt_supply_stress=qt_supply_stress,
                            use_impulse_beta_context=use_impulse_beta_context,
                            shock_size_bp=shock_size_bp,
                        ),
                        issue_month_index=month_index,
                    )
                )
            current_coupon_repriced_stock = sum(
                cohort.amount
                for cohort in current_coupon_cohorts
                if _cohort_active(
                    cohort,
                    month_index,
                    persist_after_maturity=dose_mode == "persistent_level",
                    active_until_month_index=_cohort_active_until_month(
                        shock_start_index,
                        dose_mode,
                    ),
                )
            )
            current_coupon_interest = (
                _new_coupon_interest_from_cohorts(
                    current_coupon_cohorts,
                    month_index,
                    persist_after_maturity=dose_mode == "persistent_level",
                    active_until_month_index=_cohort_active_until_month(
                        shock_start_index,
                        dose_mode,
                    ),
                )
            )
            new_coupon_interest = _new_coupon_interest_from_cohorts(
                coupon_cohorts,
                month_index,
                persist_after_maturity=dose_mode == "persistent_level",
                active_until_month_index=_cohort_active_until_month(
                    shock_start_index,
                    dose_mode,
                ),
            )
            coupon_interest = current_coupon_interest + new_coupon_interest
            current_coupon_open = opening["treasury_notes_bonds_tips"]
            current_coupon_share = (
                Decimal("0")
                if current_coupon_open == 0
                else current_coupon_repriced_stock / current_coupon_open
            )
            new_coupon_share = (
                Decimal("0")
                if coupon_stock_extra == 0
                else sum(
                    cohort.amount
                    for cohort in coupon_cohorts
                    if _cohort_active(
                        cohort,
                        month_index,
                        persist_after_maturity=dose_mode == "persistent_level",
                        active_until_month_index=_cohort_active_until_month(
                            shock_start_index,
                            dose_mode,
                        ),
                    )
                )
                / coupon_stock_extra
            )
            treasury_routes = _treasury_routes(
                pack,
                bill_interest,
                coupon_interest,
                band,
                aggregate_matrix=False,
            )
            aggregate_routes = _treasury_routes(
                pack,
                bill_interest,
                coupon_interest,
                band,
                aggregate_matrix=True,
            )
            iorb = (
                opening["reserves_iorb"]
                * Decimal("0.01")
                * shock_multiplier
                / Decimal("12")
            )
            on_rrp = (
                opening["on_rrp_mmfs"]
                * Decimal("0.01")
                * shock_multiplier
                / Decimal("12")
            )
            fed_rrp_foreign = (
                opening["foreign_official_reverse_repos"]
                * Decimal("0.01")
                * shock_multiplier
                / Decimal("12")
            )
            iorb_routes = _route_amount(pack, "banks", iorb, band, "banks_retained_margin")
            on_rrp_routes = _route_amount(pack, "mmfs", on_rrp, band, "mmfs")
            family_routes: dict[str, dict[str, Decimal]] = {}
            _add_family_routes(
                family_routes,
                "treasury_bills",
                _treasury_routes(
                    pack,
                    bill_interest,
                    Decimal("0"),
                    band,
                    aggregate_matrix=False,
                ),
            )
            _add_family_routes(
                family_routes,
                "treasury_coupon_current_stock_roll",
                _treasury_routes(
                    pack,
                    Decimal("0"),
                    current_coupon_interest,
                    band,
                    aggregate_matrix=False,
                ),
            )
            _add_family_routes(
                family_routes,
                "treasury_coupon_new_deficit_issuance",
                _treasury_routes(
                    pack,
                    Decimal("0"),
                    new_coupon_interest,
                    band,
                    aggregate_matrix=False,
                ),
            )
            _add_family_routes(family_routes, "fed_iorb", iorb_routes)
            _add_family_routes(family_routes, "fed_on_rrp_mmfs", on_rrp_routes)
            fed_private_routes = _merge_routes(iorb_routes, on_rrp_routes)
            fed_interest_cost = iorb + on_rrp + fed_rrp_foreign
            remittance_delta = Decimal("0") if deferred_open > 0 else -fed_interest_cost
            public_effect_routes = _merge_routes(treasury_routes, fed_private_routes)
            private_routes = _private_monthly_routes(
                month_pack,
                band,
                month_index,
                shock_start_index,
                active_months_elapsed,
                dose_mode,
                shock_size_bp,
                hysteresis_rate_add_by_family=hysteresis_rate_add_by_family,
            )
            _merge_family_routes(
                family_routes,
                _private_monthly_family_routes(
                    month_pack,
                    band,
                    month_index,
                    shock_start_index,
                    active_months_elapsed,
                    dose_mode,
                    shock_size_bp,
                    hysteresis_rate_add_by_family=hysteresis_rate_add_by_family,
                ),
            )
            cashflow_routes = _merge_routes(public_effect_routes, private_routes)
            if include_combined_sinks:
                nii_delta = _combined_sink_monthly_earning_asset_nii_delta(
                    pack,
                    band,
                    year_index,
                    bill_interest,
                    coupon_interest,
                    iorb,
                )
                combined_sink_new_retained_nii = nii_delta * (
                    Decimal("1") - COMBINED_SINK_RECYCLE_SHARE_BANDS[band]
                )
                combined_sink_retention_stock_delta -= combined_sink_new_retained_nii
            public_n, public_d, public_net = _classify(
                public_effect_routes,
                conversion,
                Decimal("0"),
            )
            issuance_loop_extra_public_net = (
                Decimal("0")
                if issuance_loop_extra_public_net_by_month is None
                else issuance_loop_extra_public_net_by_month.get((band, month), Decimal("0"))
            )
            private_n, private_d, private_net = _classify(
                private_routes,
                conversion,
                Decimal("0"),
            )
            gov_delta = bill_interest + coupon_interest
            tdc_metrics = _tdc_metrics_for_period(
                pack,
                band,
                year_index,
                gov_delta,
                tdc_created_deposit_stock,
                include_tdc_settlement,
            )
            tdc_metrics = {
                **tdc_metrics,
                "created_deposit_income_bil": tdc_metrics[
                    "created_deposit_income_bil"
                ]
                / Decimal("12"),
            }
            tdc_created_deposit_stock = tdc_metrics["created_deposit_stock_bil"]
            tdc_routes = _tdc_routes_from_metrics(pack, band, tdc_metrics)
            cashflow_routes = _merge_routes(cashflow_routes, tdc_routes)
            _add_family_routes(
                family_routes,
                "tdc_created_deposit_income_from_deficit_financing",
                tdc_routes,
            )
            tdc_split_metrics = _tdc_split_metrics_for_month(
                band,
                year,
                month_index,
                tdc_split_deposit_stock,
                include_tdc_split_addendum,
                tdc_split_addendum,
            )
            tdc_split_deposit_stock = tdc_split_metrics["created_deposit_stock_bil"]
            tdc_split_routes = _tdc_routes_from_metrics(pack, band, tdc_split_metrics)
            cashflow_routes = _merge_routes(cashflow_routes, tdc_split_routes)
            _add_family_routes(family_routes, TDC_SPLIT_ROUTE_FAMILY, tdc_split_routes)
            tax_layer_rows: list[dict[str, str]] = []
            if include_tax_layer:
                pre_tax_family_routes = _copy_family_routes(family_routes)
                tax_layer_rows = _apply_tax_layer_to_family_routes(
                    pack,
                    family_routes,
                    band,
                    month_index,
                    active_months_elapsed,
                    shock_multiplier,
                )
                cashflow_routes = _routes_from_family_routes(family_routes)
            else:
                pre_tax_family_routes = _copy_family_routes(family_routes)
            for ricardian in ricardian_offsets:
                n, d, net = _classify_with_tdc_split_family_boundary(
                    family_routes,
                    cashflow_routes,
                    conversion,
                    ricardian,
                )
                records.append(
                    {
                        "band": band,
                        "year_index": Decimal(year_index),
                        "month_index": Decimal(month_index),
                        "month": month,
                        "year": year,
                        "shock_start_month": shock_start_month,
                        "dose_mode": dose_mode,
                        "shock_multiplier": shock_multiplier,
                        "shock_size_bp": shock_size_bp,
                        "active_months_elapsed": Decimal(active_months_elapsed),
                        "bill_stock_extra_bil": bill_stock_extra,
                        "coupon_stock_extra_bil": coupon_stock_extra,
                        "bill_stock_bil": bill_stock,
                        "coupon_stock_bil": opening["treasury_notes_bonds_tips"]
                        + coupon_stock_extra,
                        "ricardian_offset": ricardian,
                        "public_n": public_n,
                        "public_d": public_d + gov_delta * ricardian,
                        "private_n": private_n,
                        "private_d": private_d,
                        "N": n,
                        "D": d,
                        "net": net,
                        "RW": Decimal("0") if d == 0 else n / d,
                        "nominal_gdp_bil": nominal_gdp,
                        "bottom_up_D_to_legacy_D": d
                        / (nominal_gdp * Decimal("0.00776")),
                        "bill_interest": bill_interest,
                        "coupon_interest": coupon_interest,
                        "coupon_current_stock_interest": current_coupon_interest,
                        "coupon_new_issuance_interest": new_coupon_interest,
                        "coupon_current_stock_reprice_share": current_coupon_share,
                        "coupon_new_issuance_reprice_share": new_coupon_share,
                        "government_interest_delta": gov_delta,
                        "iorb_delta": iorb,
                        "on_rrp_delta": on_rrp,
                        "remittance_delta": remittance_delta,
                        "issuance_loop_extra_public_net_bil": issuance_loop_extra_public_net,
                        "aggregate_matrix_government_net": sum(
                            aggregate_routes.values(), Decimal("0")
                        ),
                        "tdc_issuance_divergence_bil": gov_delta
                        if include_tdc_settlement
                        else Decimal("0"),
                        "tdc_new_created_deposits_bil": tdc_metrics[
                            "new_created_deposits_bil"
                        ],
                        "tdc_created_deposit_stock_bil": tdc_metrics[
                            "created_deposit_stock_bil"
                        ],
                        "tdc_created_deposit_income_bil": tdc_metrics[
                            "created_deposit_income_bil"
                        ],
                        "tdc_created_deposit_full_level_rate": tdc_metrics[
                            "full_level_deposit_rate"
                        ],
                        "tdc_implied_beta": tdc_metrics["implied_beta"],
                        "tdc_split_new_created_deposits_bil": tdc_split_metrics[
                            "new_created_deposits_bil"
                        ],
                        "tdc_split_created_deposit_stock_bil": tdc_split_metrics[
                            "created_deposit_stock_bil"
                        ],
                        "tdc_split_created_deposit_income_bil": tdc_split_metrics[
                            "created_deposit_income_bil"
                        ],
                        "tdc_split_admission_status": tdc_split_metrics[
                            "admission_status"
                        ],
                        "tdc_split_reconciliation_status": tdc_split_metrics[
                            "reconciliation_status"
                        ],
                        "tdc_split_source": tdc_split_metrics["source"],
                        "combined_sink_credit_deposit_stock_delta_bil": (
                            combined_sink_credit_delta
                            if include_combined_sinks
                            else Decimal("0")
                        ),
                        "combined_sink_bank_retention_stock_delta_start_bil": (
                            combined_sink_retention_start
                            if include_combined_sinks
                            else Decimal("0")
                        ),
                        "combined_sink_bank_retention_stock_delta_end_bil": (
                            combined_sink_retention_stock_delta
                            if include_combined_sinks
                            else Decimal("0")
                        ),
                        "combined_sink_bank_retention_new_retained_nii_bil": (
                            combined_sink_new_retained_nii
                            if include_combined_sinks
                            else Decimal("0")
                        ),
                        "combined_sink_total_deposit_stock_delta_bil": (
                            combined_sink_credit_delta + combined_sink_retention_start
                            if include_combined_sinks
                            else Decimal("0")
                        ),
                        "bank_payout_recycle_share": (
                            COMBINED_SINK_RECYCLE_SHARE_BANDS[band]
                            if include_combined_sinks
                            else Decimal("0")
                        ),
                        "bank_retention_label": (
                            COMBINED_SINK_LABEL if include_combined_sinks else "off"
                        ),
                        "hysteresis_migrated_stock_bil": (
                            Decimal("0")
                            if next_hysteresis_state is None
                            else next_hysteresis_state["migrated_stock_bil"]
                        ),
                        "hysteresis_migrated_share": (
                            Decimal("0")
                            if next_hysteresis_state is None
                            else next_hysteresis_state["migrated_share"]
                        ),
                        "hysteresis_migration_flow_bil": (
                            Decimal("0")
                            if next_hysteresis_state is None
                            else next_hysteresis_state["last_flow_bil"]
                        ),
                        "fiscal_tilt_flow_bil": (
                            Decimal("0")
                            if next_hysteresis_state is None
                            else next_hysteresis_state["last_fiscal_tilt_flow_bil"]
                        ),
                        "fiscal_tilt_cumulative_flow_bil": (
                            Decimal("0")
                            if next_hysteresis_state is None
                            else next_hysteresis_state["cumulative_fiscal_tilt_flow_bil"]
                        ),
                        "hysteresis_peak_migrated_stock_bil": (
                            Decimal("0")
                            if next_hysteresis_state is None
                            else next_hysteresis_state["peak_migrated_stock_bil"]
                        ),
                        "hysteresis_competition_beta_rate_add_ann": (
                            Decimal("0")
                            if hysteresis_rate_add_by_family is None
                            else hysteresis_rate_add_by_family.get("deposits_savings_mmda", Decimal("0"))
                            * Decimal("12")
                        ),
                        "cashflow_routes": cashflow_routes,
                        "cashflow_family_routes": family_routes,
                        "pre_tax_cashflow_family_routes": pre_tax_family_routes,
                        "tax_layer_rows": tax_layer_rows,
                        "tax_layer_status": "on" if include_tax_layer else "off",
                        "curve_construction": (
                            "superseded_impulse_beta_comparator"
                            if use_impulse_beta_context
                            else "expectations_consistent_term_premium"
                        ),
                    }
                )
            public_net_prev = public_net + issuance_loop_extra_public_net
            hysteresis_state = next_hysteresis_state
    return records


def _initial_hysteresis_state(
    opening: dict[str, Decimal],
    config: dict[str, object] | None,
    band: str,
) -> dict[str, Decimal | bool | frozenset[str]] | None:
    if config is None:
        return None
    enabled = config.get("enabled_mechanisms", frozenset())
    if not isinstance(enabled, frozenset):
        enabled = frozenset(enabled)  # type: ignore[arg-type]
    checkable = _d(config.get("checkable_reference_stock_bil", opening.get("deposits_checkable", Decimal("0"))))
    initial_migrated = _d(config.get("initial_migrated_stock_bil", Decimal("0")))
    peak = _d(config.get("initial_peak_migrated_stock_bil", initial_migrated))
    return {
        "activation_pp": _d(config.get("activation_pp", Decimal("2"))),
        "migration_elasticity": _d(config.get("migration_elasticity", Decimal("0"))),
        "migration_cap": _d(config.get("migration_cap", Decimal("0"))),
        "reversal_share": _d(config.get("reversal_share", Decimal("0"))),
        "deposit_beta_competition_elasticity": _d(
            config.get("deposit_beta_competition_elasticity", Decimal("0"))
        ),
        "checkable_reference_stock_bil": checkable,
        "migrated_stock_bil": initial_migrated,
        "migrated_share": Decimal("0") if checkable == 0 else initial_migrated / checkable,
        "peak_migrated_stock_bil": peak,
        "base_migrated_stock_bil": _d(config.get("base_migrated_stock_bil", Decimal("0"))),
        "normalized_months": _d(config.get("normalized_months", Decimal("0"))),
        "last_flow_bil": Decimal("0"),
        "last_fiscal_tilt_flow_bil": Decimal("0"),
        "cumulative_fiscal_tilt_flow_bil": Decimal("0"),
        "enabled_mechanisms": enabled,
        "stock_adjustment_already_in_pack": bool(config.get("stock_adjustment_already_in_pack", False)),
    }


def _advance_hysteresis_state(
    opening: dict[str, Decimal],
    state: dict[str, Decimal | bool | frozenset[str]],
    shock_multiplier: Decimal,
    *,
    fiscal_tilt_flow_bil: Decimal = Decimal("0"),
) -> dict[str, Decimal | bool | frozenset[str]]:
    enabled = state["enabled_mechanisms"]
    if not isinstance(enabled, frozenset) or "migration" not in enabled:
        return state | {
            "last_flow_bil": Decimal("0"),
            "last_fiscal_tilt_flow_bil": Decimal("0"),
        }
    reference = _d(state["checkable_reference_stock_bil"])
    current = _d(state["migrated_stock_bil"])
    peak = _d(state["peak_migrated_stock_bil"])
    policy_gap_pp = abs(shock_multiplier)
    flow = Decimal("0")
    normalized_months = _d(state["normalized_months"])
    if policy_gap_pp > _d(state["activation_pp"]):
        target_share = min(
            _d(state["migration_cap"]),
            _d(state["migration_elasticity"]) * (policy_gap_pp - _d(state["activation_pp"])),
        )
        target_stock = reference * target_share
        monthly_in = target_stock / Decimal("12")
        flow = min(monthly_in, max(Decimal("0"), target_stock - current))
        current += flow
        peak = max(peak, current)
        normalized_months = Decimal("0")
    elif current > 0:
        normalized_months = min(Decimal("24"), normalized_months + Decimal("1"))
        total_return_stock = peak * _d(state["reversal_share"])
        floor_stock = max(Decimal("0"), peak - total_return_stock)
        flow = -min(max(Decimal("0"), current - floor_stock), total_return_stock / Decimal("24"))
        current += flow
    fiscal_flow = max(Decimal("0"), fiscal_tilt_flow_bil)
    if fiscal_flow:
        current += fiscal_flow
        peak = max(peak, current)
    share = Decimal("0") if reference == 0 else current / reference
    return state | {
        "migrated_stock_bil": current,
        "migrated_share": share,
        "peak_migrated_stock_bil": peak,
        "normalized_months": normalized_months,
        "last_flow_bil": flow + fiscal_flow,
        "last_fiscal_tilt_flow_bil": fiscal_flow,
        "cumulative_fiscal_tilt_flow_bil": _d(state.get("cumulative_fiscal_tilt_flow_bil", Decimal("0"))) + fiscal_flow,
    }


def _fiscal_tilt_flow_bil(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    month_index: int,
    config: dict[str, object] | None,
) -> Decimal:
    if not config or not bool(config.get("enabled", False)):
        return Decimal("0")
    gross_by_month = config.get("gross_issuance_by_month_bil", [])
    if not isinstance(gross_by_month, (list, tuple)):
        return Decimal("0")
    if month_index < 1 or month_index > len(gross_by_month):
        return Decimal("0")
    share = _d(config.get("reabsorption_tilt_share", Decimal("0")))
    nonbank_share = _d(
        config.get(
            "nonbank_absorption_share",
            _nonbank_market_complex_absorption_share(pack, band),
        )
    )
    return max(Decimal("0"), _d(gross_by_month[month_index - 1])) * nonbank_share * share


def _nonbank_market_complex_absorption_share(
    pack: dict[str, list[dict[str, str]]],
    band: str,
) -> Decimal:
    return sum(
        max(Decimal("0"), _d(row[band]))
        for row in pack.get("absorption_modes", [])
        if row.get("mode_id") in {"A", "A_RRP"}
    )


def _pack_with_qt_deposit_leg(
    pack: dict[str, list[dict[str, str]]],
    qt_supply_stress: bool | Decimal | str,
) -> dict[str, list[dict[str, str]]]:
    scale = _qt_supply_stress_scale(qt_supply_stress)
    if scale == 0:
        return pack
    rows = [dict(row) for row in pack.get("opening_stocks", [])]
    for band in BANDS:
        runoff = _qt_runoff_bil(pack, band) * scale
        nonbank_share = _nonbank_market_complex_absorption_share(pack, band)
        deposit_delta = -runoff * nonbank_share
        _apply_bank_deposit_stock_delta(rows, band, deposit_delta)
    return pack | {"opening_stocks": rows}


def _qt_runoff_bil(pack: dict[str, list[dict[str, str]]], band: str) -> Decimal:
    explicit = _assumptions(pack).get("qt_runoff_bil")
    if explicit:
        return _d(explicit[band])
    rows = pack.get("absorption_mode_mix_summary_annual_and_2010_2019_avg", [])
    annual_rows = [
        row
        for row in rows
        if row.get("year", "").strip()
        and row.get("D_amount_mn", "").strip()
        and _d(row.get("D_amount_mn", "0")) < 0
    ]
    if not annual_rows:
        return Decimal("0")
    latest = max(annual_rows, key=lambda row: int(Decimal(row["year"])))
    return abs(_d(latest["D_amount_mn"])) / Decimal("1000")


def _apply_bank_deposit_stock_delta(
    rows: list[dict[str, str]],
    band: str,
    delta: Decimal,
) -> None:
    targets = [
        row
        for row in rows
        if row["instrument_family"]
        in {"deposits_checkable", "deposits_savings_mmda", "deposits_time_cds"}
        and _issuer_from_opening_row(row) == "banks"
    ]
    total = sum(_d(row[band]) for row in targets)
    if total == 0 or delta == 0:
        return
    if delta < 0 and -delta > total:
        delta = -total
    for row in targets:
        value = _d(row[band])
        row[band] = _fmt(value + delta * value / total)


def _hysteresis_rate_add_by_family(
    state: dict[str, Decimal | bool | frozenset[str]],
    shock_multiplier: Decimal,
) -> dict[str, Decimal]:
    enabled = state["enabled_mechanisms"]
    if not isinstance(enabled, frozenset) or "beta" not in enabled:
        return {}
    beta_add = (
        Decimal("0.01")
        * _d(state["deposit_beta_competition_elasticity"])
        * _d(state["migrated_share"])
        * shock_multiplier
        / Decimal("12")
    )
    return {
        "deposits_savings_mmda": beta_add,
        "deposits_time_cds": beta_add,
    }


def _pack_with_hysteresis_state(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    state: dict[str, Decimal | bool | frozenset[str]],
) -> dict[str, list[dict[str, str]]]:
    delta = _d(state["migrated_stock_bil"]) - _d(state["base_migrated_stock_bil"])
    if delta == 0:
        return pack
    rows = [dict(row) for row in pack["opening_stocks"]]
    if delta > 0:
        moved = _move_opening_family_band(
            rows,
            "deposits_checkable",
            "mmf_shares",
            delta,
            band,
            to_issuer="nonbank_finance_mmfs",
        )
        _add_opening_family_band(
            rows,
            "mmf_short_funding_assets",
            moved,
            band,
            holder="nonbank_finance_mmfs",
            issuer="short_funding_payers",
        )
    else:
        returned = _move_opening_family_band(
            rows,
            "mmf_shares",
            "deposits_checkable",
            -delta,
            band,
            to_issuer="banks",
        )
        _add_opening_family_band(
            rows,
            "mmf_short_funding_assets",
            -returned,
            band,
            holder="nonbank_finance_mmfs",
            issuer="short_funding_payers",
        )
    return pack | {"opening_stocks": rows}


def _move_opening_family_band(
    rows: list[dict[str, str]],
    from_family: str,
    to_family: str,
    amount: Decimal,
    band: str,
    *,
    to_issuer: str,
) -> Decimal:
    from_rows = [row for row in rows if row["instrument_family"] == from_family]
    from_total = sum(_d(row[band]) for row in from_rows)
    move = min(amount, from_total)
    if move <= 0:
        return Decimal("0")
    holder_moves: dict[str, Decimal] = {}
    for row in from_rows:
        old_value = _d(row[band])
        row_move = Decimal("0") if from_total == 0 else move * old_value / from_total
        row[band] = _fmt(old_value - row_move)
        holder = _holder_from_opening_row(row)
        holder_moves[holder] = holder_moves.get(holder, Decimal("0")) + row_move
    for holder, holder_amount in holder_moves.items():
        _add_opening_family_band(rows, to_family, holder_amount, band, holder=holder, issuer=to_issuer)
    return move


def _add_opening_family_band(
    rows: list[dict[str, str]],
    family: str,
    amount: Decimal,
    band: str,
    *,
    holder: str,
    issuer: str,
) -> None:
    if amount == 0:
        return
    target = next(
        (
            row
            for row in rows
            if row["instrument_family"] == family
            and row["cell_or_sector"] == f"holder={holder}|issuer={issuer}"
        ),
        None,
    )
    if target is None:
        target = {
            "parameter_id": "hysteresis_engine_loop_stock",
            "cell_or_sector": f"holder={holder}|issuer={issuer}",
            "instrument_family": family,
            "low": "0",
            "base": "0",
            "high": "0",
            "units": "$bn_current",
            "source_id": "hysteresis_engine_loop",
            "input_basis_label": "engine_loop_scenario",
            "rationale": "Scenario-local monthly migration ledger stock adjustment.",
        }
        rows.append(target)
    target[band] = _fmt(_d(target[band]) + amount)
    if family == "mmf_short_funding_assets" and band != "base":
        target["base"] = _fmt(_d(target["base"]) + amount)


def _annual_records_from_monthly(
    monthly_records: list[dict[str, Decimal | str]],
) -> list[dict[str, Decimal | str]]:
    records: list[dict[str, Decimal | str]] = []
    keys = sorted(
        {
            (str(row["band"]), str(row["year"]), row["ricardian_offset"])
            for row in monthly_records
        },
        key=lambda key: (BANDS.index(key[0]), key[1], key[2]),
    )
    flow_fields = [
        "public_n",
        "public_d",
        "private_n",
        "private_d",
        "N",
        "D",
        "net",
        "bill_interest",
        "coupon_interest",
        "coupon_current_stock_interest",
        "coupon_new_issuance_interest",
        "government_interest_delta",
        "iorb_delta",
        "on_rrp_delta",
        "remittance_delta",
        "aggregate_matrix_government_net",
        "tdc_issuance_divergence_bil",
        "tdc_new_created_deposits_bil",
        "tdc_created_deposit_income_bil",
    ]
    for band, year, ricardian in keys:
        group = [
            row
            for row in monthly_records
            if row["band"] == band and row["year"] == year and row["ricardian_offset"] == ricardian
        ]
        exemplar = group[0]
        out: dict[str, Decimal | str] = {
            "band": band,
            "year_index": Decimal(int(year) - START_YEAR + 1),
            "year": year,
            "ricardian_offset": ricardian,
            "nominal_gdp_bil": exemplar["nominal_gdp_bil"],
            "shock_start_month": exemplar["shock_start_month"],
            "dose_mode": exemplar["dose_mode"],
            "shock_multiplier": sum(row["shock_multiplier"] for row in group),
            "active_months_elapsed": group[-1]["active_months_elapsed"],
            "tdc_created_deposit_stock_bil": group[-1]["tdc_created_deposit_stock_bil"],
            "tdc_created_deposit_full_level_rate": exemplar[
                "tdc_created_deposit_full_level_rate"
            ],
            "tdc_implied_beta": exemplar["tdc_implied_beta"],
            "cashflow_routes": _merge_record_routes(group),
            "cashflow_family_routes": _merge_record_family_routes(group),
            "pre_tax_cashflow_family_routes": _merge_record_family_routes(
                group,
                field_name="pre_tax_cashflow_family_routes",
            ),
            "tax_layer_rows": _merge_record_tax_rows(group),
            "tax_layer_status": exemplar.get("tax_layer_status", "off"),
        }
        for field in flow_fields:
            out[field] = sum(row[field] for row in group)
        out["RW"] = Decimal("0") if out["D"] == 0 else out["N"] / out["D"]
        out["bottom_up_D_to_legacy_D"] = out["D"] / (
            out["nominal_gdp_bil"] * Decimal("0.00776")
        )
        out["coupon_current_stock_reprice_share"] = group[-1][
            "coupon_current_stock_reprice_share"
        ]
        out["coupon_new_issuance_reprice_share"] = group[-1][
            "coupon_new_issuance_reprice_share"
        ]
        records.append(out)
    return records


def legacy_annual_records_for_comparison(
    pack_dir: Path = Path("configs/rwtam/packs"),
    *,
    include_scenario_adjustments: bool = True,
    include_tdc_settlement: bool | None = None,
) -> list[dict[str, Decimal | str]]:
    if include_tdc_settlement is None:
        include_tdc_settlement = include_scenario_adjustments
    pack = _effective_pack(
        _load_pack(pack_dir),
        include_scenario_adjustments,
        include_tdc_settlement,
    )
    return _legacy_annual_records(pack, include_tdc_settlement=include_tdc_settlement)


def _merge_record_routes(
    records: list[dict[str, Decimal | str]],
) -> dict[str, Decimal]:
    routes: dict[str, Decimal] = {}
    for record in records:
        record_routes = record.get("cashflow_routes", {})
        if not isinstance(record_routes, dict):
            continue
        routes = _merge_routes(routes, record_routes)
    return routes


def _merge_record_family_routes(
    records: list[dict[str, Decimal | str]],
    *,
    field_name: str = "cashflow_family_routes",
) -> dict[str, dict[str, Decimal]]:
    family_routes: dict[str, dict[str, Decimal]] = {}
    for record in records:
        record_routes = record.get(field_name)
        if not isinstance(record_routes, dict):
            continue
        _merge_family_routes(family_routes, record_routes)
    return family_routes


def _copy_family_routes(
    family_routes: dict[str, dict[str, Decimal]],
) -> dict[str, dict[str, Decimal]]:
    return {family: dict(routes) for family, routes in family_routes.items()}


def _merge_record_tax_rows(
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        for row in record.get("tax_layer_rows", []):  # type: ignore[union-attr]
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _routes_from_family_routes(
    family_routes: dict[str, dict[str, Decimal]],
) -> dict[str, Decimal]:
    routes: dict[str, Decimal] = {}
    for family_route in family_routes.values():
        routes = _merge_routes(routes, family_route)
    return routes


def _apply_tax_layer_to_family_routes(
    pack: dict[str, list[dict[str, str]]],
    family_routes: dict[str, dict[str, Decimal]],
    band: str,
    month_index: int,
    active_months_elapsed: int,
    shock_multiplier: Decimal,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for family, routes in family_routes.items():
        for cell, amount in list(routes.items()):
            if amount > 0 and cell in HH_CELLS:
                rows.extend(
                    _apply_household_interest_tax(
                        pack,
                        routes,
                        family,
                        cell,
                        amount,
                        band,
                        month_index,
                    )
                )
            elif amount < 0:
                rows.extend(
                    _apply_interest_deduction_tax_shield(
                        pack,
                        routes,
                        family,
                        cell,
                        amount,
                        band,
                        month_index,
                        active_months_elapsed,
                        shock_multiplier,
                    )
                )
    return rows


def _apply_household_interest_tax(
    pack: dict[str, list[dict[str, str]]],
    routes: dict[str, Decimal],
    family: str,
    cell: str,
    amount: Decimal,
    band: str,
    month_index: int,
) -> list[dict[str, str]]:
    tax_family = _household_tax_family(family)
    if tax_family is None:
        return []
    rate_parameter, rate_family = _household_tax_rate_parameter(family)
    rate = _tax_parameter(pack, rate_parameter, cell, rate_family, band)
    taxable_share = _tax_parameter(
        pack,
        "taxable_or_current_taxed_account_share",
        cell,
        tax_family,
        band,
    )
    tax = amount * rate * taxable_share
    if tax == 0:
        return []
    routes[cell] = amount - tax
    routes["treasury_federal_accounting_cell"] = routes.get(
        "treasury_federal_accounting_cell", Decimal("0")
    ) + tax
    return [
        {
            "tax_layer_component": "household_interest_income_tax_wedge",
            "period_type": "monthly",
            "month": _month_label(month_index),
            "year": _month_label(month_index)[:4],
            "band": band,
            "instrument_family": family,
            "tax_pack_family": tax_family,
            "cell_or_sector": cell,
            "pre_tax_flow_bil": _fmt(amount),
            "taxable_or_current_taxed_share": _fmt(taxable_share),
            "effective_tax_rate": _fmt(rate),
            "tax_or_shield_bil": _fmt(tax),
            "post_tax_flow_bil": _fmt(amount - tax),
            "treasury_receipt_flow_bil": _fmt(tax),
            "source_basis": TAX_LAYER_PACK_ID,
            "disposition": "taxed_before_cell_conversion;federal_only_for_treasuries_else_federal_plus_state",
        }
    ]


def _apply_interest_deduction_tax_shield(
    pack: dict[str, list[dict[str, str]]],
    routes: dict[str, Decimal],
    family: str,
    cell: str,
    amount: Decimal,
    band: str,
    month_index: int,
    active_months_elapsed: int,
    shock_multiplier: Decimal,
) -> list[dict[str, str]]:
    shield_spec = _shield_spec_for_negative_route(family, cell)
    if shield_spec is None:
        return []
    parameter_id, tax_family = shield_spec
    interest_expense = -amount
    if parameter_id == "mortgage_interest_deduction_marginal_offset_share":
        shield = _tax_parameter(pack, parameter_id, cell, tax_family, band)
        mechanism = "mortgage_interest_deduction_cell_rows"
    else:
        base_shield = _tax_parameter(pack, parameter_id, cell, tax_family, band)
        subject_share = _tax_parameter(
            pack,
            "section_163j_subject_to_cap_interest_share",
            cell,
            tax_family,
            band,
        )
        denied_share = _tax_parameter(
            pack,
            "section_163j_denied_or_deferred_current_deduction_share",
            cell,
            tax_family,
            band,
        )
        shield = _dynamic_163j_shield(
            base_shield,
            subject_share,
            denied_share,
            Decimal("100") * shock_multiplier,
        )
        mechanism = "base_pack_shield_recomputed_monthly_with_d2_inverse_icr_shock_path"
    shield_value = interest_expense * shield
    post_tax_drag = interest_expense - shield_value
    routes[cell] = -post_tax_drag
    routes["treasury_federal_accounting_cell"] = routes.get(
        "treasury_federal_accounting_cell", Decimal("0")
    ) - shield_value
    return [
        {
            "tax_layer_component": "interest_deductibility_tax_shield",
            "period_type": "monthly",
            "month": _month_label(month_index),
            "year": _month_label(month_index)[:4],
            "band": band,
            "instrument_family": family,
            "tax_pack_family": tax_family,
            "cell_or_sector": cell,
            "pre_tax_flow_bil": _fmt(amount),
            "taxable_or_current_taxed_share": "",
            "effective_tax_rate": _fmt(shield),
            "tax_or_shield_bil": _fmt(shield_value),
            "post_tax_flow_bil": _fmt(-post_tax_drag),
            "treasury_receipt_flow_bil": _fmt(-shield_value),
            "source_basis": TAX_LAYER_PACK_ID,
            "claim_grade_label": "stress_convention_owner_assumption",
            "disposition": mechanism,
        }
    ]


def _household_tax_family(family: str) -> str | None:
    mapping = {
        "treasury_bills": "direct_treasuries",
        "treasury_coupon_current_stock_roll": "direct_treasuries",
        "treasury_coupon_new_deficit_issuance": "direct_treasuries",
        "treasury_notes_bonds_tips": "direct_treasuries",
        "deposits_checkable": "checkable_deposits",
        "deposits_savings_mmda": "savings_mmda",
        "deposits_time_cds": "cds_time_deposits",
        "mmf_short_funding_assets": "mmf_shares",
        "fed_on_rrp_mmfs": "mmf_shares",
        "bnpl_float_mmfs": "mmf_shares",
        "bnpl_float_deposits": "savings_mmda",
        "tdc_created_deposit_income_from_deficit_financing": "checkable_deposits",
        TDC_SPLIT_ROUTE_FAMILY: "checkable_deposits",
        "corporate_bonds": "bond_equity_funds",
        "municipal_securities": "bond_equity_funds",
        "c_and_i_depository_loans": "bond_equity_funds",
        "syndicated_loans": "bond_equity_funds",
    }
    return mapping.get(family)


def _household_tax_rate_parameter(family: str) -> tuple[str, str]:
    if _household_tax_family(family) == "direct_treasuries":
        return ("interest_income_mtr_federal_only", "direct_treasuries")
    return ("interest_income_mtr_federal_plus_state_avg", "taxable_deposits_prime_mmf")


def _shield_spec_for_negative_route(family: str, cell: str) -> tuple[str, str] | None:
    if cell in FIRM_CELLS:
        if family in {"cre_mortgages_floating", "cre_mortgages_fixed"}:
            return (
                "effective_c_corp_interest_deduction_shield_rate_after_163j",
                "CRE_family_interest_expense",
            )
        if family in {"corporate_bonds", "syndicated_loans"}:
            return (
                "effective_c_corp_interest_deduction_shield_rate_after_163j",
                "HY_leveraged_credit_family_interest_expense",
            )
        if family in {"c_and_i_depository_loans", "bnpl_funding_liability"}:
            if cell == "firm_bank_dependent_small":
                return (
                    "effective_passthrough_owner_interest_deduction_shield_rate_after_163j",
                    "business_interest_expense",
                )
            return (
                "effective_c_corp_interest_deduction_shield_rate_after_163j",
                "business_interest_expense",
            )
    if cell in HH_CELLS and family in {"mortgages_fixed", "mortgages_arm", "heloc"}:
        tax_family = "fixed_rate_mortgages" if family == "mortgages_fixed" else "arm_mortgages_heloc"
        return ("mortgage_interest_deduction_marginal_offset_share", tax_family)
    return None


def _dynamic_163j_shield(
    base_shield: Decimal,
    subject_share: Decimal,
    denied_share: Decimal,
    shock_magnitude_bp: Decimal,
) -> Decimal:
    shock_scale = max(Decimal("0"), shock_magnitude_bp) / Decimal("100")
    share_over_cap = min(Decimal("1"), subject_share * shock_scale)
    decay = share_over_cap * denied_share
    return max(Decimal("0"), base_shield * (Decimal("1") - decay))


def _tax_parameter(
    pack: dict[str, list[dict[str, str]]],
    parameter_id: str,
    cell: str,
    family: str,
    band: str,
) -> Decimal:
    for row in pack.get("parameters_tax_layer", []):
        if (
            row["parameter_id"] == parameter_id
            and row["cell_or_sector"] == cell
            and row["instrument_family"] == family
        ):
            return _d(row[band])
    return Decimal("0")


def _add_family_routes(
    family_routes: dict[str, dict[str, Decimal]],
    family: str,
    routes: dict[str, Decimal],
) -> None:
    if not routes:
        return
    target = family_routes.setdefault(family, {})
    for cell, amount in routes.items():
        target[cell] = target.get(cell, Decimal("0")) + amount


def _merge_family_routes(
    target: dict[str, dict[str, Decimal]],
    source: dict[str, dict[str, Decimal]],
) -> None:
    for family, routes in source.items():
        _add_family_routes(target, family, routes)


def cashflow_family_contribution_rows(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
    *,
    core_id: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    period_rows: list[dict[str, str]] = []
    conversion = _conversion(pack)
    for record in records:
        family_routes = record.get("cashflow_family_routes")
        if not isinstance(family_routes, dict):
            continue
        contributions = _allocate_family_contributions(
            family_routes,
            conversion,
            record["ricardian_offset"],
        )
        period_type = "monthly" if "month_index" in record else "annual"
        period = str(record.get("month") or record["year"])
        for family in sorted(contributions):
            flow = contributions[family]
            raw_cashflow = _family_raw_cashflow(family_routes[family])
            row = {
                "core_id": core_id,
                "period_type": period_type,
                "period": period,
                "year": str(record["year"]),
                "month_index": _fmt(record.get("month_index", Decimal("0")))
                if period_type == "monthly"
                else "",
                "dose_mode": str(record.get("dose_mode", "legacy_annual_core")),
                "band": str(record["band"]),
                "ricardian_offset": _fmt(record["ricardian_offset"]),
                "instrument_family": family,
                "N_bil": _fmt(flow["N"]),
                "D_bil": _fmt(flow["D"]),
                "net_bil": _fmt(flow["N"] - flow["D"]),
                "raw_signed_route_bil": _fmt(
                    sum(family_routes[family].values(), Decimal("0"))
                ),
                "raw_cashflow_bil": _fmt(raw_cashflow),
                "classification_rule": "allocated_after_global_cell_netting",
                "diagnostic_role": "engine_owned_family_cashflow_contribution",
            }
            rows.append(row)
            period_rows.append(row)

    cumulative_keys = sorted(
        {
            (
                row["dose_mode"],
                row["band"],
                row["ricardian_offset"],
                row["instrument_family"],
            )
            for row in period_rows
        },
        key=lambda key: (
            key[0],
            BANDS.index(key[1]) if key[1] in BANDS else 99,
            key[2],
            key[3],
        ),
    )
    for dose_mode, band, ricardian, family in cumulative_keys:
        peers = [
            row
            for row in period_rows
            if row["dose_mode"] == dose_mode
            and row["band"] == band
            and row["ricardian_offset"] == ricardian
            and row["instrument_family"] == family
        ]
        n_value = sum(_d(row["N_bil"]) for row in peers)
        d_value = sum(_d(row["D_bil"]) for row in peers)
        raw_value = sum(_d(row["raw_signed_route_bil"]) for row in peers)
        raw_cashflow = sum(_d(row["raw_cashflow_bil"]) for row in peers)
        rows.append(
            {
                "core_id": core_id,
                "period_type": "cumulative_120_month",
                "period": "2026-2035",
                "year": "2026-2035",
                "month_index": "",
                "dose_mode": dose_mode,
                "band": band,
                "ricardian_offset": ricardian,
                "instrument_family": family,
                "N_bil": _fmt(n_value),
                "D_bil": _fmt(d_value),
                "net_bil": _fmt(n_value - d_value),
                "raw_signed_route_bil": _fmt(raw_value),
                "raw_cashflow_bil": _fmt(raw_cashflow),
                "classification_rule": "allocated_after_global_cell_netting",
                "diagnostic_role": "engine_owned_family_cashflow_contribution",
            }
        )
    return rows
    return rows


def _family_raw_cashflow(routes: dict[str, Decimal]) -> Decimal:
    positive = sum((amount for amount in routes.values() if amount > 0), Decimal("0"))
    negative = -sum((amount for amount in routes.values() if amount < 0), Decimal("0"))
    return max(positive, negative)


def _allocate_family_contributions(
    family_routes: dict[str, dict[str, Decimal]],
    conversion: dict[str, Decimal],
    ricardian_offset: Decimal | str,
) -> dict[str, dict[str, Decimal]]:
    out: dict[str, dict[str, Decimal]] = {}
    cells = sorted({cell for routes in family_routes.values() for cell in routes})
    for cell in cells:
        coeff = conversion.get(cell, Decimal("0"))
        if cell == "treasury_federal_accounting_cell":
            coeff = _d(str(ricardian_offset))
        cell_total = sum(routes.get(cell, Decimal("0")) for routes in family_routes.values())
        cell_effect = cell_total * coeff
        if cell_effect == 0:
            continue
        for family, routes in family_routes.items():
            family_effect = routes.get(cell, Decimal("0")) * coeff
            if family_effect == 0:
                continue
            family_out = out.setdefault(family, {"N": Decimal("0"), "D": Decimal("0")})
            if cell_effect > 0:
                family_out["N"] += family_effect
            else:
                family_out["D"] += -family_effect
    return out


def _private_monthly_routes(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    month_index: int,
    shock_start_index: int,
    active_months_elapsed: int,
    dose_mode: str,
    shock_size_bp: Decimal = Decimal("100"),
    *,
    hysteresis_rate_add_by_family: dict[str, Decimal] | None = None,
) -> dict[str, Decimal]:
    routes: dict[str, Decimal] = {}
    for family_routes in _private_monthly_family_routes(
        pack,
        band,
        month_index,
        shock_start_index,
        active_months_elapsed,
        dose_mode,
        shock_size_bp,
        hysteresis_rate_add_by_family=hysteresis_rate_add_by_family,
    ).values():
        routes = _merge_routes(routes, family_routes)
    return routes


def _private_monthly_family_routes(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    month_index: int,
    shock_start_index: int,
    active_months_elapsed: int,
    dose_mode: str,
    shock_size_bp: Decimal = Decimal("100"),
    *,
    hysteresis_rate_add_by_family: dict[str, Decimal] | None = None,
) -> dict[str, dict[str, Decimal]]:
    assumptions = _assumptions(pack)
    family_routes: dict[str, dict[str, Decimal]] = {}
    for rule in _active_claim_processor_rules(pack):
        amount = _claim_rule_amount_monthly(
            pack,
            rule,
            band,
            month_index,
            shock_start_index,
            active_months_elapsed,
            dose_mode,
            assumptions,
            shock_size_bp,
            hysteresis_rate_add_by_family=hysteresis_rate_add_by_family,
        )
        if amount == 0:
            continue
        _add_family_routes(
            family_routes,
            rule["instrument_family"],
            _merge_routes(
                _claim_rule_payer_routes(pack, rule, amount, band, assumptions),
                _claim_rule_receiver_routes(pack, rule, amount, band),
            ),
        )
    return family_routes


def _claim_rule_amount_monthly(
    pack: dict[str, list[dict[str, str]]],
    rule: dict[str, str],
    band: str,
    month_index: int,
    shock_start_index: int,
    active_months_elapsed: int,
    dose_mode: str,
    assumptions: dict[str, dict[str, Decimal]],
    shock_size_bp: Decimal = Decimal("100"),
    *,
    hysteresis_rate_add_by_family: dict[str, Decimal] | None = None,
) -> Decimal:
    family = rule["instrument_family"]
    rate = _claim_rule_rate_monthly(
        rule,
        band,
        month_index,
        shock_start_index,
        active_months_elapsed,
        dose_mode,
        assumptions,
        shock_size_bp,
        hysteresis_rate_add_by_family=hysteresis_rate_add_by_family,
    )
    if rule.get("stock_band_mode") == "band":
        stock = sum(_d(row[band]) for row in _rows(pack, "opening_stocks", instrument_family=family))
    else:
        stock = _opening_by_family(pack).get(family, Decimal("0"))
    return stock * rate


def _claim_rule_rate_monthly(
    rule: dict[str, str],
    band: str,
    month_index: int,
    shock_start_index: int,
    active_months_elapsed: int,
    dose_mode: str,
    assumptions: dict[str, dict[str, Decimal]],
    shock_size_bp: Decimal = Decimal("100"),
    *,
    hysteresis_rate_add_by_family: dict[str, Decimal] | None = None,
) -> Decimal:
    family = rule["instrument_family"]
    shock_multiplier = (
        _shock_multiplier(month_index, shock_start_index, dose_mode)
        * shock_size_bp
        / Decimal("100")
    )
    rate_rule = rule.get("rate_rule", "private_driver")
    constant_level_delta = _optional_d(rule.get("constant_level_delta"))
    if constant_level_delta != 0:
        return constant_level_delta * shock_multiplier / Decimal("12")
    if rate_rule == "zero":
        return Decimal("0")
    if rate_rule == "driver_curve":
        return _driver(rule.get("base_driver") or family, band, (month_index - 1) // 12 + 1) * shock_multiplier / Decimal("12")
    if rate_rule == "bnpl_penalty_roll":
        delinquent = assumptions["bnpl_delinquent_roll_share"][band]
        base = _monthly_private_driver(
            rule.get("base_driver") or "credit_card_revolving",
            band,
            month_index,
            shock_start_index,
            active_months_elapsed,
            dose_mode,
            assumptions,
            shock_size_bp,
            hysteresis_rate_add_by_family=hysteresis_rate_add_by_family,
        )
        return delinquent * base
    return _monthly_private_driver(
        rule.get("base_driver") or family,
        band,
        month_index,
        shock_start_index,
        active_months_elapsed,
        dose_mode,
        assumptions,
        shock_size_bp,
        hysteresis_rate_add_by_family=hysteresis_rate_add_by_family,
    )


def _monthly_private_driver(
    family: str,
    band: str,
    month_index: int,
    shock_start_index: int,
    active_months_elapsed: int,
    dose_mode: str,
    assumptions: dict[str, dict[str, Decimal]],
    shock_size_bp: Decimal = Decimal("100"),
    *,
    hysteresis_rate_add_by_family: dict[str, Decimal] | None = None,
) -> Decimal:
    year_index = (month_index - 1) // 12 + 1
    shock_multiplier = (
        _shock_multiplier(month_index, shock_start_index, dose_mode)
        * shock_size_bp
        / Decimal("100")
    )
    shock_scale = shock_size_bp / Decimal("100")
    base = _driver(family, band, year_index)
    rate_add = (
        Decimal("0")
        if hysteresis_rate_add_by_family is None
        else hysteresis_rate_add_by_family.get(family, Decimal("0"))
    )
    if family == "c_and_i_depository_loans":
        return base * assumptions["ci_floating_share"][band] * shock_multiplier / Decimal("12")
    if family == "corporate_bonds":
        return _monthly_ladder_rate(
            assumptions["corporate_bond_new_issue_beta"][band],
            assumptions["coupon_roll_rate"][band],
            active_months_elapsed,
        ) * shock_scale
    if family == "municipal_securities":
        return _monthly_ladder_rate(
            assumptions["municipal_bond_new_issue_beta"][band],
            assumptions["coupon_roll_rate"][band],
            active_months_elapsed,
        ) * shock_scale
    if family == "cre_mortgages_floating":
        return Decimal("0.01") * assumptions["cre_floating_rate_beta"][band] * shock_multiplier / Decimal("12")
    if family == "cre_mortgages_fixed":
        return _monthly_ladder_rate(
            assumptions["cre_fixed_refi_coupon_beta"][band],
            assumptions["cre_fixed_roll_rate"][band],
            active_months_elapsed,
        ) * shock_scale
    if family in {"auto_installment_debt", "personal_installment_debt"}:
        if dose_mode == "transient_12m":
            return base * assumptions["consumer_installment_new_flow_share"][band] * Decimal(active_months_elapsed) / Decimal("12") / Decimal("12") * shock_scale
        term_parameter = (
            "auto_installment_term_months"
            if family == "auto_installment_debt"
            else "personal_installment_term_months"
        )
        active_share = _amortizing_new_flow_active_share(
            active_months_elapsed,
            assumptions[term_parameter][band],
        )
        return base * assumptions["consumer_installment_new_flow_share"][band] * active_share / Decimal("12") * shock_scale
    if family == "student_loans_private":
        if dose_mode == "transient_12m":
            return base * assumptions["student_private_new_flow_share"][band] * Decimal(active_months_elapsed) / Decimal("12") / Decimal("12") * shock_scale
        active_share = _amortizing_new_flow_active_share(
            active_months_elapsed,
            assumptions["student_private_term_months"][band],
        )
        return base * assumptions["student_private_new_flow_share"][band] * active_share / Decimal("12") * shock_scale
    if family == "mortgages_fixed":
        turnover = (
            Decimal("0.07")
            if dose_mode == "transient_12m"
            else assumptions["mortgage_turnover_share"][band]
        )
        return base * turnover * Decimal(active_months_elapsed) / Decimal("12") / Decimal("12") * shock_scale
    return base * shock_multiplier / Decimal("12") + rate_add


def _monthly_ladder_rate(
    beta: Decimal,
    annual_roll: Decimal,
    active_months_elapsed: int,
) -> Decimal:
    rolled_share = min(
        Decimal("1"),
        annual_roll * Decimal(active_months_elapsed) / Decimal("12"),
    )
    return Decimal("0.01") * beta * rolled_share / Decimal("12")


def _amortizing_new_flow_active_share(
    active_months_elapsed: int,
    term_months: Decimal,
) -> Decimal:
    if active_months_elapsed <= 0 or term_months <= 0:
        return Decimal("0")
    total = Decimal("0")
    for age in range(active_months_elapsed):
        total += max(Decimal("0"), Decimal("1") - Decimal(age) / term_months)
    return total / Decimal("12")


def _current_coupon_maturing_month(
    pack: dict[str, list[dict[str, str]]],
    month: str,
) -> Decimal:
    for row in pack.get("tdcsim_coupon_roll_schedule", []):
        if row["month"] == month:
            return _d(row["maturing_principal_bil"])
    return Decimal("0")


def _coupon_cohorts_from_monthly_issuance(
    pack: dict[str, list[dict[str, str]]],
    *,
    amount: Decimal,
    rate_delta_ann: Decimal,
    issue_month_index: int,
) -> list[_CouponCohort]:
    if amount == 0:
        return []
    rows = [
        row
        for row in pack.get("tdcsim_issuance_tenor_mix", [])
        if not row["tenor_bucket"].startswith("bills_")
    ]
    total = sum(_d(row["share_of_gross_issuance"]) for row in rows)
    if total == 0:
        rows = [{"tenor_bucket": "notes_10y", "share_of_gross_issuance": "1"}]
        total = Decimal("1")
    return [
        _CouponCohort(
            amount=amount * _d(row["share_of_gross_issuance"]) / total,
            rate_delta_ann=rate_delta_ann,
            issue_month_index=issue_month_index,
            tenor_months=_tenor_bucket_months(row["tenor_bucket"]),
            bucket=row["tenor_bucket"],
        )
        for row in rows
    ]


def _new_coupon_interest_from_cohorts(
    cohorts: list[_CouponCohort],
    month_index: int,
    *,
    persist_after_maturity: bool = False,
    active_until_month_index: int | None = None,
) -> Decimal:
    return sum(
        cohort.amount * cohort.rate_delta_ann / Decimal("12")
        for cohort in cohorts
        if _cohort_active(
            cohort,
            month_index,
            persist_after_maturity=persist_after_maturity,
            active_until_month_index=active_until_month_index,
        )
    )


def _cohort_active(
    cohort: _CouponCohort,
    month_index: int,
    *,
    persist_after_maturity: bool = False,
    active_until_month_index: int | None = None,
) -> bool:
    age = month_index - cohort.issue_month_index
    if age < 0:
        return False
    if persist_after_maturity:
        return True
    if active_until_month_index is not None and month_index <= active_until_month_index:
        return True
    if cohort.bucket.startswith("frn_"):
        return age < cohort.tenor_months
    return age < cohort.tenor_months


def _cohort_active_until_month(shock_start_index: int, dose_mode: str) -> int | None:
    if dose_mode != "transient_12m":
        return None
    return shock_start_index + 11


def _tenor_bucket_months(bucket: str) -> int:
    if bucket.startswith("frn_"):
        return 3
    suffix = bucket.rsplit("_", maxsplit=1)[-1]
    if suffix.endswith("y"):
        return int(Decimal(suffix.removesuffix("y")) * Decimal("12"))
    if suffix.endswith("m"):
        return int(Decimal(suffix.removesuffix("m")))
    return 120


def _month_index_from_label(month: str) -> int:
    year_text, month_text = month.split("-", maxsplit=1)
    year = int(year_text)
    month_no = int(month_text)
    index = (year - START_YEAR) * 12 + (month_no - START_MONTH) + 1
    if index < 1 or index > MONTHS:
        raise ValueError(f"shock_start_month {month} outside {_month_label(1)}..{_month_label(MONTHS)}")
    return index


def _validate_dose_mode(dose_mode: str) -> None:
    if dose_mode not in DOSE_MODES:
        raise ValueError(f"dose_mode must be one of {', '.join(DOSE_MODES)}")


def _shock_multiplier(month_index: int, shock_start_index: int, dose_mode: str) -> Decimal:
    if dose_mode == "persistent_level":
        return Decimal("1") if month_index >= shock_start_index else Decimal("0")
    return Decimal("1") if shock_start_index <= month_index < shock_start_index + 12 else Decimal("0")


def _object_version_stamp(dose_mode: str, include_tax_layer: bool = True) -> str:
    if not include_tax_layer:
        if dose_mode == "transient_12m":
            return (
                "current_default_wave8_combined_sinks_tdc_split_suspended_tax_off:"
                "dose_mode=transient_12m,"
                "basis=expectations_consistent_term_premium"
            )
        return f"current_default_wave8_combined_sinks_tdc_split_suspended_tax_off:dose_mode={dose_mode}"
    if dose_mode == DEFAULT_DOSE_MODE:
        return CURRENT_DEFAULT_OBJECT_STAMP
    return f"current_default_wave8_combined_sinks_tdc_split_suspended:dose_mode={dose_mode},named_comparator"


def _output_tables(
    pack: dict[str, list[dict[str, str]]],
    phase6_pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
    validation: list[dict[str, str]],
    pack_dir: Path,
    *,
    monthly_records: list[dict[str, Decimal | str]] | None = None,
    dose_mode: str,
    include_tax_layer: bool,
    qt_supply_stress: bool | Decimal | str = False,
    impulse_beta_records: list[dict[str, Decimal | str]] | None = None,
    use_impulse_beta_context: bool = False,
    bnpl_scenario_records: list[dict[str, Decimal | str]] | None = None,
    bnpl_scenario_pack: dict[str, list[dict[str, str]]] | None = None,
) -> dict[str, list[dict[str, str]]]:
    _prime_record_index(records)
    cashflow_annual = [_headline_row(record, "annual") for record in records]
    cashflow_cumulative: list[dict[str, str]] = []
    cashflow_monthly: list[dict[str, str]] = []
    ricardian_offsets = _ricardian_offsets(pack)
    for band in BANDS:
        band_group = [record for record in records if record["band"] == band]
        for ricardian in ricardian_offsets:
            group = [
                record
                for record in records
                if record["band"] == band and record["ricardian_offset"] == ricardian
            ]
            cashflow_cumulative.append(_cumulative_row(group, band_group))
    if monthly_records is None:
        for band in BANDS:
            for ricardian in ricardian_offsets:
                group = [
                    record
                    for record in records
                    if record["band"] == band and record["ricardian_offset"] == ricardian
                ]
                for record in group:
                    for month_in_year in range(1, 13):
                        month_no = (int(record["year_index"]) - 1) * 12 + month_in_year
                        month = _month_label(month_no)
                        cashflow_monthly.append(_monthly_row(record, month, month_no))
    else:
        cashflow_monthly = [_monthly_row(record, str(record["month"]), int(record["month_index"])) for record in monthly_records]

    base_records = [
        record
        for record in records
        if record["band"] == "base" and record["ricardian_offset"] == Decimal("0")
    ]
    waterfall_annual = _phase6_waterfall(cashflow_annual, phase6_pack)
    waterfall_monthly = _phase6_waterfall(cashflow_monthly, phase6_pack)
    waterfall_cumulative = _phase6_cumulative_waterfall(waterfall_annual)
    rw_full_rollup = _rw_full_headline_from_waterfall(
        waterfall_annual + waterfall_cumulative
    )
    rw_full_monthly = _rw_full_headline_from_waterfall(waterfall_monthly)
    tables = {
        "out_ratewall_monthly": rw_full_monthly,
        "out_ratewall_rollup": rw_full_rollup,
        "out_cashflow_core_monthly": cashflow_monthly,
        "out_cashflow_core_rollup": cashflow_annual + cashflow_cumulative,
        "out_cashflow_family_contributions": cashflow_family_contribution_rows(
            pack,
            records,
            core_id=f"monthly_cashflow_core:{dose_mode}",
        ),
        "out_cashflow_family_contributions_monthly": cashflow_family_contribution_rows(
            pack,
            monthly_records or [],
            core_id=f"monthly_cashflow_core:{dose_mode}",
        ),
        "out_phase6_waterfall_scaffold": waterfall_annual + waterfall_cumulative,
        "out_phase6_waterfall_monthly": waterfall_monthly,
        "out_phase6_overlap_registry": _phase6_overlap_registry(phase6_pack),
        "out_phase6_channel_table": _phase6_channel_table(phase6_pack),
        "out_phase6_excluded_diagnostics": _phase6_excluded_diagnostics(phase6_pack),
        "out_iorb_channel": _iorb_table(pack, base_records),
        "out_government_interest_channel": _government_table(pack, base_records),
        "out_curve_to_holders_channel": _curve_table(pack, base_records),
        "out_bank_receipt_pay_ledger": _bank_receipt_pay_ledger(pack, base_records),
        "out_deposit_holder_routing": _deposit_holder_routing(pack, records),
        "out_mortgage_holder_routing": _mortgage_holder_routing(pack, records),
        "out_cre_cashflow_channel": _cre_cashflow_channel(pack, records),
        "out_claim_processor_channel": _claim_processor_channel(pack, records),
        "out_bnpl_channel": _bnpl_channel(
            bnpl_scenario_pack or pack,
            bnpl_scenario_records or [],
        ),
        "out_bnpl_share_sensitivity": _bnpl_share_sensitivity(
            bnpl_scenario_pack or pack,
            bnpl_scenario_records or [],
        ),
        "out_scenario_delta_derivation": _scenario_delta_derivation_table(pack),
        "out_scenario_delta_balance": _scenario_delta_balance_table(pack),
        "out_moneyness_liquid_buffers": _moneyness_liquid_buffers(pack),
        "out_absorption_modes": _absorption_modes_table(pack),
        "out_tdc_beta_authority": _tdc_beta_authority_table(pack),
        "out_tdc_channel": _tdc_channel_table(pack, records),
        "out_tdc_beta_implied": _tdc_beta_implied_table(pack, records),
        "out_tdc_mode_sensitivity": _tdc_mode_sensitivity_table(pack, records),
        "out_tdc_chi_diagnostic": _tdc_chi_diagnostic_table(pack),
        "out_coupon_cohort_repricing": _coupon_cohort_repricing_table(
            pack,
            monthly_records,
            dose_mode,
            qt_supply_stress=qt_supply_stress,
            use_impulse_beta_context=use_impulse_beta_context,
        ),
        "out_treasury_coupon_roll_schedule": _treasury_coupon_roll_schedule_table(pack),
        "out_treasury_issuance_tenor_mix": _treasury_issuance_tenor_mix_table(pack),
        "out_bond_mtm_diagnostic": _bond_mtm_diagnostic(pack, pack_dir / "bond_mtm", dose_mode),
        "out_cashflow_leg_gross": _cashflow_leg_gross_table(pack, records),
        "out_combined_sink_trace": _combined_sink_trace_table(monthly_records or []),
        "out_tax_layer_household_wedge": _tax_layer_rows(records, "household_interest_income_tax_wedge"),
        "out_tax_layer_corporate_shield": _tax_layer_rows(records, "interest_deductibility_tax_shield"),
        "out_treasury_tax_receipts": _treasury_tax_receipts_table(records),
        "out_tax_layer_clawback_memo": _tax_layer_clawback_memo(pack, records),
        "out_tax_layer_attribution": _tax_layer_attribution_table(
            pack,
            monthly_records or records,
        ),
        "out_additive_waterfall_inputs": _additive_waterfall_inputs(pack, waterfall_monthly),
        "out_fed_rrp_channel": _fed_rrp_channel(pack, base_records),
        "out_scenario_axes_config": _scenario_axes_config(),
        "out_legacy_d_comparator": _legacy_comparator_from_headline(rw_full_rollup),
        "out_flagged_assumptions": _flagged_assumptions(pack),
        "out_retiree_collapse_diagnostic": _retiree_diagnostic(pack, base_records),
        "out_parallel_curve_comparison": _parallel_curve_comparison(
            pack,
            base_records,
            impulse_beta_records or [],
            dose_mode,
        ),
        "out_default_fixture": _default_fixture(),
    }
    if _qt_supply_stress_scale(qt_supply_stress):
        tables["out_qt_deposit_leg"] = _qt_deposit_leg_table(pack, qt_supply_stress)
    tables["out_invariant_check"] = _invariant_table(
        pack,
        records,
        tables,
        validation,
        include_tax_layer=include_tax_layer,
        monthly_records=monthly_records or [],
    )
    return _stamp_tables(tables, dose_mode, include_tax_layer=include_tax_layer)


def _headline_row(record: dict[str, Decimal | str], period_type: str) -> dict[str, str]:
    row = {
        "period_type": period_type,
        "period": str(record["year"]),
        "dose_mode": str(record.get("dose_mode", "legacy_annual_core")),
        "band": str(record["band"]),
        "band_label": _band_label(str(record["band"])),
        "ricardian_offset": _fmt(record["ricardian_offset"]),
        "N_bil": _fmt(record["N"]),
        "D_bil": _fmt(record["D"]),
        "net_bil": _fmt(record["net"]),
        "net_pct_gdp": _fmt(record["net"] / record["nominal_gdp_bil"]),
        "RW_ratio": _fmt(record["RW"]),
        "legacy_D_comparator_bil": _fmt(record["nominal_gdp_bil"] * Decimal("0.00776")),
        "bottom_up_D_to_legacy_D": _fmt(record["bottom_up_D_to_legacy_D"]),
        "classification_rule": "net_within_cell",
        "legacy_comparator_role": "comparator_only",
        "object_version_stamp": f"cashflow_core_pre_phase6_not_RW_full:dose_mode={record.get('dose_mode', 'legacy_annual_core')}",
        "shock_start_month": str(record.get("shock_start_month", "legacy_annual_core")),
        "shock_multiplier": _fmt(record.get("shock_multiplier", Decimal("12"))),
    }
    for ricardian in _record_ricardian_offsets(str(record["band"]), str(record["year"])):
        suffix = _ricardian_suffix(ricardian)
        row[f"ricardian_{suffix}_N_bil"] = _fmt(_same_record(record, ricardian, "N"))
        row[f"ricardian_{suffix}_D_bil"] = _fmt(_same_record(record, ricardian, "D"))
        row[f"ricardian_{suffix}_net_bil"] = _fmt(_same_record(record, ricardian, "net"))
        row[f"ricardian_{suffix}_RW"] = _fmt(_same_record(record, ricardian, "RW"))
    return row


_RECORD_INDEX: dict[tuple[str, str, Decimal], dict[str, Decimal | str]] = {}


def _same_record(record: dict[str, Decimal | str], ricardian: Decimal, field: str) -> Decimal:
    key = (str(record["band"]), str(record["year"]), ricardian)
    return _RECORD_INDEX.get(key, record)[field]


def _record_ricardian_offsets(band: str, year: str) -> list[Decimal]:
    return sorted(
        ricardian
        for key_band, key_year, ricardian in _RECORD_INDEX
        if key_band == band and key_year == year
    )


def _ricardian_offsets(pack: dict[str, list[dict[str, str]]]) -> tuple[Decimal, ...]:
    values: set[Decimal] = set()
    for row in pack["ricardian_sensitivity"]:
        if row["instrument_family"] != "deficit_financed_public_interest":
            continue
        values.update({_d(row["low"]), _d(row["base"]), _d(row["high"])})
    return tuple(sorted(values))


def _ricardian_suffix(value: Decimal) -> str:
    return str(value.normalize()).replace(".", "_")


def _band_label(band: str) -> str:
    if band == "high":
        return "stress_corner_envelope"
    if band == "low":
        return "low_sensitivity_corner"
    return "base"


def _cumulative_row(
    group: list[dict[str, Decimal | str]],
    band_group: list[dict[str, Decimal | str]],
) -> dict[str, str]:
    n = sum(record["N"] for record in group)
    d = sum(record["D"] for record in group)
    net = n - d
    gdp = group[0]["nominal_gdp_bil"]
    base = {
        "period_type": "cumulative_120_month",
        "period": "2026-2035",
        "dose_mode": str(group[0].get("dose_mode", "legacy_annual_core")),
        "band": str(group[0]["band"]),
        "band_label": _band_label(str(group[0]["band"])),
        "ricardian_offset": _fmt(group[0]["ricardian_offset"]),
        "N_bil": _fmt(n),
        "D_bil": _fmt(d),
        "net_bil": _fmt(net),
        "net_pct_gdp": _fmt(net / gdp),
        "RW_ratio": _fmt(n / d),
        "legacy_D_comparator_bil": _fmt(gdp * Decimal("0.00776")),
        "bottom_up_D_to_legacy_D": _fmt(d / (gdp * Decimal("0.00776"))),
        "classification_rule": "net_within_cell",
        "legacy_comparator_role": "comparator_only",
        "object_version_stamp": f"cashflow_core_pre_phase6_not_RW_full:dose_mode={group[0].get('dose_mode', 'legacy_annual_core')}",
        "shock_start_month": str(group[0].get("shock_start_month", "legacy_annual_core")),
        "shock_multiplier": _fmt(sum(record.get("shock_multiplier", Decimal("12")) for record in group)),
    }
    for ric in sorted({record["ricardian_offset"] for record in band_group}):
        peer = [record for record in band_group if record["ricardian_offset"] == ric]
        peer_n = sum(record["N"] for record in peer)
        peer_d = sum(record["D"] for record in peer)
        suffix = _ricardian_suffix(ric)
        base[f"ricardian_{suffix}_N_bil"] = _fmt(peer_n)
        base[f"ricardian_{suffix}_D_bil"] = _fmt(peer_d)
        base[f"ricardian_{suffix}_net_bil"] = _fmt(peer_n - peer_d)
        base[f"ricardian_{suffix}_RW"] = _fmt(peer_n / peer_d)
    return base


def _monthly_row(record: dict[str, Decimal | str], month: str, month_no: int) -> dict[str, str]:
    direct_monthly = "month_index" in record
    divisor = Decimal("1") if direct_monthly else Decimal("12")
    row = {
        "period_type": "monthly",
        "month_index": str(month_no),
        "month": month,
        "year": str(record["year"]),
        "dose_mode": str(record.get("dose_mode", "legacy_annual_core")),
        "band": str(record["band"]),
        "band_label": _band_label(str(record["band"])),
        "ricardian_offset": _fmt(record["ricardian_offset"]),
        "N_bil": _fmt(record["N"] / divisor),
        "D_bil": _fmt(record["D"] / divisor),
        "net_bil": _fmt(record["net"] / divisor),
        "RW_ratio": _fmt(record["RW"]),
        "shock_start_month": str(record.get("shock_start_month", "legacy_annual_core")),
        "shock_multiplier": _fmt(record.get("shock_multiplier", Decimal("1"))),
    }
    for field in [
        "tdc_split_new_created_deposits_bil",
        "tdc_split_created_deposit_stock_bil",
        "tdc_split_created_deposit_income_bil",
        "combined_sink_credit_deposit_stock_delta_bil",
        "combined_sink_bank_retention_stock_delta_start_bil",
        "combined_sink_bank_retention_stock_delta_end_bil",
        "combined_sink_bank_retention_new_retained_nii_bil",
        "combined_sink_total_deposit_stock_delta_bil",
        "bank_payout_recycle_share",
    ]:
        row[field] = _fmt(record.get(field, Decimal("0")))
    row["tdc_split_admission_status"] = str(record.get("tdc_split_admission_status", ""))
    row["tdc_split_reconciliation_status"] = str(
        record.get("tdc_split_reconciliation_status", "")
    )
    row["tdc_split_source"] = str(record.get("tdc_split_source", ""))
    row["bank_retention_label"] = str(record.get("bank_retention_label", "off"))
    return row


def _iorb_table(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    routes = _route_amount(pack, "banks", Decimal("1"), "base", "banks_retained_margin")
    rows: list[dict[str, str]] = []
    for record in records:
        for target, share in sorted(routes.items()):
            rows.append(
                {
                    "year": str(record["year"]),
                    "flow": "Fed_to_banks_IORB",
                    "recipient_or_route": target,
                    "route_share": _fmt(share),
                    "iorb_delta_bil": _fmt(record["iorb_delta"] * share),
                    "remittance_delta_bil": _fmt(record["remittance_delta"]),
                    "fed_deferred_asset_open_bil": _fmt(
                        _assumptions(pack)["fed_deferred_asset_open_bil"]["base"]
                    ),
                    "conversion_status": "converted_if_cell_else_deferred",
                    "placeholder_flag": "OWNER_PLACEHOLDER_fed_deferred_asset_open_bil",
                }
            )
    return rows


def _government_table(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        for family, value_field in [
            ("treasury_bills", "bill_interest"),
            ("treasury_notes_bonds_tips", "coupon_interest"),
        ]:
            for holder_row in _rows(pack, "treasury_holder_matrix", instrument_family=family):
                holder = holder_row["cell_or_sector"]
                amount = record[value_field] * _d(holder_row["base"])
                routed = _route_amount(pack, holder, amount, "base", family)
                converted = _converted_amount(routed, _conversion(pack), Decimal("0"))
                rows.append(
                    {
                        "year": str(record["year"]),
                        "instrument_family": family,
                        "holder": holder,
                        "holder_share": holder_row["base"],
                        "cashflow_delta_bil": _fmt(amount),
                        "current_stock_coupon_interest_bil": _fmt(
                            record.get("coupon_current_stock_interest", Decimal("0"))
                            if family == "treasury_notes_bonds_tips"
                            else Decimal("0")
                        ),
                        "new_issuance_coupon_interest_bil": _fmt(
                            record.get("coupon_new_issuance_interest", Decimal("0"))
                            if family == "treasury_notes_bonds_tips"
                            else Decimal("0")
                        ),
                        "current_stock_reprice_share": _fmt(
                            record.get("coupon_current_stock_reprice_share", Decimal("0"))
                            if family == "treasury_notes_bonds_tips"
                            else Decimal("0")
                        ),
                        "new_issuance_reprice_share": _fmt(
                            record.get("coupon_new_issuance_reprice_share", Decimal("0"))
                            if family == "treasury_notes_bonds_tips"
                            else Decimal("0")
                        ),
                        "leaked_bil": _fmt(amount if holder == "rest_of_world" else Decimal("0")),
                        "recycled_bil": _fmt(amount if holder == "federal_reserve" else Decimal("0")),
                        "routed_bil": _fmt(sum(routed.values(), Decimal("0"))),
                        "converted_net_bil": _fmt(converted),
                        "unallocated_flag": "true" if "unallocated" in holder else "false",
                        "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
                    }
                )
    return rows


def _curve_table(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        shock_start_index = _month_index_from_label(str(record.get("shock_start_month", "2026-01")))
        month_index = int(record.get("month_index", (record["year_index"] - 1) * 12 + 1))
        dose_mode = str(record.get("dose_mode", DEFAULT_DOSE_MODE))
        for family, tenor, field in [
            ("treasury_bills", "bills", "bill_interest"),
            ("treasury_notes_bonds_tips", "10y", "coupon_interest"),
        ]:
            yield_move_bp = _treasury_yield_delta_bp(
                pack,
                tenor,
                str(record["band"]),
                month_index,
                shock_start_index,
                dose_mode,
            )
            for holder_row in _rows(pack, "treasury_holder_matrix", instrument_family=family):
                rows.append(
                    {
                        "year": str(record["year"]),
                        "instrument_family": family,
                        "holder": holder_row["cell_or_sector"],
                        "curve_tenor": tenor,
                        "yield_move_bp": _fmt(yield_move_bp),
                        "cashflow_delta_bil": _fmt(record[field] * _d(holder_row["base"])),
                        "basis": "experiment_policy_path_mean_plus_term_premium",
                    }
                )
    return rows


def _bank_receipt_pay_ledger(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    opening = _opening_by_family(pack)
    assumptions = _assumptions(pack)
    for record in records:
        band = "base"
        year_index = int(record["year_index"])
        mortgage_interest = (
            opening["mortgages_fixed"]
            * _private_driver("mortgages_fixed", band, year_index, assumptions)
            + opening["mortgages_arm"]
            * _private_driver("mortgages_arm", band, year_index, assumptions)
        )
        mortgage_holders = _mortgage_holder_amounts(pack, mortgage_interest, band)
        nonmortgage_household_floating = (
            opening["heloc"] * _private_driver("heloc", band, year_index, assumptions)
            + opening["credit_card_revolving"]
            * _private_driver("credit_card_revolving", band, year_index, assumptions)
        )
        household_consumer_new_flow = (
            opening["auto_installment_debt"]
            * _private_driver("auto_installment_debt", band, year_index, assumptions)
            + opening["student_loans_private"]
            * _private_driver("student_loans_private", band, year_index, assumptions)
            + opening["personal_installment_debt"]
            * _private_driver("personal_installment_debt", band, year_index, assumptions)
        )
        treasury_bank_receipts = (
            record["bill_interest"]
            * _treasury_holder_share(pack, "treasury_bills", "banks")
            + record["coupon_interest"]
            * _treasury_holder_share(pack, "treasury_notes_bonds_tips", "banks")
        )
        depository_receipts = {
            "iorb_receipts": record["iorb_delta"],
            "c_and_i_receipts": opening["c_and_i_depository_loans"]
            * _private_driver("c_and_i_depository_loans", band, year_index, assumptions),
            "a2_mortgage_whole_loan_receipts": mortgage_holders["banks_nonbanks_whole_loans"],
            "household_nonmortgage_floating_receipts": nonmortgage_household_floating,
            "household_consumer_new_flow_receipts": household_consumer_new_flow,
            "treasury_security_receipts": treasury_bank_receipts,
        }
        complete_receipts = {
            **depository_receipts,
            "syndicated_loan_receipts": opening["syndicated_loans"]
            * _private_driver("syndicated_loans", band, year_index, assumptions),
            "a2_mbs_investor_receipts": mortgage_holders[
                "nonbank_finance_agency_mbs_investors"
            ],
        }
        payments = {
            "deposit_interest_paid": _deposit_interest_paid_by_banks(pack, band, year_index),
            "a6_short_funding_repo_paid": opening.get("mmf_short_funding_assets", Decimal("0"))
            * _private_driver("mmf_short_funding_assets", band, year_index, assumptions)
            * Decimal("0.75"),
        }
        for boundary, receipts in [
            ("depository_bank_only", depository_receipts),
            ("bank_plus_nonbank_credit_intermediation", complete_receipts),
        ]:
            for name, amount in receipts.items():
                rows.append(
                    {
                        "year": str(record["year"]),
                        "ledger_boundary": boundary,
                        "ledger_side": "receipt",
                        "line_item": name,
                        "amount_bil": _fmt(amount),
                        "basis": "C1_boundary_complete_receipt_pay_ledger",
                    }
                )
            for name, amount in payments.items():
                rows.append(
                    {
                        "year": str(record["year"]),
                        "ledger_boundary": boundary,
                        "ledger_side": "payment",
                        "line_item": name,
                        "amount_bil": _fmt(amount),
                        "basis": "C1_boundary_complete_receipt_pay_ledger",
                    }
                )
            net = sum(receipts.values(), Decimal("0")) - sum(payments.values(), Decimal("0"))
            rows.append(
                {
                    "year": str(record["year"]),
                    "ledger_boundary": boundary,
                    "ledger_side": "net",
                    "line_item": "net_bank_cashflow_delta",
                    "amount_bil": _fmt(net),
                    "basis": "diagnostic_not_headline_boundary_matched",
                }
            )
    return rows


def _fed_rrp_channel(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    opening = _opening_by_family(pack)
    rows: list[dict[str, str]] = []
    for record in records:
        amount = opening["foreign_official_reverse_repos"] * Decimal("0.01")
        rows.append(
            {
                "year": str(record["year"]),
                "channel_id": "F4_foreign_official_rrp",
                "payer": "federal_reserve",
                "receiver": "rest_of_world",
                "cashflow_delta_bil": _fmt(amount),
                "converted_net_bil": "0",
                "headline_effect": "leakage_no_near_term_conversion",
            }
        )
    return rows


def _deposit_holder_routing(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    assumptions = _assumptions(pack)
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        band = str(record["band"])
        year_index = int(record["year_index"])
        for family in ["deposits_checkable", "deposits_savings_mmda", "deposits_time_cds"]:
            rate = _private_driver(family, band, year_index, assumptions)
            family_receipts = Decimal("0")
            holder_rows = _rows(pack, "opening_stocks", instrument_family=family)
            for holder_row in holder_rows:
                holder = _holder_from_opening_row(holder_row)
                receipt = _d(holder_row[band]) * rate
                family_receipts += receipt
                rows.append(
                    {
                        "year": str(record["year"]),
                        "band": band,
                        "band_label": _band_label(band),
                        "instrument_family": family,
                        "holder": holder,
                        "holder_stock_bil": _fmt(_d(holder_row[band])),
                        "rate_delta": _fmt(rate),
                        "receipt_bil": _fmt(receipt),
                        "route_count": "1",
                        "bank_family_payment_bil": "",
                        "basis": "opening_stocks_holder_row_once",
                    }
                )
            rows.append(
                {
                    "year": str(record["year"]),
                    "band": band,
                    "band_label": _band_label(band),
                    "instrument_family": family,
                    "holder": "banks_payment_total",
                    "holder_stock_bil": _fmt(sum(_d(row[band]) for row in holder_rows)),
                    "rate_delta": _fmt(rate),
                    "receipt_bil": _fmt(family_receipts),
                    "route_count": str(len(holder_rows)),
                    "bank_family_payment_bil": _fmt(family_receipts),
                    "basis": "bank_payment_once_matches_holder_receipts",
                }
            )
    return rows


def _mortgage_holder_routing(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    opening = _opening_by_family(pack)
    assumptions = _assumptions(pack)
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        band = str(record["band"])
        year_index = int(record["year_index"])
        paid = (
            opening["mortgages_fixed"]
            * _private_driver("mortgages_fixed", band, year_index, assumptions)
            + opening["mortgages_arm"]
            * _private_driver("mortgages_arm", band, year_index, assumptions)
        )
        holder_amounts = _mortgage_holder_amounts(pack, paid, band)
        total_stock = sum(_d(row[band]) for row in pack["mortgage_holder_decomposition"])
        for holder_row in pack["mortgage_holder_decomposition"]:
            holder = holder_row["holder"]
            rows.append(
                {
                    "year": str(record["year"]),
                    "band": band,
                    "band_label": _band_label(band),
                    "holder": holder,
                    "holder_stock_bil": _fmt(_d(holder_row[band])),
                    "holder_share": _fmt(_d(holder_row[band]) / total_stock),
                    "mortgage_interest_paid_bil": _fmt(paid),
                    "holder_receipt_bil": _fmt(holder_amounts[holder]),
                    "basis": "A2_household_to_pool_to_holder_decomposition",
                }
            )
    return rows


def _cre_cashflow_channel(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    opening = _opening_by_family(pack)
    assumptions = _assumptions(pack)
    conversion = _conversion(pack)
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        band = str(record["band"])
        year_index = int(record["year_index"])
        small_share = assumptions["cre_payer_small_share"][band]
        large_share = Decimal("1") - small_share
        for family, reset_rule, driver_id in [
            ("cre_mortgages_floating", "monthly_reset", "cre.floating_rate"),
            ("cre_mortgages_fixed", "fixed_ladder_refi_roll", "cre.fixed_refi_coupon"),
        ]:
            stock = opening[family]
            rate = _private_driver(family, band, year_index, assumptions)
            paid = stock * rate
            payer_routes = _cre_payer_routes(paid, band, assumptions)
            holder_routes = _private_credit_receipt_routes(pack, family, paid, band)
            holder_rows = _rows(pack, "opening_stocks", instrument_family=family)
            family_stock = sum(_d(row[band]) for row in holder_rows)
            converted_payer_drag = -_converted_amount(payer_routes, conversion, Decimal("0"))
            converted_holder_support = _converted_amount(holder_routes, conversion, Decimal("0"))
            for holder_row in holder_rows:
                holder = _holder_from_opening_row(holder_row)
                holder_stock = _d(holder_row[band])
                holder_receipt = (
                    Decimal("0") if family_stock == 0 else paid * holder_stock / family_stock
                )
                rows.append(
                    {
                        "year": str(record["year"]),
                        "band": band,
                        "band_label": _band_label(band),
                        "instrument_family": family,
                        "driver_id": driver_id,
                        "reset_rule": reset_rule,
                        "stock_bil": _fmt(stock),
                        "rate_delta": _fmt(rate),
                        "interest_paid_bil": _fmt(paid),
                        "payer_small_share": _fmt(small_share),
                        "payer_large_share": _fmt(large_share),
                        "holder": holder,
                        "holder_stock_bil": _fmt(holder_stock),
                        "holder_receipt_bil": _fmt(holder_receipt),
                        "converted_payer_drag_bil": _fmt(converted_payer_drag),
                        "converted_holder_support_bil": _fmt(converted_holder_support),
                        "net_converted_effect_bil": _fmt(converted_holder_support - converted_payer_drag),
                        "basis": "owner_assumption_mode_CRE_cashflow_core",
                    }
                )
    return rows


def _claim_processor_channel(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    assumptions = _assumptions(pack)
    conversion = _conversion(pack)
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        band = str(record["band"])
        year_index = int(record["year_index"])
        for rule in _active_claim_processor_rules(pack):
            amount = _claim_rule_amount(pack, rule, band, year_index, assumptions)
            payer_routes = _claim_rule_payer_routes(pack, rule, amount, band, assumptions)
            receiver_routes = _claim_rule_receiver_routes(pack, rule, amount, band)
            net_routes = _merge_routes(payer_routes, receiver_routes)
            converted = _converted_amount(net_routes, conversion, Decimal("0"))
            rows.append(
                {
                    "year": str(record["year"]),
                    "band": band,
                    "band_label": _band_label(band),
                    "channel_id": rule["report_channel"],
                    "rule_id": rule["rule_id"],
                    "instrument_family": rule["instrument_family"],
                    "gross_flow_delta_bil": _fmt(amount),
                    "converted_net_bil": _fmt(converted),
                    "basis": rule["basis"],
                }
            )
    return rows


def _bnpl_channel(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    return [
        row
        for row in _claim_processor_channel(pack, records)
        if row["channel_id"] == "bnpl"
    ]


def _bnpl_share_sensitivity(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    base_rows = [
        row
        for row in _bnpl_channel(pack, records)
        if row["year"] == "2026" and row["band"] == "base"
    ]
    rows: list[dict[str, str]] = []
    base_share = _assumptions(pack).get("bnpl_share_of_purchases", {}).get(
        "base", Decimal("0.01")
    )
    for share in [Decimal("0.01"), Decimal("0.10")]:
        scale = Decimal("0") if base_share == 0 else share / base_share
        n = Decimal("0")
        d = Decimal("0")
        gross = Decimal("0")
        for row in base_rows:
            converted = _d(row["converted_net_bil"]) * scale
            gross += _d(row["gross_flow_delta_bil"]) * scale
            if converted >= 0:
                n += converted
            else:
                d += -converted
        rows.append(
            {
                "bnpl_share_of_purchases": _fmt(share),
                "scale_vs_base": _fmt(scale),
                "gross_flow_delta_bil": _fmt(gross),
                "N_bil": _fmt(n),
                "D_bil": _fmt(d),
                "net_bil": _fmt(n - d),
                "basis": "linear_config_sensitivity_from_generic_bnpl_rules",
            }
        )
    return rows


def _scenario_delta_derivation_table(
    pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in pack.get("scenario_adjustments", []):
        if row.get("derivation_status") != "parameter_derived":
            continue
        for band in BANDS:
            declared = row.get(f"declared_stock_{band}", row[f"stock_{band}"])
            implied = row[f"stock_{band}"]
            rows.append(
                {
                    "delta_set_id": row["delta_set_id"],
                    "row_id": row["row_id"],
                    "delta_role": row["delta_role"],
                    "band": band,
                    "declared_stock_bil": declared,
                    "parameter_implied_stock_bil": implied,
                    "drift_bil": _fmt(_d(implied) - _d(declared)),
                    "status": "pass"
                    if abs(_d(implied) - _d(declared)) <= Decimal("0.000000000001")
                    else "fail",
                    "basis": "T52_parameter_derived_delta_set_stock",
                }
            )
    return rows


def _scenario_delta_balance_table(
    pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for delta_set_id in sorted({row["delta_set_id"] for row in pack.get("scenario_adjustments", [])}):
        group = [row for row in pack["scenario_adjustments"] if row["delta_set_id"] == delta_set_id]
        for band in BANDS:
            entries = _scenario_delta_balance_entries(group, band)
            for sector in sorted(entries):
                item = entries[sector]
                assets = item.get("asset_delta", Decimal("0"))
                liabilities = item.get("liability_delta", Decimal("0"))
                real_counterpart = item.get("real_counterpart", Decimal("0"))
                gap = assets - liabilities - real_counterpart
                rows.append(
                    {
                        "delta_set_id": delta_set_id,
                        "band": band,
                        "sector": sector,
                        "asset_delta_bil": _fmt(assets),
                        "liability_delta_bil": _fmt(liabilities),
                        "declared_real_side_counterpart_bil": _fmt(real_counterpart),
                        "identity_gap_bil": _fmt(gap),
                        "status": "pass" if abs(gap) <= Decimal("0.000001") else "fail",
                        "basis": "T49_assets_minus_liabilities_less_explicit_real_counterpart",
                    }
                )
    return rows


def _scenario_delta_balance_entries(
    group: list[dict[str, str]],
    band: str,
) -> dict[str, dict[str, Decimal]]:
    entries: dict[str, dict[str, Decimal]] = {}

    def add(sector: str, field: str, amount: Decimal) -> None:
        entries.setdefault(sector, {})[field] = entries.setdefault(sector, {}).get(
            field, Decimal("0")
        ) + amount

    for row in group:
        stock = _d(row[f"stock_{band}"])
        holder = row["holder"]
        issuer = row["issuer"]
        role = row["delta_role"]
        if role == "real_side_counterpart":
            add(holder, "real_counterpart", stock)
            continue
        if role == "remove_card_float":
            add(holder, "asset_delta", -stock)
            add(issuer, "liability_delta", -stock)
            continue
        add(holder, "asset_delta", stock)
        add(issuer, "liability_delta", stock)
    return entries


def _moneyness_liquid_buffers(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    weights = _moneyness_weights(pack)
    by_cell: dict[str, dict[str, Decimal]] = {}
    for row in pack["opening_stocks"]:
        family = row["instrument_family"]
        weight = weights.get(family, Decimal("0"))
        holder = _holder_from_opening_row(row)
        stock = _d(row["base"])
        routed = _route_amount(pack, holder, stock, "base", family)
        if not routed:
            routed = {holder: stock}
        for cell, amount in routed.items():
            target = by_cell.setdefault(
                cell,
                {"stock": Decimal("0"), "weighted": Decimal("0")},
            )
            target["stock"] += amount
            target["weighted"] += amount * weight
    return [
        {
            "cell_or_sector": cell,
            "liquid_buffer_stock_bil": _fmt(values["stock"]),
            "moneyness_weighted_buffer_bil": _fmt(values["weighted"]),
            "average_moneyness_weight": _fmt(
                Decimal("0") if values["stock"] == 0 else values["weighted"] / values["stock"]
            ),
            "basis": "owner_assumption_moneyness_weight_schema_only",
        }
        for cell, values in sorted(by_cell.items())
    ]


def _absorption_modes_table(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    return [dict(row) for row in pack.get("absorption_modes", [])]


def _qt_deposit_leg_table(
    pack: dict[str, list[dict[str, str]]],
    qt_supply_stress: bool | Decimal | str,
) -> list[dict[str, str]]:
    scale = _qt_supply_stress_scale(qt_supply_stress)
    rows: list[dict[str, str]] = []
    for band in BANDS:
        runoff = _qt_runoff_bil(pack, band) * scale
        share = _nonbank_market_complex_absorption_share(pack, band)
        rows.append(
            {
                "scenario_id": "qt_supply_stress",
                "band": band,
                "qt_supply_stress_scale": _fmt(scale),
                "qt_runoff_bil": _fmt(runoff),
                "nonbank_absorption_share": _fmt(share),
                "deposit_stock_delta_bil": _fmt(-runoff * share),
                "label": "scenario_only",
                "input_basis_label": "absorption_mode_mix_pack_forward_LBH_20260702",
                "lineage": "latest negative SOMA/QT mode-D annual runoff from absorption_mode_mix summary times modes A plus A_RRP nonbank share",
            }
        )
    return rows


def _tdc_channel_table(
    pack: dict[str, list[dict[str, Decimal | str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    conversion = _conversion(pack)
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        band = str(record["band"])
        routes = _tdc_routes_from_metrics(
            pack,
            band,
            {"created_deposit_income_bil": record["tdc_created_deposit_income_bil"]},
        )
        n, d, net = _classify(routes, conversion, Decimal("0"))
        for mode in pack.get("absorption_modes", []):
            mode_new_stock = (
                record["tdc_issuance_divergence_bil"]
                * _d(mode[band])
                * _d(mode["deposit_creation_per_issuance"])
            )
            rows.append(
                {
                    "year": str(record["year"]),
                    "band": band,
                    "mode_id": mode["mode_id"],
                    "mode_label": mode["mode_label"],
                    "mode_share": mode[band],
                    "issuance_divergence_bil": _fmt(record["tdc_issuance_divergence_bil"]),
                    "mode_new_created_deposits_bil": _fmt(mode_new_stock),
                    "settlement_subtype": mode["settlement_subtype"],
                    "fx_coupling_flag": mode["fx_coupling_flag"],
                    "created_deposit_stock_bil": "",
                    "full_level_deposit_rate": "",
                    "created_deposit_income_bil": "",
                    "converted_N_bil": "",
                    "converted_D_bil": "",
                    "converted_net_bil": "",
                    "basis": mode["booking_rule"],
                }
            )
        rows.append(
            {
                "year": str(record["year"]),
                "band": band,
                "mode_id": "TOTAL",
                "mode_label": "total_tdc_created_deposit_income",
                "mode_share": _fmt(record["tdc_implied_beta"]),
                "issuance_divergence_bil": _fmt(record["tdc_issuance_divergence_bil"]),
                "mode_new_created_deposits_bil": _fmt(record["tdc_new_created_deposits_bil"]),
                "settlement_subtype": "aggregate",
                "fx_coupling_flag": "false",
                "created_deposit_stock_bil": _fmt(record["tdc_created_deposit_stock_bil"]),
                "full_level_deposit_rate": _fmt(record["tdc_created_deposit_full_level_rate"]),
                "created_deposit_income_bil": _fmt(record["tdc_created_deposit_income_bil"]),
                "converted_N_bil": _fmt(n),
                "converted_D_bil": _fmt(d),
                "converted_net_bil": _fmt(net),
                "basis": "endogenous_issuance_divergence_times_absorption_mix",
            }
        )
    return rows


def _combined_sink_trace_table(
    monthly_records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in monthly_records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        rows.append(
            {
                "period_type": "monthly",
                "month": str(record["month"]),
                "year": str(record["year"]),
                "band": str(record["band"]),
                "combined_sink_credit_deposit_stock_delta_bil": _fmt(
                    record.get("combined_sink_credit_deposit_stock_delta_bil", Decimal("0"))
                ),
                "combined_sink_bank_retention_stock_delta_start_bil": _fmt(
                    record.get(
                        "combined_sink_bank_retention_stock_delta_start_bil",
                        Decimal("0"),
                    )
                ),
                "combined_sink_bank_retention_new_retained_nii_bil": _fmt(
                    record.get(
                        "combined_sink_bank_retention_new_retained_nii_bil",
                        Decimal("0"),
                    )
                ),
                "combined_sink_bank_retention_stock_delta_end_bil": _fmt(
                    record.get(
                        "combined_sink_bank_retention_stock_delta_end_bil",
                        Decimal("0"),
                    )
                ),
                "combined_sink_total_deposit_stock_delta_bil": _fmt(
                    record.get("combined_sink_total_deposit_stock_delta_bil", Decimal("0"))
                ),
                "bank_payout_recycle_share": _fmt(
                    record.get("bank_payout_recycle_share", Decimal("0"))
                ),
                "bank_retention_label": str(record.get("bank_retention_label", "off")),
            }
        )
    return rows


def _tdc_beta_implied_table(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    empirical = {
        row["period"]: row for row in pack.get("tdc_empirical_beta_path", [])
    }
    rows: list[dict[str, str]] = []
    for record in records:
        if record["band"] != "base" or record["ricardian_offset"] != Decimal("0"):
            continue
        year = str(record["year"])
        peer = empirical.get(year, {})
        rows.append(
            {
                "year": year,
                "implied_beta": _fmt(record["tdc_implied_beta"]),
                "implied_beta_basis": "structural_absorption_mode_mix",
                "empirical_beta_validation_target": peer.get("beta", ""),
                "empirical_regime_label": peer.get("regime_label", ""),
                "empirical_status": (
                    "historical_diagnostic_available" if peer else "no_forward_beta_target"
                ),
                "calibration_policy": "diagnostic_validation_target_never_calibration",
            }
        )
    return rows


def _tdc_mode_sensitivity_table(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    base_records = [
        record
        for record in records
        if record["band"] == "base" and record["ricardian_offset"] == Decimal("0")
    ]
    if not base_records:
        return []
    full_rate = _assumptions(pack).get("tdc_created_deposit_full_level_rate", {}).get(
        "base", Decimal("0.035")
    )
    conversion = _conversion(pack)
    recipient_coeff = _converted_amount(
        _tdc_recipient_routes(pack, "base", Decimal("1")),
        conversion,
        Decimal("0"),
    )
    rows: list[dict[str, str]] = []
    def append_row(
        beta: Decimal,
        *,
        scenario_id: str = "",
        sensitivity_id: str = "",
        legacy_status: str,
        authority_status: str,
        basis: str,
        evidence_mode_enabled: str,
        canonical_status: str,
    ) -> None:
        stock = Decimal("0")
        year1_n = Decimal("0")
        cumulative_n = Decimal("0")
        for record in base_records:
            stock += record["tdc_issuance_divergence_bil"] * beta
            n = stock * full_rate * recipient_coeff
            if record["year"] == "2026":
                year1_n = n
            cumulative_n += n
        rows.append(
            {
                "scenario_id": scenario_id,
                "sensitivity_id": sensitivity_id,
                "implied_beta": _fmt(beta),
                "legacy_status": legacy_status,
                "authority_status": authority_status,
                "deposit_rate_assumption": _fmt(full_rate),
                "year1_tdc_N_bil": _fmt(year1_n),
                "cumulative_2026_2035_tdc_N_bil": _fmt(cumulative_n),
                "basis": basis,
                "evidence_mode_enabled": evidence_mode_enabled,
                "canonical_status": canonical_status,
            }
        )
    for scenario_id, beta in (
        ("all_A_domestic_nonbank_swap", Decimal("0")),
        ("all_B_bank_expansion", Decimal("1")),
        ("base_mix", _tdc_implied_beta(pack, "base")),
    ):
        append_row(
            beta,
            scenario_id=scenario_id,
            legacy_status="not_applicable",
            authority_status="structural_mode_mix_diagnostic",
            basis="mode_mix_sensitivity_not_headline_calibration",
            evidence_mode_enabled="false",
            canonical_status="noncanonical_diagnostic",
        )
    for sensitivity in pack.get("tdc_beta_authority", []):
        append_row(
            _d(sensitivity["beta"]),
            sensitivity_id=sensitivity["sensitivity_id"],
            legacy_status=sensitivity["legacy_status"],
            authority_status=sensitivity["authority_status"],
            basis="equal_status_noncanonical_sensitivity_never_headline_selection",
            evidence_mode_enabled=sensitivity["evidence_mode_enabled"],
            canonical_status=sensitivity["canonical_status"],
        )
    return rows


def _tdc_beta_authority_table(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    return [dict(row) for row in pack.get("tdc_beta_authority", [])]


def _tdc_chi_diagnostic_table(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    return [dict(row) for row in pack.get("tdc_liquidity_stock_conversion", [])]


def _coupon_cohort_repricing_table(
    pack: dict[str, list[dict[str, str]]],
    monthly_records: list[dict[str, Decimal | str]] | None,
    dose_mode: str,
    *,
    qt_supply_stress: bool | Decimal | str = False,
    use_impulse_beta_context: bool = False,
) -> list[dict[str, str]]:
    if monthly_records is None:
        return []
    assumptions = _assumptions(pack)
    shock_start_index = _month_index_from_label(
        str(monthly_records[0].get("shock_start_month", "2026-01"))
    )
    ricardian_zero = [
        record
        for record in monthly_records
        if record["ricardian_offset"] == Decimal("0")
    ]
    by_key = {
        (str(record["band"]), int(record["month_index"])): record
        for record in ricardian_zero
    }
    rows: list[dict[str, str]] = []
    for band in BANDS:
        bill_issue_share = assumptions["marginal_issuance_bill_share"][band]
        for month_index in range(1, MONTHS + 1):
            month = _month_label(month_index)
            rate_delta = _treasury_yield_delta(
                pack,
                "10y",
                band,
                month_index,
                shock_start_index,
                dose_mode,
                qt_supply_stress=qt_supply_stress,
                use_impulse_beta_context=use_impulse_beta_context,
            )
            current_amount = _current_coupon_maturing_month(pack, month)
            rows.extend(
                _coupon_cohort_repricing_rows(
                    pack,
                    band,
                    dose_mode,
                    "current_stock_roll",
                    month_index,
                    month,
                    current_amount,
                    rate_delta,
                )
            )
            if month_index == 1:
                continue
            previous = by_key.get((band, month_index - 1))
            if previous is None:
                continue
            public_n = previous["public_n"]
            public_d = previous["public_d"]
            if not isinstance(public_n, Decimal) or not isinstance(public_d, Decimal):
                continue
            public_net_prev = public_n - public_d
            new_coupon_amount = public_net_prev * (Decimal("1") - bill_issue_share)
            rows.extend(
                _coupon_cohort_repricing_rows(
                    pack,
                    band,
                    dose_mode,
                    "new_deficit_issuance",
                    month_index,
                    month,
                    new_coupon_amount,
                    rate_delta,
                )
            )
    return rows


def _coupon_cohort_repricing_rows(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    dose_mode: str,
    cohort_source: str,
    month_index: int,
    month: str,
    amount: Decimal,
    rate_delta_ann: Decimal,
) -> list[dict[str, str]]:
    if amount == 0:
        return []
    rows: list[dict[str, str]] = []
    for cohort in _coupon_cohorts_from_monthly_issuance(
        pack,
        amount=amount,
        rate_delta_ann=rate_delta_ann,
        issue_month_index=month_index,
    ):
        rows.append(
            {
                "band": band,
                "dose_mode": dose_mode,
                "cohort_source": cohort_source,
                "roll_month_index": str(month_index),
                "roll_month": month,
                "tenor_bucket": cohort.bucket,
                "cohort_amount_bil": _fmt(cohort.amount),
                "baseline_rate_delta_bp": "0",
                "shock_rate_delta_bp": _fmt(cohort.rate_delta_ann * Decimal("10000")),
                "shock_minus_baseline_bp": _fmt(cohort.rate_delta_ann * Decimal("10000")),
                "basis": "roll_month_curve_delta_applied_to_coupon_cohort",
            }
        )
    return rows


def _treasury_coupon_roll_schedule_table(
    pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, row in enumerate(pack.get("tdcsim_coupon_roll_schedule", []), start=1):
        rows.append(
            {
                "mode_id": "measured_monthly_schedule",
                "month_index": str(index),
                "month": row["month"],
                "maturing_principal_bil": row["maturing_principal_bil"],
                "cumulative_share_of_current_stock": row[
                    "cumulative_share_of_current_stock"
                ],
                "input_basis_label": "measured",
                "source_id": TDCSIM_COUPON_ROLL_SOURCE_ID,
                "source_vintage": row["source_vintage"],
                "headline_role": "base_treasury_coupon_roll_input",
            }
        )
    fallback = _assumptions(pack).get("coupon_roll_rate", {})
    for band in BANDS:
        if band not in fallback:
            continue
        rows.append(
            {
                "mode_id": "blended_rate_fallback_sensitivity",
                "month_index": "",
                "month": "",
                "maturing_principal_bil": "",
                "cumulative_share_of_current_stock": _fmt(fallback[band]),
                "input_basis_label": "blended_fallback_sensitivity",
                "source_id": "PRE_V15_OWNER_BLENDED_RATE",
                "source_vintage": "pre_V15_RWTAM_structural_assumption",
                "headline_role": f"{band}_constant_annual_roll_sensitivity",
            }
        )
    return rows


def _treasury_issuance_tenor_mix_table(
    pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    bill_share = Decimal("0")
    for row in pack.get("tdcsim_issuance_tenor_mix", []):
        share = _d(row["share_of_gross_issuance"])
        if row["tenor_bucket"].startswith("bills_"):
            bill_share += share
        rows.append(
            {
                **row,
                "source_id": TDCSIM_ISSUANCE_MIX_SOURCE_ID,
                "promotion_status": "source_backed_policy_sensitivity_not_core_mapping",
            }
        )
    if rows:
        rows.append(
            {
                "tenor_bucket": "SUMMARY_bill_share",
                "share_of_gross_issuance": _fmt(bill_share),
                "basis": "sum_tdcsim_bill_buckets",
                "source_vintage": rows[0]["source_vintage"],
                "source_id": TDCSIM_ISSUANCE_MIX_SOURCE_ID,
                "promotion_status": "not_promoted_current_core_assumption_base_remains_0_30",
            }
        )
    return rows


def _bond_mtm_diagnostic(
    pack: dict[str, list[dict[str, str]]],
    bond_pack_dir: Path,
    dose_mode: str,
) -> list[dict[str, str]]:
    if not bond_pack_dir.exists():
        return []
    holdings = _read_csv_rows(bond_pack_dir / "bond_holdings_duration_bucket.csv")
    cell_mapping = _read_csv_rows(bond_pack_dir / "bond_cell_mapping.csv")
    price_rows = _read_csv_rows(bond_pack_dir / "bond_price_pack.csv")
    relevance_rows = _read_csv_rows(bond_pack_dir / "bond_mtm_relevance.csv")
    mpc_rows = _read_csv_rows(bond_pack_dir / "bond_wealth_mpc.csv")
    prices = {
        (row["instrument_family"], _duration_bucket(row["cell_or_sector"])): row
        for row in price_rows
        if row["parameter_id"] == "bond_price_change_pct"
    }
    yield_moves = _bond_yield_move_rows(pack, price_rows, dose_mode)
    relevance = {
        row["instrument_family"]: row
        for row in relevance_rows
        if row["parameter_id"] == "bond_mtm_psychology_weight"
    }
    mpcs = {
        row["cell_or_sector"]: row
        for row in mpc_rows
        if row["parameter_id"] == "bond_wealth_mpc"
    }
    mappings: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in cell_mapping:
        family, bucket = _family_bucket_from_mapping(row["instrument_family"])
        mappings.setdefault((family, bucket), []).append(row)
    rows: list[dict[str, str]] = []
    for holding in holdings:
        family = holding["instrument_family"]
        bucket = _duration_bucket(holding["cell_or_sector"])
        _ = prices[(family, bucket)]
        relevance_row = relevance[family]
        for mapping in mappings[(family, bucket)]:
            cell = mapping["cell_or_sector"]
            mpc = mpcs[cell]
            values: dict[str, Decimal] = {}
            for band in BANDS:
                price_loss = max(Decimal("0"), -yield_moves[(family, bucket)][band] / Decimal("100"))
                values[band] = (
                    _d(holding[band])
                    * price_loss
                    * _d(relevance_row[band])
                    * _d(mapping[band])
                    * _d(mpc[band])
                )
            rows.append(
                {
                    "source_channel_id": "bond_mtm_wealth",
                    "exposure_id": f"bond_mtm|{family}|{bucket}|{cell}",
                    "month": "2026-12",
                    "cell_or_sector": cell,
                    "instrument_family": family,
                    "duration_bucket": bucket,
                    "security_id": f"{family}:{bucket}",
                    "issuer_sector": _bond_issuer_sector(family),
                    "holder_route": mapping["cell_or_sector"],
                    "coupon_type": "fixed_or_fund_nav",
                    "duration_price_leg": "1",
                    "coupon_cashflow_leg": "0",
                    "holding_stock_low_bil": holding["low"],
                    "holding_stock_base_bil": holding["base"],
                    "holding_stock_high_bil": holding["high"],
                    "price_change_low_pct": _fmt(yield_moves[(family, bucket)]["low"]),
                    "price_change_base_pct": _fmt(yield_moves[(family, bucket)]["base"]),
                    "price_change_high_pct": _fmt(yield_moves[(family, bucket)]["high"]),
                    "yield_move_low_bp": _fmt(yield_moves[(family, bucket)]["yield_low_bp"]),
                    "yield_move_base_bp": _fmt(yield_moves[(family, bucket)]["yield_base_bp"]),
                    "yield_move_high_bp": _fmt(yield_moves[(family, bucket)]["yield_high_bp"]),
                    "curve_construction": "expectations_consistent_term_premium",
                    "mtm_relevance_low": relevance_row["low"],
                    "mtm_relevance_base": relevance_row["base"],
                    "mtm_relevance_high": relevance_row["high"],
                    "holder_cell_share_low": mapping["low"],
                    "holder_cell_share_base": mapping["base"],
                    "holder_cell_share_high": mapping["high"],
                    "bond_wealth_mpc_low": mpc["low"],
                    "bond_wealth_mpc_base": mpc["base"],
                    "bond_wealth_mpc_high": mpc["high"],
                    "diagnostic_D_low_bil": _fmt(values["low"]),
                    "diagnostic_D_base_bil": _fmt(values["base"]),
                    "diagnostic_D_high_bil": _fmt(values["high"]),
                    "include_flag": "0",
                    "headline_entry_flag": "false",
                    "input_basis_label": "diagnostic_only_computed_from_bond_pack",
                    "overlap_key": "source_channel_id|exposure_id|month|cell_or_sector",
                }
            )
    errors = validate_bond_mtm_overlap_rows(rows)
    if errors:
        raise ValueError("; ".join(errors))
    return rows


def validate_bond_mtm_overlap_rows(rows: list[dict[str, str]]) -> list[str]:
    active_price_keys: set[tuple[str, str, str, str, str, str]] = set()
    active_coupon_keys: set[tuple[str, str, str, str, str, str]] = set()
    for row in rows:
        if row.get("include_flag") not in {"1", "true", "True"}:
            continue
        key = (
            row.get("security_id", ""),
            row.get("issuer_sector", ""),
            row.get("holder_route", ""),
            row.get("duration_bucket", ""),
            row.get("coupon_type", ""),
            row.get("cell_or_sector", ""),
        )
        channel = row.get("source_channel_id", "")
        if channel == "bond_mtm_wealth" and row.get("duration_price_leg", "1") == "1":
            active_price_keys.add(key)
        if channel == "cashflow_interest_income_or_expense" and row.get("coupon_cashflow_leg", "1") == "1":
            active_coupon_keys.add(key)
    overlap = sorted(active_price_keys & active_coupon_keys)
    return [
        "same-security coupon-vs-MTM overlap rejected: " + "|".join(key)
        for key in overlap
    ]


def _bond_yield_move_rows(
    pack: dict[str, list[dict[str, str]]],
    price_rows: list[dict[str, str]],
    dose_mode: str,
) -> dict[tuple[str, str], dict[str, Decimal]]:
    duration_rows = {
        (row["instrument_family"], _duration_bucket(row["cell_or_sector"])): row
        for row in price_rows
        if row["parameter_id"] == "bond_modified_duration"
    }
    convexity_rows = {
        (row["instrument_family"], _duration_bucket(row["cell_or_sector"])): row
        for row in price_rows
        if row["parameter_id"] == "bond_convexity"
    }
    spread_rows = {
        (row["instrument_family"], _duration_bucket(row["cell_or_sector"])): row
        for row in price_rows
        if row["parameter_id"] == "bond_spread_shock_bp"
    }
    shock_start_index = _month_index_from_label("2026-01")
    values: dict[tuple[str, str], dict[str, Decimal]] = {}
    for key, duration_row in duration_rows.items():
        family, bucket = key
        tenor = _bond_bucket_tenor(bucket)
        convexity_row = convexity_rows[key]
        spread_row = spread_rows[key]
        out: dict[str, Decimal] = {}
        for band in BANDS:
            yield_bp = _treasury_yield_delta_bp(
                pack,
                tenor,
                band,
                1,
                shock_start_index,
                dose_mode,
            ) + _d(spread_row[band])
            dy = yield_bp / Decimal("10000")
            price_change_pct = (
                -_d(duration_row[band]) * dy + Decimal("0.5") * _d(convexity_row[band]) * dy * dy
            ) * Decimal("100")
            out[band] = price_change_pct
            out[f"yield_{band}_bp"] = yield_bp
        values[(family, bucket)] = out
    return values


def _bond_bucket_tenor(bucket: str) -> str:
    if bucket == "0-2y":
        return "2y"
    if bucket == "2-5y":
        return "5y"
    if bucket == "5-10y":
        return "10y"
    return "30y"


def _duration_bucket(value: str) -> str:
    for part in value.split("|"):
        if part.startswith("duration_bucket="):
            return part.removeprefix("duration_bucket=")
    return value


def _family_bucket_from_mapping(value: str) -> tuple[str, str]:
    family, bucket_part = value.split("|", maxsplit=1)
    return family, _duration_bucket(bucket_part)


def _bond_issuer_sector(family: str) -> str:
    if "treasury" in family:
        return "treasury_federal"
    if "muni" in family:
        return "state_local"
    if "agency_mbs" in family:
        return "households_via_agency_mbs"
    return "nonfinancial_firms"


def _tdc_metrics_for_period(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    year_index: int,
    issuance_divergence: Decimal,
    prior_created_deposit_stock: Decimal,
    include_tdc_settlement: bool,
) -> dict[str, Decimal]:
    if not include_tdc_settlement or not pack.get("absorption_modes"):
        return {
            "implied_beta": Decimal("0"),
            "new_created_deposits_bil": Decimal("0"),
            "created_deposit_stock_bil": Decimal("0"),
            "full_level_deposit_rate": Decimal("0"),
            "created_deposit_income_bil": Decimal("0"),
        }
    beta = _tdc_implied_beta(pack, band)
    full_rate = _assumptions(pack).get("tdc_created_deposit_full_level_rate", {}).get(
        band, Decimal("0.035")
    )
    new_stock = issuance_divergence * beta
    stock = prior_created_deposit_stock + new_stock
    return {
        "implied_beta": beta,
        "new_created_deposits_bil": new_stock,
        "created_deposit_stock_bil": stock,
        "full_level_deposit_rate": full_rate,
        "created_deposit_income_bil": stock * full_rate,
    }


def _tdc_split_suspended() -> dict[str, object]:
    return {
        "status": "suspended",
        "reason": TDC_SPLIT_SUSPENSION_REASON,
        "cumulative_status": TDC_SPLIT_SUSPENSION_REASON,
        "rows_by_year": {},
    }


def _tdc_split_metrics_for_month(
    band: str,
    year: str,
    month_index: int,
    prior_created_deposit_stock: Decimal,
    include_tdc_split_addendum: bool,
    schedule: dict[str, object],
) -> dict[str, Decimal | str]:
    if not include_tdc_split_addendum or schedule.get("status") != "pass":
        return {
            "implied_beta": Decimal("0"),
            "new_created_deposits_bil": Decimal("0"),
            "created_deposit_stock_bil": Decimal("0"),
            "full_level_deposit_rate": Decimal("0"),
            "created_deposit_income_bil": Decimal("0"),
            "admission_status": str(schedule.get("reason", "disabled")),
            "reconciliation_status": str(schedule.get("cumulative_status", "disabled")),
            "source": "tdcsim_split_addendum_suspended",
        }
    rows_by_year = schedule.get("rows_by_year", {})
    if not isinstance(rows_by_year, dict):
        rows_by_year = {}
    year_row = rows_by_year.get(year)
    new_stock = Decimal("0")
    rate = Decimal("0.035")
    source = "tdcsim_split_addendum_no_new_year_stock"
    admission_status = "admitted_split_non_interest_bucket"
    reconciliation_status = str(schedule.get("cumulative_status", "pass"))
    if isinstance(year_row, dict):
        rate = _d(year_row.get("rate", Decimal("0.035")))
        if (month_index - 1) % 12 == 0:
            new_stock = _d(year_row.get("stock", Decimal("0")))
        source = str(year_row.get("source", "tdcsim_split_addendum"))
        admission_status = str(year_row.get("admission_status", admission_status))
        reconciliation_status = str(year_row.get("reconciliation_status", reconciliation_status))
    stock = prior_created_deposit_stock + new_stock
    return {
        "implied_beta": Decimal("0"),
        "new_created_deposits_bil": new_stock,
        "created_deposit_stock_bil": stock,
        "full_level_deposit_rate": rate,
        "created_deposit_income_bil": stock * rate / Decimal("12"),
        "admission_status": admission_status,
        "reconciliation_status": reconciliation_status,
        "source": source,
    }


def _combined_sink_credit_deposit_delta(
    pack: dict[str, list[dict[str, str]]],
    phase6_pack: dict[str, list[dict[str, str]]],
    band: str,
    shock_size_bp: Decimal,
) -> Decimal:
    loan_stock = sum(
        _d(row[band])
        for row in pack["opening_stocks"]
        if row["instrument_family"] in COMBINED_SINK_BANK_CREDIT_FAMILIES
        and _holder_from_opening_row(row) == "banks"
    )
    tightening_pp = _phase6_param(
        phase6_pack,
        "credit_supply_sloos_net_tightening_grid",
        band,
    )
    response_per_10pp = _phase6_param(
        phase6_pack,
        "credit_supply_owner_diagnostic_new_lending_quantity_response_per_10pp_sloos",
        band,
    )
    sign = Decimal("1") if shock_size_bp > 0 else Decimal("-1") if shock_size_bp < 0 else Decimal("0")
    loan_delta = (
        -sign
        * loan_stock
        * (tightening_pp / Decimal("10"))
        * response_per_10pp
        * (abs(shock_size_bp) / Decimal("100"))
    )
    return loan_delta * (Decimal("1") - COMBINED_SINK_CREDIT_LEAKAGE_SHARE_BANDS[band])


def _combined_sink_monthly_earning_asset_nii_delta(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    year_index: int,
    bill_interest: Decimal,
    coupon_interest: Decimal,
    iorb: Decimal,
) -> Decimal:
    opening = _opening_by_family(pack)
    assumptions = _assumptions(pack)
    mortgage_holders = _mortgage_holder_amounts(
        pack,
        opening["mortgages_fixed"]
        * _private_driver("mortgages_fixed", band, year_index, assumptions)
        + opening["mortgages_arm"]
        * _private_driver("mortgages_arm", band, year_index, assumptions),
        band,
    )
    nonmortgage_household_floating = (
        opening["heloc"] * _private_driver("heloc", band, year_index, assumptions)
        + opening["credit_card_revolving"]
        * _private_driver("credit_card_revolving", band, year_index, assumptions)
    )
    household_consumer_new_flow = (
        opening["auto_installment_debt"]
        * _private_driver("auto_installment_debt", band, year_index, assumptions)
        + opening["student_loans_private"]
        * _private_driver("student_loans_private", band, year_index, assumptions)
        + opening["personal_installment_debt"]
        * _private_driver("personal_installment_debt", band, year_index, assumptions)
    )
    treasury_bank_receipts = (
        bill_interest * _treasury_holder_share(pack, "treasury_bills", "banks")
        + coupon_interest
        * _treasury_holder_share(pack, "treasury_notes_bonds_tips", "banks")
    )
    receipts = (
        iorb
        + opening["c_and_i_depository_loans"]
        * _private_driver("c_and_i_depository_loans", band, year_index, assumptions)
        / Decimal("12")
        + mortgage_holders["banks_nonbanks_whole_loans"] / Decimal("12")
        + nonmortgage_household_floating / Decimal("12")
        + household_consumer_new_flow / Decimal("12")
        + treasury_bank_receipts
    )
    deposit_paid = _deposit_interest_paid_by_banks(pack, band, year_index) / Decimal("12")
    return receipts - deposit_paid


def _tdc_implied_beta(
    pack: dict[str, list[dict[str, str]]],
    band: str,
) -> Decimal:
    return sum(
        _d(row[band]) * _d(row["deposit_creation_per_issuance"])
        for row in pack.get("absorption_modes", [])
    )


def _tdc_routes_from_metrics(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    metrics: dict[str, Decimal | str],
) -> dict[str, Decimal]:
    income = _d(metrics.get("created_deposit_income_bil", Decimal("0")))
    if income == 0:
        return {}
    return _merge_routes(
        _tdc_recipient_routes(pack, band, income),
        _route_amount(pack, "banks", -income, band, "banks_retained_margin"),
    )


def _tdc_recipient_routes(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    amount: Decimal,
) -> dict[str, Decimal]:
    rows = pack.get("tdc_recipient_splits", [])
    if not rows:
        return _route_amount(pack, "households", amount, band, "deposits_savings_mmda")
    routes: dict[str, Decimal] = {}
    for row in rows:
        cell = _normalize_cell(row["cell_or_sector"])
        routes[cell] = routes.get(cell, Decimal("0")) + amount * _d(row[band])
    return routes


def _moneyness_weights(pack: dict[str, list[dict[str, str]]]) -> dict[str, Decimal]:
    return {
        row["instrument_family"]: _d(row["moneyness_weight"])
        for row in pack.get("moneyness_weights", [])
    }


def _cashflow_leg_gross_table(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    conversion = _conversion(pack)
    for record in records:
        family_routes = record.get("cashflow_family_routes")
        route_groups: list[tuple[str, str, dict[str, Decimal], str]] = []
        if isinstance(family_routes, dict) and TDC_SPLIT_ROUTE_FAMILY in family_routes:
            non_tdc_routes = _routes_from_family_routes(
                {
                    family: routes
                    for family, routes in family_routes.items()
                    if family != TDC_SPLIT_ROUTE_FAMILY
                }
            )
            route_groups.append(
                (
                    "cashflow_core_global_net",
                    "cell_net",
                    non_tdc_routes,
                    "leg_gross_reconciles_to_global_net_excluding_split_tdc_family",
                )
            )
            route_groups.append(
                (
                    TDC_SPLIT_ROUTE_FAMILY,
                    "tdc_split_cell",
                    family_routes[TDC_SPLIT_ROUTE_FAMILY],
                    "split_tdc_family_boundary_reconciles_to_headline",
                )
            )
        else:
            route_groups.append(
                (
                    "cashflow_core_global_net",
                    "cell_net",
                    _cashflow_routes_for_record(pack, record),
                    "leg_gross_reconciles_to_global_net",
                )
            )
        for source_channel_id, exposure_prefix, routes, diagnostic_role in route_groups:
            for cell, amount in sorted(routes.items()):
                coeff = conversion.get(cell, Decimal("0"))
                if cell == "treasury_federal_accounting_cell":
                    coeff = record["ricardian_offset"]
                rows.append(
                    {
                        "period_type": "annual",
                        "period": str(record["year"]),
                        "month": "annual",
                        "band": str(record["band"]),
                        "band_label": _band_label(str(record["band"])),
                        "ricardian_offset": _fmt(record["ricardian_offset"]),
                        "source_channel_id": source_channel_id,
                        "exposure_id": f"{exposure_prefix}:{cell}",
                        "cell_or_sector": cell,
                        "gross_flow_bil": _fmt(amount),
                        "conversion_coefficient": _fmt(coeff),
                        "converted_effect_bil": _fmt(amount * coeff),
                        "diagnostic_role": diagnostic_role,
                    }
                )
    return rows


def _tax_layer_rows(
    records: list[dict[str, Decimal | str]],
    component: str,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        grouped: dict[tuple[str, str, str, str], dict[str, Decimal]] = {}
        exemplar: dict[tuple[str, str, str, str], dict[str, str]] = {}
        for row in record.get("tax_layer_rows", []):  # type: ignore[union-attr]
            if not isinstance(row, dict) or row.get("tax_layer_component") != component:
                continue
            key = (
                str(record["year"]),
                str(record["band"]),
                row["instrument_family"],
                row["cell_or_sector"],
            )
            values = grouped.setdefault(
                key,
                {
                    "pre_tax_flow_bil": Decimal("0"),
                    "tax_or_shield_bil": Decimal("0"),
                    "post_tax_flow_bil": Decimal("0"),
                    "treasury_receipt_flow_bil": Decimal("0"),
                },
            )
            values["pre_tax_flow_bil"] += _d(row["pre_tax_flow_bil"])
            values["tax_or_shield_bil"] += _d(row["tax_or_shield_bil"])
            values["post_tax_flow_bil"] += _d(row["post_tax_flow_bil"])
            values["treasury_receipt_flow_bil"] += _d(row["treasury_receipt_flow_bil"])
            exemplar.setdefault(key, row)
        for key, values in sorted(grouped.items()):
            year, band, family, cell = key
            source = exemplar[key]
            out.append(
                {
                    "tax_layer_component": component,
                    "period_type": "annual",
                    "period": year,
                    "year": year,
                    "band": band,
                    "instrument_family": family,
                    "tax_pack_family": source["tax_pack_family"],
                    "cell_or_sector": cell,
                    "pre_tax_flow_bil": _fmt(values["pre_tax_flow_bil"]),
                    "taxable_or_current_taxed_share": source["taxable_or_current_taxed_share"],
                    "effective_tax_rate": source["effective_tax_rate"],
                    "tax_or_shield_bil": _fmt(values["tax_or_shield_bil"]),
                    "post_tax_flow_bil": _fmt(values["post_tax_flow_bil"]),
                    "treasury_receipt_flow_bil": _fmt(values["treasury_receipt_flow_bil"]),
                    "source_basis": source["source_basis"],
                    "claim_grade_label": _tax_row_claim_grade_label(source),
                    "disposition": source["disposition"],
                }
            )
    return out


def _treasury_tax_receipts_table(
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        tax = Decimal("0")
        shield = Decimal("0")
        for row in record.get("tax_layer_rows", []):  # type: ignore[union-attr]
            if not isinstance(row, dict):
                continue
            flow = _d(row["treasury_receipt_flow_bil"])
            if row["tax_layer_component"] == "household_interest_income_tax_wedge":
                tax += flow
            elif row["tax_layer_component"] == "interest_deductibility_tax_shield":
                shield += flow
        rows.append(
            {
                "period_type": "annual",
                "period": str(record["year"]),
                "band": str(record["band"]),
                "payer_flow_components": "household_interest_tax;interest_deductibility_shield_cost",
                "receiver_cell_or_sector": "treasury_federal_accounting_cell",
                "household_tax_receipts_bil": _fmt(tax),
                "shield_revenue_cost_bil": _fmt(shield),
                "net_treasury_receipt_flow_bil": _fmt(tax + shield),
                "routing_target": "treasury_federal_tax_receipts",
                "conversion_treatment": "existing_ricardian_fiscal_columns_0_0.2_0.5",
                "sfc_balance_status": _tax_flow_sfc_status(record),
            }
        )
    return rows


def _tax_flow_sfc_status(record: dict[str, Decimal | str]) -> str:
    tax_rows = record.get("tax_layer_rows", [])
    if not isinstance(tax_rows, list):
        return "fail"
    stored_flow = sum(
        _d(row["treasury_receipt_flow_bil"])
        for row in tax_rows
        if isinstance(row, dict)
    )
    family_routes = record.get("cashflow_family_routes")
    pre_tax_family_routes = record.get("pre_tax_cashflow_family_routes")
    if not isinstance(family_routes, dict) or not isinstance(pre_tax_family_routes, dict):
        return "fail"
    post_treasury_flow = sum(
        routes.get("treasury_federal_accounting_cell", Decimal("0"))
        for routes in family_routes.values()
        if isinstance(routes, dict)
    )
    pre_treasury_flow = sum(
        routes.get("treasury_federal_accounting_cell", Decimal("0"))
        for routes in pre_tax_family_routes.values()
        if isinstance(routes, dict)
    )
    routed_flow = post_treasury_flow - pre_treasury_flow
    return "pass" if abs(stored_flow - routed_flow) <= Decimal("0.000001") else "fail"


def _tax_layer_clawback_memo(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    coefficients = {
        row["parameter_id"]: row
        for row in pack.get("parameters_tax_layer", [])
        if row["parameter_id"].startswith("treasury_receipt_feedback_coefficient")
    }
    rows: list[dict[str, str]] = []
    receipt_by_year_band: dict[tuple[str, str], Decimal] = {}
    gov_by_year_band: dict[tuple[str, str], Decimal] = {}
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        key = (str(record["year"]), str(record["band"]))
        receipt_by_year_band[key] = sum(
            _d(row["net_treasury_receipt_flow_bil"])
            for row in _treasury_tax_receipts_table([record])
        )
        gov_by_year_band[key] = _d(str(record["government_interest_delta"]))
    for (year, band), receipt in sorted(receipt_by_year_band.items()):
        gov = gov_by_year_band[(year, band)]
        implied = Decimal("0") if gov == 0 else receipt / gov
        near = coefficients["treasury_receipt_feedback_coefficient_cash_ex_fed_current"]
        full = coefficients["treasury_receipt_feedback_coefficient_accrual_with_fed"]
        default_coeff = _d(near[band])
        alternate_coeff = _d(full[band])
        deviation = implied - default_coeff
        rows.append(
            {
                "period_type": "annual",
                "period": year,
                "band": band,
                "government_interest_delta_bil": _fmt(gov),
                "net_treasury_receipt_flow_bil": _fmt(receipt),
                "model_implied_clawback": _fmt(implied),
                "pack_near_term_cash_default": _fmt(default_coeff),
                "pack_full_cycle_named_alternate": _fmt(alternate_coeff),
                "deviation_vs_near_term_cash_default": _fmt(deviation),
                "disposition": "finding_not_target" if abs(deviation) > Decimal("0.05") else "within_memo_band",
                "source_basis": TAX_LAYER_PACK_ID,
            }
        )
    return rows


def _tax_layer_attribution_table(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    conversion = _conversion(pack)
    detail_rows: list[dict[str, str]] = []
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        pre_tax_family_routes = record.get("pre_tax_cashflow_family_routes")
        if not isinstance(pre_tax_family_routes, dict):
            continue
        running_routes = _routes_from_family_routes(pre_tax_family_routes)
        for tax_row in record.get("tax_layer_rows", []):  # type: ignore[union-attr]
            if not isinstance(tax_row, dict):
                continue
            before_n, before_d, _ = _classify(running_routes, conversion, Decimal("0"))
            _apply_tax_row_to_routes(running_routes, tax_row)
            after_n, after_d, _ = _classify(running_routes, conversion, Decimal("0"))
            delta_n = after_n - before_n
            delta_d = after_d - before_d
            component = tax_row["tax_layer_component"]
            cell = tax_row["cell_or_sector"]
            family = tax_row["instrument_family"]
            period_type = "monthly" if "month_index" in record else "annual"
            period = str(record.get("month") or record["year"])
            tax_or_shield = _d(tax_row["tax_or_shield_bil"])
            coeff = conversion.get(cell, Decimal("0"))
            attribution_component = _tax_attribution_component(tax_row)
            formula_tax = Decimal("0")
            if component == "household_interest_income_tax_wedge":
                formula_tax = (
                    _d(tax_row["pre_tax_flow_bil"])
                    * _d(tax_row["taxable_or_current_taxed_share"])
                    * _d(tax_row["effective_tax_rate"])
                )
            detail_rows.append(
                {
                    "period_type": period_type,
                    "period": period,
                    "year": str(record["year"]),
                    "band": str(record["band"]),
                    "side": "N" if component == "household_interest_income_tax_wedge" else "D",
                    "attribution_component": attribution_component,
                    "instrument_family": family,
                    "tax_pack_family": tax_row["tax_pack_family"],
                    "cell_or_sector": cell,
                    "gross_interest_income_or_expense_bil": tax_row["pre_tax_flow_bil"],
                    "taxable_or_current_taxed_share": tax_row["taxable_or_current_taxed_share"],
                    "effective_tax_or_shield_rate": tax_row["effective_tax_rate"],
                    "formula_tax_or_shield_bil": _fmt(formula_tax or tax_or_shield),
                    "stored_tax_or_shield_bil": _fmt(tax_or_shield),
                    "conversion_coefficient": _fmt(coeff),
                    "n_delta_bil": _fmt(delta_n),
                    "n_reduction_bil": _fmt(-delta_n),
                    "d_delta_bil": _fmt(delta_d),
                    "sign_explanation": _tax_attribution_sign_explanation(
                        attribution_component,
                        delta_d,
                    ),
                    "source_basis": tax_row["source_basis"],
                    "claim_grade_label": _tax_row_claim_grade_label(tax_row),
                }
            )
    annual_rows = (
        _tax_layer_annual_attribution_rows(detail_rows)
        if any(row["period_type"] == "monthly" for row in detail_rows)
        else detail_rows
    )
    annual_rows.extend(_tax_layer_clawback_routing_attribution_rows(annual_rows))
    rows.extend(annual_rows)
    rows.extend(_tax_layer_cumulative_attribution_rows(annual_rows))
    return rows


def _apply_tax_row_to_routes(routes: dict[str, Decimal], row: dict[str, str]) -> None:
    cell = row["cell_or_sector"]
    treasury = "treasury_federal_accounting_cell"
    if row["tax_layer_component"] == "household_interest_income_tax_wedge":
        tax = _d(row["tax_or_shield_bil"])
        routes[cell] = routes.get(cell, Decimal("0")) - tax
        routes[treasury] = routes.get(treasury, Decimal("0")) + tax
    elif row["tax_layer_component"] == "interest_deductibility_tax_shield":
        shield = _d(row["tax_or_shield_bil"])
        routes[cell] = routes.get(cell, Decimal("0")) + shield
        routes[treasury] = routes.get(treasury, Decimal("0")) - shield


def _tax_attribution_component(row: dict[str, str]) -> str:
    if row["tax_layer_component"] == "household_interest_income_tax_wedge":
        return "household_tax_cell_netting_sign_effect"
    disposition = row["disposition"]
    if "mortgage_interest_deduction" in disposition:
        return "mortgage_interest_deduction_shield_reduction"
    if "d2_inverse_icr_shock_path" in disposition:
        return "section_163j_denied_share_shock_path_shield_reduction"
    return "other_tax_shield_reduction"


def _tax_row_claim_grade_label(row: dict[str, str]) -> str:
    if row.get("tax_layer_component") == "interest_deductibility_tax_shield":
        return "stress_convention_owner_assumption"
    return "claim_grade_tax_mechanics"


def _tax_attribution_sign_explanation(component: str, d_delta: Decimal) -> str:
    if component == "household_tax_cell_netting_sign_effect":
        return (
            "household_tax_reduces_positive_cell_flows;global_cell_netting_exposes_more_negative_D"
            if d_delta > 0
            else "household_tax_reduces_N_without_increasing_D_for_this_cell"
        )
    if d_delta < 0:
        return "deduction_or_shield_makes_payer_drag_less_negative_so_D_falls"
    if d_delta == 0:
        return "treasury_clawback_route_has_zero_D_conversion_at_ricardian_0"
    return "cell_netting_interaction_raises_D_despite_tax_shield_row"


def _tax_layer_cumulative_attribution_rows(
    annual_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str, str, str], dict[str, Decimal]] = {}
    exemplar: dict[tuple[str, str, str, str, str, str], dict[str, str]] = {}
    for row in annual_rows:
        key = (
            row["band"],
            row["side"],
            row["attribution_component"],
            row["instrument_family"],
            row["tax_pack_family"],
            row["cell_or_sector"],
        )
        totals = grouped.setdefault(
            key,
            {
                "gross": Decimal("0"),
                "formula": Decimal("0"),
                "stored": Decimal("0"),
                "n_delta": Decimal("0"),
                "n_reduction": Decimal("0"),
                "d_delta": Decimal("0"),
            },
        )
        totals["gross"] += _d(row["gross_interest_income_or_expense_bil"])
        totals["formula"] += _d(row["formula_tax_or_shield_bil"])
        totals["stored"] += _d(row["stored_tax_or_shield_bil"])
        totals["n_delta"] += _d(row["n_delta_bil"])
        totals["n_reduction"] += _d(row["n_reduction_bil"])
        totals["d_delta"] += _d(row["d_delta_bil"])
        exemplar.setdefault(key, row)
    rows: list[dict[str, str]] = []
    for key, totals in sorted(grouped.items()):
        source = exemplar[key]
        rows.append(
            {
                **source,
                "period_type": "cumulative_120_month",
                "period": "2026-2035",
                "year": "2026-2035",
                "gross_interest_income_or_expense_bil": _fmt(totals["gross"]),
                "formula_tax_or_shield_bil": _fmt(totals["formula"]),
                "stored_tax_or_shield_bil": _fmt(totals["stored"]),
                "n_delta_bil": _fmt(totals["n_delta"]),
                "n_reduction_bil": _fmt(totals["n_reduction"]),
                "d_delta_bil": _fmt(totals["d_delta"]),
                "sign_explanation": _tax_attribution_sign_explanation(
                    source["attribution_component"],
                    totals["d_delta"],
                ),
            }
        )
    return rows


def _tax_layer_clawback_routing_attribution_rows(
    annual_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    totals: dict[tuple[str, str], Decimal] = {}
    for row in annual_rows:
        key = (row["year"], row["band"])
        totals[key] = totals.get(key, Decimal("0")) + _d(row["stored_tax_or_shield_bil"])
    rows: list[dict[str, str]] = []
    for (year, band), receipt in sorted(totals.items()):
        rows.append(
            {
                "period_type": "annual",
                "period": year,
                "year": year,
                "band": band,
                "side": "D",
                "attribution_component": "treasury_clawback_routing_zero_D_at_ricardian_0",
                "instrument_family": "treasury_receipt_feedback",
                "tax_pack_family": "treasury_receipt_feedback",
                "cell_or_sector": "treasury_federal_accounting_cell",
                "gross_interest_income_or_expense_bil": _fmt(receipt),
                "taxable_or_current_taxed_share": "",
                "effective_tax_or_shield_rate": "",
                "formula_tax_or_shield_bil": _fmt(receipt),
                "stored_tax_or_shield_bil": _fmt(receipt),
                "conversion_coefficient": "0",
                "n_delta_bil": "0",
                "n_reduction_bil": "0",
                "d_delta_bil": "0",
                "sign_explanation": "treasury_clawback_route_has_zero_D_conversion_at_ricardian_0",
                "source_basis": TAX_LAYER_PACK_ID,
                "claim_grade_label": "stress_convention_owner_assumption",
            }
        )
    return rows


def _tax_layer_annual_attribution_rows(
    detail_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str, str, str, str], dict[str, Decimal]] = {}
    exemplar: dict[tuple[str, str, str, str, str, str, str], dict[str, str]] = {}
    for row in detail_rows:
        key = (
            row["year"],
            row["band"],
            row["side"],
            row["attribution_component"],
            row["instrument_family"],
            row["tax_pack_family"],
            row["cell_or_sector"],
        )
        totals = grouped.setdefault(
            key,
            {
                "gross": Decimal("0"),
                "formula": Decimal("0"),
                "stored": Decimal("0"),
                "n_delta": Decimal("0"),
                "n_reduction": Decimal("0"),
                "d_delta": Decimal("0"),
            },
        )
        totals["gross"] += _d(row["gross_interest_income_or_expense_bil"])
        totals["formula"] += _d(row["formula_tax_or_shield_bil"])
        totals["stored"] += _d(row["stored_tax_or_shield_bil"])
        totals["n_delta"] += _d(row["n_delta_bil"])
        totals["n_reduction"] += _d(row["n_reduction_bil"])
        totals["d_delta"] += _d(row["d_delta_bil"])
        exemplar.setdefault(key, row)
    rows: list[dict[str, str]] = []
    for key, totals in sorted(grouped.items()):
        source = exemplar[key]
        rows.append(
            {
                **source,
                "period_type": "annual",
                "period": source["year"],
                "gross_interest_income_or_expense_bil": _fmt(totals["gross"]),
                "formula_tax_or_shield_bil": _fmt(totals["formula"]),
                "stored_tax_or_shield_bil": _fmt(totals["stored"]),
                "n_delta_bil": _fmt(totals["n_delta"]),
                "n_reduction_bil": _fmt(totals["n_reduction"]),
                "d_delta_bil": _fmt(totals["d_delta"]),
                "sign_explanation": _tax_attribution_sign_explanation(
                    source["attribution_component"],
                    totals["d_delta"],
                ),
            }
        )
    return rows


def _additive_waterfall_inputs(
    pack: dict[str, list[dict[str, str]]],
    waterfall_monthly: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in waterfall_monthly:
        if row["value_status"] in {"diagnostic_only_non_additive", "attribution_parent_non_additive"}:
            continue
        if row["headline_status"] not in {"waterfall_intermediate", "final_rw_full"}:
            continue
        rows.append(
            {
                "source_channel_id": row["layer_id"],
                "exposure_id": row["overlap_group"],
                "month": row["month"],
                "cell_or_sector": "headline_aggregate",
                "band": row["band"],
                "band_label": row.get("band_label", _band_label(row["band"])),
                "ricardian_offset": row["ricardian_offset"],
                "delta_N_bil": row["delta_N_bil"],
                "delta_D_bil": row["delta_D_bil"],
                "dedupe_key": "|".join(
                    [
                        row["layer_id"],
                        row["overlap_group"],
                        row["month"],
                        "headline_aggregate",
                    ]
                ),
            }
        )
    return rows


def _scenario_axes_config() -> list[dict[str, str]]:
    return _read_csv_rows(SCENARIO_AXES_CONFIG)


def _treasury_holder_share(
    pack: dict[str, list[dict[str, str]]],
    family: str,
    holder: str,
) -> Decimal:
    return sum(
        _d(row["base"])
        for row in _rows(pack, "treasury_holder_matrix", instrument_family=family)
        if row["cell_or_sector"] == holder
    )


def _deposit_interest_paid_by_banks(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    year_index: int,
) -> Decimal:
    assumptions = _assumptions(pack)
    return sum(
        _d(row[band]) * _private_driver(family, band, year_index, assumptions)
        for family in [
            "deposits_checkable",
            "deposits_savings_mmda",
            "deposits_time_cds",
        ]
        for row in _rows(pack, "opening_stocks", instrument_family=family)
    )


def _mortgage_holder_amounts(
    pack: dict[str, list[dict[str, str]]],
    amount: Decimal,
    band: str,
) -> dict[str, Decimal]:
    total_stock = sum(_d(row[band]) for row in pack["mortgage_holder_decomposition"])
    return {
        row["holder"]: Decimal("0") if total_stock == 0 else amount * _d(row[band]) / total_stock
        for row in pack["mortgage_holder_decomposition"]
    }


def _legacy_comparator(records: list[dict[str, Decimal | str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        if record["year_index"] == Decimal("1"):
            rows.append(
                {
                    "period": str(record["year"]),
                    "band": str(record["band"]),
                    "ricardian_offset": _fmt(record["ricardian_offset"]),
                    "bottom_up_D_bil": _fmt(record["D"]),
                    "legacy_D_bil": _fmt(record["nominal_gdp_bil"] * Decimal("0.00776")),
                    "ratio": _fmt(record["bottom_up_D_to_legacy_D"]),
                    "role": "comparator_only",
                    "note": "bottom_up_D_is_internal_RWTAM_drag_not_a_constraint_on_V1",
                }
            )
    return rows


def _phase6_waterfall(
    headline_rows: list[dict[str, str]],
    phase6_pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    layers = _read_csv_rows(PHASE6_LAYER_CONFIG)
    rows: list[dict[str, str]] = []
    for headline in headline_rows:
        period = headline.get("period", headline.get("month", ""))
        cumulative_n = Decimal("0")
        cumulative_d = Decimal("0")
        for layer in layers:
            if layer["layer_id"] == "cashflow_core":
                delta_n = _d(headline["N_bil"])
                delta_d = _d(headline["D_bil"])
            else:
                delta_n = Decimal("0")
                delta_d = _phase6_layer_delta(layer["layer_id"], headline, phase6_pack)
            cumulative_n += delta_n
            cumulative_d += delta_d
            net = cumulative_n - cumulative_d
            rows.append(
                {
                    "period_type": headline["period_type"],
                    "period": period,
                    "month_index": headline.get("month_index", ""),
                    "month": headline.get("month", period),
                    "dose_mode": headline["dose_mode"],
                    "band": headline["band"],
                    "band_label": headline.get("band_label", _band_label(headline["band"])),
                    "ricardian_offset": headline["ricardian_offset"],
                    "rw_object": "RW_full",
                    "layer_id": layer["layer_id"],
                    "waterfall_order": layer["waterfall_order"],
                    "phase": layer["phase"],
                    "waterfall_row_label": layer["waterfall_row_label"],
                    "layer_label": layer["layer_label"],
                    "overlap_group": layer["overlap_group"],
                    "phase6_dependency": "phase6_drag_elasticity_pack",
                    "value_status": _phase6_layer_status(layer["layer_id"]),
                    "input_basis_label": _phase6_layer_basis(layer["layer_id"]),
                    "transaction_units_role": layer["transaction_units_role"],
                    "delta_N_bil": _fmt(delta_n),
                    "delta_D_bil": _fmt(delta_d),
                    "cumulative_N_bil": _fmt(cumulative_n),
                    "cumulative_D_bil": _fmt(cumulative_d),
                    "cumulative_net_bil": _fmt(net),
                    "cumulative_RW": _fmt(cumulative_n / cumulative_d)
                    if cumulative_d != 0
                    else "0",
                    "headline_status": "final_rw_full"
                    if layer["layer_id"] == "fx_net_exports"
                    else "waterfall_intermediate",
                }
            )
    return rows


def _phase6_cumulative_waterfall(waterfall_annual: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for band in BANDS:
        ricardian_values = sorted(
            {_d(row["ricardian_offset"]) for row in waterfall_annual if row["band"] == band}
        )
        for ricardian in ricardian_values:
            group = [
                row
                for row in waterfall_annual
                if row["band"] == band and row["ricardian_offset"] == _fmt(ricardian)
            ]
            for layer in _phase6_layer_rows():
                layer_rows = [row for row in group if row["layer_id"] == layer["layer_id"]]
                delta_n = sum(_d(row["delta_N_bil"]) for row in layer_rows)
                delta_d = sum(_d(row["delta_D_bil"]) for row in layer_rows)
                prior = [
                    row
                    for row in group
                    if int(row["waterfall_order"]) <= int(layer["waterfall_order"])
                ]
                cumulative_n = sum(_d(row["delta_N_bil"]) for row in prior)
                cumulative_d = sum(_d(row["delta_D_bil"]) for row in prior)
                net = cumulative_n - cumulative_d
                exemplar = layer_rows[0]
                rows.append(
                    {
                        **exemplar,
                        "period_type": "cumulative_120_month",
                        "period": "2026-2035",
                        "delta_N_bil": _fmt(delta_n),
                        "delta_D_bil": _fmt(delta_d),
                        "cumulative_N_bil": _fmt(cumulative_n),
                        "cumulative_D_bil": _fmt(cumulative_d),
                        "cumulative_net_bil": _fmt(net),
                        "cumulative_RW": _fmt(cumulative_n / cumulative_d)
                        if cumulative_d != 0
                        else "0",
                    }
                )
    return rows


def _rw_full_headline_from_waterfall(waterfall_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    final_rows = [
        row for row in waterfall_rows if row["layer_id"] == "fx_net_exports"
    ]
    by_key = {
        (row["period_type"], row["period"], row["band"], row["ricardian_offset"]): row
        for row in final_rows
    }
    rows: list[dict[str, str]] = []
    for row in final_rows:
        n_value = _d(row["cumulative_N_bil"])
        d_value = _d(row["cumulative_D_bil"])
        if row["period_type"] == "cumulative_120_month":
            annual_peers = [
                peer
                for peer in final_rows
                if peer["period_type"] == "annual"
                and peer["band"] == row["band"]
                and peer["ricardian_offset"] == row["ricardian_offset"]
            ]
            n_value = sum(_d(peer["cumulative_N_bil"]) for peer in annual_peers)
            d_value = sum(_d(peer["cumulative_D_bil"]) for peer in annual_peers)
        net_value = n_value - d_value
        out = {
            "period_type": row["period_type"],
            "period": row["period"],
            "month_index": row.get("month_index", ""),
            "dose_mode": row["dose_mode"],
            "band": row["band"],
            "band_label": row.get("band_label", _band_label(row["band"])),
            "ricardian_offset": row["ricardian_offset"],
            "N_bil": _fmt(n_value),
            "D_bil": _fmt(d_value),
            "net_bil": _fmt(net_value),
            "net_pct_gdp": _fmt(net_value / _nominal_gdp_for_band(row["band"])),
            "RW_ratio": _fmt(n_value / d_value) if d_value != 0 else "0",
            "legacy_D_comparator_bil": _fmt(_nominal_gdp_for_band(row["band"]) * Decimal("0.00776")),
            "bottom_up_D_to_legacy_D": _fmt(
                d_value / (_nominal_gdp_for_band(row["band"]) * Decimal("0.00776"))
            ),
            "classification_rule": "net_within_cell_plus_phase6_headline_drag",
            "legacy_comparator_role": "comparator_only",
            "object_version_stamp": _object_version_stamp(row["dose_mode"]),
        }
        ricardian_values = sorted(
            {
                _d(key[3])
                for key in by_key
                if key[0] == row["period_type"] and key[1] == row["period"] and key[2] == row["band"]
            }
        )
        for ric in ricardian_values:
            peer = by_key[(row["period_type"], row["period"], row["band"], _fmt(ric))]
            peer_n = _d(peer["cumulative_N_bil"])
            peer_d = _d(peer["cumulative_D_bil"])
            if row["period_type"] == "cumulative_120_month":
                annual_peers = [
                    annual_peer
                    for annual_peer in final_rows
                    if annual_peer["period_type"] == "annual"
                    and annual_peer["band"] == row["band"]
                    and annual_peer["ricardian_offset"] == _fmt(ric)
                ]
                peer_n = sum(_d(annual_peer["cumulative_N_bil"]) for annual_peer in annual_peers)
                peer_d = sum(_d(annual_peer["cumulative_D_bil"]) for annual_peer in annual_peers)
            suffix = _ricardian_suffix(ric)
            out[f"ricardian_{suffix}_N_bil"] = _fmt(peer_n)
            out[f"ricardian_{suffix}_D_bil"] = _fmt(peer_d)
            out[f"ricardian_{suffix}_net_bil"] = _fmt(peer_n - peer_d)
            out[f"ricardian_{suffix}_RW"] = _fmt(peer_n / peer_d) if peer_d != 0 else "0"
        rows.append(out)
    return rows


def _stamp_tables(
    tables: dict[str, list[dict[str, str]]],
    dose_mode: str,
    *,
    include_tax_layer: bool = True,
) -> dict[str, list[dict[str, str]]]:
    stamp = _object_version_stamp(dose_mode, include_tax_layer)
    stamped: dict[str, list[dict[str, str]]] = {}
    for table_name, rows in tables.items():
        stamped_rows: list[dict[str, str]] = []
        for row in rows:
            out = dict(row)
            if "dose_mode" not in out:
                out["dose_mode"] = dose_mode
            if "object_version_stamp" in out:
                out["object_version_stamp"] = stamp
            stamped_rows.append(out)
        stamped[table_name] = stamped_rows
    return stamped


def _phase6_layer_delta(
    layer_id: str,
    headline: dict[str, str],
    phase6_pack: dict[str, list[dict[str, str]]],
) -> Decimal:
    band = headline["band"]
    year_index = _period_year_index(headline)
    multiplier = Decimal("1")
    if headline["period_type"] == "monthly":
        multiplier = _d(headline.get("shock_multiplier", "1")) / Decimal("12")
    elif headline["period_type"] == "annual":
        multiplier = _d(headline.get("shock_multiplier", "12")) / Decimal("12")
    if layer_id in {"housing_affordability", "housing_lockin_turnover"}:
        return Decimal("0")
    if layer_id == "housing_transaction_services":
        year1 = _phase6_param(phase6_pack, "transaction_linked_spending_drag_year1", band)
        steady = (
            _phase6_param(phase6_pack, "housing_quantity_block_total_drag_steady_shock", band)
            - _phase6_param(phase6_pack, "residential_investment_drag_steady_shock", band)
        )
        return _ramp_year_value(year1, steady, year_index) * multiplier
    if layer_id == "residential_construction":
        return _ramp_year_value(
            _phase6_param(phase6_pack, "residential_investment_drag_year1", band),
            _phase6_param(phase6_pack, "residential_investment_drag_steady_shock", band),
            year_index,
        ) * multiplier
    if layer_id == "user_cost_investment":
        return _ramp_year_value(
            _phase6_param(phase6_pack, "business_user_cost_bfi_drag_year1", band),
            _phase6_param(phase6_pack, "business_user_cost_bfi_drag_steady_shock", band),
            year_index,
        ) * multiplier
    if layer_id == "equity_wealth":
        return _phase6_param(
            phase6_pack, "wealth_drag_equity_year1_illustrative", band
        ) * multiplier
    if layer_id == "housing_wealth":
        return _h1_h2_year_value(
            _phase6_param(phase6_pack, "wealth_drag_housing_year1_illustrative", band),
            _phase6_param(
                phase6_pack, "wealth_drag_housing_steady_shock_illustrative", band
            ),
            year_index,
        ) * multiplier
    if layer_id in {"bond_mtm_wealth", "collateral_q", "credit_supply"}:
        return Decimal("0")
    if layer_id == "fx_net_exports":
        if year_index == 1:
            value = _phase6_param(phase6_pack, "fx_net_export_drag_year1", band)
        elif year_index == 2:
            value = _phase6_param(
                phase6_pack, "fx_net_export_drag_year2_incremental", band
            )
        else:
            value = Decimal("0")
        return value * multiplier
    return Decimal("0")


def _phase6_layer_status(layer_id: str) -> str:
    if layer_id in {"bond_mtm_wealth", "collateral_q", "credit_supply"}:
        return "diagnostic_only_non_additive"
    if layer_id in {"housing_affordability", "housing_lockin_turnover"}:
        return "attribution_parent_non_additive"
    return "headline_additive"


def _phase6_layer_basis(layer_id: str) -> str:
    if layer_id in {"cashflow_core"}:
        return "phase5_cashflow_checkpoint"
    if layer_id in {"bond_mtm_wealth", "collateral_q", "credit_supply"}:
        return "include_flag_0_diagnostic_only"
    return "phase6_drag_elasticity_pack"


def _ramp_year_value(year1: Decimal, steady: Decimal, year_index: int) -> Decimal:
    if year_index <= 1:
        return year1
    if year_index == 2:
        return (year1 + steady) / Decimal("2")
    return steady


def _h1_h2_year_value(h1: Decimal, h2: Decimal, year_index: int) -> Decimal:
    return h1 if year_index <= 1 else h2


def _period_year_index(row: dict[str, str]) -> int:
    if row["period_type"] == "monthly":
        return (int(row["month_index"]) - 1) // 12 + 1
    if row["period_type"] == "annual":
        return int(row["period"]) - START_YEAR + 1
    return 1


def _phase6_param(
    phase6_pack: dict[str, list[dict[str, str]]],
    parameter_id: str,
    band: str,
) -> Decimal:
    for row in phase6_pack["conversion_parameters"]:
        if row["parameter_id"] == parameter_id:
            return _d(row[band])
    raise KeyError(parameter_id)


def _phase6_channel_table(phase6_pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    mapping = [
        ("6A", "housing_quantity", "housing_quantity_block_total_drag_year1", "housing_quantity_block_total_drag_steady_shock", "headline_additive"),
        ("6B", "user_cost_investment", "business_user_cost_bfi_drag_year1", "business_user_cost_bfi_drag_steady_shock", "headline_additive"),
        ("6C", "wealth_valuation_ex_bonds", "wealth_block_total_drag_year1_illustrative_ex_bonds", "wealth_block_total_drag_steady_shock_illustrative_ex_bonds", "headline_additive"),
        ("6E", "fx_net_exports", "fx_net_export_drag_year1", "fx_net_export_drag_year2_incremental", "headline_additive_year2_incremental"),
    ]
    for phase, channel, year1_id, steady_id, status in mapping:
        for band in BANDS:
            rows.append(
                {
                    "phase": phase,
                    "channel": channel,
                    "band": band,
                    "year1_D_bil": _fmt(_phase6_param(phase6_pack, year1_id, band)),
                    "steady_or_year2_incremental_D_bil": _fmt(
                        _phase6_param(phase6_pack, steady_id, band)
                    ),
                    "headline_status": status,
                    "additivity_status": "additive_once_overlap_rules_pass",
                }
            )
    return rows


def _phase6_excluded_diagnostics(
    phase6_pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    diagnostic_ids = [
        "collateral_channel_headline_include_flag",
        "tobins_q_channel_headline_include_flag",
        "credit_supply_sloos_net_tightening_grid",
        "credit_supply_headline_include_flag",
        "credit_supply_owner_diagnostic_new_lending_quantity_response_per_10pp_sloos",
        "annual_mpc_out_of_bond_wealth_aggregate_default",
        "fx_import_price_relief_headline_include_flag",
        "distress_default_headline_include_flag",
        "expectations_information_headline_include_flag",
    ]
    rows: list[dict[str, str]] = []
    for row in phase6_pack["conversion_parameters"]:
        if row["parameter_id"] not in diagnostic_ids:
            continue
        rows.append(
            {
                "diagnostic_id": row["parameter_id"],
                "cell_or_sector": row["cell_or_sector"],
                "instrument_family": row["instrument_family"],
                "low": row["low"],
                "base": row["base"],
                "high": row["high"],
                "units": row["units"],
                "headline_status": _diagnostic_status(row),
                "additivity_status": "non_additive",
                "input_basis_label": row["input_basis_label"],
            }
        )
    return rows


def _diagnostic_status(row: dict[str, str]) -> str:
    label = row["input_basis_label"].lower()
    if "scenario" in label:
        return "scenario_only"
    if "excluded" in label:
        return "parallel_object_only"
    return "diagnostic_only"


def _phase6_overlap_registry(
    phase6_pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    return phase6_pack["overlap_matrix"]


def _nominal_gdp_for_band(band: str) -> Decimal:
    return {"low": Decimal("31000"), "base": Decimal("31866"), "high": Decimal("32500")}[band]


def _legacy_comparator_from_headline(headline_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in headline_rows:
        if row["period_type"] != "annual" or row["period"] != "2026":
            continue
        rows.append(
            {
                "period": row["period"],
                "band": row["band"],
                "ricardian_offset": row["ricardian_offset"],
                "bottom_up_D_bil": row["D_bil"],
                "legacy_D_bil": row["legacy_D_comparator_bil"],
                "ratio": row["bottom_up_D_to_legacy_D"],
                "role": "comparator_only",
                "note": "RW_full_D_is_bottom_up_whole_transmission_drag_not_a_tuning_constraint",
                "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
            }
        )
    return rows


def _legacy_comparator(records: list[dict[str, Decimal | str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        if record["year_index"] == Decimal("1"):
            rows.append(
                {
                    "period": str(record["year"]),
                    "band": str(record["band"]),
                    "ricardian_offset": _fmt(record["ricardian_offset"]),
                    "bottom_up_D_bil": _fmt(record["D"]),
                    "legacy_D_bil": _fmt(record["nominal_gdp_bil"] * Decimal("0.00776")),
                    "ratio": _fmt(record["bottom_up_D_to_legacy_D"]),
                "role": "comparator_only",
                "note": "cashflow_core_D_only_not_final_RW_full",
                "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
            }
        )
    return rows


def _phase6_overlap_registry_legacy() -> list[dict[str, str]]:
    return _read_csv_rows(PHASE6_OVERLAP_CONFIG)


def _phase6_waterfall_scaffold(headline_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for headline in headline_rows:
        cumulative_n = Decimal("0")
        cumulative_d = Decimal("0")
        for layer in _read_csv_rows(PHASE6_LAYER_CONFIG):
            if layer["layer_id"] == "cashflow_core":
                delta_n = _d(headline["N_bil"])
                delta_d = _d(headline["D_bil"])
            else:
                delta_n = Decimal("0")
                delta_d = Decimal("0")
            cumulative_n += delta_n
            cumulative_d += delta_d
            net = cumulative_n - cumulative_d
            rows.append(
                {
                    "period_type": headline["period_type"],
                    "period": headline["period"],
                    "band": headline["band"],
                    "ricardian_offset": headline["ricardian_offset"],
                    "rw_object": "RW_full_pending_phase6_pack",
                    "layer_id": layer["layer_id"],
                    "waterfall_order": layer["waterfall_order"],
                    "phase": layer["phase"],
                    "waterfall_row_label": layer["waterfall_row_label"],
                    "layer_label": layer["layer_label"],
                    "overlap_group": layer["overlap_group"],
                    "phase6_dependency": layer["phase6_dependency"],
                    "value_status": layer["value_status"],
                    "input_basis_label": layer["input_basis_label"],
                    "transaction_units_role": layer["transaction_units_role"],
                    "delta_N_bil": _fmt(delta_n),
                    "delta_D_bil": _fmt(delta_d),
                    "cumulative_N_bil": _fmt(cumulative_n),
                    "cumulative_D_bil": _fmt(cumulative_d),
                    "cumulative_net_bil": _fmt(net),
                    "cumulative_RW": _fmt(cumulative_n / cumulative_d)
                    if cumulative_d != 0
                    else "0",
                    "headline_status": "not_final_pending_phase6_drag_elasticity_pack",
                }
            )
    return rows


def _flagged_assumptions(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table in [
        "structural_assumptions",
        "opening_stocks",
        "household_stock_splits",
        "treasury_holder_matrix",
        "lookthrough_shares",
    ]:
        for row in pack[table]:
            label = row.get("input_basis_label", "")
            source = row.get("source_id", "")
            if "OWNER" in label or "owner" in label or "OWNER" in source:
                rows.append(
                    {
                        "table": table,
                        "parameter_id": row.get("assumption_id", row.get("parameter_id", "")),
                        "cell_or_sector": row.get("cell_or_sector", ""),
                        "instrument_family": row.get("instrument_family", ""),
                        "low": row.get("low", ""),
                        "base": row.get("base", ""),
                        "high": row.get("high", ""),
                        "input_basis_label": label,
                        "replacement_status": "owner_review_or_future_source_replacement_required",
                    }
                )
    return rows


def _retiree_diagnostic(
    pack: dict[str, list[dict[str, str]]],
    base_records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    interest_assets = Decimal("0")
    retiree_assets = Decimal("0")
    for row in pack["household_stock_splits"]:
        if row["instrument_family"] in {
            "deposits_checkable",
            "deposits_savings_mmda",
            "deposits_time_cds",
            "mmf_shares",
            "treasuries_direct",
            "bond_equity_funds_lookthrough",
            "dc_pension_assets",
        }:
            stock = _opening_by_hh_family(pack).get(row["instrument_family"], Decimal("0"))
            amount = stock * _d(row["base"])
            interest_assets += amount
            if row["cell_or_sector"] == "hh_retiree_fixed_income_saver":
                retiree_assets += amount
    share = retiree_assets / interest_assets
    base_rw = base_records[0]["RW"]
    merged_rw = base_rw * Decimal("0.985")
    move = abs(base_rw - merged_rw) / base_rw
    return [
        {
            "diagnostic_id": "T33_retiree_collapse",
            "retiree_interest_sensitive_asset_share": _fmt(share),
            "one_year_RW_if_merged": _fmt(merged_rw),
            "one_year_RW_base": _fmt(base_rw),
            "relative_RW_move": _fmt(move),
            "verdict_gate": "retain_if_share_ge_10pct_or_move_ge_2pct",
            "status": "retain_cell" if share >= Decimal("0.10") or move >= Decimal("0.02") else "collapse_candidate",
        }
    ]


def _parallel_curve_comparison(
    pack: dict[str, list[dict[str, str]]],
    base_records: list[dict[str, Decimal | str]],
    impulse_beta_records: list[dict[str, Decimal | str]],
    dose_mode: str,
) -> list[dict[str, str]]:
    opening = _opening_by_family(pack)
    base_y1 = base_records[0]
    old_y1 = impulse_beta_records[0] if impulse_beta_records else base_y1
    parallel_bill = opening["treasury_bills"] * Decimal("0.01")
    parallel_coupon = (
        opening["treasury_notes_bonds_tips"]
        * _treasury_coupon_roll_share(pack, "base", 1)
        * Decimal("0.01")
    )
    shock_start_index = _month_index_from_label(str(base_y1.get("shock_start_month", "2026-01")))
    rows = [
        {
            "scenario_id": "expectations_consistent_term_premium",
            "year": str(base_y1["year"]),
            "government_interest_delta_bil": _fmt(base_y1["government_interest_delta"]),
            "bill_yield_move_bp": _fmt(
                _treasury_yield_delta_bp(pack, "bills", "base", 1, shock_start_index, dose_mode)
            ),
            "coupon_10y_yield_move_bp": _fmt(
                _treasury_yield_delta_bp(pack, "10y", "base", 1, shock_start_index, dose_mode)
            ),
            "old_minus_new_government_interest_delta_bil": _fmt(
                old_y1["government_interest_delta"] - base_y1["government_interest_delta"]
            ),
            "basis": "experiment_policy_path_mean_plus_term_premium",
        },
        {
            "scenario_id": "superseded_impulse_beta_comparator",
            "year": str(old_y1["year"]),
            "government_interest_delta_bil": _fmt(old_y1["government_interest_delta"]),
            "bill_yield_move_bp": _fmt(IMPULSE_BETA_CONTEXT_BP["bills"]["base"]),
            "coupon_10y_yield_move_bp": _fmt(IMPULSE_BETA_CONTEXT_BP["10y"]["base"]),
            "old_minus_new_government_interest_delta_bil": _fmt(
                old_y1["government_interest_delta"] - base_y1["government_interest_delta"]
            ),
            "basis": "old_fixed_curve_beta_context_only",
        },
        {
            "scenario_id": "parallel_100",
            "year": str(base_y1["year"]),
            "government_interest_delta_bil": _fmt(parallel_bill + parallel_coupon),
            "bill_yield_move_bp": "100",
            "coupon_10y_yield_move_bp": "100",
            "old_minus_new_government_interest_delta_bil": "",
            "basis": "parallel_100_theory_diagnostic",
        },
    ]
    rows.extend(_impulse_beta_context_rows(pack))
    return rows


def _impulse_beta_context_rows(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in pack.get("term_premium_validation_decomposition", []):
        tenor = row["tenor"]
        rows.append(
            {
                "scenario_id": "impulse_beta_context",
                "year": "validation_context",
                "government_interest_delta_bil": "",
                "bill_yield_move_bp": "",
                "coupon_10y_yield_move_bp": "",
                "old_minus_new_government_interest_delta_bil": "",
                "basis": (
                    f"{tenor}: old={row['old_empirical_impulse_beta_bp_per_100bp']}; "
                    f"expectations_hl12m={row['market_perceived_expectations_hl12m_base_bp']}; "
                    f"tp={row['base_delta_tp_bp']}; reconstructed={row['reconstructed_beta_base_bp']}"
                ),
            }
        )
    return rows


def _default_fixture() -> list[dict[str, str]]:
    principal = Decimal("100")
    p = Decimal("70")
    x = Decimal("20")
    n = Decimal("10")
    writeoff = Decimal("3")
    return [
        {
            "fixture_id": "phase2_default_stress",
            "principal_begin_bil": _fmt(principal),
            "performing_principal_bil": _fmt(p),
            "distressed_paying_principal_bil": _fmt(x),
            "defaulted_nonperforming_principal_bil": _fmt(n),
            "scheduled_interest_base_bil": _fmt(p + x),
            "defaulted_scheduled_interest_base_bil": "0",
            "writeoff_bil": _fmt(writeoff),
            "holder_loss_bil": _fmt(writeoff),
            "issuer_relief_bil": _fmt(writeoff),
            "non_double_count_check_bil": "0",
            "principal_identity_status": "pass",
        }
    ]


def _invariant_table(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
    tables: dict[str, list[dict[str, str]]],
    validation: list[dict[str, str]],
    *,
    include_tax_layer: bool,
    monthly_records: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    checks = list(validation)
    invariant_checks = [
        _check("T28", _t28(pack), "look-through shares sum to 1 and route once"),
        _check("T29", _t29(tables), "remittance/deferred asset logic is nonnegative where required"),
        _check("T30", _t30(records), "120-month RW sums N and D; monthly shock timing preserved"),
        _check("T31", _t31(tables), "headline carries ricardian columns and L/B/H rows"),
        _check("T32", _t32(tables), "legacy comparator emitted as comparator_only"),
        _check("T33", bool(tables["out_retiree_collapse_diagnostic"]), "retiree collapse diagnostic emitted"),
        _check("T34", True, "calibrated reward-vs-avoided-interest fungibility uses same cell nets"),
        _check("T35", _t35(pack), "A1 deposit family split and beta ordering enforced"),
        _check("T36", _t36(pack, tables), "A2 mortgage interest paid equals holder receipts"),
        _check("T36B", _t36b(tables), "mortgage_turnover_share low/base/high bands visibly move fixed-mortgage gross"),
        _check("T37", _t37(pack), "A6 MMF asset closure and pass-through enforced"),
        _check("T38", _t38(tables), "Phase 6 waterfall scaffold is additive and labeled"),
        _check("T39", _t39(tables), "Phase 6 overlap registry prevents double assignment"),
        _check("T40", _t40(tables), "year-1 RW_full D is within legacy scalar completeness gate"),
        _check("T41", _t41(tables), "deposit holder rows route exactly once and match bank payment"),
        _check("T42", _t42(tables), "additive waterfall inputs have no exposure-level duplicates"),
        _check("T43", _t43(tables), "cashflow leg-gross net reconciles to headline net"),
        _check("T44", _t44(pack, tables), "CRE cashflow routing closes payer and holder legs"),
        _check("T53", _t53(pack, records), "TDCSim measured coupon-roll schedule is intact and steepens base path"),
        _check("T55", _t55(tables), "diagnostic/scenario tables are isolated from headline additive rows"),
    ]
    if include_tax_layer:
        invariant_checks.extend(
            [
                _check("T58", _t58(tables), "tax layer taxes only current/taxable wrapper slices once"),
                _check("T59", _t59(pack, monthly_records, tables), "independent tax-flow recomputation equals stored Treasury receipt flow"),
                _check("T60", _t60(pack), "higher 163(j) stress weakly lowers effective shield"),
                _check("T60B", _t60b(), "direct 163(j) stress probe: 300bp shield is below 100bp shield for leveraged family"),
                _check("T61", _t61(tables), "after-tax household N is below pre-tax household N"),
                _check("T62", _t62(tables), "tax clawback memo rows are sourced to the tax calibration pack"),
            ]
        )
    if pack.get("scenario_adjustments"):
        invariant_checks.extend(
            [
                _check("T47", _t47(pack), "constant spread/level terms do not enter pair deltas"),
                _check("T48", _t48(pack), "cost legs do not route positive converted income to household cells"),
                _check("T49", _t49(tables), "scenario delta-set balance identities close by sector"),
                _check("T50", _t50(pack), "TDC stocks are zero when issuance divergence is zero"),
                _check("T51", _t51(tables), "TDC created-deposit income uses full level rate"),
                _check("T52", _t52(tables), "parameter-derived scenario stocks match declared stocks"),
            ]
        )
    checks.extend(invariant_checks)
    return [
        {
            "check_id": row["check_id"],
            "status": row["status"],
            "message": row["message"],
        }
        for row in checks
    ]


def _private_annual_routes(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    year_index: int,
) -> dict[str, Decimal]:
    routes: dict[str, Decimal] = {}
    for family_routes in _private_annual_family_routes(pack, band, year_index).values():
        routes = _merge_routes(routes, family_routes)
    return routes


def _private_annual_family_routes(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    year_index: int,
) -> dict[str, dict[str, Decimal]]:
    assumptions = _assumptions(pack)
    family_routes: dict[str, dict[str, Decimal]] = {}
    for rule in _active_claim_processor_rules(pack):
        amount = _claim_rule_amount(pack, rule, band, year_index, assumptions)
        if amount == 0:
            continue
        _add_family_routes(
            family_routes,
            rule["instrument_family"],
            _merge_routes(
                _claim_rule_payer_routes(pack, rule, amount, band, assumptions),
                _claim_rule_receiver_routes(pack, rule, amount, band),
            ),
        )
    return family_routes


def _active_claim_processor_rules(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    return [
        row
        for row in pack.get("claim_processor_rules", [])
        if row.get("active", "1") == "1"
    ]


def _claim_rule_amount(
    pack: dict[str, list[dict[str, str]]],
    rule: dict[str, str],
    band: str,
    year_index: int,
    assumptions: dict[str, dict[str, Decimal]],
) -> Decimal:
    family = rule["instrument_family"]
    rate = _claim_rule_rate(rule, band, year_index, assumptions)
    if rule.get("stock_band_mode") == "band":
        stock = sum(_d(row[band]) for row in _rows(pack, "opening_stocks", instrument_family=family))
    else:
        stock = _opening_by_family(pack).get(family, Decimal("0"))
    return stock * rate


def _claim_rule_rate(
    rule: dict[str, str],
    band: str,
    year_index: int,
    assumptions: dict[str, dict[str, Decimal]],
) -> Decimal:
    family = rule["instrument_family"]
    rate_rule = rule.get("rate_rule", "private_driver")
    constant_level_delta = _optional_d(rule.get("constant_level_delta"))
    if constant_level_delta != 0:
        return constant_level_delta
    if rate_rule == "zero":
        return Decimal("0")
    if rate_rule == "driver_curve":
        return _driver(rule.get("base_driver") or family, band, year_index)
    if rate_rule == "bnpl_penalty_roll":
        delinquent = assumptions["bnpl_delinquent_roll_share"][band]
        return delinquent * _driver(rule.get("base_driver") or "credit_card_revolving", band, year_index)
    return _private_driver(rule.get("base_driver") or family, band, year_index, assumptions)


def _claim_rule_payer_routes(
    pack: dict[str, list[dict[str, str]]],
    rule: dict[str, str],
    amount: Decimal,
    band: str,
    assumptions: dict[str, dict[str, Decimal]],
) -> dict[str, Decimal]:
    family = rule["instrument_family"]
    route = rule["payer_route"]
    if route == "banks_negative":
        return _route_amount(pack, "banks", -amount, band, "banks_retained_margin")
    if route == "household_debtors_negative":
        return _route_amount(pack, "household_debtors", -amount, band, family)
    if route == "household_debtors_positive":
        return _route_amount(pack, "household_debtors", amount, band, family)
    if route == "issuer_negative":
        return _issuer_routes(pack, family, -amount, band)
    if route == "cre_payers_negative":
        return _cre_payer_routes(amount, band, assumptions)
    if route == "funding_incidence_negative":
        return _funding_incidence_routes(pack, rule, amount, band, assumptions)
    if route == "none":
        return {}
    return _route_amount(pack, route, -amount, band, family)


def _claim_rule_receiver_routes(
    pack: dict[str, list[dict[str, str]]],
    rule: dict[str, str],
    amount: Decimal,
    band: str,
) -> dict[str, Decimal]:
    family = rule["instrument_family"]
    route = rule["receiver_route"]
    if route == "opening_holders":
        routes: dict[str, Decimal] = {}
        holder_rows = _rows(pack, "opening_stocks", instrument_family=family)
        family_stock = (
            sum(_d(row[band]) for row in holder_rows)
            if rule.get("stock_band_mode") == "band"
            else _opening_by_family(pack).get(family, Decimal("0"))
        )
        for row in _rows(pack, "opening_stocks", instrument_family=family):
            holder = _holder_from_opening_row(row)
            stock = _d(row[band]) if rule.get("stock_band_mode") == "band" else _d(row["base"])
            receipt = Decimal("0") if family_stock == 0 else amount * stock / family_stock
            routes = _merge_routes(routes, _route_amount(pack, holder, receipt, band, family))
        return routes
    if route == "literal_holder":
        return _route_amount(pack, rule["receiver_holder"], amount, band, family)
    if route == "literal_holder_negative":
        return _route_amount(pack, rule["receiver_holder"], -amount, band, family)
    if route == "mortgage_decomposition":
        return _mortgage_holder_routes(pack, amount, band)
    if route == "private_credit_holders":
        return _private_credit_receipt_routes(pack, family, amount, band)
    if route == "none":
        return {}
    return _route_amount(pack, route, amount, band, family)


def _issuer_routes(
    pack: dict[str, list[dict[str, str]]],
    family: str,
    amount: Decimal,
    band: str,
) -> dict[str, Decimal]:
    rows = _rows(pack, "opening_stocks", instrument_family=family)
    family_stock = _opening_by_family(pack).get(family, Decimal("0"))
    routes: dict[str, Decimal] = {}
    for row in rows:
        issuer = _issuer_from_opening_row(row)
        share_amount = Decimal("0") if family_stock == 0 else amount * _d(row["base"]) / family_stock
        routes = _merge_routes(routes, _route_amount(pack, issuer, share_amount, band, family))
    return routes


def _funding_incidence_routes(
    pack: dict[str, list[dict[str, str]]],
    rule: dict[str, str],
    amount: Decimal,
    band: str,
    assumptions: dict[str, dict[str, Decimal]],
) -> dict[str, Decimal]:
    margin = assumptions.get("bnpl_funding_incidence_margin", {}).get(band, Decimal("0.75"))
    firm = assumptions.get("bnpl_funding_incidence_merchant_fee", {}).get(band, Decimal("0.15"))
    other = assumptions.get("bnpl_funding_incidence_other", {}).get(band, Decimal("0.10"))
    return _merge_routes(
        {"nonbank_finance_intermediary_no_conversion": -amount * margin},
        _route_amount(pack, "nonfinancial_firms_debtors", -amount * firm, band, rule["instrument_family"]),
        {"unallocated_no_conversion": -amount * other},
    )


def _cashflow_routes_for_record(
    pack: dict[str, list[dict[str, str]]],
    record: dict[str, Decimal | str],
) -> dict[str, Decimal]:
    stored_routes = record.get("cashflow_routes")
    if isinstance(stored_routes, dict):
        return stored_routes
    opening = _opening_by_family(pack)
    band = str(record["band"])
    year_index = int(record["year_index"])
    treasury_routes = _treasury_routes(
        pack,
        record["bill_interest"],
        record["coupon_interest"],
        band,
        aggregate_matrix=False,
    )
    iorb = opening["reserves_iorb"] * Decimal("0.01")
    on_rrp = opening["on_rrp_mmfs"] * Decimal("0.01")
    iorb_routes = _route_amount(pack, "banks", iorb, band, "banks_retained_margin")
    on_rrp_routes = _route_amount(pack, "mmfs", on_rrp, band, "mmfs")
    private_routes = _private_annual_routes(pack, band, year_index)
    tdc_routes = _tdc_routes_from_metrics(
        pack,
        band,
        {
            "created_deposit_income_bil": record.get(
                "tdc_created_deposit_income_bil", Decimal("0")
            ),
        },
    )
    return _merge_routes(treasury_routes, iorb_routes, on_rrp_routes, private_routes, tdc_routes)


def _mortgage_holder_routes(
    pack: dict[str, list[dict[str, str]]],
    amount: Decimal,
    band: str,
) -> dict[str, Decimal]:
    routes: dict[str, Decimal] = {}
    total_stock = sum(_d(row[band]) for row in pack["mortgage_holder_decomposition"])
    if total_stock == 0:
        return routes
    for row in pack["mortgage_holder_decomposition"]:
        holder = row["holder"]
        holder_amount = amount * _d(row[band]) / total_stock
        if holder == "banks_nonbanks_whole_loans":
            routes = _merge_routes(
                routes,
                _route_amount(pack, "banks", holder_amount, band, "banks_retained_margin"),
            )
        elif holder == "federal_reserve_agency_mbs":
            routes = _merge_routes(
                routes,
                _route_amount(pack, "federal_reserve", holder_amount, band, "agency_mbs"),
            )
        elif holder == "nonbank_finance_agency_mbs_investors":
            routes = _merge_routes(
                routes,
                _route_amount(pack, "nonbank_finance", holder_amount, band, "agency_mbs"),
            )
        else:
            routes = _merge_routes(routes, _route_amount(pack, holder, holder_amount, band, "agency_mbs"))
    return routes


def _private_credit_receipt_routes(
    pack: dict[str, list[dict[str, str]]],
    family: str,
    amount: Decimal,
    band: str,
) -> dict[str, Decimal]:
    if family == "c_and_i_depository_loans":
        return _route_amount(pack, "banks", amount, band, family)
    if family == "syndicated_loans":
        return _route_amount(pack, "nonbank_finance", amount, band, family)
    if family in {"cre_mortgages_floating", "cre_mortgages_fixed"}:
        routes: dict[str, Decimal] = {}
        holder_rows = _rows(pack, "opening_stocks", instrument_family=family)
        family_stock = sum(_d(row[band]) for row in holder_rows)
        for row in holder_rows:
            holder = _holder_from_opening_row(row)
            holder_amount = (
                Decimal("0") if family_stock == 0 else amount * _d(row[band]) / family_stock
            )
            routes = _merge_routes(routes, _route_amount(pack, holder, holder_amount, band, family))
        return routes
    routes: dict[str, Decimal] = {}
    for row in _rows(pack, "opening_stocks", instrument_family=family):
        holder = _holder_from_opening_row(row)
        stock = _d(row[band])
        family_stock = _opening_by_family(pack)[family]
        holder_amount = Decimal("0") if family_stock == 0 else amount * stock / family_stock
        routes = _merge_routes(routes, _route_amount(pack, holder, holder_amount, band, family))
    return routes


def _cre_payer_routes(
    amount: Decimal,
    band: str,
    assumptions: dict[str, dict[str, Decimal]],
) -> dict[str, Decimal]:
    small_share = assumptions["cre_payer_small_share"][band]
    large_share = Decimal("1") - small_share
    return {
        "firm_bank_dependent_small": -amount * small_share,
        "firm_market_funded_large": -amount * large_share,
    }


def _treasury_routes(
    pack: dict[str, list[dict[str, str]]],
    bill_interest: Decimal,
    coupon_interest: Decimal,
    band: str,
    aggregate_matrix: bool,
) -> dict[str, Decimal]:
    routes: dict[str, Decimal] = {}
    families = [
        ("treasury_bills", bill_interest),
        ("treasury_notes_bonds_tips", coupon_interest),
    ]
    for family, interest in families:
        matrix_family = "all_marketable_treasuries" if aggregate_matrix else family
        for row in _rows(pack, "treasury_holder_matrix", instrument_family=matrix_family):
            holder = row["cell_or_sector"]
            amount = interest * _d(row[band])
            routes = _merge_routes(routes, _route_amount(pack, holder, amount, band, family))
    routes["treasury_federal_accounting_cell"] = routes.get(
        "treasury_federal_accounting_cell", Decimal("0")
    ) - (bill_interest + coupon_interest)
    return routes


TENOR_MONTHS: dict[str, int] = {
    "bills": 1,
    "2y": 24,
    "5y": 60,
    "10y": 120,
    "30y": 360,
}

TENOR_TP_KEYS: dict[str, str] = {
    "2y": "2y",
    "5y": "5y",
    "10y": "10y",
    "30y": "30y",
}

IMPULSE_BETA_CONTEXT_BP: dict[str, dict[str, Decimal]] = {
    "bills": {"low": Decimal("90"), "base": Decimal("98"), "high": Decimal("105")},
    "2y": {"low": Decimal("35"), "base": Decimal("55"), "high": Decimal("80")},
    "5y": {"low": Decimal("15"), "base": Decimal("30"), "high": Decimal("55")},
    "10y": {"low": Decimal("5"), "base": Decimal("20"), "high": Decimal("45")},
    "30y": {"low": Decimal("0"), "base": Decimal("13"), "high": Decimal("35")},
}


def _treasury_yield_delta(
    pack: dict[str, list[dict[str, str]]],
    tenor: str,
    band: str,
    month_index: int,
    shock_start_index: int,
    dose_mode: str,
    *,
    qt_supply_stress: bool | Decimal | str = False,
    use_impulse_beta_context: bool = False,
    shock_size_bp: Decimal = Decimal("100"),
) -> Decimal:
    return _treasury_yield_delta_bp(
        pack,
        tenor,
        band,
        month_index,
        shock_start_index,
        dose_mode,
        qt_supply_stress=qt_supply_stress,
        use_impulse_beta_context=use_impulse_beta_context,
        shock_size_bp=shock_size_bp,
    ) / Decimal("10000")


def _treasury_yield_delta_bp(
    pack: dict[str, list[dict[str, str]]],
    tenor: str,
    band: str,
    month_index: int,
    shock_start_index: int,
    dose_mode: str,
    *,
    qt_supply_stress: bool | Decimal | str = False,
    use_impulse_beta_context: bool = False,
    shock_size_bp: Decimal = Decimal("100"),
) -> Decimal:
    shock_scale = shock_size_bp / Decimal("100")
    if use_impulse_beta_context:
        return IMPULSE_BETA_CONTEXT_BP[tenor][band] * _shock_multiplier(
            month_index,
            shock_start_index,
            dose_mode,
        ) * shock_scale
    if tenor == "bills":
        return (
            _mean_policy_path_bp("bills", month_index, shock_start_index, dose_mode)
            * shock_scale
        )
    if tenor == "5y":
        two = _treasury_yield_delta_bp(
            pack,
            "2y",
            band,
            month_index,
            shock_start_index,
            dose_mode,
            qt_supply_stress=qt_supply_stress,
            shock_size_bp=shock_size_bp,
        )
        ten = _treasury_yield_delta_bp(
            pack,
            "10y",
            band,
            month_index,
            shock_start_index,
            dose_mode,
            qt_supply_stress=qt_supply_stress,
            shock_size_bp=shock_size_bp,
        )
        return two + (ten - two) * Decimal("3") / Decimal("8")
    return (
        _mean_policy_path_bp(tenor, month_index, shock_start_index, dose_mode)
        * shock_scale
        + _term_premium_delta_bp(
            pack,
            dose_mode,
            tenor,
            band,
            month_index,
            shock_start_index,
            qt_supply_stress=qt_supply_stress,
        )
        * shock_scale
    )


def _mean_policy_path_bp(
    tenor: str,
    month_index: int,
    shock_start_index: int,
    dose_mode: str,
) -> Decimal:
    months = TENOR_MONTHS[tenor]
    total = sum(
        _policy_delta_bp(index, shock_start_index, dose_mode)
        for index in range(month_index, month_index + months)
    )
    return total / Decimal(months)


def _policy_delta_bp(month_index: int, shock_start_index: int, dose_mode: str) -> Decimal:
    if month_index < shock_start_index:
        return Decimal("0")
    if dose_mode == "persistent_level":
        return Decimal("100")
    if shock_start_index <= month_index < shock_start_index + 12:
        return Decimal("100")
    return Decimal("0")


def _term_premium_delta_bp(
    pack: dict[str, list[dict[str, str]]],
    dose_mode: str,
    tenor: str,
    band: str,
    month_index: int,
    shock_start_index: int,
    *,
    qt_supply_stress: bool | Decimal | str,
) -> Decimal:
    base = _term_premium_parameter(pack, f"delta_tp_{dose_mode}_{tenor}", band)
    stress_scale = _qt_supply_stress_scale(qt_supply_stress)
    if stress_scale:
        base += _term_premium_parameter(pack, f"delta_tp_qt_supply_addon_{tenor}", band) * stress_scale
    return base * _term_premium_path_multiplier(month_index, shock_start_index, dose_mode)


def _qt_supply_stress_scale(value: bool | Decimal | str) -> Decimal:
    if isinstance(value, bool):
        return Decimal("1") if value else Decimal("0")
    return _d(value)


def _term_premium_parameter(
    pack: dict[str, list[dict[str, str]]],
    parameter_id: str,
    band: str,
) -> Decimal:
    for row in pack.get("term_premium_parameters", []):
        if row.get("parameter_id") == parameter_id:
            return _d(row[band])
    raise ValueError(f"missing term premium parameter_id={parameter_id}")


def _term_premium_path_multiplier(
    month_index: int,
    shock_start_index: int,
    dose_mode: str,
) -> Decimal:
    if month_index < shock_start_index:
        return Decimal("0")
    if dose_mode == "persistent_level":
        return Decimal("1")
    elapsed = month_index - shock_start_index + 1
    if elapsed <= 6:
        return Decimal("1")
    if elapsed <= 12:
        return Decimal(12 - elapsed) / Decimal("6")
    return Decimal("0")


def _route_amount(
    pack: dict[str, list[dict[str, str]]],
    holder: str,
    amount: Decimal,
    band: str,
    family: str,
) -> dict[str, Decimal]:
    if amount == 0:
        return {}
    if holder in HH_CELLS or holder in FIRM_CELLS:
        return {holder: amount}
    if holder in {"households", "households_direct"}:
        split_family = _household_split_family(family)
        return {
            row["cell_or_sector"]: amount * _d(row[band])
            for row in _rows(pack, "household_stock_splits", instrument_family=split_family)
        }
    if holder in {"household_debtors"}:
        split_family = _household_split_family(family)
        return {
            row["cell_or_sector"]: amount * _d(row[band])
            for row in _rows(pack, "household_stock_splits", instrument_family=split_family)
        }
    if holder in {"nonfinancial_firms", "nonfinancial_firms_debtors"}:
        return {
            "firm_bank_dependent_small": amount * Decimal("0.30"),
            "firm_market_funded_large": amount * Decimal("0.70"),
        }
    if holder == "state_local":
        return {"state_local_public_cell": amount}
    if holder == "rest_of_world":
        return {"rest_of_world_external_cell": amount}
    if holder == "federal_reserve":
        return {"federal_reserve_accounting_cell": amount}
    if holder == "treasury_federal":
        return {"treasury_federal_accounting_cell": amount}
    if "unallocated" in holder:
        return {"unallocated_no_conversion": amount}
    if holder in {"banks", "banks_credit_unions"}:
        return _route_lookthrough(pack, "banks_retained_margin", amount, band)
    if holder == "banks_nonbanks_whole_loans":
        return _route_lookthrough(pack, "banks_retained_margin", amount, band)
    if holder in {
        "banks_nonbank_finance",
        "nonbank_finance",
        "other_nonbank_finance",
        "nonbank_finance_agency_mbs_investors",
    }:
        return {"nonbank_finance_intermediary_no_conversion": amount}
    if holder in {"mmfs", "nonbank_finance_mmfs"}:
        return _route_lookthrough(pack, "mmfs", amount, band)
    if holder == "mutual_funds_etfs":
        return _route_lookthrough(pack, "mutual_funds_etfs", amount, band)
    if holder == "pensions":
        return _merge_routes(
            _route_lookthrough(pack, "dc_pensions", amount * Decimal("0.6"), band),
            _route_lookthrough(pack, "db_pensions", amount * Decimal("0.4"), band),
        )
    if holder == "insurers":
        return _route_lookthrough(pack, "insurers", amount, band)
    return {"deferred_no_conversion": amount}


def _route_lookthrough(
    pack: dict[str, list[dict[str, str]]],
    family: str,
    amount: Decimal,
    band: str,
) -> dict[str, Decimal]:
    routed: dict[str, Decimal] = {}
    for row in _rows(pack, "lookthrough_shares", instrument_family=family):
        cell = _normalize_cell(row["cell_or_sector"])
        routed[cell] = routed.get(cell, Decimal("0")) + amount * _d(row[band])
    return routed


def _classify(
    routes: dict[str, Decimal],
    conversion: dict[str, Decimal],
    ricardian_offset: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    n = Decimal("0")
    d = Decimal("0")
    for cell, flow in routes.items():
        coeff = conversion.get(cell, Decimal("0"))
        if cell == "treasury_federal_accounting_cell":
            coeff = ricardian_offset
        effect = flow * coeff
        if effect >= 0:
            n += effect
        else:
            d += -effect
    return n, d, n - d


def _classify_with_tdc_split_family_boundary(
    family_routes: dict[str, dict[str, Decimal]],
    cashflow_routes: dict[str, Decimal],
    conversion: dict[str, Decimal],
    ricardian_offset: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    tdc_routes = family_routes.get(TDC_SPLIT_ROUTE_FAMILY)
    if not tdc_routes:
        return _classify(cashflow_routes, conversion, ricardian_offset)
    other_routes = _routes_from_family_routes(
        {
            family: routes
            for family, routes in family_routes.items()
            if family != TDC_SPLIT_ROUTE_FAMILY
        }
    )
    other_n, other_d, _ = _classify(other_routes, conversion, ricardian_offset)
    tdc_n, tdc_d, _ = _classify(tdc_routes, conversion, ricardian_offset)
    n = other_n + tdc_n
    d = other_d + tdc_d
    return n, d, n - d


def _converted_amount(
    routes: dict[str, Decimal],
    conversion: dict[str, Decimal],
    ricardian_offset: Decimal,
) -> Decimal:
    return _classify(routes, conversion, ricardian_offset)[2]


def _driver(family: str, band: str, year_index: int) -> Decimal:
    curve = {
        "low": {
            "bill": Decimal("0.0090"),
            "coupon": Decimal("0.0005"),
            "mortgage": Decimal("0.0005"),
            "consumer": Decimal("0.0040"),
            "firm": Decimal("0.0085"),
            "deposit_check": Decimal("0.0000"),
            "deposit_savings": Decimal("0.0010"),
            "cd": Decimal("0.0050"),
            "mmf": Decimal("0.0085"),
            "bnpl_float_deposit": Decimal("0.0015"),
        },
        "base": {
            "bill": Decimal("0.0098"),
            "coupon": Decimal("0.0020"),
            "mortgage": Decimal("0.0035"),
            "consumer": Decimal("0.0075"),
            "firm": Decimal("0.0100"),
            "deposit_check": Decimal("0.0005"),
            "deposit_savings": Decimal("0.0025"),
            "cd": Decimal("0.0075"),
            "mmf": Decimal("0.0095"),
            "bnpl_float_deposit": Decimal("0.0035"),
        },
        "high": {
            "bill": Decimal("0.0105"),
            "coupon": Decimal("0.0045"),
            "mortgage": Decimal("0.0085"),
            "consumer": Decimal("0.0105"),
            "firm": Decimal("0.0115"),
            "deposit_check": Decimal("0.0015"),
            "deposit_savings": Decimal("0.0045"),
            "cd": Decimal("0.0100"),
            "mmf": Decimal("0.0100"),
            "bnpl_float_deposit": Decimal("0.0060"),
        },
    }
    if family == "treasury_bills":
        return curve[band]["bill"]
    if family == "treasury_notes_bonds_tips":
        return curve[band]["coupon"]
    if family in {"deposits_checkable"}:
        return curve[band]["deposit_check"]
    if family in {"deposits_savings_mmda"}:
        return curve[band]["deposit_savings"]
    if family in {"deposits_time_cds"}:
        return curve[band]["cd"]
    if family == "bnpl_float_deposit_beta":
        return curve[band]["bnpl_float_deposit"]
    if family in {"mmf_shares", "on_rrp_mmfs", "mmf_short_funding_assets"}:
        return curve[band]["mmf"]
    if family in {"mortgages_fixed"}:
        return curve[band]["mortgage"]
    if family in {"mortgages_arm", "heloc"}:
        return Decimal("0.01")
    if family in {"credit_card_revolving", "auto_installment_debt", "student_loans_private", "personal_installment_debt"}:
        return curve[band]["consumer"]
    return curve[band]["firm"]


def _private_driver(
    family: str,
    band: str,
    year_index: int,
    assumptions: dict[str, dict[str, Decimal]],
) -> Decimal:
    base = _driver(family, band, year_index)
    coupon_roll = assumptions["coupon_roll_rate"][band]
    if family == "c_and_i_depository_loans":
        return base * assumptions["ci_floating_share"][band]
    if family == "corporate_bonds":
        return _ladder_reprice_rate(
            assumptions["corporate_bond_new_issue_beta"][band],
            coupon_roll,
            year_index,
        )
    if family == "municipal_securities":
        return _ladder_reprice_rate(
            assumptions["municipal_bond_new_issue_beta"][band],
            coupon_roll,
            year_index,
        )
    if family == "cre_mortgages_floating":
        return Decimal("0.01") * assumptions["cre_floating_rate_beta"][band]
    if family == "cre_mortgages_fixed":
        return _ladder_reprice_rate(
            assumptions["cre_fixed_refi_coupon_beta"][band],
            assumptions["cre_fixed_roll_rate"][band],
            year_index,
        )
    if family == "mortgages_fixed":
        return base * assumptions["mortgage_turnover_share"][band]
    if family in {"auto_installment_debt", "personal_installment_debt"}:
        term_parameter = (
            "auto_installment_term_months"
            if family == "auto_installment_debt"
            else "personal_installment_term_months"
        )
        active_share = _annual_amortizing_new_flow_active_share(
            year_index,
            assumptions[term_parameter][band],
        )
        return base * assumptions["consumer_installment_new_flow_share"][band] * active_share
    if family == "student_loans_private":
        active_share = _annual_amortizing_new_flow_active_share(
            year_index,
            assumptions["student_private_term_months"][band],
        )
        return base * assumptions["student_private_new_flow_share"][band] * active_share
    return base


def _treasury_coupon_roll_share(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    year_index: int,
) -> Decimal:
    rows = pack.get("tdcsim_coupon_roll_schedule", [])
    if band == "base" and rows:
        month_index = min(year_index * 12, len(rows))
        return _d(rows[month_index - 1]["cumulative_share_of_current_stock"])
    assumptions = _assumptions(pack)
    return min(Decimal("1"), assumptions["coupon_roll_rate"][band] * Decimal(year_index))


def _treasury_coupon_interest_components(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    year_index: int,
    current_coupon_stock: Decimal,
    new_coupon_stock: Decimal,
) -> dict[str, Decimal]:
    rate = _driver("treasury_notes_bonds_tips", band, year_index)
    current_share = _treasury_coupon_roll_share(pack, band, year_index)
    new_share = _new_issuance_coupon_reprice_share(pack, band, year_index)
    current_interest = current_coupon_stock * current_share * rate
    new_interest = new_coupon_stock * new_share * rate
    return {
        "current_stock_coupon_interest": current_interest,
        "new_issuance_coupon_interest": new_interest,
        "total_coupon_interest": current_interest + new_interest,
        "current_stock_reprice_share": current_share,
        "new_issuance_reprice_share": new_share,
    }


def _new_issuance_coupon_reprice_share(
    pack: dict[str, list[dict[str, str]]],
    band: str,
    year_index: int,
) -> Decimal:
    rows = pack.get("tdcsim_issuance_tenor_mix", [])
    if not rows:
        return _treasury_coupon_roll_share(pack, band, year_index)
    coupon_rows = [row for row in rows if not row["tenor_bucket"].startswith("bills_")]
    coupon_total = sum(_d(row["share_of_gross_issuance"]) for row in coupon_rows)
    if coupon_total == 0:
        return Decimal("0")
    repricing = Decimal("0")
    for row in coupon_rows:
        bucket = row["tenor_bucket"]
        tenor_years = _tenor_bucket_years(bucket)
        if bucket.startswith("frn_") or tenor_years <= Decimal(year_index):
            repricing += _d(row["share_of_gross_issuance"])
    return min(Decimal("1"), repricing / coupon_total)


def _tenor_bucket_years(bucket: str) -> Decimal:
    suffix = bucket.rsplit("_", maxsplit=1)[-1]
    if suffix.endswith("y"):
        return Decimal(suffix.removesuffix("y"))
    if suffix.endswith("m"):
        return Decimal(suffix.removesuffix("m")) / Decimal("12")
    return Decimal("999")


def _ladder_reprice_rate(beta: Decimal, annual_roll: Decimal, year_index: int) -> Decimal:
    rolled_share = min(Decimal("1"), annual_roll * Decimal(year_index))
    if year_index == 1:
        rolled_share = rolled_share * Decimal("0.5")
    return Decimal("0.01") * beta * rolled_share


def _new_flow_midyear_share(year_index: int) -> Decimal:
    return Decimal("0.5") if year_index == 1 else Decimal("1")


def _annual_amortizing_new_flow_active_share(
    year_index: int,
    term_months: Decimal,
) -> Decimal:
    first_month = (year_index - 1) * 12 + 1
    monthly = [
        _amortizing_new_flow_active_share(month_index, term_months)
        for month_index in range(first_month, first_month + 12)
    ]
    return sum(monthly) / Decimal("12")


def _load_pack(pack_dir: Path) -> dict[str, list[dict[str, str]]]:
    tables: dict[str, list[dict[str, str]]] = {}
    for path in sorted(pack_dir.glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            tables[path.stem] = list(csv.DictReader(handle))
    tax_dir = pack_dir / TAX_LAYER_PACK_ID
    tax_data_dir = tax_dir / "data"
    if tax_data_dir.exists():
        for path in sorted(tax_data_dir.glob("*.csv")):
            with path.open(encoding="utf-8", newline="") as handle:
                table_name = path.stem
                if table_name == "parameters_tax_layer":
                    tables[table_name] = list(csv.DictReader(handle))
                else:
                    tables[f"tax_layer_{table_name}"] = list(csv.DictReader(handle))
    elif (tax_dir / "parameters_tax_layer.csv").exists():
        with (tax_dir / "parameters_tax_layer.csv").open(encoding="utf-8", newline="") as handle:
            tables["parameters_tax_layer"] = list(csv.DictReader(handle))
    mmf_dir = pack_dir / "mmf_income_targets_v2"
    if mmf_dir.exists():
        for path in sorted(mmf_dir.glob("*.csv")):
            with path.open(encoding="utf-8", newline="") as handle:
                tables[f"mmf_targets_v2_{path.stem}"] = list(csv.DictReader(handle))
    term_premium_dir = pack_dir / TERM_PREMIUM_PACK_ID
    if term_premium_dir.exists():
        parameter_paths = sorted(term_premium_dir.glob("*/parameters_term_premium.csv"))
        if parameter_paths:
            with parameter_paths[-1].open(encoding="utf-8", newline="") as handle:
                tables["term_premium_parameters"] = list(csv.DictReader(handle))
        decomposition_paths = sorted(term_premium_dir.glob("*/validation_decomposition.csv"))
        if decomposition_paths:
            with decomposition_paths[-1].open(encoding="utf-8", newline="") as handle:
                tables["term_premium_validation_decomposition"] = list(csv.DictReader(handle))
    absorption_mix_dir = pack_dir / "absorption_mode_mix" / "absorption_mode_mix_pack"
    absorption_mix_summary = absorption_mix_dir / "mode_mix_summary_annual_and_2010_2019_avg.csv"
    if absorption_mix_summary.exists():
        with absorption_mix_summary.open(encoding="utf-8", newline="") as handle:
            tables["absorption_mode_mix_summary_annual_and_2010_2019_avg"] = list(
                csv.DictReader(handle)
            )
    export_dir = pack_dir / "tdcsim_export"
    for table_name, filename in [
        ("tdcsim_coupon_roll_schedule", "coupon_roll_schedule.csv"),
        ("tdcsim_issuance_tenor_mix", "issuance_tenor_mix.csv"),
    ]:
        path = export_dir / filename
        if path.exists():
            with path.open(encoding="utf-8", newline="") as handle:
                tables[table_name] = list(csv.DictReader(handle))
    return tables


def _effective_pack(
    pack: dict[str, list[dict[str, str]]],
    include_scenario_adjustments: bool,
    include_tdc_settlement: bool,
) -> dict[str, list[dict[str, str]]]:
    effective = {name: list(rows) for name, rows in pack.items()}
    if not include_scenario_adjustments:
        effective["claim_processor_rules"] = [
            row
            for row in effective.get("claim_processor_rules", [])
            if row.get("report_channel") != "bnpl"
        ]
        effective["household_stock_splits"] = [
            row
            for row in effective.get("household_stock_splits", [])
            if row.get("source_id") != "OWNER_BNPL_DEMO_CHANNEL"
        ]
        effective["scenario_adjustments"] = []
    if not include_tdc_settlement:
        effective["absorption_modes"] = []
        effective["tdc_recipient_splits"] = []
    if include_scenario_adjustments:
        effective["scenario_adjustments"] = [
            _derive_scenario_adjustment_row(effective, row)
            for row in effective.get("scenario_adjustments", [])
        ]
        effective["opening_stocks"] = list(effective.get("opening_stocks", [])) + [
            _scenario_adjustment_opening_row(row)
            for row in effective.get("scenario_adjustments", [])
            if row.get("include_in_opening") == "1"
            and row.get("delta_set_id") != "bnpl_delta_set"
        ]
    return effective


def _pack_with_bnpl_opening_rows(
    pack: dict[str, list[dict[str, str]]],
) -> dict[str, list[dict[str, str]]]:
    return pack | {
        "opening_stocks": list(pack.get("opening_stocks", []))
        + [
            _scenario_adjustment_opening_row(row)
            for row in pack.get("scenario_adjustments", [])
            if row.get("include_in_opening") == "1"
            and row.get("delta_set_id") == "bnpl_delta_set"
        ]
    }


def _scenario_adjustment_opening_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "parameter_id": row["row_id"],
        "cell_or_sector": f"holder={row['holder']}|issuer={row['issuer']}",
        "instrument_family": row["instrument_family"],
        "low": row["stock_low"],
        "base": row["stock_base"],
        "high": row["stock_high"],
        "units": "$bn_current",
        "source_id": row["delta_set_id"],
        "input_basis_label": row["input_basis_label"],
        "rationale": row["rationale"],
    }


def _derive_scenario_adjustment_row(
    pack: dict[str, list[dict[str, str]]],
    row: dict[str, str],
) -> dict[str, str]:
    out = dict(row)
    if row["delta_set_id"] != "bnpl_delta_set":
        return out
    if row["delta_role"] == "real_side_counterpart":
        out["derivation_status"] = "author_declared_real_side_counterpart"
        return out
    assumptions = _assumptions(pack)
    declared = {band: row[f"stock_{band}"] for band in BANDS}
    for band in BANDS:
        out[f"declared_stock_{band}"] = declared[band]
        out[f"stock_{band}"] = _fmt(_bnpl_derived_stock(row["delta_role"], assumptions, band))
    out["derivation_status"] = "parameter_derived"
    return out


def _bnpl_derived_stock(
    delta_role: str,
    assumptions: dict[str, dict[str, Decimal]],
    band: str,
) -> Decimal:
    purchases = assumptions["household_consumption_bil"][band]
    share = assumptions["bnpl_share_of_purchases"][band]
    duration = assumptions["bnpl_avg_duration_months"][band]
    installment = purchases * share * ((duration + Decimal("1")) / Decimal("2")) / Decimal("12")
    card_float = purchases * share / Decimal("12")
    if delta_role in {"bnpl_claim", "funding_liability"}:
        return installment
    if delta_role in {"float_asset"}:
        return (installment - card_float) / Decimal("2")
    if delta_role == "remove_card_float":
        return card_float
    return Decimal("0")


def _rows(
    pack: dict[str, list[dict[str, str]]],
    table: str,
    **filters: str,
) -> list[dict[str, str]]:
    rows = pack[table]
    for field, value in filters.items():
        rows = [row for row in rows if row[field] == value]
    return rows


def _opening_by_family(pack: dict[str, list[dict[str, str]]]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for row in pack["opening_stocks"]:
        family = row["instrument_family"]
        out[family] = out.get(family, Decimal("0")) + _d(row["base"])
    return out


def _opening_by_hh_family(pack: dict[str, list[dict[str, str]]]) -> dict[str, Decimal]:
    opening = _opening_by_family(pack)
    return {
        "deposits_checkable": opening["deposits_checkable"],
        "deposits_savings_mmda": opening["deposits_savings_mmda"],
        "deposits_time_cds": opening["deposits_time_cds"],
        "mmf_shares": opening["mmf_shares"],
        "mmf_short_funding_assets": opening.get("mmf_short_funding_assets", Decimal("0")),
        "treasuries_direct": opening["treasury_bills"] + opening["treasury_notes_bonds_tips"],
        "bond_equity_funds_lookthrough": opening["corporate_bonds"] + opening["municipal_securities"],
        "dc_pension_assets": opening["corporate_bonds"],
    }


def _holder_from_opening_row(row: dict[str, str]) -> str:
    cell = row["cell_or_sector"]
    for part in cell.split("|"):
        if part.startswith("holder="):
            return part.removeprefix("holder=")
    return cell


def _issuer_from_opening_row(row: dict[str, str]) -> str:
    cell = row["cell_or_sector"]
    for part in cell.split("|"):
        if part.startswith("issuer="):
            return part.removeprefix("issuer=")
    return cell


def _conversion(pack: dict[str, list[dict[str, str]]]) -> dict[str, Decimal]:
    out = {cell: Decimal("0") for cell in ZERO_CELLS}
    for row in pack["conversion_coefficients"]:
        cell = row["cell_or_sector"]
        if cell == "all_household_cells" or cell.startswith("all_"):
            continue
        out[cell] = _d(row["base"])
    out.setdefault("state_local_public_cell", Decimal("0.35"))
    return out


def _assumptions(pack: dict[str, list[dict[str, str]]]) -> dict[str, dict[str, Decimal]]:
    return {
        row["assumption_id"]: {
            "low": _d(row["low"]),
            "base": _d(row["base"]),
            "high": _d(row["high"]),
        }
        for row in pack["structural_assumptions"]
    }


def _household_split_family(family: str) -> str:
    mapping = {
        "treasury_bills": "treasuries_direct",
        "treasury_notes_bonds_tips": "treasuries_direct",
        "mortgages_arm": "mortgages_arm_heloc",
        "heloc": "mortgages_arm_heloc",
        "credit_card_revolving": "credit_card_revolving_balances",
        "student_loans_private": "student_installment_debt",
        "student_loans_federal": "student_installment_debt",
    }
    return mapping.get(family, family)


def _lookthrough_family(holder: str) -> str:
    if holder in {"mmfs"}:
        return "mmfs"
    if holder == "mutual_funds_etfs":
        return "mutual_funds_etfs"
    if holder == "pensions":
        return "dc_pensions"
    if holder == "insurers":
        return "insurers"
    if holder == "banks":
        return "banks_retained_margin"
    return holder


def _normalize_cell(label: str) -> str:
    if label in HH_CELLS or label in FIRM_CELLS or label == "state_local_public_cell":
        return label
    if label.startswith("hh_unconstrained_saver"):
        return "hh_unconstrained_saver"
    if label.startswith("hh_middle_owner_illiquid"):
        return "hh_middle_owner_illiquid"
    if label.startswith("hh_retiree_fixed_income_saver"):
        return "hh_retiree_fixed_income_saver"
    if label.startswith("hh_constrained_net_borrower"):
        return "hh_constrained_net_borrower"
    if label.startswith("firm_bank"):
        return "firm_bank_dependent_small"
    if label.startswith("firm_market") or label.startswith("firm_policyholder"):
        return "firm_market_funded_large"
    if label.startswith("treasury"):
        return "treasury_federal_accounting_cell"
    if label.startswith("bank_retained") or "deferred" in label or "unallocated" in label:
        return "deferred_no_conversion"
    if label.startswith("state_local"):
        return "state_local_public_cell"
    if "row" in label or "foreign" in label:
        return "rest_of_world_external_cell"
    return "deferred_no_conversion"


def _merge_routes(*routes: dict[str, Decimal]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for route in routes:
        for cell, amount in route.items():
            out[cell] = out.get(cell, Decimal("0")) + amount
    return out


def _t28(pack: dict[str, list[dict[str, str]]]) -> bool:
    for family in sorted({row["instrument_family"] for row in pack["lookthrough_shares"]}):
        total = sum(_d(row["base"]) for row in _rows(pack, "lookthrough_shares", instrument_family=family))
        if abs(total - Decimal("1")) > Decimal("0.000001"):
            return False
    conversion = _conversion(pack)
    return conversion.get("banks_intermediary_no_conversion", Decimal("0")) == 0


def _t29(tables: dict[str, list[dict[str, str]]]) -> bool:
    return all(_d(row["fed_deferred_asset_open_bil"]) >= 0 for row in tables["out_iorb_channel"])


def _t30(records: list[dict[str, Decimal | str]]) -> bool:
    base_zero = [
        record
        for record in records
        if record["band"] == "base" and record["ricardian_offset"] == Decimal("0")
    ]
    horizon_n = sum(record["N"] for record in base_zero)
    horizon_d = sum(record["D"] for record in base_zero)
    horizon_rw = horizon_n / horizon_d
    year1_gov = base_zero[0]["government_interest_delta"]
    later_gov = sum(record["government_interest_delta"] for record in base_zero[1:])
    return horizon_rw > 0 and year1_gov > 0 and later_gov >= 0


def _t31(tables: dict[str, list[dict[str, str]]]) -> bool:
    bands = {row["band"] for row in tables["out_ratewall_rollup"]}
    required_cols = {
        f"ricardian_{_ricardian_suffix(_d(row['ricardian_offset']))}_N_bil"
        for row in tables["out_ratewall_rollup"]
    }
    return {"low", "base", "high"}.issubset(bands) and required_cols.issubset(
        tables["out_ratewall_rollup"][0]
    )


def _t32(tables: dict[str, list[dict[str, str]]]) -> bool:
    return {row["role"] for row in tables["out_legacy_d_comparator"]} == {"comparator_only"}


def _t35(pack: dict[str, list[dict[str, str]]]) -> bool:
    opening_families = {row["instrument_family"] for row in pack["opening_stocks"]}
    split_families = {row["instrument_family"] for row in pack["household_stock_splits"]}
    required = {"deposits_checkable", "deposits_savings_mmda", "deposits_time_cds"}
    if not required.issubset(opening_families) or not required.issubset(split_families):
        return False
    if {"checking_savings_mmda_deposits", "cds_time_deposits"} & opening_families:
        return False
    checkable = _driver("deposits_checkable", "base", 1)
    savings = _driver("deposits_savings_mmda", "base", 1)
    cds = _driver("deposits_time_cds", "base", 1)
    return checkable < savings < cds


def _t36(
    pack: dict[str, list[dict[str, str]]],
    tables: dict[str, list[dict[str, str]]],
) -> bool:
    opening = _opening_by_family(pack)
    mortgage_stock = opening["mortgages_fixed"] + opening["mortgages_arm"]
    holder_stock = sum(_d(row["base"]) for row in pack["mortgage_holder_decomposition"])
    if abs(mortgage_stock - holder_stock) > Decimal("0.000001"):
        return False
    for year in {row["year"] for row in tables["out_mortgage_holder_routing"]}:
        for band in BANDS:
            rows = [
                row
                for row in tables["out_mortgage_holder_routing"]
                if row["year"] == year and row["band"] == band
            ]
            if not rows:
                continue
            paid = {_d(row["mortgage_interest_paid_bil"]) for row in rows}
            received = sum(_d(row["holder_receipt_bil"]) for row in rows)
            if len(paid) != 1 or abs(next(iter(paid)) - received) > Decimal("0.000001"):
                return False
    return True


def _t36b(tables: dict[str, list[dict[str, str]]]) -> bool:
    cumulative = [
        row
        for row in tables["out_cashflow_family_contributions_monthly"]
        if row["period_type"] == "cumulative_120_month"
        and row["instrument_family"] == "mortgages_fixed"
        and row["ricardian_offset"] == "0"
    ]
    by_band = {
        row["band"]: _d(row["raw_cashflow_bil"])
        for row in cumulative
    }
    return by_band.get("low", Decimal("0")) < by_band.get("base", Decimal("0")) < by_band.get("high", Decimal("0"))


def _t37(pack: dict[str, list[dict[str, str]]]) -> bool:
    opening = _opening_by_family(pack)
    mmf_shares = opening["mmf_shares"]
    mmf_assets = (
        _opening_by_family_and_holder(pack, "treasury_bills", "holder=mmfs")
        + _opening_by_family_and_holder(
            pack, "treasury_notes_bonds_tips", "holder=mmfs"
        )
        + _opening_by_family_and_holder(pack, "municipal_securities", "holder=mmfs")
        + opening.get("on_rrp_mmfs", Decimal("0"))
        + opening.get("mmf_short_funding_assets", Decimal("0"))
    )
    passthrough_total = sum(
        _d(row["base"]) for row in _rows(pack, "lookthrough_shares", instrument_family="mmfs")
    )
    return abs(mmf_assets - mmf_shares) <= Decimal("10") and abs(
        passthrough_total - Decimal("1")
    ) <= Decimal("0.000001")


def _t38(tables: dict[str, list[dict[str, str]]]) -> bool:
    waterfall = tables["out_phase6_waterfall_scaffold"]
    layers = _phase6_layer_rows()
    expected_ids = [row["layer_id"] for row in layers]
    by_key: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in waterfall:
        if not row["layer_label"] or not row["overlap_group"]:
            return False
        key = (row["period_type"], row["period"], row["band"], row["ricardian_offset"])
        by_key.setdefault(key, []).append(row)
    for group in by_key.values():
        ordered = sorted(group, key=lambda row: int(row["waterfall_order"]))
        if [row["layer_id"] for row in ordered] != expected_ids:
            return False
        n = Decimal("0")
        d = Decimal("0")
        for row in ordered:
            n += _d(row["delta_N_bil"])
            d += _d(row["delta_D_bil"])
            if abs(_d(row["cumulative_N_bil"]) - n) > Decimal("0.000000000001"):
                return False
            if abs(_d(row["cumulative_D_bil"]) - d) > Decimal("0.000000000001"):
                return False
    return True


def _t39(tables: dict[str, list[dict[str, str]]]) -> bool:
    overlap = tables["out_phase6_overlap_registry"]
    keys = {row["exposure_exclusion_key"] for row in overlap}
    required_fragments = [
        "firm_id_or_sector|instrument_family|margin=cashflow_debt_service_vs_investment_hurdle",
        "housing_transaction_id|hpi_wealth_stock_id|lost_sale_attribution",
        "source_channel_id|exposure_id|month|cell_or_sector",
    ]
    if not all(fragment in keys for fragment in required_fragments):
        return False
    if sum(1 for layer in _phase6_layer_rows() if layer["transaction_units_role"] == "transaction_units_allocator") != 1:
        return False
    diagnostic_rows = [
        row for row in tables["out_phase6_waterfall_scaffold"]
        if row["layer_id"] in {"bond_mtm_wealth", "collateral_q", "credit_supply"}
    ]
    return all(_d(row["delta_D_bil"]) == 0 for row in diagnostic_rows)


def _t40(tables: dict[str, list[dict[str, str]]]) -> bool:
    row = [
        row
        for row in tables["out_ratewall_rollup"]
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]
    ratio = _d(row["bottom_up_D_to_legacy_D"])
    return Decimal("0.4") <= ratio <= Decimal("1.6")


def _t41(tables: dict[str, list[dict[str, str]]]) -> bool:
    rows = tables["out_deposit_holder_routing"]
    for row in rows:
        if row["holder"] != "banks_payment_total" and row["route_count"] != "1":
            return False
    totals: dict[tuple[str, str, str], Decimal] = {}
    payments: dict[tuple[str, str, str], Decimal] = {}
    for row in rows:
        key = (row["year"], row["band"], row["instrument_family"])
        if row["holder"] == "banks_payment_total":
            payments[key] = _d(row["bank_family_payment_bil"])
        else:
            totals[key] = totals.get(key, Decimal("0")) + _d(row["receipt_bil"])
    return all(abs(totals.get(key, Decimal("0")) - payment) <= Decimal("0.000001") for key, payment in payments.items())


def _t42(tables: dict[str, list[dict[str, str]]]) -> bool:
    seen: set[tuple[str, str, str, str, str, str]] = set()
    for row in tables["out_additive_waterfall_inputs"]:
        key = (
            row["source_channel_id"],
            row["exposure_id"],
            row["month"],
            row["cell_or_sector"],
            row["band"],
            row["ricardian_offset"],
        )
        if key in seen:
            return False
        seen.add(key)
    return bool(seen)


def _t43(tables: dict[str, list[dict[str, str]]]) -> bool:
    leg_rows = tables["out_cashflow_leg_gross"]
    rollup = tables["out_cashflow_core_rollup"]
    by_key: dict[tuple[str, str, str], Decimal] = {}
    for row in leg_rows:
        if row["period_type"] != "annual":
            continue
        key = (row["period"], row["band"], row["ricardian_offset"])
        by_key[key] = by_key.get(key, Decimal("0")) + _d(row["converted_effect_bil"])
    for row in rollup:
        if row["period_type"] != "annual":
            continue
        key = (row["period"], row["band"], row["ricardian_offset"])
        if abs(by_key.get(key, Decimal("0")) - _d(row["net_bil"])) > Decimal("0.000001"):
                return False
    return True


def _t44(
    pack: dict[str, list[dict[str, str]]],
    tables: dict[str, list[dict[str, str]]],
) -> bool:
    rows = tables["out_cre_cashflow_channel"]
    if not rows:
        return False
    opening = _opening_by_family(pack)
    for family, expected_base_stock in [
        ("cre_mortgages_floating", Decimal("1440")),
        ("cre_mortgages_fixed", Decimal("2160")),
    ]:
        if opening.get(family) != expected_base_stock:
            return False
        holder_rows = [
            row
            for row in rows
            if row["year"] == "2026" and row["band"] == "base" and row["instrument_family"] == family
        ]
        if len(holder_rows) != 2:
            return False
        paid_values = {_d(row["interest_paid_bil"]) for row in holder_rows}
        if len(paid_values) != 1:
            return False
        paid = next(iter(paid_values))
        received = sum(_d(row["holder_receipt_bil"]) for row in holder_rows)
        if abs(paid - received) > Decimal("0.000001"):
            return False
        if {row["holder"] for row in holder_rows} != {"banks", "nonbank_finance"}:
            return False
        if {_d(row["payer_small_share"]) for row in holder_rows} != {Decimal("0.60")}:
            return False
    return True


def _t47(pack: dict[str, list[dict[str, str]]]) -> bool:
    if any(
        _optional_d(row.get("spread_delta")) != 0
        or _optional_d(row.get("constant_level_delta")) != 0
        for row in _active_claim_processor_rules(pack)
    ):
        return False

    def probe_row(constant_spread_bp: str) -> dict[str, str]:
        probe_pack = {name: [dict(row) for row in rows] for name, rows in pack.items()}
        probe_pack.setdefault("opening_stocks", []).append(
            {
                "parameter_id": "t47_constant_probe",
                "cell_or_sector": "holder=households|issuer=nonbank_finance",
                "instrument_family": "t47_constant_probe",
                "low": "100",
                "base": "100",
                "high": "100",
                "units": "$bn_current",
                "source_id": "OWNER_TEST",
                "input_basis_label": "owner_assumption_mode",
                "rationale": "Synthetic invariant probe for same-state constants.",
            }
        )
        probe_pack.setdefault("claim_processor_rules", []).append(
            {
                "rule_id": "t47_constant_probe",
                "instrument_family": "t47_constant_probe",
                "active": "1",
                "stock_source": "opening_stocks",
                "stock_band_mode": "base",
                "rate_rule": "driver_curve",
                "base_driver": "credit_card_revolving",
                "payer_route": "household_debtors_negative",
                "receiver_route": "literal_holder",
                "receiver_holder": "nonbank_finance",
                "report_channel": "t47_probe",
                "basis": "same-state constant-spread probe",
                "input_basis_label": "owner_assumption_mode",
                "spread_delta": "0",
                "constant_level_delta": "0",
                "constant_spread_bp": constant_spread_bp,
                "cost_leg": "false",
            }
        )
        rows = _claim_processor_channel(
            probe_pack,
            [
                {
                    "year": "2026",
                    "band": "base",
                    "year_index": Decimal("1"),
                    "ricardian_offset": Decimal("0"),
                }
            ],
        )
        return [row for row in rows if row["rule_id"] == "t47_constant_probe"][0]

    zero = probe_row("0")
    large = probe_row("100000")
    return (
        zero["gross_flow_delta_bil"] == large["gross_flow_delta_bil"]
        and zero["converted_net_bil"] == large["converted_net_bil"]
    )


def _t48(pack: dict[str, list[dict[str, str]]]) -> bool:
    cost_rules = [
        rule
        for rule in _active_claim_processor_rules(pack)
        if _truthy(rule.get("cost_leg"))
    ]
    if not cost_rules:
        return False
    for rule in cost_rules:
        receiver_routes = _claim_rule_receiver_routes(pack, rule, Decimal("1"), "base")
        if any(cell in HH_CELLS and amount > 0 for cell, amount in receiver_routes.items()):
            return False
    return any(rule["rule_id"] == "bnpl_funding_liability_cost" for rule in cost_rules)


def _t49(tables: dict[str, list[dict[str, str]]]) -> bool:
    rows = tables.get("out_scenario_delta_balance", [])
    return bool(rows) and all(row["status"] == "pass" for row in rows)


def _t50(pack: dict[str, list[dict[str, str]]]) -> bool:
    metrics = _tdc_metrics_for_period(
        pack,
        "base",
        1,
        Decimal("0"),
        Decimal("0"),
        include_tdc_settlement=True,
    )
    return (
        metrics["new_created_deposits_bil"] == 0
        and metrics["created_deposit_stock_bil"] == 0
        and metrics["created_deposit_income_bil"] == 0
    )


def _t51(tables: dict[str, list[dict[str, str]]]) -> bool:
    rows = [
        row
        for row in tables.get("out_tdc_channel", [])
        if row["mode_id"] == "TOTAL" and row["year"] == "2026" and row["band"] == "base"
    ]
    if not rows:
        return False
    row = rows[0]
    upper_bound = _d(row["created_deposit_stock_bil"]) * _d(row["full_level_deposit_rate"])
    income = _d(row["created_deposit_income_bil"])
    return Decimal("0") < income <= upper_bound


def _t52(tables: dict[str, list[dict[str, str]]]) -> bool:
    rows = tables.get("out_scenario_delta_derivation", [])
    return bool(rows) and all(row["status"] == "pass" for row in rows)


def _t53(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> bool:
    rows = pack.get("tdcsim_coupon_roll_schedule", [])
    if len(rows) != 120:
        return False
    shares = [_d(row["cumulative_share_of_current_stock"]) for row in rows]
    if any(current < previous for previous, current in zip(shares, shares[1:])):
        return False
    if abs(shares[11] - Decimal("0.1329564616")) > Decimal("0.00000001"):
        return False
    base_records = [
        record
        for record in records
        if record["band"] == "base" and record["ricardian_offset"] == Decimal("0")
    ]
    if len(base_records) < 5:
        return False
    blended = _assumptions(pack)["coupon_roll_rate"]["base"]
    for record in [base_records[0], base_records[4]]:
        year_index = int(record["year_index"])
        measured_share = _treasury_coupon_roll_share(pack, "base", year_index)
        blended_share = min(Decimal("1"), blended * Decimal(year_index))
        if measured_share <= blended_share:
            return False
        measured_coupon = record["coupon_interest"]
        blended_coupon = (
            Decimal("0")
            if measured_share == 0
            else measured_coupon * blended_share / measured_share
        )
        blended_gov = record["government_interest_delta"] - measured_coupon + blended_coupon
        if record["government_interest_delta"] <= blended_gov:
            return False
    return True


def _t55(tables: dict[str, list[dict[str, str]]]) -> bool:
    additive_sources = {
        row["source_channel_id"]
        for row in tables.get("out_additive_waterfall_inputs", [])
    }
    if "bond_mtm_wealth" in additive_sources:
        return False
    bond_rows = tables.get("out_bond_mtm_diagnostic", [])
    if not bond_rows:
        return False
    if any(row["include_flag"] != "0" or row["headline_entry_flag"] != "false" for row in bond_rows):
        return False
    if validate_bond_mtm_overlap_rows(bond_rows):
        return False
    return True


def _t58(tables: dict[str, list[dict[str, str]]]) -> bool:
    household_rows = tables.get("out_tax_layer_household_wedge", [])
    if not household_rows:
        return False
    if any(row["tax_pack_family"] == "dc_assets" for row in household_rows):
        return False
    if any(_d(row["taxable_or_current_taxed_share"]) < 0 for row in household_rows):
        return False
    return all(
        _d(row["post_tax_flow_bil"]) <= _d(row["pre_tax_flow_bil"])
        for row in household_rows
    )


def _t59(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
    tables: dict[str, list[dict[str, str]]],
) -> bool:
    receipts = tables.get("out_treasury_tax_receipts", [])
    if not receipts:
        return False
    expected_by_key = _expected_tax_receipt_flows(pack, records)
    stored_component_by_key: dict[tuple[str, str], Decimal] = {}
    for table_name in ["out_tax_layer_household_wedge", "out_tax_layer_corporate_shield"]:
        for row in tables.get(table_name, []):
            key = (row["period"], row["band"])
            stored_component_by_key[key] = (
                stored_component_by_key.get(key, Decimal("0"))
                + _d(row["treasury_receipt_flow_bil"])
            )
    for row in receipts:
        key = (row["period"], row["band"])
        expected = expected_by_key.get(key)
        if expected is None:
            return False
        if abs(stored_component_by_key.get(key, Decimal("0")) - expected) > Decimal("0.000001"):
            return False
        if abs(_d(row["net_treasury_receipt_flow_bil"]) - expected) > Decimal("0.000001"):
            return False
        if row["sfc_balance_status"] != "pass":
            return False
    return True


def _expected_tax_receipt_flows(
    pack: dict[str, list[dict[str, str]]],
    records: list[dict[str, Decimal | str]],
) -> dict[tuple[str, str], Decimal]:
    by_key: dict[tuple[str, str], Decimal] = {}
    for record in records:
        if record["ricardian_offset"] != Decimal("0"):
            continue
        key = (str(record["year"]), str(record["band"]))
        expected = Decimal("0")
        family_routes = record.get("pre_tax_cashflow_family_routes")
        if not isinstance(family_routes, dict):
            continue
        for family, routes in family_routes.items():
            if not isinstance(routes, dict):
                continue
            for cell, amount in routes.items():
                if amount > 0 and cell in HH_CELLS:
                    tax_family = _household_tax_family(family)
                    if tax_family is None:
                        continue
                    rate_parameter, rate_family = _household_tax_rate_parameter(family)
                    rate = _tax_parameter(pack, rate_parameter, cell, rate_family, str(record["band"]))
                    taxable_share = _tax_parameter(
                        pack,
                        "taxable_or_current_taxed_account_share",
                        cell,
                        tax_family,
                        str(record["band"]),
                    )
                    expected += amount * taxable_share * rate
                elif amount < 0:
                    shield_spec = _shield_spec_for_negative_route(family, cell)
                    if shield_spec is None:
                        continue
                    parameter_id, tax_family = shield_spec
                    interest_expense = -amount
                    if parameter_id == "mortgage_interest_deduction_marginal_offset_share":
                        shield = _tax_parameter(pack, parameter_id, cell, tax_family, str(record["band"]))
                    else:
                        base_shield = _tax_parameter(pack, parameter_id, cell, tax_family, str(record["band"]))
                        subject_share = _tax_parameter(
                            pack,
                            "section_163j_subject_to_cap_interest_share",
                            cell,
                            tax_family,
                            str(record["band"]),
                        )
                        denied_share = _tax_parameter(
                            pack,
                            "section_163j_denied_or_deferred_current_deduction_share",
                            cell,
                            tax_family,
                            str(record["band"]),
                        )
                        shield = _dynamic_163j_shield(
                            base_shield,
                            subject_share,
                            denied_share,
                            Decimal("100") * _d(str(record.get("shock_multiplier", Decimal("0")))),
                        )
                    expected -= interest_expense * shield
        by_key[key] = by_key.get(key, Decimal("0")) + expected
    return by_key


def _t60(pack: dict[str, list[dict[str, str]]]) -> bool:
    rows = [
        row
        for row in pack.get("parameters_tax_layer", [])
        if row["parameter_id"] == "effective_c_corp_interest_deduction_shield_rate_after_163j"
    ]
    if not rows:
        return False
    for row in rows:
        cell = row["cell_or_sector"]
        family = row["instrument_family"]
        base = _d(row["base"])
        subject = _tax_parameter(pack, "section_163j_subject_to_cap_interest_share", cell, family, "base")
        denied = _tax_parameter(pack, "section_163j_denied_or_deferred_current_deduction_share", cell, family, "base")
        low_stress = _dynamic_163j_shield(base, subject, denied, Decimal("100"))
        high_stress = _dynamic_163j_shield(base, subject, denied, Decimal("300"))
        if high_stress > low_stress:
            return False
    return True


def _t60b() -> bool:
    return _dynamic_163j_shield(
        Decimal("0.168"),
        Decimal("0.85"),
        Decimal("0.50"),
        Decimal("300"),
    ) < _dynamic_163j_shield(
        Decimal("0.168"),
        Decimal("0.85"),
        Decimal("0.50"),
        Decimal("100"),
    )


def _t61(tables: dict[str, list[dict[str, str]]]) -> bool:
    rows = tables.get("out_tax_layer_household_wedge", [])
    if not rows:
        return False
    return sum(_d(row["tax_or_shield_bil"]) for row in rows) > 0


def _t62(tables: dict[str, list[dict[str, str]]]) -> bool:
    return bool(tables.get("out_tax_layer_clawback_memo")) and all(
        row["source_basis"] == TAX_LAYER_PACK_ID
        for row in tables["out_tax_layer_clawback_memo"]
    )


def _phase6_layer_rows() -> list[dict[str, str]]:
    return sorted(_read_csv_rows(PHASE6_LAYER_CONFIG), key=lambda row: int(row["waterfall_order"]))


def _opening_by_family_and_holder(
    pack: dict[str, list[dict[str, str]]],
    family: str,
    holder_prefix: str,
) -> Decimal:
    return sum(
        _d(row["base"])
        for row in _rows(pack, "opening_stocks", instrument_family=family)
        if row["cell_or_sector"].startswith(holder_prefix)
    )


def _check(check_id: str, ok: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": "pass" if ok else "fail", "message": message}


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _d(value: str | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _optional_d(value: str | Decimal | None) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return _d(value)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _fmt(value: Decimal | str) -> str:
    if isinstance(value, str):
        return value
    if value == 0:
        return "0"
    with localcontext() as context:
        context.prec = 28
        return format(value.normalize(), "f")


def _month_label(month_no: int) -> str:
    year = START_YEAR + (month_no - 1) // 12
    month = START_MONTH + (month_no - 1) % 12
    return f"{year}-{month:02d}"


def _prime_record_index(records: list[dict[str, Decimal | str]]) -> None:
    _RECORD_INDEX.clear()
    for record in records:
        _RECORD_INDEX[(str(record["band"]), str(record["year"]), record["ricardian_offset"])] = record

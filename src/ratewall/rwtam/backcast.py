"""Diagnostic RWTAM historical backcast builder."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.v1 import (
    _assumptions,
    _classify,
    _conversion,
    _d,
    _effective_pack,
    _fmt,
    _load_pack,
    _merge_routes,
    _opening_by_family,
    _private_credit_receipt_routes,
    _read_csv_rows,
    _route_amount,
    _tdc_implied_beta,
    _tdc_recipient_routes,
    _treasury_routes,
    build_v1,
)
from ratewall.rwtam.fed_pnl import (
    build_backcast_fed_pnl_tables,
    simulate_backcast_actual_path,
)


BACKCAST_CHANNELS = (
    "government_interest_public_net_block",
    "direct_treasury_interest_support",
    "iorb_recipient_support",
    "on_rrp_recipient_support",
    "remittance_offsets",
    "public_interest_absorber_rows",
    "deposit_safe_yield_income_d1_candidate",
    "tdc_ex_overlap_support_context",
    "mmf_income_gross_model",
    "mmf_expense_ratio_wedge",
    "mmf_yield_lag_wedge",
    "mmf_income_ici_or_nmfp",
    "credit_card_interest_g19",
    "auto_student_personal_g19",
)


@dataclass(frozen=True)
class BackcastResult:
    """CSV-ready RWTAM backcast output tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_backcast(
    pack_dir: Path = Path("configs/rwtam/packs"),
    backcast_dir: Path = Path("do/backcast"),
    *,
    anchor_quarter: str = "2022Q1",
    end_year: int = 2024,
) -> BackcastResult:
    base_pack = _effective_pack(
        _load_pack(pack_dir),
        include_scenario_adjustments=False,
        include_tdc_settlement=True,
    )
    state_packs = _load_state_packs(backcast_dir)
    state_rows = state_packs[anchor_quarter]
    pack = {name: list(rows) for name, rows in base_pack.items()}
    pack["opening_stocks"] = [dict(row) for row in state_rows]
    state_registry = _state_pack_registry(state_packs)
    selected_state = [
        row for row in state_registry if row["anchor_quarter"] == anchor_quarter
    ][0]
    rate_rows = _rate_rows_for_window(
        _read_csv_rows(backcast_dir / "historical_rate_paths.csv"),
        anchor_quarter,
        end_year,
    )
    baseline = _baseline_rates(rate_rows, anchor_quarter)
    fed_pnl_monthly = simulate_backcast_actual_path(pack, rate_rows)
    monthly = _monthly_backcast_rows(
        pack,
        rate_rows,
        baseline,
        anchor_quarter,
        selected_state,
        fed_pnl_monthly=fed_pnl_monthly,
    )
    predicted = _annual_predicted_flows(monthly, anchor_quarter, selected_state)
    rw_series = _annual_rw_series(monthly, anchor_quarter, selected_state)
    beta = _beta_diagnostic(pack, predicted, anchor_quarter, selected_state)
    targets = _mmf_v2_target_overlay(
        _read_csv_rows(backcast_dir / "realized_flow_targets.csv"),
        base_pack,
    )
    tracking = _tracking_rows(predicted, targets, anchor_quarter, selected_state)
    tables = {
        "out_backcast_state_packs": state_registry,
        "out_backcast_predicted_flows": predicted,
        "out_backcast_tracking": tracking,
        "out_mmf_income_gross_to_net_decomposition": _mmf_income_decomposition(
            predicted,
            targets,
            backcast_dir,
            base_pack,
        ),
        "out_RW_cash_backcast_series": rw_series,
        "out_backcast_on_rrp_opening_check": _on_rrp_opening_check_rows(state_packs),
        "out_episode_waterfall_housing_cash_only": _episode_waterfall_housing_cash_only(
            rw_series,
            rate_rows,
            baseline,
            pack_dir,
            anchor_quarter,
            selected_state,
        ),
        "out_backcast_beta_diagnostic": beta,
        "out_backcast_fed_pnl_dynamic_monthly": [
            {
                key: _fmt(value) if isinstance(value, Decimal) else str(value)
                for key, value in row.items()
            }
            for row in fed_pnl_monthly
        ],
        "out_backcast_fed_pnl_dynamic_scores": build_backcast_fed_pnl_tables(
            pack_dir=pack_dir,
            backcast_dir=backcast_dir,
        )[1],
    }
    tables["out_backcast_invariant_check"] = _backcast_invariant_table(
        tables,
        pack_dir,
    )
    return BackcastResult(tables=tables)


def write_backcast_outputs(result: BackcastResult, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def _load_state_packs(backcast_dir: Path) -> dict[str, list[dict[str, str]]]:
    packs: dict[str, list[dict[str, str]]] = {}
    for path in sorted(backcast_dir.glob("historical_opening_state_*.csv")):
        anchor = path.stem.removeprefix("historical_opening_state_")
        packs[anchor] = _read_csv_rows(path)
    if not {"2022Q1", "2023Q1", "2024Q1", "2025Q1"}.issubset(packs):
        raise ValueError("missing expected historical opening state packs")
    return packs


def _state_pack_registry(
    state_packs: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for anchor, state_rows in sorted(state_packs.items()):
        total = sum(_d(row["base"]) for row in state_rows)
        proxy_rows = [
            row
            for row in state_rows
            if "OWNER_BACKCAST_PROXY" in row.get("source_id", "")
            or "OWNER_BACKCAST_PROXY" in row.get("input_basis_label", "")
        ]
        proxy_total = sum(_d(row["base"]) for row in proxy_rows)
        rows.append(
            {
                "anchor_quarter": anchor,
                "state_pack_id": f"historical_opening_state_{anchor}",
                "row_count": str(len(state_rows)),
                "base_stock_bil": _fmt(total),
                "proxy_row_count": str(len(proxy_rows)),
                "proxy_base_stock_bil": _fmt(proxy_total),
                "proxy_base_share": _fmt(Decimal("0") if total == 0 else proxy_total / total),
                "label": "backcast_diagnostic_proxy_heavy_state",
            }
        )
    return rows


def _on_rrp_opening_check_rows(
    state_packs: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for anchor in ["2022Q1", "2023Q1", "2024Q1"]:
        state_row = next(
            row for row in state_packs[anchor] if row["instrument_family"] == "on_rrp_mmfs"
        )
        base = _d(state_row["base"])
        rows.append(
            {
                "anchor_quarter": anchor,
                "instrument_family": "on_rrp_mmfs",
                "opening_base_bil": _fmt(base),
                "minimum_allowed_bil": "50",
                "maximum_allowed_bil": "3000",
                "status": "pass" if Decimal("50") <= base <= Decimal("3000") else "fail",
                "message": "opening ON RRP must be billions-scale for 2022-24 states",
                "claim_grade_label": "non_claim_grade",
            }
        )
    return rows


def _rate_rows_for_window(
    rows: list[dict[str, str]],
    anchor_quarter: str,
    end_year: int,
) -> list[dict[str, str]]:
    rows = _monthly_rate_rows(rows)
    start = f"{anchor_quarter[:4]}-{_quarter_start_month(anchor_quarter[4:])}"
    return [
        row
        for row in rows
        if start <= row["month"] <= f"{end_year}-12"
    ]


def _monthly_rate_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows or rows[0].get("month"):
        return rows
    if not rows[0].get("year"):
        raise ValueError("historical_rate_paths.csv must provide month or year")
    monthly: list[dict[str, str]] = []
    for row in rows:
        year = row["year"]
        for month in range(1, 13):
            out = dict(row)
            out["month"] = f"{year}-{month:02d}"
            out["quarter_source"] = out.get("quarter_source") or f"{year}Q{(month - 1) // 3 + 1}"
            note = out.get("source_note", "")
            flag = "OWNER_APPROX_MONTHLY_INTERPOLATION"
            out["source_note"] = f"{note}; {flag}" if note else flag
            monthly.append(out)
    return monthly


def _baseline_rates(
    rows: list[dict[str, str]],
    anchor_quarter: str,
) -> dict[str, Decimal]:
    baseline_rows = [row for row in rows if row["quarter_source"] == anchor_quarter]
    fields = _rate_fields()
    return {
        field: sum(_d(row[field]) for row in baseline_rows) / Decimal(len(baseline_rows))
        for field in fields
    }


def _monthly_backcast_rows(
    pack: dict[str, list[dict[str, str]]],
    rate_rows: list[dict[str, str]],
    baseline: dict[str, Decimal],
    anchor_quarter: str,
    selected_state: dict[str, str],
    fed_pnl_monthly: list[dict[str, Decimal | str]] | None = None,
) -> list[dict[str, str | Decimal]]:
    opening = _opening_by_family(pack)
    conversion = _conversion(pack)
    assumptions = _assumptions(pack)
    rows: list[dict[str, str | Decimal]] = []
    tdc_stock = Decimal("0")
    fed_deltas: list[Decimal] = []
    for month_index, rate_row in enumerate(rate_rows, start=1):
        year = rate_row["month"][:4]
        bill_delta = _rate_delta(rate_row, baseline, "treasury_bill_3mo_rate_pct")
        coupon_delta = _rate_delta(rate_row, baseline, "treasury_note_10yr_rate_pct")
        iorb_delta = _rate_delta(rate_row, baseline, "iorb_rate_pct")
        fed_delta = _rate_delta(rate_row, baseline, "fed_funds_rate_pct")
        fed_deltas.append(fed_delta)
        bill_interest = opening.get("treasury_bills", Decimal("0")) * bill_delta / Decimal("12")
        coupon_interest = (
            opening.get("treasury_notes_bonds_tips", Decimal("0"))
            * _coupon_roll_month_share(pack, month_index)
            * coupon_delta
            / Decimal("12")
        )
        direct_treasury = bill_interest + coupon_interest
        iorb = opening.get("reserves_iorb", Decimal("0")) * iorb_delta / Decimal("12")
        on_rrp = opening.get("on_rrp_mmfs", Decimal("0")) * fed_delta / Decimal("12")
        remittance = (
            Decimal("0")
            if fed_pnl_monthly is None
            else _d(fed_pnl_monthly[month_index - 1]["public_cost_deferred_minus_cash_remit_bil"])
        )
        absorber_rows = Decimal("0")
        deposit_income = _deposit_income_delta(pack, rate_row, baseline)
        mmf_gross = opening.get("mmf_shares", Decimal("0")) * fed_delta / Decimal("12")
        mmf_lagged_delta = _lagged_rate_delta(
            fed_deltas,
            assumptions["mmf_yield_lag_months"]["base"],
        )
        mmf_lagged_gross = opening.get("mmf_shares", Decimal("0")) * mmf_lagged_delta / Decimal("12")
        mmf_expense_ratio = _mmf_expense_ratio_for_year(pack, year, assumptions)
        mmf_fee_wedge = opening.get("mmf_shares", Decimal("0")) * mmf_expense_ratio / Decimal("12")
        mmf_income = mmf_lagged_gross - mmf_fee_wedge
        credit_card = opening.get("credit_card_revolving", Decimal("0")) * fed_delta / Decimal("12")
        installment = (
            opening.get("auto_installment_debt", Decimal("0"))
            * assumptions["consumer_installment_new_flow_share"]["base"]
            + opening.get("personal_installment_debt", Decimal("0"))
            * assumptions["consumer_installment_new_flow_share"]["base"]
            + opening.get("student_loans_private", Decimal("0"))
            * assumptions["student_private_new_flow_share"]["base"]
        ) * fed_delta / Decimal("12")
        public_net = direct_treasury + iorb + on_rrp + remittance - absorber_rows
        tdc_stock += direct_treasury * _tdc_implied_beta(pack, "base")
        tdc_context = tdc_stock * assumptions["tdc_created_deposit_full_level_rate"]["base"]
        routes = _merge_routes(
            _treasury_routes(pack, bill_interest, coupon_interest, "base", False),
            _route_amount(pack, "banks", iorb, "base", "banks_retained_margin"),
            _route_amount(pack, "mmfs", on_rrp, "base", "mmfs"),
            _deposit_routes(pack, rate_row, baseline),
            _consumer_credit_routes(pack, "credit_card_revolving", credit_card),
            _consumer_credit_routes(pack, "auto_installment_debt", installment),
        )
        n, d, net = _classify(routes, conversion, Decimal("0"))
        rows.append(
            {
                "anchor_quarter": anchor_quarter,
                "month": rate_row["month"],
                "year": year,
                "direct_treasury_interest_support": direct_treasury,
                "iorb_recipient_support": iorb,
                "on_rrp_recipient_support": on_rrp,
                "remittance_offsets": remittance,
                "public_interest_absorber_rows": absorber_rows,
                "government_interest_public_net_block": public_net,
                "deposit_safe_yield_income_d1_candidate": deposit_income,
                "tdc_ex_overlap_support_context": tdc_context,
                "mmf_income_gross_model": mmf_gross,
                "mmf_expense_ratio_wedge": mmf_fee_wedge,
                "mmf_yield_lag_wedge": mmf_gross - mmf_lagged_gross,
                "mmf_income_ici_or_nmfp": mmf_income,
                "credit_card_interest_g19": credit_card,
                "auto_student_personal_g19": installment,
                "N_bil": n,
                "D_bil": d,
                "net_bil": net,
                "proxy_base_share": selected_state["proxy_base_share"],
            }
        )
    return rows


def _annual_predicted_flows(
    monthly: list[dict[str, str | Decimal]],
    anchor_quarter: str,
    selected_state: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    years = sorted({str(row["year"]) for row in monthly})
    for year in years:
        year_rows = [row for row in monthly if row["year"] == year]
        for channel in BACKCAST_CHANNELS:
            rows.append(
                {
                    "run_id": f"backcast_diagnostic_{anchor_quarter}_option2",
                    "anchor_quarter": anchor_quarter,
                    "calendar_year": year,
                    "channel": channel,
                    "predicted_value_bil": _fmt(
                        sum(row[channel] for row in year_rows)  # type: ignore[arg-type]
                    ),
                    "state_pack_id": selected_state["state_pack_id"],
                    "state_proxy_base_share": selected_state["proxy_base_share"],
                    "diagnostic_label": "backcast_diagnostic",
                    "shock_design": "option2_incremental_realized_minus_prehike_path",
                    "headline_entry_flag": "false",
                    "claim_grade_label": _backcast_claim_grade_label(channel),
                }
            )
    return rows


def _annual_rw_series(
    monthly: list[dict[str, str | Decimal]],
    anchor_quarter: str,
    selected_state: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in sorted({str(row["year"]) for row in monthly}):
        year_rows = [row for row in monthly if row["year"] == year]
        n = sum(row["N_bil"] for row in year_rows)  # type: ignore[arg-type]
        d = sum(row["D_bil"] for row in year_rows)  # type: ignore[arg-type]
        net = n - d
        rows.append(
            {
                "run_id": f"backcast_diagnostic_{anchor_quarter}_option2",
                "anchor_quarter": anchor_quarter,
                "calendar_year": year,
                "rw_object": "RW_cash_backcast",
                "N_bil": _fmt(n),
                "D_bil": _fmt(d),
                "net_bil": _fmt(net),
                "RW_ratio": _fmt(n / d) if d != 0 else "0",
                "state_proxy_base_share": selected_state["proxy_base_share"],
                "diagnostic_label": "RW_cash_backcast_no_scenario_TDC_on_diagnostic",
                "forbidden_comparisons": "headline_RW_full;scalar;P0/P1_bands;claim_ratios",
                "headline_entry_flag": "false",
                "claim_grade_label": "non_claim_grade",
            }
        )
    return rows


def _beta_diagnostic(
    pack: dict[str, list[dict[str, str]]],
    predicted: list[dict[str, str]],
    anchor_quarter: str,
    selected_state: dict[str, str],
) -> list[dict[str, str]]:
    beta = _tdc_implied_beta(pack, "base")
    recipient_coeff = _classify(_tdc_recipient_routes(pack, "base", Decimal("1")), _conversion(pack), Decimal("0"))[2]
    rows: list[dict[str, str]] = []
    for year in sorted({row["calendar_year"] for row in predicted}):
        direct = _predicted_value(predicted, "direct_treasury_interest_support", year)
        rows.append(
            {
                "run_id": f"backcast_diagnostic_{anchor_quarter}_option2",
                "calendar_year": year,
                "v2a_implied_beta": _fmt(beta),
                "owner_episode_beta_low": "0.5",
                "owner_episode_beta_high": "0.7",
                "direct_treasury_interest_support_bil": _fmt(direct),
                "v2a_created_deposit_flow_bil": _fmt(direct * beta),
                "owner_low_created_deposit_flow_bil": _fmt(direct * Decimal("0.5")),
                "owner_high_created_deposit_flow_bil": _fmt(direct * Decimal("0.7")),
                "recipient_conversion_coeff": _fmt(recipient_coeff),
                "state_proxy_base_share": selected_state["proxy_base_share"],
                "diagnostic_role": "beta_episode_comparison_never_calibration",
            }
        )
    return rows


def _tracking_rows(
    predicted: list[dict[str, str]],
    targets: list[dict[str, str]],
    anchor_quarter: str,
    selected_state: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    level_baselines = {
        target["channel"]: _d(target["realized_value_bil"])
        for target in targets
        if target["year"] == "2021" and target["realized_value_bil"]
    }
    for target in targets:
        year = target["year"]
        channel = target["channel"]
        predicted_channel = _tracking_prediction_channel(channel)
        predicted_value = _predicted_value(predicted, predicted_channel, year)
        realized_text = target["realized_value_bil"]
        realized = _aligned_realized_value(channel, year, realized_text, level_baselines)
        error = None if realized is None else predicted_value - realized
        circularity = _circularity_flag(channel, target.get("circularity_note", ""))
        rows.append(
            {
                "run_id": f"backcast_diagnostic_{anchor_quarter}_option2",
                "channel": channel,
                "perimeter": _target_perimeter(target),
                "predicted_channel": _tracking_prediction_label(channel, predicted_channel),
                "calendar_year": year,
                "predicted_value_bil": _fmt(predicted_value),
                "realized_value_bil": realized_text,
                "aligned_realized_value_bil": "" if realized is None else _fmt(realized),
                "error_bil": "" if error is None else _fmt(error),
                "coverage": target["coverage"],
                "source_note": target.get("source_note", target.get("circularity_note", "")),
                "circularity_flag": circularity,
                "classification": _tracking_classification(
                    channel,
                    target["coverage"],
                    circularity,
                    error,
                    _target_perimeter(target),
                ),
                "state_pack_id": selected_state["state_pack_id"],
                "state_proxy_base_share": selected_state["proxy_base_share"],
                "definition_alignment": _definition_alignment_note(channel, year),
                "no_fit_policy": "no_coefficients_or_mixes_adjusted_to_tracking_errors",
                "claim_grade_label": "non_claim_grade"
                if _tracking_prediction_channel(channel)
                in {
                    "government_interest_public_net_block",
                    "on_rrp_recipient_support",
                    "credit_card_interest_g19",
                }
                else "diagnostic_context",
            }
        )
    return rows


def _tracking_prediction_channel(channel: str) -> str:
    mapping = {
        "direct_treasury_public_issues_interest_support_vs_2021": "direct_treasury_interest_support",
        "direct_treasury_interest_support": "direct_treasury_interest_support",
        "treasury_public_issues_interest_mts_level": "direct_treasury_interest_support",
        "treasury_marketable_fixed_coupon_bill_interest_residual_level": "direct_treasury_interest_support",
        "fed_iorb_and_other_deposits_interest_expense_level": "iorb_recipient_support",
        "fed_on_rrp_total_interest_expense_level": "on_rrp_recipient_support",
        "fed_cash_remittances_transferred_to_treasury_level": "remittance_offsets",
        "fed_public_cost_from_remittances_deferred_support_vs_2021": "remittance_offsets",
        "public_interest_net_block_v2_anchor_support_vs_2021": "government_interest_public_net_block",
        "public_interest_net_block_v2_anchor_level": "government_interest_public_net_block",
        "mmf_income_ici_table39_dividends_paid_total": "mmf_income_ici_or_nmfp",
        "mmf_income_accrual_net_yield_construction": "mmf_income_ici_or_nmfp",
        "credit_card_interest_g19_proxy_level": "credit_card_interest_g19",
        "credit_card_interest_cfpb_observed": "credit_card_interest_g19",
    }
    return mapping.get(channel, channel)


def _backcast_claim_grade_label(channel: str) -> str:
    if channel in {
        "government_interest_public_net_block",
        "on_rrp_recipient_support",
        "credit_card_interest_g19",
        "mmf_income_ici_or_nmfp",
    }:
        return "non_claim_grade"
    return "diagnostic_context"


def _mmf_v2_target_overlay(
    targets: list[dict[str, str]],
    pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    v2_rows = pack.get("mmf_targets_v2_mmf_income_targets_v2", [])
    if not v2_rows:
        return targets
    out = [
        dict(row)
        for row in targets
        if not row["channel"].startswith("mmf_income_ici_table39")
    ]
    for row in v2_rows:
        parameter = row["parameter_id"]
        year = parameter.split("_cy")[-1].split("_", maxsplit=1)[0]
        basis = row["input_basis_label"]
        if basis == "accrual_net_yield_construction":
            out.append(
                {
                    "channel": "mmf_income_accrual_net_yield_construction",
                    "perimeter": "accrual_net_yield_construction",
                    "year": year,
                    "realized_value_bil": row["base"],
                    "source_artifact_path": "configs/rwtam/packs/mmf_income_targets_v2/mmf_income_targets_v2.csv",
                    "coverage": "scored_sec_nmfp_accrual_target",
                    "circularity_note": "none",
                    "source_note": "SEC N-MFP accrual construction selected by 2026-07-02 adjudication.",
                }
            )
        elif basis == "total_incl_reinvested":
            out.append(
                {
                    "channel": "mmf_income_ici_table39_distribution_series_context",
                    "perimeter": "distribution_series_context",
                    "year": year,
                    "realized_value_bil": row["base"],
                    "source_artifact_path": "configs/rwtam/packs/mmf_income_targets_v2/mmf_income_targets_v2.csv",
                    "coverage": "context_not_scored_paid_includes_reinvested",
                    "circularity_note": "do_not_score_distribution_perimeter_gap",
                    "source_note": "ICI Table 39 paid total includes reinvested distributions; not model-comparable accrual target.",
                }
            )
    return sorted(out, key=lambda item: (item["channel"], item["year"]))


def _mmf_expense_ratio_for_year(
    pack: dict[str, list[dict[str, str]]],
    year: str,
    assumptions: dict[str, dict[str, Decimal]],
) -> Decimal:
    for row in pack.get("mmf_targets_v2_expense_waiver_evidence_2021_2024", []):
        if row["calendar_year"] == year:
            return _d(row["asset_weighted_average_mmf_expense_ratio_pct"]) / Decimal("100")
    return assumptions["mmf_expense_ratio"]["base"]


def _mmf_income_decomposition(
    predicted: list[dict[str, str]],
    targets: list[dict[str, str]],
    backcast_dir: Path,
    pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    ici_rows = _read_csv_rows(backcast_dir / "mmf_income_ici_table39.csv")
    target_by_year = {
        row["year"]: row
        for row in targets
        if row["channel"] == "mmf_income_accrual_net_yield_construction"
    }
    ici_target_by_year = {
        row["year"]: row
        for row in targets
        if row["channel"] == "mmf_income_ici_table39_distribution_series_context"
    }
    ici_by_year = {row["year"]: row for row in ici_rows}
    rows: list[dict[str, str]] = []
    for year in sorted({row["calendar_year"] for row in predicted}):
        target = target_by_year.get(year, {})
        ici_target = ici_target_by_year.get(year, {})
        ici = ici_by_year.get(year, {})
        realized = _d(target.get("realized_value_bil", "0"))
        ici_paid = _d(ici_target.get("realized_value_bil", "0"))
        gross = _predicted_value(predicted, "mmf_income_gross_model", year)
        fee = _predicted_value(predicted, "mmf_expense_ratio_wedge", year)
        lag = _predicted_value(predicted, "mmf_yield_lag_wedge", year)
        net = _predicted_value(predicted, "mmf_income_ici_or_nmfp", year)
        reinvested = ici.get("reinvested_dividends_bil", "")
        reconstructed_target = ""
        residual_vs_reconstructed = ""
        if reinvested:
            reconstructed = ici_paid + _d(reinvested)
            reconstructed_target = _fmt(reconstructed)
            residual_vs_reconstructed = _fmt(net - reconstructed)
        rows.append(
            {
                "calendar_year": year,
                "gross_model_income_bil": _fmt(gross),
                "mmf_expense_ratio_base": _fmt(
                    _mmf_expense_ratio_for_year(pack, year, _assumptions(pack))
                ),
                "expense_ratio_wedge_bil": _fmt(fee),
                "mmf_yield_lag_months_base": "1",
                "yield_lag_wedge_bil": _fmt(lag),
                "net_model_income_bil": _fmt(net),
                "sec_accrual_net_yield_construction_bil": target.get("realized_value_bil", ""),
                "ratio_net_to_sec_accrual": _fmt(net / realized) if realized else "",
                "ici_table39_dividends_paid_bil": ici_target.get("realized_value_bil", ""),
                "ratio_net_to_dividends_paid": _fmt(net / ici_paid) if ici_paid else "",
                "reinvested_dividends_memo_bil": reinvested,
                "possible_paid_plus_reinvested_bil": reconstructed_target,
                "residual_vs_sec_accrual_bil": _fmt(net - realized) if realized else "",
                "residual_vs_dividends_paid_bil": _fmt(net - ici_paid) if ici_paid else "",
                "residual_vs_possible_paid_plus_reinvested_bil": residual_vs_reconstructed,
                "target_quality_status": "scored_accrual_net_yield_construction",
                "distribution_context_status": "target_side_perimeter_gap_unexplained",
                "disposition": "scored_sec_accrual_target;ici_distribution_series_context_not_scored;paid_plus_reinvested_do_not_use",
                "claim_grade_label": "non_claim_grade",
            }
        )
    return rows


def _tracking_prediction_label(channel: str, predicted_channel: str) -> str:
    if channel == "fed_iorb_and_other_deposits_interest_expense_level":
        return "iorb_and_other_deposits_recipient_support"
    return predicted_channel


def _target_perimeter(target: dict[str, str]) -> str:
    perimeter = target.get("perimeter", "")
    if perimeter:
        return perimeter
    channel = target["channel"]
    if channel in {
        "direct_treasury_public_issues_interest_support_vs_2021",
        "treasury_public_issues_interest_mts_level",
    }:
        return "public_issues_total_incl_tips_frn_nonmarketable"
    if channel in {"government_interest_public_net_block", "government_interest_public_net_block_v1_replaced_invalid"}:
        return "identity_context_not_model_validation"
    if channel == "credit_card_interest_cfpb_observed":
        return "observed_level_context"
    return "not_applicable"


def _aligned_realized_value(
    channel: str,
    year: str,
    realized_text: str,
    level_baselines: dict[str, Decimal],
) -> Decimal | None:
    if not realized_text:
        return None
    realized = _d(realized_text)
    if year == "2021":
        return None
    if channel.endswith("_level") and channel in level_baselines:
        return realized - level_baselines[channel]
    return realized


def _lagged_rate_delta(values: list[Decimal], lag_months: Decimal) -> Decimal:
    lag = int(lag_months)
    index = len(values) - 1 - lag
    if index < 0:
        return Decimal("0")
    return values[index]


def _definition_alignment_note(channel: str, year: str) -> str:
    if year == "2021":
        return "baseline_row_used_for_vs_2021_alignment_not_tracked"
    if channel == "credit_card_interest_cfpb_observed":
        return "observed_level_context_not_scored_as_success_or_failure"
    if channel == "stock_growth_interest_bridge":
        return "already_vs_2021_support; derived residual_perimeter_support_minus_v1_fixed_stock_support"
    if channel.endswith("_level"):
        return "target_level_minus_2021_level_to_match_2022Q1_flat_model_counterfactual"
    if "support_vs_2021" in channel:
        return "already_vs_2021_support; compared_to_2022Q1_flat_model_support_with_residual_wedge_reported"
    return "direct_project_schema_channel_or_alias"


def _backcast_invariant_table(
    tables: dict[str, list[dict[str, str]]],
    pack_dir: Path,
) -> list[dict[str, str]]:
    return [
        {
            "check_id": "T54",
            "status": "pass" if _t54_backcast_closure(tables) else "fail",
            "message": "backcast public net block closes and annual RW series nets N minus D",
        },
        {
            "check_id": "T55",
            "status": "pass" if _t55_backcast_not_headline(pack_dir) else "fail",
            "message": "backcast outputs are separate diagnostic tables and never enter headline V1 tables",
        },
        {
            "check_id": "T56",
            "status": "pass" if _t56_on_rrp_opening_magnitude(tables) else "fail",
            "message": "2022-24 ON RRP opening stocks are in billions, not trillions coded as ones",
        },
        {
            "check_id": "T57",
            "status": "pass" if _t57_episode_housing_flow_bound(tables) else "fail",
            "message": "episode housing D stays on a flow-base scale at <=500bp shocks",
        },
    ]


def _episode_waterfall_housing_cash_only(
    rw_series: list[dict[str, str]],
    rate_rows: list[dict[str, str]],
    baseline: dict[str, Decimal],
    pack_dir: Path,
    anchor_quarter: str,
    selected_state: dict[str, str],
) -> list[dict[str, str]]:
    parameter_path = _find_pack_file(pack_dir / "phase6_episode_elasticities", "episode_phase6_parameter_pack.csv")
    if parameter_path is None:
        return []
    params = {row["parameter_id"]: row for row in _read_csv_rows(parameter_path)}
    flow_bases = _episode_housing_flow_bases(pack_dir)
    by_year: dict[str, list[dict[str, str]]] = {}
    for row in rate_rows:
        by_year.setdefault(row["month"][:4], []).append(row)
    cash = {row["calendar_year"]: row for row in rw_series}
    out: list[dict[str, str]] = []
    for year, rows in sorted(by_year.items()):
        avg_shock_bp = sum(
            (_d(row["fed_funds_rate_pct"]) - baseline["fed_funds_rate_pct"]) * Decimal("100")
            for row in rows
        ) / Decimal(len(rows))
        existing_sales_share = _episode_housing_share(
            params,
            avg_shock_bp,
            prefix="episode_housing_existing_sales",
        )
        starts_share = _episode_housing_share(
            params,
            avg_shock_bp,
            prefix="episode_housing_total_starts",
        )
        transaction_base = flow_bases["existing_sales_transaction_linked_spending"]
        residential_investment_base = flow_bases["residential_investment_flow"]
        transaction_drag = transaction_base * existing_sales_share
        residential_investment_drag = residential_investment_base * starts_share
        housing_drag = transaction_drag + residential_investment_drag
        cash_row = cash.get(year, {})
        cash_n = _d(cash_row.get("N_bil", "0"))
        cash_d = _d(cash_row.get("D_bil", "0"))
        d_total = cash_d + housing_drag
        out.append(
            {
                "run_id": f"episode_waterfall_housing_cash_only_{anchor_quarter}",
                "anchor_quarter": anchor_quarter,
                "calendar_year": year,
                "rw_object": "episode_waterfall_housing_cash_only",
                "cash_N_bil": _fmt(cash_n),
                "cash_D_bil": _fmt(cash_d),
                "transaction_linked_spending_base_bil": _fmt(transaction_base),
                "residential_investment_base_bil": _fmt(residential_investment_base),
                "existing_sales_decline_share": _fmt(existing_sales_share),
                "residential_investment_decline_share": _fmt(starts_share),
                "transaction_linked_D_bil": _fmt(transaction_drag),
                "residential_investment_D_bil": _fmt(residential_investment_drag),
                "housing_quantity_D_bil": _fmt(housing_drag),
                "N_bil": _fmt(cash_n),
                "D_bil": _fmt(d_total),
                "net_bil": _fmt(cash_n - d_total),
                "RW_ratio": _fmt(cash_n / d_total) if d_total else "0",
                "avg_policy_shock_bp_vs_2022Q1": _fmt(avg_shock_bp),
                "state_proxy_base_share": selected_state["proxy_base_share"],
                "diagnostic_label": "housing_plus_cashflow_only_episode_waterfall",
                "forbidden_comparisons": "headline_RW_full;scalar;P0/P1_bands;claim_ratios;RW_cash_backcast",
                "headline_entry_flag": "false",
                "claim_grade_label": "non_claim_grade",
            }
        )
    return out


def _episode_housing_flow_bases(pack_dir: Path) -> dict[str, Decimal]:
    path = _find_pack_file(pack_dir / "phase6_episode_elasticities", "episode_housing_flow_bases.csv")
    if path is None:
        raise ValueError("missing episode_housing_flow_bases.csv")
    bases: dict[str, Decimal] = {}
    for row in _read_csv_rows(path):
        layer = row["layer_id"]
        if row["base_flow_bil"]:
            bases[layer] = _d(row["base_flow_bil"])
            continue
        bases[layer] = (
            _d(row["annual_units_mil"])
            * _d(row["average_price_thousand_dollars"])
            * _d(row["transaction_cost_moving_spend_share"])
        )
    required = {"existing_sales_transaction_linked_spending", "residential_investment_flow"}
    if not required.issubset(bases):
        raise ValueError("episode housing flow bases missing required layers")
    return bases


def _episode_housing_share(
    params: dict[str, dict[str, str]],
    shock_bp: Decimal,
    *,
    prefix: str,
) -> Decimal:
    shock = max(Decimal("0"), min(shock_bp, Decimal("500")))
    segments = [
        (Decimal("200"), _d(params[f"{prefix}_slope_0_200bp"]["base"])),
        (Decimal("150"), _d(params[f"{prefix}_slope_200_350bp"]["base"])),
        (Decimal("150"), _d(params[f"{prefix}_slope_350_500bp"]["base"])),
    ]
    pct = Decimal("0")
    remaining = shock
    for width, slope in segments:
        used = min(width, remaining)
        pct += used / Decimal("100") * slope
        remaining -= used
        if remaining <= 0:
            break
    cap = abs(_d(params[f"{prefix}_decline_cap"]["base"]))
    return min(abs(pct), cap) / Decimal("100")


def _find_pack_file(root: Path, filename: str) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(root.rglob(filename))
    return matches[0] if matches else None


def _t54_backcast_closure(tables: dict[str, list[dict[str, str]]]) -> bool:
    predicted = tables["out_backcast_predicted_flows"]
    for year in sorted({row["calendar_year"] for row in predicted}):
        public_net = _predicted_value(predicted, "government_interest_public_net_block", year)
        parts = (
            _predicted_value(predicted, "direct_treasury_interest_support", year)
            + _predicted_value(predicted, "iorb_recipient_support", year)
            + _predicted_value(predicted, "on_rrp_recipient_support", year)
            + _predicted_value(predicted, "remittance_offsets", year)
            - _predicted_value(predicted, "public_interest_absorber_rows", year)
        )
        if abs(public_net - parts) > Decimal("0.000001"):
            return False
    tracking_keys = set()
    for row in tables["out_backcast_tracking"]:
        predicted_channel = _tracking_internal_label(row.get("predicted_channel", row["channel"]))
        if (
            row["calendar_year"] != "2021"
            and (row.get("aligned_realized_value_bil", "") or row.get("coverage") != "absent")
            and predicted_channel in BACKCAST_CHANNELS
        ):
            tracking_keys.add((predicted_channel, row["calendar_year"]))
    predicted_keys = {
        (row["channel"], row["calendar_year"])
        for row in predicted
    }
    if not tracking_keys.issubset(predicted_keys):
        return False
    for row in tables["out_RW_cash_backcast_series"]:
        if abs(_d(row["N_bil"]) - _d(row["D_bil"]) - _d(row["net_bil"])) > Decimal("0.000001"):
            return False
    return True


def _tracking_internal_label(predicted_channel: str) -> str:
    if predicted_channel == "iorb_and_other_deposits_recipient_support":
        return "iorb_recipient_support"
    return predicted_channel


def _t55_backcast_not_headline(pack_dir: Path) -> bool:
    headline_tables = set(build_v1(pack_dir).tables)
    return not any(table.startswith("out_backcast") for table in headline_tables)


def _t56_on_rrp_opening_magnitude(tables: dict[str, list[dict[str, str]]]) -> bool:
    return all(row["status"] == "pass" for row in tables["out_backcast_on_rrp_opening_check"])


def _t57_episode_housing_flow_bound(tables: dict[str, list[dict[str, str]]]) -> bool:
    for row in tables["out_episode_waterfall_housing_cash_only"]:
        shock = _d(row["avg_policy_shock_bp_vs_2022Q1"])
        drag = _d(row["housing_quantity_D_bil"])
        if shock <= Decimal("500") and not (Decimal("20") <= drag <= Decimal("600")):
            return False
    return True


def _deposit_income_delta(
    pack: dict[str, list[dict[str, str]]],
    rate_row: dict[str, str],
    baseline: dict[str, Decimal],
) -> Decimal:
    rates = _deposit_rate_deltas(rate_row, baseline)
    total = Decimal("0")
    for family, rate in rates.items():
        total += _opening_by_family(pack).get(family, Decimal("0")) * rate / Decimal("12")
    return total


def _deposit_routes(
    pack: dict[str, list[dict[str, str]]],
    rate_row: dict[str, str],
    baseline: dict[str, Decimal],
) -> dict[str, Decimal]:
    routes: dict[str, Decimal] = {}
    rates = _deposit_rate_deltas(rate_row, baseline)
    for family, rate in rates.items():
        family_total = Decimal("0")
        for stock_row in [row for row in pack["opening_stocks"] if row["instrument_family"] == family]:
            amount = _d(stock_row["base"]) * rate / Decimal("12")
            family_total += amount
            routes = _merge_routes(
                routes,
                _route_amount(pack, _holder_from_opening_row(stock_row), amount, "base", family),
            )
        routes = _merge_routes(
            routes,
            _route_amount(pack, "banks", -family_total, "base", "banks_retained_margin"),
        )
    return routes


def _consumer_credit_routes(
    pack: dict[str, list[dict[str, str]]],
    family: str,
    amount: Decimal,
) -> dict[str, Decimal]:
    if amount == 0:
        return {}
    return _merge_routes(
        _route_amount(pack, "household_debtors", -amount, "base", family),
        _private_credit_receipt_routes(pack, family, amount, "base"),
    )


def _deposit_rate_deltas(
    rate_row: dict[str, str],
    baseline: dict[str, Decimal],
) -> dict[str, Decimal]:
    return {
        "deposits_checkable": _rate_delta(rate_row, baseline, "savings_deposit_rate_pct"),
        "deposits_savings_mmda": _rate_delta(
            rate_row, baseline, "money_market_deposit_rate_pct"
        ),
        "deposits_time_cds": _rate_delta(rate_row, baseline, "twelve_month_cd_rate_pct"),
    }


def _coupon_roll_month_share(
    pack: dict[str, list[dict[str, str]]],
    month_index: int,
) -> Decimal:
    rows = pack.get("tdcsim_coupon_roll_schedule", [])
    if rows:
        return _d(rows[min(month_index, len(rows)) - 1]["cumulative_share_of_current_stock"])
    return min(Decimal("1"), _assumptions(pack)["coupon_roll_rate"]["base"] * Decimal(month_index) / Decimal("12"))


def _predicted_value(
    predicted: list[dict[str, str]],
    channel: str,
    year: str,
) -> Decimal:
    matches = [
        row
        for row in predicted
        if row["channel"] == channel and row["calendar_year"] == year
    ]
    return Decimal("0") if not matches else _d(matches[0]["predicted_value_bil"])


def _tracking_classification(
    channel: str,
    coverage: str,
    circularity: str,
    error: Decimal | None,
    perimeter: str = "",
) -> str:
    if coverage == "absent":
        return "absent_realized_target_no_tracking_error"
    if perimeter == "public_issues_total_incl_tips_frn_nonmarketable":
        return "perimeter_not_model_comparable"
    if "needs_reconstruction" in coverage:
        return "needs_reconstruction"
    if perimeter == "perimeter_not_fixed_stock_comparable":
        return "perimeter_not_fixed_stock_comparable"
    if perimeter == "identity_context_not_model_validation":
        return "identity_context_not_model_validation"
    if perimeter == "observed_level_context":
        return "observed_level_context"
    if perimeter == "distribution_series_context":
        return "distribution_series_context_not_scored"
    if perimeter == "accrual_net_yield_construction":
        return "mmf_scored_accrual_target_tracking_error_no_fit"
    if perimeter in {"tips_inflation_compensation", "frn_interest", "savings_nonmarketable"}:
        return "treasury_perimeter_component_not_scored"
    if channel == "direct_treasury_interest_support" and perimeter != "repricing_on_fixed_stock_approx":
        return "perimeter_not_model_comparable"
    if channel == "government_interest_public_net_block" and "invalid" in coverage:
        return "net_block_tracking_invalid_until_component_reconstruction"
    if circularity == "true":
        return "target_quality_or_circularity_flag_do_not_fit"
    if error is None:
        return "target_quality_missing_value"
    if channel in {
        "government_interest_public_net_block",
        "direct_treasury_interest_support",
        "iorb_recipient_support",
        "on_rrp_recipient_support",
        "remittance_offsets",
    }:
        return "public_interest_clean_test_state_proxy_or_rate_path_error"
    if channel == "deposit_safe_yield_income_d1_candidate":
        return "deposit_pass_through_or_target_quality_error"
    return "diagnostic_tracking_error_no_fit"


def _circularity_flag(channel: str, note: str) -> str:
    lowered = note.lower()
    if "sfos-circular" in lowered or "context only" in lowered or channel.startswith("tdc_"):
        return "true"
    return "false"


def _rate_delta(
    row: dict[str, str],
    baseline: dict[str, Decimal],
    field: str,
) -> Decimal:
    return (_d(row[field]) - baseline[field]) / Decimal("100")


def _rate_fields() -> tuple[str, ...]:
    return (
        "fed_funds_rate_pct",
        "treasury_bill_3mo_rate_pct",
        "treasury_note_10yr_rate_pct",
        "iorb_rate_pct",
        "savings_deposit_rate_pct",
        "money_market_deposit_rate_pct",
        "twelve_month_cd_rate_pct",
    )


def _quarter_start_month(quarter: str) -> str:
    return {"Q1": "01", "Q2": "04", "Q3": "07", "Q4": "10"}[quarter]


def _holder_from_opening_row(row: dict[str, str]) -> str:
    cell = row["cell_or_sector"]
    for part in cell.split("|"):
        if part.startswith("holder="):
            return part.removeprefix("holder=")
    return cell


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

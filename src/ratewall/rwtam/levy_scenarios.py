"""Levy-legible scenario/readout quartet for RWTAM."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.backcast import build_backcast
from ratewall.rwtam.fed_pnl import (
    GOVERNMENT_REVENUE_DOCTRINE,
    GOVERNMENT_REVENUE_DOCTRINE_LINEAGE,
)
from ratewall.rwtam.reissuance_policy import (
    REISSUANCE_POLICY_ORDER,
    build_reissuance_policy_scenarios,
)
from ratewall.rwtam.scenarios import ScenarioResult
from ratewall.rwtam.v1 import (
    CURRENT_DEFAULT_OBJECT_STAMP,
    DEFAULT_DOSE_MODE,
    _classify,
    _conversion,
    _d,
    _effective_pack,
    _fmt,
    _load_pack,
    _merge_routes,
    _monthly_records,
    _opening_by_family,
    _route_amount,
    _write_rows,
    build_v1,
)


OUTPUT_TABLES = (
    "out_levy_reissuance_comparative",
    "out_all_bills_convergence_path",
    "out_cycle_2022_24_readout",
    "out_corridor_floor_comparison",
    "out_distributional_incidence_per_100bp",
    "out_levy_invariant_check",
)

HORIZONS = {
    "year_1": ("annual", "2026"),
    "year_5": ("annual", "2030"),
    "year_10": ("annual", "2035"),
}

REQUESTED_DISTRIBUTION_ORDER = (
    "hh_constrained_net_borrower",
    "hh_middle_owner_illiquid",
    "hh_retiree_fixed_income_saver",
    "hh_unconstrained_saver",
    "firm_bank_dependent_small",
    "firm_market_funded_large",
    "government",
    "banks",
    "foreign",
    "other_finance_unallocated_tieout",
)


def build_levy_scenarios(
    pack_dir: Path = Path("configs/rwtam/packs"),
    *,
    backcast_dir: Path = Path("do/backcast"),
    dose_mode: str = DEFAULT_DOSE_MODE,
) -> ScenarioResult:
    """Build the four scenario-only/readout tables requested for the Levy memo."""

    raw_pack = _load_pack(pack_dir)
    pack = _effective_pack(raw_pack, True, True)
    base_v1 = build_v1(pack_dir, dose_mode=dose_mode)
    reissuance = build_reissuance_policy_scenarios(pack_dir, dose_mode=dose_mode)
    backcast = build_backcast(pack_dir, backcast_dir, anchor_quarter="2022Q1", end_year=2024)

    reissuance_rows = _reissuance_comparative_rows(reissuance)
    convergence_rows = _all_bills_convergence_rows(reissuance)
    cycle_rows = _cycle_readout_rows(backcast)
    corridor_rows = _corridor_floor_rows(pack, base_v1)
    distribution_rows = _distribution_rows(base_v1)
    invariant_rows = _invariant_rows(
        base_v1,
        reissuance,
        reissuance_rows,
        cycle_rows,
        corridor_rows,
        distribution_rows,
    )
    tables = {
        "out_levy_reissuance_comparative": reissuance_rows,
        "out_all_bills_convergence_path": convergence_rows,
        "out_cycle_2022_24_readout": cycle_rows,
        "out_corridor_floor_comparison": corridor_rows,
        "out_distributional_incidence_per_100bp": distribution_rows,
        "out_levy_invariant_check": invariant_rows,
    }
    for rows in tables.values():
        for row in rows:
            row.setdefault("object_version_stamp", CURRENT_DEFAULT_OBJECT_STAMP)
    return ScenarioResult(scenario_id="rwtam_levy_scenarios_20260704", tables=tables)


def write_levy_scenario_outputs(
    result: ScenarioResult,
    output_root: Path = Path("var/rwtam/scenarios/levy_scenarios"),
) -> dict[str, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name in OUTPUT_TABLES:
        path = output_root / f"{table_name}.csv"
        _write_rows(path, result.rows(table_name))
        paths[table_name] = path
    return paths


def write_levy_scenarios_report(
    result: ScenarioResult,
    output_path: Path = Path("do/rwtam_levy_scenarios_report_20260704.md"),
) -> Path:
    l1_y10 = next(
        row
        for row in result.rows("out_levy_reissuance_comparative")
        if row["scenario_id"] == "bills_only" and row["horizon"] == "year_10"
    )
    l3_y1 = next(
        row
        for row in result.rows("out_corridor_floor_comparison")
        if row["horizon"] == "year_1" and row["variant_id"] == "corridor_with_issuance_loop"
    )
    l4_rows = [
        row
        for row in result.rows("out_distributional_incidence_per_100bp")
        if row["row_type"] == "incidence"
    ]
    checks = result.rows("out_levy_invariant_check")
    lines = [
        "# RWTAM Levy-legible scenario quartet",
        "",
        "Date: 2026-07-04.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: scenario/readout-only; no headline or golden promotion.",
        "",
        "## Dispositions",
        "",
        "| item | disposition | output |",
        "| --- | --- | --- |",
        "| L1 all-bills issuance | built: `bills_only` extends the existing reissuance grid; coupon principal converges into bills through measured runoff, not an instantaneous swap | `out_levy_reissuance_comparative.csv`; `out_all_bills_convergence_path.csv` |",
        "| L2 2022-24 cycle readout | assembled from existing backcast surfaces; label `realized_cycle_readout; not_a_counterfactual_claim` | `out_cycle_2022_24_readout.csv` |",
        "| L3 IORB-zero corridor | rebuilt under the government-revenue doctrine: private administered-rate legs are removed directly; intra-government remittance clawback gets zero direct D and the financing effect enters only through the issuance loop | `out_corridor_floor_comparison.csv` |",
        "| L4 distributional incidence | assembled from default-run cell-net flow ledger; row tie-out asserted | `out_distributional_incidence_per_100bp.csv` |",
        "",
        "## Headline findings",
        "",
        f"- L1: `bills_only` year-10 RW is `{l1_y10['RW_ratio']}`; year-10 multiple vs base is `{l1_y10['multiple_RW_vs_base']}`.",
        f"- L3: corridor year-1 base RW is `{l3_y1['corridor_RW_ratio']}` vs floor `{l3_y1['floor_RW_ratio']}`; raw remittance D clawback is `{l3_y1['remittance_loop_D_clawback_bil']}` and issuance-loop extra public net is `{l3_y1['issuance_loop_extra_public_net_bil']}`.",
        f"- L4: emitted {len(l4_rows)} incidence rows; positive converted effects sum to N and negative converted effects sum to D.",
        "",
        "## Invariants",
        "",
        "| check | status | message |",
        "| --- | --- | --- |",
    ]
    for row in checks:
        lines.append(f"| {row['check_id']} | {row['status']} | {row['message']} |")
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- L2 is a realized-cycle readout, not a counterfactual claim; the D-side uses the existing housing-plus-cashflow episode backcast so N attenuates the drag without reversing it.",
            "- L3 changes the N perimeter and remittance accounting treatment; it does not model reserve-scarcity credit dynamics or bank behavioral changes.",
            "- L4 uses the default-run global cell-net ledger, so gross received/paid are positive and negative sides of already-netted cell rows; retiree and unconstrained-saver splits are the existing V1 look-through allocation, not a new distribution model.",
            "",
            "## Outputs",
            "",
            "- `var/rwtam/scenarios/levy_scenarios/out_levy_reissuance_comparative.csv`",
            "- `var/rwtam/scenarios/levy_scenarios/out_cycle_2022_24_readout.csv`",
            "- `var/rwtam/scenarios/levy_scenarios/out_corridor_floor_comparison.csv`",
            "- `var/rwtam/scenarios/levy_scenarios/out_distributional_incidence_per_100bp.csv`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _reissuance_comparative_rows(results: dict[str, ScenarioResult]) -> list[dict[str, str]]:
    base = _horizon_rows(results["base"])
    rows: list[dict[str, str]] = []
    for scenario_id in REISSUANCE_POLICY_ORDER:
        horizon_rows = _horizon_rows(results[scenario_id])
        composition = {row["year"]: row for row in results[scenario_id].rows("out_reissuance_composition_path")}
        config = results[scenario_id].rows("out_reissuance_policy_config")[0]
        for horizon, (_, period) in HORIZONS.items():
            row = horizon_rows[horizon]
            base_row = base[horizon]
            multiple = _d(row["RW_ratio"]) / _d(base_row["RW_ratio"]) if _d(base_row["RW_ratio"]) else Decimal("0")
            rows.append(
                {
                    "row_type": "issuance_comparative_static",
                    "scenario_id": scenario_id,
                    "horizon": horizon,
                    "period": period,
                    "policy_bill_share": config["policy_bill_share"],
                    "active_bill_runoff_share": config["active_bill_runoff_share"],
                    "bill_share_end": composition[period]["bill_share_end"],
                    "coupon_stock_end_bil": composition[period]["stock_coupons_end_bil"],
                    "RW_ratio": row["RW_ratio"],
                    "N_bil": row["N_bil"],
                    "D_bil": row["D_bil"],
                    "base_RW_ratio": base_row["RW_ratio"],
                    "delta_RW_ratio_vs_base": _fmt(_d(row["RW_ratio"]) - _d(base_row["RW_ratio"])),
                    "multiple_RW_vs_base": _fmt(multiple),
                    "label": "scenario_only;mosler_wray_operational_proposal_endpoint"
                    if scenario_id == "bills_only"
                    else "scenario_only;reissuance_policy_grid",
                }
            )
    return rows


def _all_bills_convergence_rows(results: dict[str, ScenarioResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in results["bills_only"].rows("out_reissuance_composition_path"):
        out = dict(row)
        out["row_type"] = "all_bills_measured_coupon_runoff_convergence"
        out["label"] = "coupon_principal_rolls_into_bills_no_instantaneous_swap"
        rows.append(out)
    return rows


def _cycle_readout_rows(backcast: ScenarioResult) -> list[dict[str, str]]:
    episode = {row["calendar_year"]: row for row in backcast.rows("out_episode_waterfall_housing_cash_only")}
    tracking = backcast.rows("out_backcast_tracking")
    rows: list[dict[str, str]] = []
    public_targets = {
        row["calendar_year"]: row
        for row in tracking
        if row["channel"] == "public_interest_net_block_v2_anchor_support_vs_2021"
    }
    for year in ("2022", "2023", "2024"):
        ep = episode[year]
        n = _d(ep["N_bil"])
        d = _d(ep["D_bil"])
        realized_public = _d(public_targets[year]["aligned_realized_value_bil"])
        rows.append(
            {
                "row_type": "annual_summary",
                "calendar_year": year,
                "channel": "cycle_total",
                "realized_bil": _fmt(realized_public),
                "model_N_bil": ep["N_bil"],
                "model_D_bil": ep["D_bil"],
                "model_net_N_minus_D_bil": _fmt(n - d),
                "attenuation_share_N_over_D": _fmt(n / d) if d else "0",
                "tracking_ratio_model_to_realized": "",
                "classification": "attenuation_never_reversal_N_minus_D_lt_0",
                "label": "realized_cycle_readout;not_a_counterfactual_claim",
                "note": "realized consolidated government support uses public-interest v2 anchor; D is existing housing-plus-cashflow episode backcast",
            }
        )
    rows.append(_cycle_total_row(rows))
    channel_set = {
        "direct_treasury_public_issues_interest_support_vs_2021",
        "fed_iorb_and_other_deposits_interest_expense_level",
        "fed_on_rrp_total_interest_expense_level",
        "fed_public_cost_from_remittances_deferred_support_vs_2021",
        "deposit_safe_yield_income_d1_candidate",
        "mmf_income_accrual_net_yield_construction",
        "credit_card_interest_g19_proxy_level",
    }
    for row in tracking:
        if row["calendar_year"] not in {"2022", "2023", "2024"} or row["channel"] not in channel_set:
            continue
        realized = row["aligned_realized_value_bil"] or row["realized_value_bil"]
        predicted = _d(row["predicted_value_bil"])
        ratio = _fmt(predicted / _d(realized)) if realized and _d(realized) else ""
        rows.append(
            {
                "row_type": "n_channel",
                "calendar_year": row["calendar_year"],
                "channel": row["channel"],
                "realized_bil": realized,
                "model_N_bil": "",
                "model_D_bil": "",
                "model_net_N_minus_D_bil": "",
                "attenuation_share_N_over_D": "",
                "tracking_ratio_model_to_realized": ratio,
                "classification": row["classification"],
                "label": "realized_cycle_readout;not_a_counterfactual_claim",
                "note": row["definition_alignment"],
            }
        )
    for row in backcast.rows("out_mmf_income_gross_to_net_decomposition"):
        rows.append(
            {
                "row_type": "validation_tracking_ratio",
                "calendar_year": row["calendar_year"],
                "channel": "mmf_income_accrual_net_yield_construction",
                "realized_bil": row["sec_accrual_net_yield_construction_bil"],
                "model_N_bil": "",
                "model_D_bil": "",
                "model_net_N_minus_D_bil": "",
                "attenuation_share_N_over_D": "",
                "tracking_ratio_model_to_realized": row["ratio_net_to_sec_accrual"],
                "classification": row["target_quality_status"],
                "label": "realized_cycle_readout;not_a_counterfactual_claim",
                "note": "credibility anchor from existing MMF gross-to-net backcast decomposition",
            }
        )
    return rows


def _cycle_total_row(summary_rows: list[dict[str, str]]) -> dict[str, str]:
    total_realized = sum(_d(row["realized_bil"]) for row in summary_rows)
    total_n = sum(_d(row["model_N_bil"]) for row in summary_rows)
    total_d = sum(_d(row["model_D_bil"]) for row in summary_rows)
    return {
        "row_type": "cycle_total_2022_24",
        "calendar_year": "2022-2024",
        "channel": "cycle_total",
        "realized_bil": _fmt(total_realized),
        "model_N_bil": _fmt(total_n),
        "model_D_bil": _fmt(total_d),
        "model_net_N_minus_D_bil": _fmt(total_n - total_d),
        "attenuation_share_N_over_D": _fmt(total_n / total_d) if total_d else "0",
        "tracking_ratio_model_to_realized": "",
        "classification": "attenuation_never_reversal_N_minus_D_lt_0",
        "label": "realized_cycle_readout;not_a_counterfactual_claim",
        "note": "sum of annual existing backcast rows",
    }


def _corridor_floor_rows(pack: dict[str, list[dict[str, str]]], base_v1: ScenarioResult) -> list[dict[str, str]]:
    opening = _opening_by_family(pack)
    conversion = _conversion(pack)
    admin_routes = _merge_routes(
        _route_amount(pack, "banks", opening["reserves_iorb"] * Decimal("0.01"), "base", "banks_retained_margin"),
        _route_amount(pack, "mmfs", opening["on_rrp_mmfs"] * Decimal("0.01"), "base", "mmfs"),
    )
    admin_n, admin_d, _ = _classify(admin_routes, conversion, Decimal("0"))
    annual_iorb = opening["reserves_iorb"] * Decimal("0.01")
    annual_on_rrp = opening["on_rrp_mmfs"] * Decimal("0.01")
    annual_foreign_rrp = opening["foreign_official_reverse_repos"] * Decimal("0.01")
    monthly_admin_cost = (annual_iorb + annual_on_rrp + annual_foreign_rrp) / Decimal("12")
    base_records = _monthly_records(
        pack,
        include_tdc_settlement=True,
        shock_start_month="2026-01",
        dose_mode=DEFAULT_DOSE_MODE,
        include_tax_layer=True,
    )
    loop_records = _monthly_records(
        pack,
        include_tdc_settlement=True,
        shock_start_month="2026-01",
        dose_mode=DEFAULT_DOSE_MODE,
        include_tax_layer=True,
        issuance_loop_extra_public_net_by_month={
            ("base", f"{2026 + (month - 1) // 12}-{(month - 1) % 12 + 1:02d}"): -monthly_admin_cost
            for month in range(1, 121)
        },
    )
    full_cycle_coeff = _tax_feedback_coeff(pack, "treasury_receipt_feedback_coefficient_accrual_with_fed")
    cash_ex_fed_coeff = _tax_feedback_coeff(pack, "treasury_receipt_feedback_coefficient_cash_ex_fed_current")
    rows: list[dict[str, str]] = []
    horizons = _horizon_rows(base_v1)
    for horizon in ("year_1", "year_5", "year_10", "cumulative_120_month"):
        row = horizons[horizon]
        multiplier = Decimal("10") if horizon == "cumulative_120_month" else Decimal("1")
        admin_cost = (annual_iorb + annual_on_rrp + annual_foreign_rrp) * multiplier
        no_loop_n = _d(row["N_bil"]) - admin_n * multiplier
        no_loop_d = _d(row["D_bil"]) - admin_d * multiplier
        loop_delta_n, loop_delta_d = _loop_horizon_delta(base_records, loop_records, horizon)
        variants = (
            (
                "corridor_no_loop_p1_private_counterpart_only",
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                no_loop_n,
                no_loop_d,
            ),
            (
                "corridor_with_issuance_loop",
                -admin_cost,
                loop_delta_n,
                loop_delta_d,
                _d(row["N_bil"]) + loop_delta_n - admin_n * multiplier,
                _d(row["D_bil"]) + loop_delta_d - admin_d * multiplier,
            ),
        )
        for variant_id, loop_extra, loop_delta_n, loop_delta_d, corridor_n, corridor_d in variants:
            delta_rw = (corridor_n / corridor_d) - _d(row["RW_ratio"]) if corridor_d else Decimal("0")
            rows.append(
                {
                "row_type": "operating_regime_comparative_static",
                "variant_id": variant_id,
                "horizon": horizon,
                "period": row["period"],
                "floor_N_bil": row["N_bil"],
                "floor_D_bil": row["D_bil"],
                "floor_RW_ratio": row["RW_ratio"],
                "admin_rate_N_removed_bil": _fmt(admin_n * multiplier),
                "admin_rate_D_removed_bil": _fmt(admin_d * multiplier),
                "iorb_cashflow_removed_bil": _fmt(annual_iorb * multiplier),
                "on_rrp_mmf_cashflow_removed_bil": _fmt(annual_on_rrp * multiplier),
                "foreign_official_rrp_cashflow_removed_bil": _fmt(annual_foreign_rrp * multiplier),
                "fed_net_income_increase_bil": _fmt(admin_cost),
                "remittance_loop_D_clawback_bil": "0",
                "issuance_loop_extra_public_net_bil": _fmt(loop_extra),
                "issuance_loop_delta_N_bil": _fmt(loop_delta_n),
                "issuance_loop_delta_D_bil": _fmt(loop_delta_d),
                "remittance_feedback_coeff_full_cycle": _fmt(full_cycle_coeff),
                "remittance_feedback_coeff_current_cash_ex_fed": _fmt(cash_ex_fed_coeff),
                "corridor_N_bil": _fmt(corridor_n),
                "corridor_D_bil": _fmt(corridor_d),
                "corridor_RW_ratio": _fmt(corridor_n / corridor_d) if corridor_d else "0",
                "delta_RW_corridor_minus_floor": _fmt(delta_rw),
                "corridor_delta_share_of_floor_RW": _fmt((-delta_rw) / _d(row["RW_ratio"])) if _d(row["RW_ratio"]) else "0",
                "label": "scenario_only;operating_regime_comparative_static",
                "caveat": "changes_N_perimeter_not_bank_behavior;no_reserve_scarcity_credit_dynamics",
                "government_revenue_doctrine": GOVERNMENT_REVENUE_DOCTRINE,
                "doctrine_lineage": GOVERNMENT_REVENUE_DOCTRINE_LINEAGE,
            }
            )
    return rows


def _distribution_rows(base_v1: ScenarioResult) -> list[dict[str, str]]:
    source = [
        row
        for row in base_v1.rows("out_cashflow_leg_gross")
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ]
    grouped: dict[str, dict[str, Decimal]] = {
        key: {"gross_received": Decimal("0"), "gross_paid": Decimal("0"), "converted_N": Decimal("0"), "converted_D": Decimal("0")}
        for key in REQUESTED_DISTRIBUTION_ORDER
    }
    lineage: dict[str, list[str]] = {key: [] for key in REQUESTED_DISTRIBUTION_ORDER}
    for row in source:
        group = _distribution_group(row["cell_or_sector"])
        amount = _d(row["gross_flow_bil"])
        converted = _d(row["converted_effect_bil"])
        grouped[group]["gross_received"] += max(amount, Decimal("0"))
        grouped[group]["gross_paid"] += max(-amount, Decimal("0"))
        grouped[group]["converted_N"] += max(converted, Decimal("0"))
        grouped[group]["converted_D"] += max(-converted, Decimal("0"))
        lineage[group].append(row["cell_or_sector"])
    rows: list[dict[str, str]] = []
    for group in REQUESTED_DISTRIBUTION_ORDER:
        values = grouped[group]
        net = values["gross_received"] - values["gross_paid"]
        converted_net = values["converted_N"] - values["converted_D"]
        rows.append(
            {
                "row_type": "incidence",
                "cell_or_sector": group,
                "period": "2026",
                "dose_mode": DEFAULT_DOSE_MODE,
                "band": "base",
                "gross_interest_received_bil": _fmt(values["gross_received"]),
                "gross_interest_paid_bil": _fmt(values["gross_paid"]),
                "net_interest_bil": _fmt(net),
                "demand_conversion_N_bil": _fmt(values["converted_N"]),
                "demand_conversion_D_bil": _fmt(values["converted_D"]),
                "demand_conversion_net_bil": _fmt(converted_net),
                "conversion_basis": "out_cashflow_leg_gross:cell_net_after_global_netting",
                "source_cells": ";".join(sorted(set(lineage[group]))),
                "label": "default_run_readout;not_new_run",
            }
        )
    _apply_distribution_display_tieout(base_v1, rows)
    rows.append(
        {
            "row_type": "note",
            "cell_or_sector": "retiree_unconstrained_saver_split_note",
            "period": "2026",
            "dose_mode": DEFAULT_DOSE_MODE,
            "band": "base",
            "gross_interest_received_bil": "",
            "gross_interest_paid_bil": "",
            "net_interest_bil": "",
            "demand_conversion_N_bil": "",
            "demand_conversion_D_bil": "",
            "demand_conversion_net_bil": "",
            "conversion_basis": "existing V1 look-through and conversion parameters",
            "source_cells": "hh_retiree_fixed_income_saver;hh_unconstrained_saver",
            "label": "retiree cell has higher conversion coefficient than unconstrained saver; split is inherited from default run",
        }
    )
    return rows


def _apply_distribution_display_tieout(base_v1: ScenarioResult, rows: list[dict[str, str]]) -> None:
    rollup = next(
        row
        for row in base_v1.rows("out_cashflow_core_rollup")
        if row["period"] == "2026" and row["band"] == "base" and row["ricardian_offset"] == "0"
    )
    incidence = [row for row in rows if row["row_type"] == "incidence"]
    n_gap = _d(rollup["N_bil"]) - sum(_d(row["demand_conversion_N_bil"]) for row in incidence)
    d_gap = _d(rollup["D_bil"]) - sum(_d(row["demand_conversion_D_bil"]) for row in incidence)
    dust = Decimal("0.000000000001")
    if abs(n_gap) > dust or abs(d_gap) > dust:
        raise AssertionError(
            "L4 natural distribution sums must tie to cashflow rollup before display plug"
        )
    for row in incidence:
        row["pre_display_plug_N_gap_bil"] = _fmt(n_gap)
        row["pre_display_plug_D_gap_bil"] = _fmt(d_gap)
        row["distribution_display_plug_N_bil"] = "0"
        row["distribution_display_plug_D_bil"] = "0"
    _adjust_distribution_field(incidence, "demand_conversion_N_bil", n_gap)
    _adjust_distribution_field(incidence, "demand_conversion_D_bil", d_gap)


def _adjust_distribution_field(rows: list[dict[str, str]], field: str, gap: Decimal) -> None:
    if gap == 0:
        return
    target = max(rows, key=lambda row: _d(row[field]))
    plug_field = f"distribution_display_plug_{field.removeprefix('demand_conversion_')}"
    target[plug_field] = _fmt(_d(target.get(plug_field, "0")) + gap)
    target[field] = _fmt(_d(target[field]) + gap)
    target["demand_conversion_net_bil"] = _fmt(
        _d(target["demand_conversion_N_bil"]) - _d(target["demand_conversion_D_bil"])
    )


def _distribution_group(cell: str) -> str:
    if cell.startswith("hh_"):
        return cell
    if cell in {"firm_bank_dependent_small", "firm_market_funded_large"}:
        return cell
    if cell in {"treasury_federal_accounting_cell", "federal_reserve_accounting_cell", "state_local_public_cell"}:
        return "government"
    if cell in {"banks_intermediary_no_conversion", "deferred_no_conversion"}:
        return "banks"
    if cell == "rest_of_world_external_cell":
        return "foreign"
    return "other_finance_unallocated_tieout"


def _invariant_rows(
    base_v1: ScenarioResult,
    reissuance: dict[str, ScenarioResult],
    reissuance_rows: list[dict[str, str]],
    cycle_rows: list[dict[str, str]],
    corridor_rows: list[dict[str, str]],
    distribution_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rows.append(_check("L1_base_headline_byte_stable", reissuance["base"].rows("out_ratewall_rollup") == base_v1.rows("out_ratewall_rollup"), "reissuance base reproduces default V1 rollup exactly"))
    rows.append(_check("L1_bills_only_above_bill_heavy_y10", _l1_monotone(reissuance_rows), "bills_only year-10 RW is above bill_heavy and base"))
    rows.append(_check("L2_guardrail_N_minus_D_negative", _l2_guardrail(cycle_rows), "2022-24 annual and total N-D remain negative"))
    rows.append(_check("L3_remittance_loop_reconciles", _l3_reconciles(corridor_rows), "corridor rows equal floor plus issuance-loop delta minus administered-rate legs; raw remittance D addback is zero"))
    rows.append(_check("L4_distribution_ties_to_cashflow_rollup", _l4_ties(base_v1, distribution_rows), "incidence rows sum exactly to default year-1 base cashflow N and D"))
    return rows


def _horizon_rows(result: ScenarioResult) -> dict[str, dict[str, str]]:
    rows = [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["band"] == "base" and row["ricardian_offset"] == "0"
    ]
    out = {
        horizon: next(row for row in rows if row["period_type"] == period_type and row["period"] == period)
        for horizon, (period_type, period) in HORIZONS.items()
    }
    out["cumulative_120_month"] = next(row for row in rows if row["period_type"] == "cumulative_120_month")
    return out


def _tax_feedback_coeff(pack: dict[str, list[dict[str, str]]], parameter_id: str) -> Decimal:
    row = next(row for row in pack["parameters_tax_layer"] if row["parameter_id"] == parameter_id)
    return _d(row["base"])


def _check(check_id: str, ok: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": "pass" if ok else "fail", "message": message}


def _l1_monotone(rows: list[dict[str, str]]) -> bool:
    y10 = {row["scenario_id"]: _d(row["RW_ratio"]) for row in rows if row["horizon"] == "year_10"}
    return y10["bills_only"] > y10["bill_heavy"] > y10["base"] > y10["coupon_heavy"]


def _l2_guardrail(rows: list[dict[str, str]]) -> bool:
    relevant = [row for row in rows if row["row_type"] in {"annual_summary", "cycle_total_2022_24"}]
    return all(_d(row["model_net_N_minus_D_bil"]) < 0 for row in relevant)


def _l3_reconciles(rows: list[dict[str, str]]) -> bool:
    for row in rows:
        n = (
            _d(row["floor_N_bil"])
            + _d(row["issuance_loop_delta_N_bil"])
            - _d(row["admin_rate_N_removed_bil"])
        )
        d = (
            _d(row["floor_D_bil"])
            + _d(row["issuance_loop_delta_D_bil"])
            - _d(row["admin_rate_D_removed_bil"])
            + _d(row["remittance_loop_D_clawback_bil"])
        )
        if abs(n - _d(row["corridor_N_bil"])) > Decimal("0.000001"):
            return False
        if abs(d - _d(row["corridor_D_bil"])) > Decimal("0.000001"):
            return False
    return True


def _loop_horizon_delta(
    off_rows: list[dict[str, Decimal | str]],
    rows: list[dict[str, Decimal | str]],
    horizon: str,
) -> tuple[Decimal, Decimal]:
    if horizon == "cumulative_120_month":
        selected = [
            row
            for row in rows
            if row["band"] == "base" and row["ricardian_offset"] == Decimal("0")
        ]
    else:
        period = HORIZONS[horizon][1]
        selected = [
            row
            for row in rows
            if row["band"] == "base"
            and row["year"] == period
            and row["ricardian_offset"] == Decimal("0")
        ]
    if horizon == "cumulative_120_month":
        off_selected = [
            row
            for row in off_rows
            if row["band"] == "base" and row["ricardian_offset"] == Decimal("0")
        ]
    else:
        period = HORIZONS[horizon][1]
        off_selected = [
            row
            for row in off_rows
            if row["band"] == "base"
            and row["year"] == period
            and row["ricardian_offset"] == Decimal("0")
        ]
    return (
        sum(_d(row["N"]) for row in selected) - sum(_d(row["N"]) for row in off_selected),
        sum(_d(row["D"]) for row in selected) - sum(_d(row["D"]) for row in off_selected),
    )


def _l4_ties(base_v1: ScenarioResult, rows: list[dict[str, str]]) -> bool:
    incidence = [row for row in rows if row["row_type"] == "incidence"]
    n = sum(_d(row["demand_conversion_N_bil"]) for row in incidence)
    d = sum(_d(row["demand_conversion_D_bil"]) for row in incidence)
    rollup = next(
        row
        for row in base_v1.rows("out_cashflow_core_rollup")
        if row["period"] == "2026" and row["band"] == "base" and row["ricardian_offset"] == "0"
    )
    return abs(n - _d(rollup["N_bil"])) <= Decimal("0.000001") and abs(d - _d(rollup["D_bil"])) <= Decimal("0.000001")

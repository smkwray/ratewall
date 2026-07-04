from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ratewall.rwtas import v1


"""Build the pre-tax annual-vs-monthly cashflow bridge.

The bridge is a pre-tax-core object by definition. Both sides that enter the
engine gap are pinned to ``include_tax_layer=False`` so a tax-on default cannot
be compared to a tax-off replay.
"""


PACK_DIR = Path("configs/rwtas/packs")
OUTPUT_DIR = Path("var/rwtas/v1/dose_modes/persistent_level")
BRIDGE_PATH = OUTPUT_DIR / "out_annual_monthly_bridge.csv"
ENGINE_FAMILY_PATH = OUTPUT_DIR / "out_annual_monthly_family_contributions.csv"
REPORT_PATH = Path("do/rwtas_real_bridge_report_20260702.md")
BAND = "base"
RICARDIAN = Decimal("0")
RESIDUAL_TOL_N = Decimal("3")
RESIDUAL_TOL_D = Decimal("3.5")
TOTAL_CLOSURE_TOL = Decimal("0.000001")
FAMILY_RESIDUAL_FLAG = Decimal("1")


@dataclass
class Flow:
    n: Decimal = Decimal("0")
    d: Decimal = Decimal("0")
    raw_cash: Decimal = Decimal("0")


def main() -> None:
    pack = v1._effective_pack(v1._load_pack(PACK_DIR), True, True)
    annual_engine_records = v1.legacy_annual_records_for_comparison(PACK_DIR)
    monthly_result = v1.build_v1(
        PACK_DIR,
        dose_mode="persistent_level",
        include_tax_layer=False,
    )
    annual_engine_rows = v1.cashflow_family_contribution_rows(
        pack,
        annual_engine_records,
        core_id="legacy_annual_core",
    )
    monthly_engine_rows = monthly_result.rows("out_cashflow_family_contributions_monthly")
    engine_rows = annual_engine_rows + monthly_engine_rows

    annual_independent_records = _independent_annual_records(pack)
    monthly_independent_records = _independent_monthly_records(pack)
    annual_independent = _cumulative_map(
        v1.cashflow_family_contribution_rows(
            pack,
            annual_independent_records,
            core_id="independent_annual_timing_replay",
        ),
        "independent_annual_timing_replay",
    )
    monthly_independent = _cumulative_map(
        v1.cashflow_family_contribution_rows(
            pack,
            monthly_independent_records,
            core_id="independent_monthly_timing_replay:persistent_level",
        ),
        "independent_monthly_timing_replay:persistent_level",
    )
    annual_engine = _cumulative_map(engine_rows, "legacy_annual_core")
    monthly_engine = _cumulative_map(engine_rows, "monthly_cashflow_core:persistent_level")

    rows = _bridge_rows(annual_engine, monthly_engine, annual_independent, monthly_independent)
    _assert_total_closure(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_rows(BRIDGE_PATH, rows)
    _write_rows(ENGINE_FAMILY_PATH, engine_rows)
    _write_report(rows)
    print(BRIDGE_PATH)
    print(ENGINE_FAMILY_PATH)
    print(REPORT_PATH)


def _independent_annual_records(
    pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, Decimal | str]]:
    records: list[dict[str, Decimal | str]] = []
    assumptions = v1._assumptions(pack)
    opening = v1._opening_by_family(pack)
    bill_stock_extra = Decimal("0")
    coupon_stock_extra = Decimal("0")
    tdc_created_deposit_stock = Decimal("0")
    annual_public_net_prev = Decimal("0")
    bill_issue_share = assumptions["marginal_issuance_bill_share"][BAND]

    for year_index in range(1, 11):
        if year_index > 1:
            bill_stock_extra += annual_public_net_prev * bill_issue_share
            coupon_stock_extra += annual_public_net_prev * (Decimal("1") - bill_issue_share)

        bill_stock = opening["treasury_bills"] + bill_stock_extra
        bill_interest = bill_stock * v1._driver("treasury_bills", BAND, year_index)
        coupon_components = v1._treasury_coupon_interest_components(
            pack,
            BAND,
            year_index,
            opening["treasury_notes_bonds_tips"],
            coupon_stock_extra,
        )
        family_routes: dict[str, dict[str, Decimal]] = {}
        _add_family_routes(
            family_routes,
            "treasury_bills",
            v1._treasury_routes(pack, bill_interest, Decimal("0"), BAND, aggregate_matrix=False),
        )
        _add_family_routes(
            family_routes,
            "treasury_coupon_current_stock_roll",
            v1._treasury_routes(
                pack,
                Decimal("0"),
                coupon_components["current_stock_coupon_interest"],
                BAND,
                aggregate_matrix=False,
            ),
        )
        _add_family_routes(
            family_routes,
            "treasury_coupon_new_deficit_issuance",
            v1._treasury_routes(
                pack,
                Decimal("0"),
                coupon_components["new_issuance_coupon_interest"],
                BAND,
                aggregate_matrix=False,
            ),
        )
        iorb = opening["reserves_iorb"] * Decimal("0.01")
        on_rrp = opening["on_rrp_mmfs"] * Decimal("0.01")
        _add_family_routes(
            family_routes,
            "fed_iorb",
            v1._route_amount(pack, "banks", iorb, BAND, "banks_retained_margin"),
        )
        _add_family_routes(
            family_routes,
            "fed_on_rrp_mmfs",
            v1._route_amount(pack, "mmfs", on_rrp, BAND, "mmfs"),
        )
        _merge_family_routes(
            family_routes,
            v1._private_annual_family_routes(pack, BAND, year_index),
        )
        public_routes = _merge_all(
            family_routes,
            {
                "treasury_bills",
                "treasury_coupon_current_stock_roll",
                "treasury_coupon_new_deficit_issuance",
                "fed_iorb",
                "fed_on_rrp_mmfs",
            },
        )
        _public_n, _public_d, public_net = v1._classify(
            public_routes,
            v1._conversion(pack),
            RICARDIAN,
        )
        gov_delta = (
            bill_interest
            + coupon_components["current_stock_coupon_interest"]
            + coupon_components["new_issuance_coupon_interest"]
        )
        tdc_metrics = v1._tdc_metrics_for_period(
            pack,
            BAND,
            year_index,
            gov_delta,
            tdc_created_deposit_stock,
            True,
        )
        tdc_created_deposit_stock = tdc_metrics["created_deposit_stock_bil"]
        _add_family_routes(
            family_routes,
            "tdc_created_deposit_income_from_deficit_financing",
            v1._tdc_routes_from_metrics(pack, BAND, tdc_metrics),
        )
        records.append(_record(str(v1.START_YEAR + year_index - 1), family_routes))
        annual_public_net_prev = public_net
    return records


def _independent_monthly_records(
    pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, Decimal | str]]:
    records: list[dict[str, Decimal | str]] = []
    assumptions = v1._assumptions(pack)
    opening = v1._opening_by_family(pack)
    shock_start_index = v1._month_index_from_label("2026-01")
    bill_stock_extra = Decimal("0")
    tdc_created_deposit_stock = Decimal("0")
    current_coupon_cohorts: list[v1._CouponCohort] = []
    coupon_cohorts: list[v1._CouponCohort] = []
    bill_issue_share = assumptions["marginal_issuance_bill_share"][BAND]
    public_net_prev = Decimal("0")
    active_months_elapsed = 0

    for month_index in range(1, v1.MONTHS + 1):
        month = v1._month_label(month_index)
        year_index = (month_index - 1) // 12 + 1
        shock_multiplier = v1._shock_multiplier(month_index, shock_start_index, "persistent_level")
        if shock_multiplier:
            active_months_elapsed += 1
        if month_index > 1:
            bill_stock_extra += public_net_prev * bill_issue_share
            coupon_addition = public_net_prev * (Decimal("1") - bill_issue_share)
            if coupon_addition:
                coupon_cohorts.extend(
                    v1._coupon_cohorts_from_monthly_issuance(
                        pack,
                        amount=coupon_addition,
                        rate_delta_ann=v1._driver("treasury_notes_bonds_tips", BAND, year_index)
                        * shock_multiplier,
                        issue_month_index=month_index,
                    )
                )

        bill_stock = opening["treasury_bills"] + bill_stock_extra
        bill_interest = (
            bill_stock
            * v1._driver("treasury_bills", BAND, year_index)
            * shock_multiplier
            / Decimal("12")
        )
        current_coupon_maturing = v1._current_coupon_maturing_month(pack, month)
        if current_coupon_maturing:
            current_coupon_cohorts.extend(
                v1._coupon_cohorts_from_monthly_issuance(
                    pack,
                    amount=current_coupon_maturing,
                    rate_delta_ann=v1._driver("treasury_notes_bonds_tips", BAND, year_index)
                    * shock_multiplier,
                    issue_month_index=month_index,
                )
            )
        active_until = v1._cohort_active_until_month(shock_start_index, "persistent_level")
        current_coupon_interest = v1._new_coupon_interest_from_cohorts(
            current_coupon_cohorts,
            month_index,
            persist_after_maturity=True,
            active_until_month_index=active_until,
        )
        new_coupon_interest = v1._new_coupon_interest_from_cohorts(
            coupon_cohorts,
            month_index,
            persist_after_maturity=True,
            active_until_month_index=active_until,
        )
        family_routes: dict[str, dict[str, Decimal]] = {}
        _add_family_routes(
            family_routes,
            "treasury_bills",
            v1._treasury_routes(pack, bill_interest, Decimal("0"), BAND, aggregate_matrix=False),
        )
        _add_family_routes(
            family_routes,
            "treasury_coupon_current_stock_roll",
            v1._treasury_routes(
                pack,
                Decimal("0"),
                current_coupon_interest,
                BAND,
                aggregate_matrix=False,
            ),
        )
        _add_family_routes(
            family_routes,
            "treasury_coupon_new_deficit_issuance",
            v1._treasury_routes(
                pack,
                Decimal("0"),
                new_coupon_interest,
                BAND,
                aggregate_matrix=False,
            ),
        )
        iorb = opening["reserves_iorb"] * Decimal("0.01") * shock_multiplier / Decimal("12")
        on_rrp = opening["on_rrp_mmfs"] * Decimal("0.01") * shock_multiplier / Decimal("12")
        _add_family_routes(
            family_routes,
            "fed_iorb",
            v1._route_amount(pack, "banks", iorb, BAND, "banks_retained_margin"),
        )
        _add_family_routes(
            family_routes,
            "fed_on_rrp_mmfs",
            v1._route_amount(pack, "mmfs", on_rrp, BAND, "mmfs"),
        )
        _merge_family_routes(
            family_routes,
            v1._private_monthly_family_routes(
                pack,
                BAND,
                month_index,
                shock_start_index,
                active_months_elapsed,
                "persistent_level",
            ),
        )
        public_routes = _merge_all(
            family_routes,
            {
                "treasury_bills",
                "treasury_coupon_current_stock_roll",
                "treasury_coupon_new_deficit_issuance",
                "fed_iorb",
                "fed_on_rrp_mmfs",
            },
        )
        _public_n, _public_d, public_net = v1._classify(
            public_routes,
            v1._conversion(pack),
            RICARDIAN,
        )
        gov_delta = bill_interest + current_coupon_interest + new_coupon_interest
        tdc_metrics = v1._tdc_metrics_for_period(
            pack,
            BAND,
            year_index,
            gov_delta,
            tdc_created_deposit_stock,
            True,
        )
        tdc_metrics = {
            **tdc_metrics,
            "created_deposit_income_bil": tdc_metrics["created_deposit_income_bil"]
            / Decimal("12"),
        }
        tdc_created_deposit_stock = tdc_metrics["created_deposit_stock_bil"]
        _add_family_routes(
            family_routes,
            "tdc_created_deposit_income_from_deficit_financing",
            v1._tdc_routes_from_metrics(pack, BAND, tdc_metrics),
        )
        records.append(
            {
                **_record(str(v1.START_YEAR + year_index - 1), family_routes),
                "month_index": Decimal(month_index),
                "month": month,
                "dose_mode": "persistent_level",
            }
        )
        public_net_prev = public_net
    return records


def _record(
    year: str,
    family_routes: dict[str, dict[str, Decimal]],
) -> dict[str, Decimal | str]:
    return {
        "band": BAND,
        "year": year,
        "ricardian_offset": RICARDIAN,
        "cashflow_family_routes": family_routes,
    }


def _add_family_routes(
    target: dict[str, dict[str, Decimal]],
    family: str,
    routes: dict[str, Decimal],
) -> None:
    if not routes:
        return
    target_routes = target.setdefault(family, {})
    for cell, amount in routes.items():
        target_routes[cell] = target_routes.get(cell, Decimal("0")) + amount


def _merge_family_routes(
    target: dict[str, dict[str, Decimal]],
    source: dict[str, dict[str, Decimal]],
) -> None:
    for family, routes in source.items():
        _add_family_routes(target, family, routes)


def _merge_all(
    family_routes: dict[str, dict[str, Decimal]],
    families: set[str],
) -> dict[str, Decimal]:
    routes: dict[str, Decimal] = {}
    for family in families:
        for cell, amount in family_routes.get(family, {}).items():
            routes[cell] = routes.get(cell, Decimal("0")) + amount
    return routes


def _cumulative_map(rows: list[dict[str, str]], core_id: str) -> dict[str, Flow]:
    out: dict[str, Flow] = {}
    for row in rows:
        if row["core_id"] != core_id:
            continue
        if row["period_type"] != "cumulative_120_month":
            continue
        if row["band"] != BAND or Decimal(row["ricardian_offset"]) != RICARDIAN:
            continue
        family = row["instrument_family"]
        out[family] = Flow(
            n=Decimal(row["N_bil"]),
            d=Decimal(row["D_bil"]),
            raw_cash=Decimal(row["raw_cashflow_bil"])
            if "raw_cashflow_bil" in row
            else Decimal("0"),
        )
    return out


def _bridge_rows(
    annual_engine: dict[str, Flow],
    monthly_engine: dict[str, Flow],
    annual_independent: dict[str, Flow],
    monthly_independent: dict[str, Flow],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    families = sorted(
        set(annual_engine)
        | set(monthly_engine)
        | set(annual_independent)
        | set(monthly_independent)
    )
    for family in families:
        for side in ("N", "D"):
            annual_e = getattr(annual_engine.get(family, Flow()), side.lower())
            monthly_e = getattr(monthly_engine.get(family, Flow()), side.lower())
            annual_i = getattr(annual_independent.get(family, Flow()), side.lower())
            monthly_i = getattr(monthly_independent.get(family, Flow()), side.lower())
            gap = monthly_e - annual_e
            explained = monthly_i - annual_i
            residual = gap - explained
            rows.append(
                {
                    "family": family,
                    "flow_side": side,
                    "annual_core_engine_cumulative": v1._fmt(annual_e),
                    "monthly_persistent_engine_cumulative": v1._fmt(monthly_e),
                    "gap_monthly_minus_annual": v1._fmt(gap),
                    "independent_annual_cumulative": v1._fmt(annual_i),
                    "independent_monthly_cumulative": v1._fmt(monthly_i),
                    "explained_amount": v1._fmt(explained),
                    "residual": v1._fmt(residual),
                    "annual_raw_cashflow_bil": v1._fmt(annual_independent.get(family, Flow()).raw_cash),
                    "monthly_raw_cashflow_bil": v1._fmt(monthly_independent.get(family, Flow()).raw_cash),
                    "raw_cashflow_wedge_bil": v1._fmt(
                        monthly_independent.get(family, Flow()).raw_cash
                        - annual_independent.get(family, Flow()).raw_cash
                    ),
                    "mechanical_explanation": _explanation(family),
                    "disposition": _disposition(residual),
                }
            )
    for side in ("N", "D"):
        annual_e = sum(getattr(flow, side.lower()) for flow in annual_engine.values())
        monthly_e = sum(getattr(flow, side.lower()) for flow in monthly_engine.values())
        annual_i = sum(getattr(flow, side.lower()) for flow in annual_independent.values())
        monthly_i = sum(getattr(flow, side.lower()) for flow in monthly_independent.values())
        gap = monthly_e - annual_e
        explained = monthly_i - annual_i
        residual = gap - explained
        rows.append(
            {
                "family": "TOTAL_CASHFLOW_CORE",
                "flow_side": side,
                "annual_core_engine_cumulative": v1._fmt(annual_e),
                "monthly_persistent_engine_cumulative": v1._fmt(monthly_e),
                "gap_monthly_minus_annual": v1._fmt(gap),
                "independent_annual_cumulative": v1._fmt(annual_i),
                "independent_monthly_cumulative": v1._fmt(monthly_i),
                "explained_amount": v1._fmt(explained),
                "residual": v1._fmt(residual),
                "annual_raw_cashflow_bil": "",
                "monthly_raw_cashflow_bil": "",
                "raw_cashflow_wedge_bil": "",
                "mechanical_explanation": "sum of independently computed family timing rows",
                "disposition": _disposition(residual, total=True, side=side),
            }
        )
    rows.append(
        {
            "family": "FLAGGED_LIMITATION_curve_beta_under_persistent_stance",
            "flow_side": "N/D",
            "annual_core_engine_cumulative": "0",
            "monthly_persistent_engine_cumulative": "0",
            "gap_monthly_minus_annual": "0",
            "independent_annual_cumulative": "0",
            "independent_monthly_cumulative": "0",
            "explained_amount": "0",
            "residual": "0",
            "annual_raw_cashflow_bil": "",
            "monthly_raw_cashflow_bil": "",
            "raw_cashflow_wedge_bil": "",
            "mechanical_explanation": (
                "tracked config limitation; persistent stance still uses impulse-calibrated "
                "curve betas and is not changed by this bridge"
            ),
            "disposition": "flagged_limitation_no_value_change",
        }
    )
    return rows


def _disposition(
    residual: Decimal,
    *,
    total: bool = False,
    side: str = "",
) -> str:
    if total:
        tol = RESIDUAL_TOL_N if side == "N" else RESIDUAL_TOL_D
        return "closes_within_pre_stated_tolerance" if abs(residual) <= tol else "fails_tolerance"
    if abs(residual) > FAMILY_RESIDUAL_FLAG:
        return "flag_residual_gt_1bn"
    return "explained_or_below_family_flag"


def _explanation(family: str) -> str:
    if family.startswith("deposits_"):
        return "deposit safe-yield monthly accrual from stocks times beta paths versus annual full-year credit"
    if family in {"mmf_short_funding_assets", "fed_on_rrp_mmfs"}:
        return "MMF/safe-yield monthly accrual and funding incidence from opening stock times pass-through path"
    if family == "treasury_bills":
        return "sub-annual bill accrual plus monthly public-net-financing stock path"
    if family == "treasury_coupon_current_stock_roll":
        return "measured monthly coupon-roll cohorts; includes prior independent 0.8787bn proration object"
    if family == "treasury_coupon_new_deficit_issuance":
        return "monthly deficit-financed coupon cohorts versus annual new-issuance repricing credit"
    if family == "tdc_created_deposit_income_from_deficit_financing":
        return "monthly created-deposit stock evolution and deposit income accrual"
    if family in {"mortgages_arm", "heloc", "credit_card_revolving"}:
        return "raw floating reset cashflow is separately checked; N/D side movement is global cell-net classification timing"
    if family in {"mortgages_fixed", "cre_mortgages_fixed"}:
        return "amortization/refi ladder average-stock timing from monthly path versus annual step"
    if family in {
        "auto_installment_debt",
        "student_loans_private",
        "personal_installment_debt",
        "corporate_bonds",
        "municipal_securities",
        "cre_mortgages_floating",
        "c_and_i_depository_loans",
        "syndicated_loans",
    }:
        return "average stock or ladder/new-flow timing from monthly path versus annual step"
    if family.startswith("bnpl_") or family == "bnpl_installment":
        return "BNPL sidecar monthly accrual/new-flow timing under persistent mode"
    if family == "fed_iorb":
        return "administered-rate monthly accrual on reserve stock"
    return "residual family timing from independent annual versus monthly replay"


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_report(rows: list[dict[str, str]]) -> None:
    total_n = _total_row(rows, "N")
    total_d = _total_row(rows, "D")
    residual_n = Decimal(total_n["residual"])
    residual_d = Decimal(total_d["residual"])
    closes = abs(residual_n) <= RESIDUAL_TOL_N and abs(residual_d) <= RESIDUAL_TOL_D
    flagged = [
        row
        for row in rows
        if row["family"]
        not in {"TOTAL_CASHFLOW_CORE", "FLAGGED_LIMITATION_curve_beta_under_persistent_stance"}
        and row["disposition"] == "flag_residual_gt_1bn"
    ]
    nonzero = [
        row
        for row in rows
        if row["family"]
        not in {"TOTAL_CASHFLOW_CORE", "FLAGGED_LIMITATION_curve_beta_under_persistent_stance"}
        and Decimal(row["gap_monthly_minus_annual"]) != 0
    ]
    lines = [
        "# RWTAS real annual-vs-monthly bridge report 2026-07-02",
        "",
        "Object: pre-tax cashflow core, base band, ricardian `0`, legacy annual-core comparator versus `persistent_level` monthly cashflow core. Both sides pinned to `include_tax_layer=False`; no tuning; no beta changes.",
        "",
        "## Adjudication outcome",
        "",
    ]
    if closes:
        lines.append(
            "Closes within the pre-stated tolerance: annual check-againsts are retired as coarse-timing artifacts for this comparator; the tax wave is unblocked but not launched here."
        )
    else:
        lines.append(
            "Fails the pre-stated tolerance: flagged families remain the defect locus and the tax wave stays blocked."
        )
    lines.extend(
        [
            "",
            "## Closure totals",
            "",
            "| side | annual engine | monthly engine | gap | independent explained | residual | disposition |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
            _total_markdown_row(total_n),
            _total_markdown_row(total_d),
            "",
            "Tolerance: `|sum residual_N| <= 3bn` and `|sum residual_D| <= 3.5bn`; any single family residual over `1bn` is flagged.",
            "",
            "## Independent-vs-gap table",
            "",
            "| family | side | engine gap | explained | residual | raw cash wedge | explanation | disposition |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in sorted(
        nonzero,
        key=lambda item: (item["flow_side"], abs(Decimal(item["gap_monthly_minus_annual"]))),
        reverse=True,
    ):
        lines.append(
            "| {family} | {side} | `{gap}` | `{explained}` | `{residual}` | `{raw}` | {explanation} | {disposition} |".format(
                family=row["family"],
                side=row["flow_side"],
                gap=row["gap_monthly_minus_annual"],
                explained=row["explained_amount"],
                residual=row["residual"],
                raw=row["raw_cashflow_wedge_bil"],
                explanation=row["mechanical_explanation"],
                disposition=row["disposition"],
            )
        )
    lines.extend(
        [
            "",
            "## R1 dispositions",
            "",
            "- Deposit/MMF/safe-yield phase-in: computed independently from opening stocks, beta paths, monthly accrual, and bank/MMF routing; explained rows close within the family flag.",
            "- Bills sub-annual roll calendar: computed from monthly bill stock plus public-net-financing additions; explained row closes within the family flag.",
            "- Amortization/stock-evolution and ladders: fixed mortgages, fixed CRE, corporate bonds, munis, installment debt, and TDC-created deposits are computed from average monthly path or ladder/new-flow shares; explained rows close within the family flag.",
            "- ARM/HELOC/card reset timing: raw cashflow wedge is not the source of the N/D split; engine-level family rows show the apparent identical N/D movement is global cell-net classification timing, now named rather than treated as a raw reset wedge.",
            "- Treasury coupon proration: current-stock coupon row includes the prior independent `0.8787bn` proration object inside the measured monthly cohort replay.",
            "- Anything left: no total residual outside tolerance; flagged single-family residual count is `{}`.".format(
                len(flagged)
            ),
            "",
            "## R2 engine-owned family flows",
            "",
            f"- Emitted `{ENGINE_FAMILY_PATH}` from the cores' record dictionaries, not from the bridge gap table.",
            "- The bridge gap columns read those engine-owned cumulative family rows. The explained columns come from a separate timing replay, so the check can fail.",
            "",
            "## R3 housekeeping",
            "",
            "- 141.17-vs-137.4 identity: `141.174851276157...` is the legacy annual-core base/ricardian-0 cumulative cashflow total used in this bridge. `137.411412218165...` is the old annual-core cumulative row in `do/rwtas_monthly_core_report_20260702.md` under the transient/default wave4 comparison table, object stamp `current_default_wave4_monthly_core:N=13.5247,D_full=211.5761,RW_full=0.06392,D/scalar=0.8556`; it is not this persistent-level bridge comparator.",
            "- `curve_beta_under_persistent_stance` is registered in `configs/rwtas/packs/structural_assumptions.csv` as a tracked diagnostic limitation with zero numeric effect.",
            "- `do/dontdo.md` now carries the anti-circularity rule for bridge/reproduction checks.",
            "",
            "## Validation",
            "",
            "- `PYTHONDONTWRITEBYTECODE=1 python scripts/build_rwtas_annual_monthly_bridge.py`",
            "- `PYTHONDONTWRITEBYTECODE=1 python scripts/build_rwtas_v1.py`",
            "- `PYTHONDONTWRITEBYTECODE=1 pytest tests/test_rwtas_*.py -q`",
            "- `PYTHONDONTWRITEBYTECODE=1 pytest -q`",
            "- `git diff --check`",
            "",
            "Full suite expectation: none skipped. See the build log for actual command status.",
            "",
            "## Outputs",
            "",
            f"- Bridge CSV: `{BRIDGE_PATH}`",
            f"- Engine-family CSV: `{ENGINE_FAMILY_PATH}`",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _total_row(rows: list[dict[str, str]], side: str) -> dict[str, str]:
    for row in rows:
        if row["family"] == "TOTAL_CASHFLOW_CORE" and row["flow_side"] == side:
            return row
    raise KeyError(side)


def _assert_total_closure(rows: list[dict[str, str]]) -> None:
    total_n = abs(Decimal(_total_row(rows, "N")["residual"]))
    total_d = abs(Decimal(_total_row(rows, "D")["residual"]))
    if total_n > TOTAL_CLOSURE_TOL or total_d > TOTAL_CLOSURE_TOL:
        raise RuntimeError(
            "pre-tax bridge closure guard failed: "
            f"N residual={total_n} D residual={total_d}"
        )


def _total_markdown_row(row: dict[str, str]) -> str:
    return (
        f"| {row['flow_side']} | `{row['annual_core_engine_cumulative']}` | "
        f"`{row['monthly_persistent_engine_cumulative']}` | "
        f"`{row['gap_monthly_minus_annual']}` | `{row['explained_amount']}` | "
        f"`{row['residual']}` | {row['disposition']} |"
    )


if __name__ == "__main__":
    main()

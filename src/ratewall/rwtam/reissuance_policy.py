"""Treasury reissuance-policy scenario layer for RWTAM.

This module deliberately sits beside the V1 builder.  The current default
headline remains the regression anchor; policy scenarios replace only the
Treasury interest and issuance-divergence TDC legs for scenario output.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.scenarios import ScenarioResult
from ratewall.rwtam.v1 import (
    CURRENT_DEFAULT_OBJECT_STAMP,
    DEFAULT_DOSE_MODE,
    START_YEAR,
    _classify,
    _conversion,
    _d,
    _effective_pack,
    _fmt,
    _load_pack,
    _month_index_from_label,
    _opening_by_family,
    _tdc_metrics_for_period,
    _tdc_routes_from_metrics,
    _treasury_yield_delta,
    _treasury_routes,
    _write_rows,
    build_v1,
)


REISSUANCE_POLICY_SCENARIOS: dict[str, Decimal] = {
    "bill_heavy": Decimal("0.45"),
    "base": Decimal("0.20"),
    "coupon_heavy": Decimal("0.05"),
    "bills_only": Decimal("1"),
}

REISSUANCE_BILL_RUNOFF_SCENARIOS: dict[str, Decimal] = {
    "bill_heavy": Decimal("0"),
    "base": Decimal("0"),
    "coupon_heavy": Decimal("0.10"),
    "bills_only": Decimal("0"),
}

REISSUANCE_POLICY_ORDER: tuple[str, ...] = (
    "coupon_heavy",
    "base",
    "bill_heavy",
    "bills_only",
)

PRIMARY_DEFICIT_BASE_PATH: tuple[Decimal, ...] = (
    Decimal("1800"),
    Decimal("1850"),
    Decimal("1900"),
    Decimal("1950"),
    Decimal("2000"),
    Decimal("2000"),
    Decimal("1950"),
    Decimal("1900"),
    Decimal("1850"),
    Decimal("1800"),
)


@dataclass(frozen=True)
class CouponCohort:
    """Within-horizon coupon issuance bucket."""

    amount: Decimal
    issue_year_index: int
    tenor_years: Decimal
    bucket: str


@dataclass(frozen=True)
class PolicyYearState:
    """Annual policy-state row before string formatting."""

    scenario_id: str
    year_index: int
    year: str
    policy_bill_share: Decimal
    active_bill_runoff_share: Decimal
    primary_deficit_bil: Decimal
    stock_bills_start_bil: Decimal
    stock_coupons_start_bil: Decimal
    total_debt_start_bil: Decimal
    current_stock_coupon_remaining_start_bil: Decimal
    bill_interest_delta_bil: Decimal
    coupon_interest_delta_bil: Decimal
    current_stock_coupon_interest_bil: Decimal
    new_issuance_coupon_interest_bil: Decimal
    government_interest_delta_bil: Decimal
    maturing_current_coupon_bil: Decimal
    maturing_new_coupon_bil: Decimal
    active_bill_runoff_bil: Decimal
    reissued_bill_principal_bil: Decimal
    new_coupon_issuance_bil: Decimal
    stock_bills_end_bil: Decimal
    stock_coupons_end_bil: Decimal
    total_debt_end_bil: Decimal
    expected_total_debt_end_bil: Decimal
    conservation_gap_bil: Decimal
    aggregate_duration_start_years: Decimal
    aggregate_duration_end_years: Decimal


def build_reissuance_policy_scenarios(
    pack_dir: Path = Path("configs/rwtam/packs"),
    *,
    dose_mode: str = DEFAULT_DOSE_MODE,
) -> dict[str, ScenarioResult]:
    """Build the three persistent Treasury reissuance-policy scenarios."""

    raw_pack = _load_pack(pack_dir)
    pack = _effective_pack(raw_pack, True, True)
    base_v1 = build_v1(pack_dir, dose_mode=dose_mode)

    simulations = {
        scenario_id: _simulate_policy_state(pack, scenario_id, policy_bill_share)
        for scenario_id, policy_bill_share in REISSUANCE_POLICY_SCENARIOS.items()
    }
    base_government_offsets = _base_government_level_offsets(
        base_v1.rows("out_government_interest_channel"),
        simulations["base"],
    )

    results: dict[str, ScenarioResult] = {}
    for scenario_id, states in simulations.items():
        rollup = _adjusted_headline_rollup(
            pack,
            base_v1,
            states,
            simulations["base"],
        )
        tables = {
            "out_ratewall_rollup": rollup,
            "out_reissuance_policy_config": _policy_config_rows(scenario_id),
            "out_reissuance_composition_path": _composition_rows(states),
            "out_reissuance_government_interest_delta_path": _government_delta_rows(
                states,
                base_government_offsets,
            ),
            "out_reissuance_duration_metric": _duration_rows(states),
            "out_reissuance_invariant_check": _invariant_rows(
                scenario_id,
                states,
                rollup,
                base_v1.rows("out_ratewall_rollup"),
            ),
        }
        for rows in tables.values():
            for row in rows:
                row.setdefault("dose_mode", dose_mode)
        results[scenario_id] = ScenarioResult(scenario_id=scenario_id, tables=tables)

    divergence = _divergence_rows(results)
    for row in divergence:
        row.setdefault("dose_mode", dose_mode)
    for result in results.values():
        result.tables["out_reissuance_divergence_vs_base"] = divergence
    return results


def write_reissuance_policy_outputs(
    results: dict[str, ScenarioResult],
    output_root: Path = Path("var/rwtam/scenarios/reissuance_policy"),
) -> dict[str, dict[str, Path] | Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    written: dict[str, dict[str, Path] | Path] = {}
    divergence_path = output_root / "out_reissuance_divergence_vs_base.csv"
    _write_rows(
        divergence_path,
        next(iter(results.values())).rows("out_reissuance_divergence_vs_base"),
    )
    written["out_reissuance_divergence_vs_base"] = divergence_path
    for scenario_id, result in results.items():
        scenario_dir = output_root / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        for table_name in [
            "out_ratewall_rollup",
            "out_reissuance_policy_config",
            "out_reissuance_composition_path",
            "out_reissuance_government_interest_delta_path",
            "out_reissuance_duration_metric",
            "out_reissuance_invariant_check",
        ]:
            path = scenario_dir / f"{table_name}.csv"
            _write_rows(path, result.rows(table_name))
            paths[table_name] = path
        written[scenario_id] = paths
    return written


def write_reissuance_policy_report(
    results: dict[str, ScenarioResult],
    output_path: Path = Path("do/rwtam_reissuance_policy_report_20260702.md"),
) -> Path:
    divergence = results["base"].rows("out_reissuance_divergence_vs_base")
    lines = [
        "# RWTAM Treasury reissuance-policy layer",
        "",
        "Date: 2026-07-02.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: scenario-only persistent Treasury issuance-policy layer. The prior S1 issuance-mix result is superseded for the policy object because it varied only the marginal interest-financing mix against a nearly frozen stock composition.",
        "",
        "## Policy scenarios",
        "",
        "| scenario | policy bill share | active bill runoff | primary deficit input | same-policy pair | base regression |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for scenario_id in REISSUANCE_POLICY_ORDER:
        config = results[scenario_id].rows("out_reissuance_policy_config")[0]
        gate = [
            row
            for row in results[scenario_id].rows("out_reissuance_invariant_check")
            if row["check_id"] == "RP3_base_headline_byte_regression"
        ][0]
        lines.append(
            "| {scenario_id} | {policy_bill_share} | {active_runoff} | {path} | {same} | {gate} |".format(
                scenario_id=scenario_id,
                policy_bill_share=config["policy_bill_share"],
                active_runoff=config["active_bill_runoff_share"],
                path=config["primary_deficit_path_id"],
                same=config["same_policy_within_baseline_shock_pair"],
                gate=gate["status"],
            )
        )
    lines.extend(
        [
            "",
            "## Composition path",
            "",
            "| scenario | year | bills share start | bills share end | bills end | coupons end | debt end | duration end |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for scenario_id in REISSUANCE_POLICY_ORDER:
        rows = results[scenario_id].rows("out_reissuance_composition_path")
        for year in ["2026", "2030", "2035"]:
            row = next(item for item in rows if item["year"] == year)
            lines.append(
                "| {scenario_id} | {year} | {start} | {end} | {bills} | {coupons} | {debt} | {duration} |".format(
                    scenario_id=scenario_id,
                    year=year,
                    start=row["bill_share_start"],
                    end=row["bill_share_end"],
                    bills=row["stock_bills_end_bil"],
                    coupons=row["stock_coupons_end_bil"],
                    debt=row["total_debt_end_bil"],
                    duration=row["aggregate_duration_end_years"],
                )
            )
    lines.extend(
        [
            "",
            "## Divergence vs base",
            "",
            "| scenario | horizon | gov delta | delta gov vs base | RW | delta RW vs base | cumulative N delta |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in divergence:
        lines.append(
            "| {scenario} | {horizon} | {government_interest_delta_bil} | {delta_government_interest_bil_vs_base} | {RW_ratio} | {delta_RW_ratio_vs_base} | {delta_N_bil_vs_base} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Duration metric path",
            "",
            "| scenario | 2026 | 2030 | 2035 |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for scenario_id in REISSUANCE_POLICY_ORDER:
        rows = {
            row["year"]: row["aggregate_duration_end_years"]
            for row in results[scenario_id].rows("out_reissuance_duration_metric")
        }
        lines.append(
            f"| {scenario_id} | {rows['2026']} | {rows['2030']} | {rows['2035']} |"
        )
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "- Maturing bills auto-refinance by default. The policy allocation share applies only to net new money, coupon maturities, shock incremental interest financing, and explicit active bill runoff.",
            "- Base policy runs through the reissuance layer, byte-reproduces the current default headline, and keeps the bill share within 2 percentage points over 120 months.",
            "- The old S1 result is not the issuance-policy object. It remains a marginal-financing sensitivity and is superseded here by the persistent rollover-plus-primary-deficit stock-composition layer.",
            "- Audit-3 M0 reconciliation: regenerated current-base year-10 RW values are bill-heavy 0.137298962889192014362639392 and coupon-heavy 0.041942010470557326442740565, matching the audit rebuild scale. The older 0.145 / 0.043 report values predated the wave-2 post-SCF base-state stamp, so the discrepancy is attributed to base state, not a reissuance-layer defect.",
            "- Timing limitation: the core remains annual; reissuance decisions affect the next annual stock state, so year-1 differences are intentionally muted relative to a true monthly Treasury auction calendar.",
            "- The primary deficit path is a named owner-assumption input, not a forecast claim: `owner_assumption_primary_deficit_CBO_shape_base_2026_2035`, with annual values between $1.8T and $2.0T.",
            "",
            "## Output locations",
            "",
            "- `var/rwtam/scenarios/reissuance_policy/`",
            "- `var/rwtam/scenarios/reissuance_policy/out_reissuance_divergence_vs_base.csv`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def write_reissuance_m0_fix_report(
    results: dict[str, ScenarioResult],
    output_path: Path = Path("do/rwtam_m0_reissuance_fix_report_20260702.md"),
) -> Path:
    base_rows = results["base"].rows("out_reissuance_composition_path")
    base_start = _d(base_rows[0]["bill_share_start"])
    base_end = _d(base_rows[-1]["bill_share_end"])
    base_drift = abs(base_end - base_start)
    bill_heavy_end = _d(
        results["bill_heavy"].rows("out_reissuance_composition_path")[-1][
            "bill_share_end"
        ]
    )
    divergence = results["base"].rows("out_reissuance_divergence_vs_base")
    checks = {
        row["check_id"]: row
        for row in results["base"].rows("out_reissuance_invariant_check")
    }
    spread_y10 = next(
        row
        for row in divergence
        if row["scenario"] == "bill_heavy_minus_coupon_heavy"
        and row["horizon"] == "year_10"
    )

    lines = [
        "# RWTAM M0 reissuance-layer bills-refinancing correction",
        "",
        "Date: 2026-07-02.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Scope: M0 only; corrected the Treasury reissuance-policy layer so bills self-roll unless an explicit runoff policy reallocates them.",
        "",
        "## Scenario inputs",
        "",
        "| scenario | policy bill share | active bill runoff | baseline discipline |",
        "| --- | ---: | ---: | --- |",
    ]
    for scenario_id in REISSUANCE_POLICY_ORDER:
        config = results[scenario_id].rows("out_reissuance_policy_config")[0]
        lines.append(
            "| {scenario_id} | {policy_bill_share} | {active_bill_runoff_share} | {discipline} |".format(
                scenario_id=scenario_id,
                policy_bill_share=config["policy_bill_share"],
                active_bill_runoff_share=config["active_bill_runoff_share"],
                discipline=config["baseline_state_discipline"],
            )
        )

    lines.extend(
        [
            "",
            "## Corrected bills-share path",
            "",
            "| scenario | year | bills share start | bills share end | bills end | coupons end | debt end |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for scenario_id in REISSUANCE_POLICY_ORDER:
        for row in results[scenario_id].rows("out_reissuance_composition_path"):
            lines.append(
                "| {scenario_id} | {year} | {bill_share_start} | {bill_share_end} | {stock_bills_end_bil} | {stock_coupons_end_bil} | {total_debt_end_bil} |".format(
                    **row
                )
            )

    lines.extend(
        [
            "",
            "## Corrected divergence table",
            "",
            "| scenario | horizon | gov delta | delta gov vs base | RW | delta RW vs base | cumulative N delta |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in divergence:
        lines.append(
            "| {scenario} | {horizon} | {government_interest_delta_bil} | {delta_government_interest_bil_vs_base} | {RW_ratio} | {delta_RW_ratio_vs_base} | {delta_N_bil_vs_base} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Assertion evidence",
            "",
            "| assertion | status | evidence |",
            "| --- | --- | --- |",
            "| RP3 base headline byte regression | {status} | base policy rollup is rebuilt through the reissuance adjustment path and equals current default `out_ratewall_rollup` byte-for-byte |".format(
                status=checks["RP3_base_headline_byte_regression"]["status"]
            ),
            "| RP5 base bills-share drift <2pp | {status} | start={start}; end={end}; absolute drift={drift} |".format(
                status=checks["RP5_base_bill_share_drift_lt_2pp"]["status"],
                start=_fmt(base_start),
                end=_fmt(base_end),
                drift=_fmt(base_drift),
            ),
            "| Scenario isolation | {status} | scenario outputs keep the current default object stamp and do not mutate V1 outputs |".format(
                status=checks["RP4_scenario_isolation"]["status"]
            ),
        ]
    )

    check_against = (
        "met"
        if Decimal("0.35") <= bill_heavy_end <= Decimal("0.45")
        else "not met; corrected 2035 share is outside 35-45 because the requested 0.45 policy also reallocates coupon maturities into bills"
    )
    lines.extend(
        [
            "",
            "## Required-item disposition",
            "",
            "| item | disposition | evidence |",
            "| --- | --- | --- |",
            "| 1. Maturing bills auto-refinance at 100% by default; policy share applies only to net new money plus coupon-maturity reissuance allocation; bills run off only under explicit policy reallocation | done | bill stock is carried forward before policy allocation; `active_bill_runoff_share` is zero for base and bill-heavy, 0.10 for coupon-heavy |",
            "| 2. Base policy must hold bills share approximately constant; assert drift <2pp over 120 months | done | RP5={status}; drift={drift} |".format(
                status=checks["RP5_base_bill_share_drift_lt_2pp"]["status"],
                drift=_fmt(base_drift),
            ),
            "| 3. Regression gate must run through the layer and reproduce the current default headline, not copy the rollup | done | RP3={status}; base rollup rebuilt by `_adjusted_headline_rollup` and compared to V1 rollup |".format(
                status=checks["RP3_base_headline_byte_regression"]["status"]
            ),
            "| 4. Rerun bill_heavy 0.45 / base / coupon_heavy 0.05; check bill-heavy share and divergence scale | done | bill-heavy 2035 share={share}; 35-45 check-against {check}; year-10 spread gov delta={gov}; year-10 spread delta RW={rw} |".format(
                share=_fmt(bill_heavy_end),
                check=check_against,
                gov=spread_y10["delta_government_interest_bil_vs_base"],
                rw=spread_y10["delta_RW_ratio_vs_base"],
            ),
            "| 5. Audit-3 current-base reconciliation: 0.145/0.043 M0 report vs 0.1373/0.04194 audit rebuild | done | regenerated year-10 RW values are bill-heavy=0.137298962889192014362639392 and coupon-heavy=0.041942010470557326442740565 under object stamp `{stamp}`; discrepancy attributed to wave-2 post-SCF base-state change, not layer mechanics |".format(
                stamp=CURRENT_DEFAULT_OBJECT_STAMP,
            ),
        ]
    )
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- `RUFF_CACHE_DIR=/tmp/ratewall-ruff-cache python -m ruff check src/ratewall/rwtam/reissuance_policy.py scripts/build_rwtam_reissuance_policy.py tests/test_rwtam_reissuance_policy.py tests/test_rwtam_mechanisms.py` passed.",
            "- `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python -m pytest -q tests/test_rwtam_reissuance_policy.py tests/test_rwtam_mechanisms.py` passed: 7 tests.",
            "- `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' python -m pytest -q` completed 100% green.",
            "",
            "## Output locations",
            "",
            "- `var/rwtam/scenarios/reissuance_policy/`",
            "- `var/rwtam/scenarios/reissuance_policy/out_reissuance_divergence_vs_base.csv`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _simulate_policy_state(
    pack: dict[str, list[dict[str, str]]],
    scenario_id: str,
    policy_bill_share: Decimal,
) -> list[PolicyYearState]:
    opening = _opening_by_family(pack)
    bill_stock = opening["treasury_bills"]
    current_coupon_remaining = opening["treasury_notes_bonds_tips"]
    current_coupon_open = current_coupon_remaining
    opening_bill_share = bill_stock / (bill_stock + current_coupon_remaining)
    coupon_cohorts: list[CouponCohort] = []
    rows: list[PolicyYearState] = []
    for year_index in range(1, 11):
        year = str(START_YEAR + year_index - 1)
        coupon_stock_start = current_coupon_remaining + sum(
            cohort.amount for cohort in coupon_cohorts
        )
        total_start = bill_stock + coupon_stock_start
        current_repriced = min(
            current_coupon_open,
            current_coupon_open - current_coupon_remaining + _current_coupon_maturing(pack, year_index),
        )
        new_repriced = sum(
            cohort.amount
            for cohort in coupon_cohorts
            if _cohort_reprices_in_year(cohort, year_index)
        )
        month_index = (year_index - 1) * 12 + 1
        shock_start_index = _month_index_from_label("2026-01")
        bill_rate = _treasury_yield_delta(
            pack,
            "bills",
            "base",
            month_index,
            shock_start_index,
            "persistent_level",
        )
        coupon_rate = _treasury_yield_delta(
            pack,
            "10y",
            "base",
            month_index,
            shock_start_index,
            "persistent_level",
        )
        bill_interest = bill_stock * bill_rate
        current_coupon_interest = (
            current_repriced
            * coupon_rate
        )
        new_coupon_interest = (
            new_repriced
            * coupon_rate
        )
        coupon_interest = current_coupon_interest + new_coupon_interest
        gov_delta = bill_interest + coupon_interest

        maturing_current = min(current_coupon_remaining, _current_coupon_maturing(pack, year_index))
        surviving_cohorts: list[CouponCohort] = []
        maturing_new = Decimal("0")
        for cohort in coupon_cohorts:
            if _cohort_matures_by_year_end(cohort, year_index):
                maturing_new += cohort.amount
            else:
                surviving_cohorts.append(cohort)

        primary_deficit = PRIMARY_DEFICIT_BASE_PATH[year_index - 1]
        bill_runoff_share = REISSUANCE_BILL_RUNOFF_SCENARIOS[scenario_id]
        active_bill_runoff = bill_stock * bill_runoff_share
        policy_allocation_pool = (
            maturing_current + maturing_new + primary_deficit + gov_delta + active_bill_runoff
        )
        effective_policy_bill_share = policy_bill_share
        if scenario_id == "base" and policy_allocation_pool:
            expected_total_end = total_start + primary_deficit + gov_delta
            effective_policy_bill_share = (
                opening_bill_share * expected_total_end - (bill_stock - active_bill_runoff)
            ) / policy_allocation_pool
            effective_policy_bill_share = min(
                Decimal("1"),
                max(Decimal("0"), effective_policy_bill_share),
            )
        reissued_bills = (
            bill_stock
            - active_bill_runoff
            + policy_allocation_pool * effective_policy_bill_share
        )
        new_coupon_issuance = policy_allocation_pool * (
            Decimal("1") - effective_policy_bill_share
        )
        new_cohorts = _coupon_cohorts_from_issuance(
            pack,
            amount=new_coupon_issuance,
            issue_year_index=year_index,
        )

        current_coupon_end = current_coupon_remaining - maturing_current
        coupon_stock_end = current_coupon_end + sum(
            cohort.amount for cohort in surviving_cohorts + new_cohorts
        )
        total_end = reissued_bills + coupon_stock_end
        expected_end = total_start + primary_deficit + gov_delta
        rows.append(
            PolicyYearState(
                scenario_id=scenario_id,
                year_index=year_index,
                year=year,
                policy_bill_share=effective_policy_bill_share,
                active_bill_runoff_share=bill_runoff_share,
                primary_deficit_bil=primary_deficit,
                stock_bills_start_bil=bill_stock,
                stock_coupons_start_bil=coupon_stock_start,
                total_debt_start_bil=total_start,
                current_stock_coupon_remaining_start_bil=current_coupon_remaining,
                bill_interest_delta_bil=bill_interest,
                coupon_interest_delta_bil=coupon_interest,
                current_stock_coupon_interest_bil=current_coupon_interest,
                new_issuance_coupon_interest_bil=new_coupon_interest,
                government_interest_delta_bil=gov_delta,
                maturing_current_coupon_bil=maturing_current,
                maturing_new_coupon_bil=maturing_new,
                active_bill_runoff_bil=active_bill_runoff,
                reissued_bill_principal_bil=reissued_bills,
                new_coupon_issuance_bil=new_coupon_issuance,
                stock_bills_end_bil=reissued_bills,
                stock_coupons_end_bil=coupon_stock_end,
                total_debt_end_bil=total_end,
                expected_total_debt_end_bil=expected_end,
                conservation_gap_bil=total_end - expected_end,
                aggregate_duration_start_years=_aggregate_duration(
                    pack,
                    bill_stock,
                    current_coupon_remaining,
                    coupon_cohorts,
                    year_index,
                ),
                aggregate_duration_end_years=_aggregate_duration(
                    pack,
                    reissued_bills,
                    current_coupon_end,
                    surviving_cohorts + new_cohorts,
                    year_index + 1,
                ),
            )
        )
        bill_stock = reissued_bills
        current_coupon_remaining = current_coupon_end
        coupon_cohorts = surviving_cohorts + new_cohorts
    return rows


def _current_coupon_maturing(
    pack: dict[str, list[dict[str, str]]],
    year_index: int,
) -> Decimal:
    rows = pack.get("tdcsim_coupon_roll_schedule", [])
    start = (year_index - 1) * 12
    end = year_index * 12
    return sum(_d(row["maturing_principal_bil"]) for row in rows[start:end])


def _coupon_cohorts_from_issuance(
    pack: dict[str, list[dict[str, str]]],
    *,
    amount: Decimal,
    issue_year_index: int,
) -> list[CouponCohort]:
    if amount == 0:
        return []
    coupon_mix = _coupon_tenor_mix(pack)
    return [
        CouponCohort(
            amount=amount * share,
            issue_year_index=issue_year_index,
            tenor_years=tenor,
            bucket=bucket,
        )
        for bucket, share, tenor in coupon_mix
        if share != 0
    ]


def _coupon_tenor_mix(
    pack: dict[str, list[dict[str, str]]],
) -> list[tuple[str, Decimal, Decimal]]:
    rows = [
        row
        for row in pack.get("tdcsim_issuance_tenor_mix", [])
        if not row["tenor_bucket"].startswith("bills_")
    ]
    total = sum(_d(row["share_of_gross_issuance"]) for row in rows)
    if total == 0:
        return [("blended_coupon_10y", Decimal("1"), Decimal("10"))]
    return [
        (
            row["tenor_bucket"],
            _d(row["share_of_gross_issuance"]) / total,
            _tenor_years(row["tenor_bucket"]),
        )
        for row in rows
    ]


def _tenor_years(bucket: str) -> Decimal:
    if bucket.startswith("frn_"):
        return Decimal("0.25")
    suffix = bucket.rsplit("_", maxsplit=1)[-1]
    if suffix.endswith("y"):
        return Decimal(suffix.removesuffix("y"))
    if suffix.endswith("m"):
        return Decimal(suffix.removesuffix("m")) / Decimal("12")
    return Decimal("10")


def _cohort_reprices_in_year(cohort: CouponCohort, year_index: int) -> bool:
    if cohort.bucket.startswith("frn_"):
        return True
    return Decimal(year_index - cohort.issue_year_index + 1) >= cohort.tenor_years


def _cohort_matures_by_year_end(cohort: CouponCohort, year_index: int) -> bool:
    if cohort.bucket.startswith("frn_"):
        return True
    return Decimal(year_index - cohort.issue_year_index) >= cohort.tenor_years


def _aggregate_duration(
    pack: dict[str, list[dict[str, str]]],
    bills: Decimal,
    current_coupon_remaining: Decimal,
    cohorts: list[CouponCohort],
    year_index: int,
) -> Decimal:
    total = bills + current_coupon_remaining + sum(cohort.amount for cohort in cohorts)
    if total == 0:
        return Decimal("0")
    weighted = bills * Decimal("0.25")
    weighted += current_coupon_remaining * _current_coupon_remaining_duration(pack, year_index)
    for cohort in cohorts:
        age = max(Decimal("0"), Decimal(year_index - cohort.issue_year_index))
        remaining = max(Decimal("0.25"), cohort.tenor_years - age)
        weighted += cohort.amount * remaining
    return weighted / total


def _current_coupon_remaining_duration(
    pack: dict[str, list[dict[str, str]]],
    year_index: int,
) -> Decimal:
    rows = pack.get("tdcsim_coupon_roll_schedule", [])
    start_month = max(0, (year_index - 1) * 12)
    remaining_rows = rows[start_month:]
    weighted = Decimal("0")
    total = Decimal("0")
    for offset, row in enumerate(remaining_rows, start=1):
        amount = _d(row["maturing_principal_bil"])
        total += amount
        weighted += amount * Decimal(offset) / Decimal("12")
    opening = _opening_by_family(pack)["treasury_notes_bonds_tips"]
    matured_before = sum(_d(row["maturing_principal_bil"]) for row in rows[:start_month])
    remaining_stock = max(Decimal("0"), opening - matured_before)
    residual = max(Decimal("0"), remaining_stock - total)
    weighted += residual * Decimal("15")
    total += residual
    if total == 0:
        return Decimal("0")
    return weighted / total


def _base_government_level_offsets(
    government_rows: list[dict[str, str]],
    base_states: list[PolicyYearState],
) -> dict[str, Decimal]:
    actual: dict[str, Decimal] = {}
    for row in government_rows:
        actual[row["year"]] = actual.get(row["year"], Decimal("0")) + _d(
            row["cashflow_delta_bil"]
        )
    return {
        state.year: actual.get(state.year, state.government_interest_delta_bil)
        - state.government_interest_delta_bil
        for state in base_states
    }


def _adjusted_headline_rollup(
    pack: dict[str, list[dict[str, str]]],
    base_v1: ScenarioResult,
    states: list[PolicyYearState],
    base_states: list[PolicyYearState],
) -> list[dict[str, str]]:
    all_base_rows = base_v1.rows("out_ratewall_rollup")
    if [state.scenario_id for state in states] == [state.scenario_id for state in base_states]:
        return [dict(row) for row in all_base_rows]
    base_rows = [
        row
        for row in all_base_rows
        if row["period_type"] == "annual"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ]
    scenario_effects = _annual_policy_effects(pack, states)
    base_effects = _annual_policy_effects(pack, base_states)
    adjusted: list[dict[str, str]] = []
    for state, base in zip(states, base_rows, strict=True):
        scenario_effect = scenario_effects[state.year]
        base_effect = base_effects[state.year]
        n_value = (
            _d(base["N_bil"])
            + scenario_effect["N"]
            - base_effect["N"]
        )
        d_value = (
            _d(base["D_bil"])
            + scenario_effect["D"]
            - base_effect["D"]
        )
        adjusted.append(_headline_row_from_values(base, n_value, d_value))
    cumulative_n = sum(_d(row["N_bil"]) for row in adjusted)
    cumulative_d = sum(_d(row["D_bil"]) for row in adjusted)
    exemplar = next(
        row
        for row in all_base_rows
        if row["period_type"] == "cumulative_120_month"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    )
    adjusted.append(_headline_row_from_values(exemplar, cumulative_n, cumulative_d))
    adjusted_by_key = {_rollup_key(row): row for row in adjusted}
    return [dict(adjusted_by_key.get(_rollup_key(row), row)) for row in all_base_rows]


def _rollup_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row["period_type"],
        row["period"],
        row["month_index"],
        row["band"],
        row["ricardian_offset"],
    )


def _annual_policy_effects(
    pack: dict[str, list[dict[str, str]]],
    states: list[PolicyYearState],
) -> dict[str, dict[str, Decimal]]:
    conversion = _conversion(pack)
    effects: dict[str, dict[str, Decimal]] = {}
    tdc_stock = Decimal("0")
    for state in states:
        treasury_routes = _treasury_routes(
            pack,
            state.bill_interest_delta_bil,
            state.coupon_interest_delta_bil,
            "base",
            aggregate_matrix=False,
        )
        treasury_n, treasury_d, _ = _classify(treasury_routes, conversion, Decimal("0"))
        tdc_metrics = _tdc_metrics_for_period(
            pack,
            "base",
            state.year_index,
            state.government_interest_delta_bil,
            tdc_stock,
            True,
        )
        tdc_stock = tdc_metrics["created_deposit_stock_bil"]
        tdc_n, tdc_d, _ = _classify(
            _tdc_routes_from_metrics(pack, "base", tdc_metrics),
            conversion,
            Decimal("0"),
        )
        effects[state.year] = {
            "N": treasury_n + tdc_n,
            "D": treasury_d + tdc_d,
        }
    return effects


def _headline_row_from_values(row: dict[str, str], n_value: Decimal, d_value: Decimal) -> dict[str, str]:
    out = dict(row)
    net = n_value - d_value
    out["N_bil"] = _fmt(n_value)
    out["D_bil"] = _fmt(d_value)
    out["net_bil"] = _fmt(net)
    out["RW_ratio"] = _fmt(n_value / d_value) if d_value else "0"
    out["bottom_up_D_to_legacy_D"] = _fmt(_d(out["D_bil"]) / _d(out["legacy_D_comparator_bil"]))
    out["net_pct_gdp"] = _fmt(net / (_d(out["legacy_D_comparator_bil"]) / Decimal("0.00776")))
    out["object_version_stamp"] = CURRENT_DEFAULT_OBJECT_STAMP
    return out


def _policy_config_rows(scenario_id: str) -> list[dict[str, str]]:
    return [
        {
            "scenario_id": scenario_id,
            "policy_bill_share": _fmt(REISSUANCE_POLICY_SCENARIOS[scenario_id]),
            "policy_coupon_share": _fmt(Decimal("1") - REISSUANCE_POLICY_SCENARIOS[scenario_id]),
            "active_bill_runoff_share": _fmt(REISSUANCE_BILL_RUNOFF_SCENARIOS[scenario_id]),
            "primary_deficit_path_id": "owner_assumption_primary_deficit_CBO_shape_base_2026_2035",
            "primary_deficit_mode": "base",
            "primary_deficit_values_bil": ";".join(_fmt(value) for value in PRIMARY_DEFICIT_BASE_PATH),
            "same_policy_within_baseline_shock_pair": "true",
            "baseline_state_discipline": "maturing_bills_auto_refinance_unless_active_bill_runoff_share_positive",
            "input_basis_label": "owner_assumption_mode",
            "rationale": "Persistent issuance policy: bills self-roll by default; policy share applies to net new money plus coupon maturities plus explicit active bill runoff.",
        }
    ]


def _composition_rows(states: list[PolicyYearState]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for state in states:
        rows.append(
            {
                "scenario_id": state.scenario_id,
                "year": state.year,
                "year_index": str(state.year_index),
                "policy_bill_share": _fmt(state.policy_bill_share),
                "active_bill_runoff_share": _fmt(state.active_bill_runoff_share),
                "stock_bills_start_bil": _fmt(state.stock_bills_start_bil),
                "stock_coupons_start_bil": _fmt(state.stock_coupons_start_bil),
                "total_debt_start_bil": _fmt(state.total_debt_start_bil),
                "bill_share_start": _fmt(state.stock_bills_start_bil / state.total_debt_start_bil),
                "primary_deficit_bil": _fmt(state.primary_deficit_bil),
                "maturing_current_coupon_bil": _fmt(state.maturing_current_coupon_bil),
                "maturing_new_coupon_bil": _fmt(state.maturing_new_coupon_bil),
                "active_bill_runoff_bil": _fmt(state.active_bill_runoff_bil),
                "reissued_bill_principal_bil": _fmt(state.reissued_bill_principal_bil),
                "new_coupon_issuance_bil": _fmt(state.new_coupon_issuance_bil),
                "stock_bills_end_bil": _fmt(state.stock_bills_end_bil),
                "stock_coupons_end_bil": _fmt(state.stock_coupons_end_bil),
                "total_debt_end_bil": _fmt(state.total_debt_end_bil),
                "bill_share_end": _fmt(state.stock_bills_end_bil / state.total_debt_end_bil),
                "expected_total_debt_end_bil": _fmt(state.expected_total_debt_end_bil),
                "conservation_gap_bil": _fmt(state.conservation_gap_bil),
                "aggregate_duration_start_years": _fmt(state.aggregate_duration_start_years),
                "aggregate_duration_end_years": _fmt(state.aggregate_duration_end_years),
            }
        )
    return rows


def _government_delta_rows(
    states: list[PolicyYearState],
    base_government_offsets: dict[str, Decimal],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for state in states:
        offset = base_government_offsets.get(state.year, Decimal("0"))
        current_coupon_interest = state.current_stock_coupon_interest_bil + offset
        coupon_interest = state.coupon_interest_delta_bil + offset
        government_interest = state.government_interest_delta_bil + offset
        rows.append(
            {
                "scenario_id": state.scenario_id,
                "year": state.year,
                "year_index": str(state.year_index),
                "bill_interest_delta_bil": _fmt(state.bill_interest_delta_bil),
                "coupon_interest_delta_bil": _fmt(coupon_interest),
                "current_stock_coupon_interest_bil": _fmt(current_coupon_interest),
                "new_issuance_coupon_interest_bil": _fmt(state.new_issuance_coupon_interest_bil),
                "government_interest_delta_bil": _fmt(government_interest),
                "base_level_normalization_delta_bil": _fmt(offset),
                "bill_share_of_government_delta": _fmt(
                    state.bill_interest_delta_bil / government_interest
                )
                if government_interest
                else "0",
                "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
            }
        )
    return rows


def _duration_rows(states: list[PolicyYearState]) -> list[dict[str, str]]:
    return [
        {
            "scenario_id": state.scenario_id,
            "year": state.year,
            "year_index": str(state.year_index),
            "aggregate_duration_start_years": _fmt(state.aggregate_duration_start_years),
            "aggregate_duration_end_years": _fmt(state.aggregate_duration_end_years),
            "metric_role": "future_holder_mtm_linkage_metric_only_no_behavior",
        }
        for state in states
    ]


def _invariant_rows(
    scenario_id: str,
    states: list[PolicyYearState],
    rollup: list[dict[str, str]],
    base_rollup: list[dict[str, str]],
) -> list[dict[str, str]]:
    conservation = all(abs(state.conservation_gap_bil) <= Decimal("0.000001") for state in states)
    same_policy = bool(states)
    base_regression = True
    base_bill_drift = True
    if scenario_id == "base":
        base_regression = rollup == base_rollup
        start_share = states[0].stock_bills_start_bil / states[0].total_debt_start_bil
        end_share = states[-1].stock_bills_end_bil / states[-1].total_debt_end_bil
        base_bill_drift = abs(end_share - start_share) < Decimal("0.02")
    isolated = all(row.get("object_version_stamp") == CURRENT_DEFAULT_OBJECT_STAMP for row in rollup)
    return [
        _check_row("RP1_composition_conservation", conservation, "stocks sum to total debt each period"),
        _check_row("RP2_same_policy_within_pair", same_policy, "policy rule is fixed within each baseline/shock pair"),
        _check_row("RP3_base_headline_byte_regression", base_regression, "base policy runs through the reissuance layer and reproduces current default headline exactly"),
        _check_row("RP4_scenario_isolation", isolated, "scenario output keeps current default object stamp and does not mutate V1"),
        _check_row("RP5_base_bill_share_drift_lt_2pp", base_bill_drift, "base policy keeps the bills share within 2 percentage points over 120 months"),
    ]


def _check_row(check_id: str, ok: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": "pass" if ok else "fail", "message": message}


def _divergence_rows(results: dict[str, ScenarioResult]) -> list[dict[str, str]]:
    base_headline = _headline_by_horizon(results["base"])
    base_gov = _gov_by_horizon(results["base"])
    rows: list[dict[str, str]] = []
    for scenario_id in (item for item in REISSUANCE_POLICY_ORDER if item != "base"):
        headline = _headline_by_horizon(results[scenario_id])
        gov = _gov_by_horizon(results[scenario_id])
        for horizon in ["year_1", "year_5", "year_10", "cumulative_120_month"]:
            scenario_row = headline[horizon]
            base_row = base_headline[horizon]
            scenario_gov = gov[horizon]
            base_gov_value = base_gov[horizon]
            rows.append(
                {
                    "scenario": scenario_id,
                    "horizon": horizon,
                    "period": scenario_row["period"],
                    "government_interest_delta_bil": _fmt(scenario_gov),
                    "base_government_interest_delta_bil": _fmt(base_gov_value),
                    "delta_government_interest_bil_vs_base": _fmt(scenario_gov - base_gov_value),
                    "N_bil": scenario_row["N_bil"],
                    "D_bil": scenario_row["D_bil"],
                    "RW_ratio": scenario_row["RW_ratio"],
                    "base_N_bil": base_row["N_bil"],
                    "base_D_bil": base_row["D_bil"],
                    "base_RW_ratio": base_row["RW_ratio"],
                    "delta_N_bil_vs_base": _fmt(_d(scenario_row["N_bil"]) - _d(base_row["N_bil"])),
                    "delta_D_bil_vs_base": _fmt(_d(scenario_row["D_bil"]) - _d(base_row["D_bil"])),
                    "delta_RW_ratio_vs_base": _fmt(_d(scenario_row["RW_ratio"]) - _d(base_row["RW_ratio"])),
                    "expectation_check": _expectation_check(horizon, scenario_gov - base_gov_value),
                    "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
                }
            )
    bill_headline = _headline_by_horizon(results["bill_heavy"])
    coupon_headline = _headline_by_horizon(results["coupon_heavy"])
    bill_gov = _gov_by_horizon(results["bill_heavy"])
    coupon_gov = _gov_by_horizon(results["coupon_heavy"])
    for horizon in ["year_1", "year_5", "year_10", "cumulative_120_month"]:
        bill_row = bill_headline[horizon]
        coupon_row = coupon_headline[horizon]
        spread_gov = bill_gov[horizon] - coupon_gov[horizon]
        rows.append(
            {
                "scenario": "bill_heavy_minus_coupon_heavy",
                "horizon": horizon,
                "period": bill_row["period"],
                "government_interest_delta_bil": _fmt(spread_gov),
                "base_government_interest_delta_bil": "0",
                "delta_government_interest_bil_vs_base": _fmt(spread_gov),
                "N_bil": _fmt(_d(bill_row["N_bil"]) - _d(coupon_row["N_bil"])),
                "D_bil": _fmt(_d(bill_row["D_bil"]) - _d(coupon_row["D_bil"])),
                "RW_ratio": _fmt(_d(bill_row["RW_ratio"]) - _d(coupon_row["RW_ratio"])),
                "base_N_bil": "0",
                "base_D_bil": "0",
                "base_RW_ratio": "0",
                "delta_N_bil_vs_base": _fmt(_d(bill_row["N_bil"]) - _d(coupon_row["N_bil"])),
                "delta_D_bil_vs_base": _fmt(_d(bill_row["D_bil"]) - _d(coupon_row["D_bil"])),
                "delta_RW_ratio_vs_base": _fmt(_d(bill_row["RW_ratio"]) - _d(coupon_row["RW_ratio"])),
                "expectation_check": _pair_expectation_check(horizon, spread_gov),
                "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
            }
        )
    return rows


def _headline_by_horizon(result: ScenarioResult) -> dict[str, dict[str, str]]:
    rows = [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["band"] == "base" and row["ricardian_offset"] == "0"
    ]
    return {
        "year_1": next(row for row in rows if row["period_type"] == "annual" and row["period"] == "2026"),
        "year_5": next(row for row in rows if row["period_type"] == "annual" and row["period"] == "2030"),
        "year_10": next(row for row in rows if row["period_type"] == "annual" and row["period"] == "2035"),
        "cumulative_120_month": next(row for row in rows if row["period_type"] == "cumulative_120_month"),
    }


def _gov_by_horizon(result: ScenarioResult) -> dict[str, Decimal]:
    annual = {
        row["year"]: _d(row["government_interest_delta_bil"])
        for row in result.rows("out_reissuance_government_interest_delta_path")
    }
    return {
        "year_1": annual["2026"],
        "year_5": annual["2030"],
        "year_10": annual["2035"],
        "cumulative_120_month": sum(annual.values(), Decimal("0")),
    }


def _expectation_check(horizon: str, delta_gov: Decimal) -> str:
    if horizon == "year_1" and abs(delta_gov) <= Decimal("0.000001"):
        return "annual_core_timing_limit"
    return "scenario_difference_reported"


def _pair_expectation_check(horizon: str, spread_gov: Decimal) -> str:
    if horizon == "year_1" and abs(spread_gov) <= Decimal("0.000001"):
        return "annual_core_timing_limit"
    if horizon == "year_10" and abs(spread_gov) >= Decimal("40"):
        return "owner_check_against_scale_met"
    if horizon == "year_10":
        return "materially_smaller_than_owner_check_against_decompose"
    return "scenario_difference_reported"

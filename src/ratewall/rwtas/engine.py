"""Deterministic V0 monthly RWTAS engine."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import count

from ratewall.rwtas.contract import (
    OUTPUT_TABLES,
    PASS_TOLERANCE,
    SECTOR_CODES,
    SECTOR_IDS,
    SIGN_CONVENTIONS,
)
from ratewall.rwtas.schemas import (
    ClaimOpening,
    ClaimTerm,
    ExposureState,
    FlowTermRule,
    ReferenceRatePath,
    RwtasConfig,
)


@dataclass(frozen=True)
class RwtasResult:
    """Named CSV-ready output tables from one RWTAS run."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


@dataclass(frozen=True)
class _ScenarioFlow:
    scenario_id: str
    month: str
    claim_id: str
    flow_kind: str
    payer_sector: str
    payer_cell: str
    receiver_sector: str
    receiver_cell: str
    amount_bil: Decimal
    cash_flag: str
    stock_effect: str
    report_group_id: str
    real_conversion_eligible: bool

    @property
    def flow_key(self) -> str:
        return "|".join(
            [
                self.claim_id,
                self.flow_kind,
                self.payer_sector,
                self.payer_cell,
                self.receiver_sector,
                self.receiver_cell,
                self.month,
            ]
        )


def run_rwtas(config: RwtasConfig) -> RwtasResult:
    """Run the RWTAS V0 same-state baseline/shock pair."""

    claims = {claim.claim_id: claim for claim in config.claim_opening_stock}
    terms = {term.claim_id: term for term in config.claim_terms}
    exposures = {
        (exposure.state_id, exposure.month, exposure.claim_id): exposure
        for exposure in config.exposure_states
    }
    paths = {
        (path.scenario_id, path.month, path.reference_rate_id): path
        for path in config.reference_rate_paths
    }
    conversions = {rule.cell_id: rule for rule in config.conversion_rules}

    out_claim_state = _claim_state_rows(config, claims, exposures)
    out_claim_rate = _claim_rate_rows(config, claims, terms, exposures, paths)
    scenario_flows = _scenario_flows(config, claims, terms, exposures, paths)
    out_flow_ledger = _flow_ledger_rows(scenario_flows)
    out_flow_delta = _flow_delta_rows(config, scenario_flows)
    out_sector_flow = _sector_flow_rows(config, out_flow_delta)
    out_default_state = _default_state_rows(config, claims, exposures)
    out_real_effect_leg = _real_effect_leg_rows(out_flow_delta, conversions)
    out_real_effect_cell = _real_effect_cell_rows(
        out_flow_delta,
        out_real_effect_leg,
        conversions,
    )
    out_ratewall_monthly = _ratewall_monthly_rows(
        config,
        out_real_effect_cell,
        out_real_effect_leg,
    )
    out_ratewall_rollup = _ratewall_rollup_rows(config, out_ratewall_monthly)
    out_report_channel_monthly = _report_channel_monthly_rows(
        config,
        out_ratewall_monthly,
        out_real_effect_leg,
    )
    out_report_channel_rollup = _report_channel_rollup_rows(
        config,
        out_report_channel_monthly,
    )
    out_reference_rate = _reference_rate_rows(config, paths)
    out_run_manifest = _run_manifest_rows(config)

    tables = {
        "out_run_manifest": out_run_manifest,
        "out_reference_rate_monthly": out_reference_rate,
        "out_claim_state_monthly": out_claim_state,
        "out_claim_rate_monthly": out_claim_rate,
        "out_flow_ledger_monthly": out_flow_ledger,
        "out_flow_delta_monthly": out_flow_delta,
        "out_sector_flow_monthly": out_sector_flow,
        "out_default_state_monthly": out_default_state,
        "out_real_effect_leg_monthly": out_real_effect_leg,
        "out_real_effect_cell_monthly": out_real_effect_cell,
        "out_ratewall_monthly": out_ratewall_monthly,
        "out_ratewall_rollup": out_ratewall_rollup,
        "out_report_channel_monthly": out_report_channel_monthly,
        "out_report_channel_rollup": out_report_channel_rollup,
    }
    tables["out_invariant_check"] = _invariant_rows(config, tables)
    missing = set(OUTPUT_TABLES) - set(tables)
    if missing:
        raise AssertionError(f"missing RWTAS output tables: {sorted(missing)}")
    return RwtasResult(tables=tables)


def _claim_state_rows(
    config: RwtasConfig,
    claims: dict[str, ClaimOpening],
    exposures: dict[tuple[str, str, str], ExposureState],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for claim in config.claim_opening_stock:
        exposure = exposures[(claim.state_id, claim.opening_month, claim.claim_id)]
        for scenario_id in [
            config.scenario_pair.baseline_scenario_id,
            config.scenario_pair.shock_scenario_id,
        ]:
            rows.append(
                {
                    "run_pair_id": config.scenario_pair.run_pair_id,
                    "scenario_id": scenario_id,
                    "state_id": claim.state_id,
                    "month": claim.opening_month,
                    "claim_id": claim.claim_id,
                    "holder_sector": claim.holder_sector,
                    "holder_cell": claim.holder_cell,
                    "issuer_sector": claim.issuer_sector,
                    "issuer_cell": claim.issuer_cell,
                    "instrument": claim.instrument,
                    "principal_begin_bil": _fmt(claim.principal_begin_bil),
                    "performing_principal_bil": _fmt(
                        exposure.performing_principal_bil
                    ),
                    "distressed_paying_principal_bil": _fmt(
                        exposure.distressed_paying_principal_bil
                    ),
                    "defaulted_nonperforming_principal_bil": _fmt(
                        exposure.defaulted_nonperforming_principal_bil
                    ),
                    "issuance_bil": "0",
                    "principal_repayment_bil": "0",
                    "writeoff_bil": "0",
                    "capitalized_interest_bil": "0",
                    "other_stock_change_bil": "0",
                    "principal_end_bil": _fmt(claim.principal_begin_bil),
                    "book_value_begin_bil": _fmt(claim.book_value_begin_bil),
                    "book_value_end_bil": _fmt(claim.book_value_begin_bil),
                    "market_value_begin_bil": _fmt(claim.market_value_begin_bil),
                    "market_value_end_bil": _fmt(claim.market_value_begin_bil),
                    "stock_flow_identity_difference_bil": "0",
                }
            )
    return rows


def _claim_rate_rows(
    config: RwtasConfig,
    claims: dict[str, ClaimOpening],
    terms: dict[str, ClaimTerm],
    exposures: dict[tuple[str, str, str], ExposureState],
    paths: dict[tuple[str, str, str], ReferenceRatePath],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for claim in config.claim_opening_stock:
        term = terms[claim.claim_id]
        exposure = exposures[(claim.state_id, claim.opening_month, claim.claim_id)]
        for scenario_id in [
            config.scenario_pair.baseline_scenario_id,
            config.scenario_pair.shock_scenario_id,
        ]:
            path = paths[(scenario_id, claim.opening_month, term.reference_rate_id)]
            effective_rate = _effective_rate(term, path)
            interest_due = exposure.paying_principal_bil * effective_rate * _tau(config)
            rows.append(
                {
                    "run_pair_id": config.scenario_pair.run_pair_id,
                    "scenario_id": scenario_id,
                    "month": claim.opening_month,
                    "claim_id": claim.claim_id,
                    "reference_rate_id": term.reference_rate_id,
                    "reference_rate_ann": _fmt(path.annual_rate),
                    "spread_ann": _fmt(term.spread),
                    "contract_adjustment_ann": _fmt(term.contract_adjustment),
                    "contract_fixed_rate_ann": _fmt(term.contract_fixed_rate),
                    "effective_rate_ann": _fmt(effective_rate),
                    "rate_type": term.rate_type,
                    "reset_active": _bool_str(_resets_in_v0(term)),
                    "repricing_share": _fmt(term.repricing_share),
                    "paying_principal_bil": _fmt(exposure.paying_principal_bil),
                    "repriced_paying_principal_bil": _fmt(
                        exposure.paying_principal_bil * term.repricing_share
                    ),
                    "tau_month": _fmt(_tau(config)),
                    "interest_due_bil": _fmt(interest_due),
                    "scheduled_interest_base_bil": _fmt(
                        exposure.paying_principal_bil
                    ),
                }
            )
    return rows


def _scenario_flows(
    config: RwtasConfig,
    claims: dict[str, ClaimOpening],
    terms: dict[str, ClaimTerm],
    exposures: dict[tuple[str, str, str], ExposureState],
    paths: dict[tuple[str, str, str], ReferenceRatePath],
) -> list[_ScenarioFlow]:
    flows: list[_ScenarioFlow] = []
    for claim in config.claim_opening_stock:
        term = terms[claim.claim_id]
        exposure = exposures[(claim.state_id, claim.opening_month, claim.claim_id)]
        for scenario_id in [
            config.scenario_pair.baseline_scenario_id,
            config.scenario_pair.shock_scenario_id,
        ]:
            path = paths[(scenario_id, claim.opening_month, term.reference_rate_id)]
            amount = (
                exposure.paying_principal_bil * _effective_rate(term, path) * _tau(config)
            )
            flows.append(
                _ScenarioFlow(
                    scenario_id=scenario_id,
                    month=claim.opening_month,
                    claim_id=claim.claim_id,
                    flow_kind="interest_cash_payment",
                    payer_sector=claim.issuer_sector,
                    payer_cell=claim.issuer_cell,
                    receiver_sector=claim.holder_sector,
                    receiver_cell=claim.holder_cell,
                    amount_bil=amount,
                    cash_flag="cash",
                    stock_effect="none",
                    report_group_id=claim.report_group_id,
                    real_conversion_eligible=True,
                )
            )
    for term_rule in config.flow_term_rules:
        claim = claims[term_rule.claim_id]
        flows.extend(_manual_flows(config, claim, term_rule))
    return flows


def _manual_flows(
    config: RwtasConfig,
    claim: ClaimOpening,
    term_rule: FlowTermRule,
) -> list[_ScenarioFlow]:
    return [
        _ScenarioFlow(
            scenario_id=config.scenario_pair.baseline_scenario_id,
            month=claim.opening_month,
            claim_id=term_rule.claim_id,
            flow_kind=term_rule.flow_kind,
            payer_sector=term_rule.payer_sector,
            payer_cell=term_rule.payer_cell,
            receiver_sector=term_rule.receiver_sector,
            receiver_cell=term_rule.receiver_cell,
            amount_bil=term_rule.baseline_amount_bil,
            cash_flag=term_rule.cash_flag,
            stock_effect=term_rule.stock_effect,
            report_group_id=term_rule.report_group_id,
            real_conversion_eligible=term_rule.real_conversion_eligible,
        ),
        _ScenarioFlow(
            scenario_id=config.scenario_pair.shock_scenario_id,
            month=claim.opening_month,
            claim_id=term_rule.claim_id,
            flow_kind=term_rule.flow_kind,
            payer_sector=term_rule.payer_sector,
            payer_cell=term_rule.payer_cell,
            receiver_sector=term_rule.receiver_sector,
            receiver_cell=term_rule.receiver_cell,
            amount_bil=term_rule.shock_amount_bil,
            cash_flag=term_rule.cash_flag,
            stock_effect=term_rule.stock_effect,
            report_group_id=term_rule.report_group_id,
            real_conversion_eligible=term_rule.real_conversion_eligible,
        ),
    ]


def _flow_ledger_rows(flows: list[_ScenarioFlow]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for idx, flow in enumerate(flows, start=1):
        rows.append(
            {
                "flow_event_id": f"F{idx:04d}",
                "scenario_id": flow.scenario_id,
                "month": flow.month,
                "claim_id": flow.claim_id,
                "flow_key": flow.flow_key,
                "flow_kind": flow.flow_kind,
                "payer_sector": flow.payer_sector,
                "payer_cell": flow.payer_cell,
                "receiver_sector": flow.receiver_sector,
                "receiver_cell": flow.receiver_cell,
                "amount_bil": _fmt(flow.amount_bil),
                "payer_outflow_bil": _fmt(flow.amount_bil),
                "receiver_inflow_bil": _fmt(flow.amount_bil),
                "cash_flag": flow.cash_flag,
                "stock_effect": flow.stock_effect,
                "report_group_id": flow.report_group_id,
                "real_conversion_eligible": _bool_str(flow.real_conversion_eligible),
            }
        )
    return rows


def _flow_delta_rows(
    config: RwtasConfig,
    flows: list[_ScenarioFlow],
) -> list[dict[str, str]]:
    aggregates: dict[str, dict[str, object]] = {}
    for flow in flows:
        entry = aggregates.setdefault(
            flow.flow_key,
            {
                "month": flow.month,
                "claim_id": flow.claim_id,
                "flow_kind": flow.flow_kind,
                "payer_sector": flow.payer_sector,
                "payer_cell": flow.payer_cell,
                "receiver_sector": flow.receiver_sector,
                "receiver_cell": flow.receiver_cell,
                "cash_flag": flow.cash_flag,
                "report_group_id": flow.report_group_id,
                "real_conversion_eligible": flow.real_conversion_eligible,
                "baseline_amount_bil": Decimal("0"),
                "shock_amount_bil": Decimal("0"),
            },
        )
        key = (
            "baseline_amount_bil"
            if flow.scenario_id == config.scenario_pair.baseline_scenario_id
            else "shock_amount_bil"
        )
        entry[key] = entry[key] + flow.amount_bil

    rows: list[dict[str, str]] = []
    for idx, (flow_key, entry) in enumerate(sorted(aggregates.items()), start=1):
        baseline = entry["baseline_amount_bil"]
        shock = entry["shock_amount_bil"]
        assert isinstance(baseline, Decimal)
        assert isinstance(shock, Decimal)
        rows.append(
            {
                "flow_delta_id": f"FD{idx:04d}",
                "run_pair_id": config.scenario_pair.run_pair_id,
                "month": str(entry["month"]),
                "claim_id": str(entry["claim_id"]),
                "flow_key": flow_key,
                "flow_kind": str(entry["flow_kind"]),
                "payer_sector": str(entry["payer_sector"]),
                "payer_cell": str(entry["payer_cell"]),
                "receiver_sector": str(entry["receiver_sector"]),
                "receiver_cell": str(entry["receiver_cell"]),
                "cash_flag": str(entry["cash_flag"]),
                "report_group_id": str(entry["report_group_id"]),
                "real_conversion_eligible": _bool_str(
                    bool(entry["real_conversion_eligible"])
                ),
                "baseline_amount_bil": _fmt(baseline),
                "shock_amount_bil": _fmt(shock),
                "delta_amount_bil": _fmt(shock - baseline),
            }
        )
    return rows


def _sector_flow_rows(
    config: RwtasConfig,
    flow_delta_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    by_sector: dict[tuple[str, str], Decimal] = {}
    for row in flow_delta_rows:
        if row["cash_flag"] != "cash":
            continue
        month = row["month"]
        delta = Decimal(row["delta_amount_bil"])
        by_sector[(month, row["receiver_sector"])] = (
            by_sector.get((month, row["receiver_sector"]), Decimal("0")) + delta
        )
        by_sector[(month, row["payer_sector"])] = (
            by_sector.get((month, row["payer_sector"]), Decimal("0")) - delta
        )

    rows: list[dict[str, str]] = []
    for month in [calendar.month for calendar in config.calendar_months]:
        for sector_id in SECTOR_IDS:
            rows.append(
                {
                    "run_pair_id": config.scenario_pair.run_pair_id,
                    "month": month,
                    "sector_id": sector_id,
                    "sector_code": SECTOR_CODES[sector_id],
                    "net_cash_flow_delta_bil": _fmt(
                        by_sector.get((month, sector_id), Decimal("0"))
                    ),
                }
            )
    return rows


def _default_state_rows(
    config: RwtasConfig,
    claims: dict[str, ClaimOpening],
    exposures: dict[tuple[str, str, str], ExposureState],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for claim in config.claim_opening_stock:
        exposure = exposures[(claim.state_id, claim.opening_month, claim.claim_id)]
        rows.append(
            {
                "run_pair_id": config.scenario_pair.run_pair_id,
                "month": claim.opening_month,
                "claim_id": claim.claim_id,
                "performing_principal_bil": _fmt(exposure.performing_principal_bil),
                "distressed_paying_principal_bil": _fmt(
                    exposure.distressed_paying_principal_bil
                ),
                "defaulted_nonperforming_principal_bil": _fmt(
                    exposure.defaulted_nonperforming_principal_bil
                ),
                "new_default_exposure_bil": "0",
                "writeoff_bil": "0",
                "holder_loss_bil": "0",
                "issuer_relief_bil": "0",
                "non_double_count_check_bil": "0",
            }
        )
    return rows


def _real_effect_leg_rows(
    flow_delta_rows: list[dict[str, str]],
    conversions: dict[str, object],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    leg_counter = count(1)
    for flow in flow_delta_rows:
        if flow["real_conversion_eligible"] != "true":
            continue
        delta = Decimal(flow["delta_amount_bil"])
        for leg_role, sign, sector_field, cell_field in [
            ("receiver", Decimal("1"), "receiver_sector", "receiver_cell"),
            ("payer", Decimal("-1"), "payer_sector", "payer_cell"),
        ]:
            cell_id = flow[cell_field]
            conversion = conversions[cell_id]
            effect = (
                delta
                * sign
                * conversion.conversion_coeff
                * conversion.domestic_eligibility_weight
            )
            rows.append(
                {
                    "real_effect_leg_id": f"REL{next(leg_counter):04d}",
                    "run_pair_id": flow["run_pair_id"],
                    "month": flow["month"],
                    "flow_delta_id": flow["flow_delta_id"],
                    "flow_key": flow["flow_key"],
                    "claim_id": flow["claim_id"],
                    "flow_kind": flow["flow_kind"],
                    "leg_role": leg_role,
                    "sector_id": flow[sector_field],
                    "cell_id": cell_id,
                    "report_group_id": flow["report_group_id"],
                    "delta_flow_signed_bil": _fmt(delta * sign),
                    "conversion_coeff": _fmt(conversion.conversion_coeff),
                    "domestic_eligibility_weight": _fmt(
                        conversion.domestic_eligibility_weight
                    ),
                    "activity_component": conversion.activity_component,
                    "activity_effect_bil": _fmt(effect),
                    "support_bil": _fmt(max(effect, Decimal("0"))),
                    "drag_bil": _fmt(max(-effect, Decimal("0"))),
                    "classification_basis": "leg_gross_diagnostic",
                    "headline_basis": "false",
                    "conversion_rule_id": conversion.conversion_rule_id,
                    "generated_from": conversion.generated_from,
                }
            )
    return rows


def _real_effect_cell_rows(
    flow_delta_rows: list[dict[str, str]],
    real_effect_leg_rows: list[dict[str, str]],
    conversions: dict[str, object],
) -> list[dict[str, str]]:
    net_by_cell: dict[tuple[str, str, str], Decimal] = {}
    sector_by_cell: dict[str, str] = {}
    source_legs_by_cell: dict[tuple[str, str, str], list[str]] = {}
    for flow in flow_delta_rows:
        if flow["real_conversion_eligible"] != "true":
            continue
        month = flow["month"]
        delta = Decimal(flow["delta_amount_bil"])
        for sign, sector_field, cell_field in [
            (Decimal("1"), "receiver_sector", "receiver_cell"),
            (Decimal("-1"), "payer_sector", "payer_cell"),
        ]:
            cell_id = flow[cell_field]
            key = (flow["run_pair_id"], month, cell_id)
            net_by_cell[key] = net_by_cell.get(key, Decimal("0")) + delta * sign
            sector_by_cell[cell_id] = flow[sector_field]
    for leg in real_effect_leg_rows:
        key = (leg["run_pair_id"], leg["month"], leg["cell_id"])
        source_legs_by_cell.setdefault(key, []).append(leg["real_effect_leg_id"])

    rows: list[dict[str, str]] = []
    for idx, key in enumerate(sorted(net_by_cell), start=1):
        run_pair_id, month, cell_id = key
        conversion = conversions[cell_id]
        net_flow = net_by_cell[key]
        effect = (
            net_flow
            * conversion.conversion_coeff
            * conversion.domestic_eligibility_weight
        )
        rows.append(
            {
                "real_effect_cell_id": f"REC{idx:04d}",
                "run_pair_id": run_pair_id,
                "month": month,
                "sector_id": sector_by_cell[cell_id],
                "cell_id": cell_id,
                "net_flow_delta_bil": _fmt(net_flow),
                "conversion_coeff": _fmt(conversion.conversion_coeff),
                "domestic_eligibility_weight": _fmt(
                    conversion.domestic_eligibility_weight
                ),
                "activity_component": conversion.activity_component,
                "activity_effect_bil": _fmt(effect),
                "support_bil": _fmt(max(effect, Decimal("0"))),
                "drag_bil": _fmt(max(-effect, Decimal("0"))),
                "classification_basis": "net_within_cell",
                "headline_basis": "true",
                "source_real_effect_leg_ids": ";".join(source_legs_by_cell.get(key, [])),
                "conversion_rule_id": conversion.conversion_rule_id,
                "generated_from": conversion.generated_from,
            }
        )
    return rows


def _ratewall_monthly_rows(
    config: RwtasConfig,
    cell_rows: list[dict[str, str]],
    leg_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for month in [calendar.month for calendar in config.calendar_months]:
        month_cell_rows = [row for row in cell_rows if row["month"] == month]
        month_leg_rows = [row for row in leg_rows if row["month"] == month]
        n_bil = sum(Decimal(row["support_bil"]) for row in month_cell_rows)
        d_bil = sum(Decimal(row["drag_bil"]) for row in month_cell_rows)
        net_bil = n_bil - d_bil
        leg_n = sum(Decimal(row["support_bil"]) for row in month_leg_rows)
        leg_d = sum(Decimal(row["drag_bil"]) for row in month_leg_rows)
        leg_net = sum(Decimal(row["activity_effect_bil"]) for row in month_leg_rows)
        rw_ratio = None if d_bil == 0 else n_bil / d_bil
        rows.append(
            {
                "run_pair_id": config.scenario_pair.run_pair_id,
                "state_id": config.scenario_pair.state_id,
                "month": month,
                "N_bil": _fmt(n_bil),
                "D_bil": _fmt(d_bil),
                "net_bil": _fmt(net_bil),
                "RW_ratio": "" if rw_ratio is None else _fmt(rw_ratio),
                "zero_D_flag": _bool_str(d_bil == 0),
                "support_effect_count": str(
                    sum(1 for row in month_cell_rows if Decimal(row["support_bil"]) > 0)
                ),
                "drag_effect_count": str(
                    sum(1 for row in month_cell_rows if Decimal(row["drag_bil"]) > 0)
                ),
                "leg_gross_N_bil": _fmt(leg_n),
                "leg_gross_D_bil": _fmt(leg_d),
                "leg_gross_net_bil": _fmt(leg_net),
                "leg_gross_net_equals_headline_net": _bool_str(
                    abs(leg_net - net_bil) <= PASS_TOLERANCE
                ),
                "ricardian_offset": _fmt(config.ricardian_offset),
                "netting_rule": "net_within_cell_then_classify",
                "conversion_rule_basis": "one_symmetric_magnitude_per_cell",
            }
        )
    return rows


def _ratewall_rollup_rows(
    config: RwtasConfig,
    monthly_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    n_bil = sum(Decimal(row["N_bil"]) for row in monthly_rows)
    d_bil = sum(Decimal(row["D_bil"]) for row in monthly_rows)
    net_bil = n_bil - d_bil
    return [
        {
            "run_pair_id": config.scenario_pair.run_pair_id,
            "period_id": f"{config.scenario_pair.start_month}..{config.scenario_pair.end_month}",
            "start_month": config.scenario_pair.start_month,
            "end_month": config.scenario_pair.end_month,
            "N_bil": _fmt(n_bil),
            "D_bil": _fmt(d_bil),
            "net_bil": _fmt(net_bil),
            "RW_ratio": "" if d_bil == 0 else _fmt(n_bil / d_bil),
            "rollup_rule": "sum_monthly_N_and_D_then_divide",
        }
    ]


def _report_channel_monthly_rows(
    config: RwtasConfig,
    monthly_rows: list[dict[str, str]],
    leg_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    source_leg_ids = ";".join(row["real_effect_leg_id"] for row in leg_rows)
    rows: list[dict[str, str]] = []
    for monthly in monthly_rows:
        rows.append(
            {
                "report_channel_row_id": f"RC{len(rows) + 1:04d}",
                "run_pair_id": monthly["run_pair_id"],
                "month": monthly["month"],
                "report_view_id": "official",
                "report_group_id": "official_total",
                "channel_id": "official_total",
                "additive_flag": "true",
                "exclusive_assignment_flag": "true",
                "classification_basis": "net_within_cell",
                "N_bil": monthly["N_bil"],
                "D_bil": monthly["D_bil"],
                "net_bil": monthly["net_bil"],
                "source_real_effect_leg_ids": source_leg_ids,
            }
        )
        rows.append(
            {
                "report_channel_row_id": f"RC{len(rows) + 1:04d}",
                "run_pair_id": monthly["run_pair_id"],
                "month": monthly["month"],
                "report_view_id": "leg_gross_diagnostic",
                "report_group_id": "gross_legs",
                "channel_id": "gross_leg_diagnostic",
                "additive_flag": "false",
                "exclusive_assignment_flag": "false",
                "classification_basis": "leg_gross_diagnostic",
                "N_bil": monthly["leg_gross_N_bil"],
                "D_bil": monthly["leg_gross_D_bil"],
                "net_bil": monthly["leg_gross_net_bil"],
                "source_real_effect_leg_ids": source_leg_ids,
            }
        )
    return rows


def _report_channel_rollup_rows(
    config: RwtasConfig,
    channel_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    by_view: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = {}
    for row in channel_rows:
        key = (
            row["report_view_id"],
            row["report_group_id"],
            row["channel_id"],
            row["additive_flag"],
            row["exclusive_assignment_flag"],
        )
        by_view.setdefault(key, []).append(row)
    for idx, (key, grouped) in enumerate(sorted(by_view.items()), start=1):
        report_view_id, report_group_id, channel_id, additive, exclusive = key
        n_bil = sum(Decimal(row["N_bil"]) for row in grouped)
        d_bil = sum(Decimal(row["D_bil"]) for row in grouped)
        rows.append(
            {
                "report_channel_rollup_id": f"RCR{idx:04d}",
                "run_pair_id": config.scenario_pair.run_pair_id,
                "period_id": f"{config.scenario_pair.start_month}..{config.scenario_pair.end_month}",
                "report_view_id": report_view_id,
                "report_group_id": report_group_id,
                "channel_id": channel_id,
                "additive_flag": additive,
                "exclusive_assignment_flag": exclusive,
                "N_bil": _fmt(n_bil),
                "D_bil": _fmt(d_bil),
                "net_bil": _fmt(n_bil - d_bil),
            }
        )
    return rows


def _reference_rate_rows(
    config: RwtasConfig,
    paths: dict[tuple[str, str, str], ReferenceRatePath],
) -> list[dict[str, str]]:
    pair = config.scenario_pair
    rows: list[dict[str, str]] = []
    for reference in sorted(config.reference_rates, key=lambda item: item.reference_rate_id):
        for month in [calendar.month for calendar in config.calendar_months]:
            baseline = paths[(pair.baseline_scenario_id, month, reference.reference_rate_id)]
            shock = paths[(pair.shock_scenario_id, month, reference.reference_rate_id)]
            delta = shock.annual_rate - baseline.annual_rate
            rows.append(
                {
                    "run_pair_id": pair.run_pair_id,
                    "month": month,
                    "reference_rate_id": reference.reference_rate_id,
                    "driver_id": reference.driver_id,
                    "rate_family": reference.rate_family,
                    "baseline_annual_rate": _fmt(baseline.annual_rate),
                    "shock_annual_rate": _fmt(shock.annual_rate),
                    "delta_annual_rate": _fmt(delta),
                    "shock_pass_through_multiplier": _fmt(
                        shock.shock_pass_through_multiplier
                    ),
                    "shock_eligible_flag": _bool_str(shock.shock_eligible_flag),
                    "bp_year_intensity": _fmt(delta * _tau(config) * Decimal("10000")),
                }
            )
    return rows


def _run_manifest_rows(config: RwtasConfig) -> list[dict[str, str]]:
    pair = config.scenario_pair
    return [
        {
            "run_pair_id": pair.run_pair_id,
            "state_id": pair.state_id,
            "baseline_scenario_id": pair.baseline_scenario_id,
            "shock_scenario_id": pair.shock_scenario_id,
            "shock_id": pair.shock_id,
            "start_month": pair.start_month,
            "end_month": pair.end_month,
            "same_state_pair_flag": _bool_str(pair.same_state_pair_flag),
            "sector_count": str(len(config.sectors)),
            "claim_count": str(len(config.claim_opening_stock)),
            "ricardian_offset": _fmt(config.ricardian_offset),
            "sign_convention_flow_amount": SIGN_CONVENTIONS["flow_amount"],
            "sign_convention_activity_effect": SIGN_CONVENTIONS[
                "activity_effect_bil"
            ],
            "conversion_rule_basis": "one_symmetric_magnitude_per_cell",
            "netting_rule": "net_within_cell_then_classify",
            "status": "pass",
        }
    ]


def _invariant_rows(
    config: RwtasConfig,
    tables: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    checks = [
        _check_t01(config, tables),
        _check_t02(tables),
        _check_t03(tables),
        _check_t04(tables),
        _check_t05(tables),
        _check_t06(tables),
        _check_t07(tables),
        _check_t08(config),
        _check_t09(config, tables),
        _check_t10(tables),
        _check_t11(config, tables),
        _check_t12(tables),
        _check_t13(tables),
        _check_t14(tables),
        _check_t15(tables),
        _check_t16(tables),
        _check_t17(tables),
        _check_t18(tables),
        _check_t19(tables),
        _check_t20(tables),
        _check_t21(tables),
    ]
    return [check | {"scope": "RWTAS_V0"} for check in checks]


def _check_row(
    check_id: str,
    lhs: Decimal | str,
    rhs: Decimal | str,
    difference: Decimal,
    tolerance: Decimal = PASS_TOLERANCE,
    failed_row_count: int = 0,
    message: str = "",
) -> dict[str, str]:
    return {
        "check_id": check_id,
        "lhs": _fmt(lhs) if isinstance(lhs, Decimal) else lhs,
        "rhs": _fmt(rhs) if isinstance(rhs, Decimal) else rhs,
        "difference": _fmt(difference),
        "tolerance": _fmt(tolerance),
        "status": "pass" if failed_row_count == 0 and abs(difference) <= tolerance else "fail",
        "failed_row_count": str(failed_row_count),
        "message": message,
    }


def _check_t01(config: RwtasConfig, tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    sectors_ok = tuple(sector.sector_id for sector in config.sectors) == SECTOR_IDS
    separated_ok = {"federal_reserve", "treasury_federal_government"}.issubset(SECTOR_IDS)
    separated_ok = separated_ok and {"banks_depositories", "nonbank_financial"}.issubset(SECTOR_IDS)
    banned_count = 0
    for rows in tables.values():
        for row in rows:
            banned_count += sum(1 for value in row.values() if value in {
                "government",
                "public_sector",
                "financial_sector",
                "private_finance",
            })
    failed = 0 if sectors_ok and separated_ok and banned_count == 0 else 1 + banned_count
    return _check_row(
        "T01",
        "eight_base_sectors_and_no_collapsed_labels",
        "pass",
        Decimal("0"),
        failed_row_count=failed,
    )


def _check_t02(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    failed = sum(
        1
        for row in tables["out_claim_state_monthly"]
        if Decimal(row["principal_begin_bil"]) < 0
    )
    return _check_row("T02", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t03(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    failed = 0
    for row in tables["out_claim_state_monthly"]:
        partition = (
            Decimal(row["performing_principal_bil"])
            + Decimal(row["distressed_paying_principal_bil"])
            + Decimal(row["defaulted_nonperforming_principal_bil"])
        )
        if abs(partition - Decimal(row["principal_begin_bil"])) > PASS_TOLERANCE:
            failed += 1
    return _check_row("T03", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t04(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    failed = sum(
        1
        for row in tables["out_flow_ledger_monthly"]
        if row["payer_outflow_bil"] != row["receiver_inflow_bil"]
        or row["payer_outflow_bil"] != row["amount_bil"]
    )
    return _check_row("T04", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t05(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    lhs = sum(Decimal(row["payer_outflow_bil"]) for row in tables["out_flow_ledger_monthly"])
    rhs = sum(Decimal(row["receiver_inflow_bil"]) for row in tables["out_flow_ledger_monthly"])
    return _check_row("T05", lhs, rhs, lhs - rhs)


def _check_t06(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    total = sum(Decimal(row["net_cash_flow_delta_bil"]) for row in tables["out_sector_flow_monthly"])
    return _check_row("T06", total, Decimal("0"), total)


def _check_t07(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    failed = sum(
        1
        for row in tables["out_claim_state_monthly"]
        if abs(Decimal(row["stock_flow_identity_difference_bil"])) > PASS_TOLERANCE
    )
    return _check_row("T07", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t08(config: RwtasConfig) -> dict[str, str]:
    failed = 0 if config.scenario_pair.same_state_pair_flag else 1
    return _check_row("T08", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t09(config: RwtasConfig, tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    shock_by_id = {shock.shock_id: shock for shock in config.shocks}
    shock_delta = shock_by_id[config.scenario_pair.shock_id].shock_rate_delta_ann
    failed = 0
    for row in tables["out_reference_rate_monthly"]:
        expected = (
            shock_delta * Decimal(row["shock_pass_through_multiplier"])
            if row["shock_eligible_flag"] == "true"
            else Decimal("0")
        )
        if abs(Decimal(row["delta_annual_rate"]) - expected) > PASS_TOLERANCE:
            failed += 1
    return _check_row("T09", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t10(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    failed = 0
    for row in tables["out_claim_rate_monthly"]:
        if row["rate_type"] in {"fixed", "fixed_contract", "zero", "zero_contract"}:
            continue
        expected = (
            Decimal(row["reference_rate_ann"])
            + Decimal(row["spread_ann"])
            + Decimal(row["contract_adjustment_ann"])
        )
        if abs(Decimal(row["effective_rate_ann"]) - expected) > PASS_TOLERANCE:
            failed += 1
    return _check_row("T10", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t11(config: RwtasConfig, tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    by_claim: dict[str, list[dict[str, str]]] = {}
    for row in tables["out_claim_rate_monthly"]:
        by_claim.setdefault(row["claim_id"], []).append(row)
    failed = 0
    for rows in by_claim.values():
        if rows[0]["rate_type"] not in {"fixed", "fixed_contract"}:
            continue
        rates = {row["effective_rate_ann"] for row in rows}
        if len(rates) != 1:
            failed += 1
    return _check_row("T11", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t12(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    failed = 0
    for row in tables["out_claim_rate_monthly"]:
        expected = Decimal(row["paying_principal_bil"])
        if Decimal(row["scheduled_interest_base_bil"]) != expected:
            failed += 1
    return _check_row("T12", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t13(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    failed = 0
    for row in tables["out_default_state_monthly"]:
        if Decimal(row["holder_loss_bil"]) != Decimal(row["issuer_relief_bil"]):
            failed += 1
        if Decimal(row["non_double_count_check_bil"]) != 0:
            failed += 1
    return _check_row("T13", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t14(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    treasury_flow = any(
        row["payer_sector"] == "treasury_federal_government"
        for row in tables["out_flow_delta_monthly"]
    )
    fed_flow = any(
        row["payer_sector"] == "federal_reserve"
        for row in tables["out_flow_delta_monthly"]
    )
    failed = 0 if treasury_flow and fed_flow else 1
    return _check_row("T14", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t15(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    sectors = {row["sector_id"] for row in tables["out_sector_flow_monthly"]}
    failed = 0 if {"banks_depositories", "nonbank_financial"}.issubset(sectors) else 1
    return _check_row("T15", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t16(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    monthly_n = sum(Decimal(row["N_bil"]) for row in tables["out_ratewall_monthly"])
    monthly_d = sum(Decimal(row["D_bil"]) for row in tables["out_ratewall_monthly"])
    rollup = tables["out_ratewall_rollup"][0]
    diff = abs(monthly_n - Decimal(rollup["N_bil"])) + abs(
        monthly_d - Decimal(rollup["D_bil"])
    )
    return _check_row("T16", diff, Decimal("0"), diff)


def _check_t17(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    leg_ids = {row["real_effect_leg_id"] for row in tables["out_real_effect_leg_monthly"]}
    failed = 0
    for row in tables["out_report_channel_monthly"]:
        refs = {item for item in row["source_real_effect_leg_ids"].split(";") if item}
        if not refs or not refs.issubset(leg_ids):
            failed += 1
    return _check_row("T17", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t18(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    monthly = tables["out_ratewall_monthly"][0]
    official = [
        row
        for row in tables["out_report_channel_monthly"]
        if row["report_view_id"] == "official" and row["additive_flag"] == "true"
    ]
    n = sum(Decimal(row["N_bil"]) for row in official)
    d = sum(Decimal(row["D_bil"]) for row in official)
    diff = abs(n - Decimal(monthly["N_bil"])) + abs(d - Decimal(monthly["D_bil"]))
    return _check_row("T18", diff, Decimal("0"), diff)


def _check_t19(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    diagnostic = [
        row
        for row in tables["out_report_channel_monthly"]
        if row["report_view_id"] != "official"
    ]
    failed = sum(1 for row in diagnostic if row["additive_flag"] != "false")
    if not diagnostic:
        failed += 1
    return _check_row("T19", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t20(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    failed = 0
    for row in tables["out_real_effect_leg_monthly"]:
        if (
            row["leg_role"] == "receiver"
            and row["sector_id"] == "rest_of_world"
            and Decimal(row["delta_flow_signed_bil"]) > 0
            and Decimal(row["support_bil"]) != 0
        ):
            failed += 1
    return _check_row("T20", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _check_t21(tables: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    failed = 0
    for row in tables["out_ratewall_monthly"]:
        if Decimal(row["D_bil"]) == 0:
            if row["zero_D_flag"] != "true" or row["RW_ratio"] != "":
                failed += 1
        elif row["zero_D_flag"] != "false" or row["RW_ratio"] == "":
            failed += 1
    return _check_row("T21", Decimal(failed), Decimal("0"), Decimal(failed), failed_row_count=failed)


def _effective_rate(term: ClaimTerm, path: ReferenceRatePath) -> Decimal:
    if term.zero_rate_flag or term.rate_type in {"zero", "zero_contract"}:
        return Decimal("0")
    if term.rate_type in {"fixed", "fixed_contract"}:
        return term.contract_fixed_rate
    if term.rate_type in {"administered", "administered_policy"} and term.administered_rate:
        return term.administered_rate
    return path.annual_rate + term.spread + term.contract_adjustment


def _resets_in_v0(term: ClaimTerm) -> bool:
    if term.zero_rate_flag or term.rate_type in {"fixed", "fixed_contract", "zero", "zero_contract"}:
        return False
    return term.repricing_share > 0


def _tau(config: RwtasConfig) -> Decimal:
    if len(config.calendar_months) != 1:
        raise ValueError("RWTAS V0 supports one month per run")
    return config.calendar_months[0].tau_month


def _fmt(value: Decimal | str) -> str:
    if isinstance(value, str):
        return value
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _bool_str(value: bool) -> str:
    return "true" if value else "false"

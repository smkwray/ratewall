"""Small cross-outcome accounting contract for RWTAM adapters.

Specialized channel code may construct primitives from claims, contracts, or
source-specific state recursions.  It must hand those primitives to this module
before outcome aggregation.  The evaluator knows no channel names: it only
knows ownership, units, ledger sides, feasibility, and adjustment keys.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from typing import Mapping

from ratewall.rwtam.measurement import MEASUREMENT_CLASSES


D = Decimal
CALC_PRECISION = 40

OUTCOME_RW_Y = "rw_y"
OUTCOME_CPI_U = "cpi_u"
OUTCOME_PCE = "pce"
OUTCOMES = frozenset({OUTCOME_RW_Y, OUTCOME_CPI_U, OUTCOME_PCE})

RW_Y_MEASURE_LABEL = "Demand-equivalent attenuation ratio"
RW_Y_MEASURE_UNIT = "demand_equivalent_attenuation_ratio"
G_Y_MEASURE_LABEL = "Net demand-drag path G_Y = D_Y - N_Y"
RW_Y_ESTIMAND_DESCRIPTION = (
    "Conditional cumulative-flow gross support-to-drag ratio RW_Y = N_Y / D_Y "
    "under stated assumptions; the primary object is the net demand-drag path "
    "G_Y = D_Y - N_Y; not a causal output response"
)

SIDE_N = "N"
SIDE_D = "D"
SIDE_PRICE_LOWERING = "PRICE_LOWERING"
SIDE_PRICE_RAISING = "PRICE_RAISING"
LEDGER_SIDES = frozenset(
    {SIDE_N, SIDE_D, SIDE_PRICE_LOWERING, SIDE_PRICE_RAISING}
)

ROLE_HEADLINE_ADDITIVE = "headline_additive"
ROLE_DIAGNOSTIC = "diagnostic"
AGGREGATION_ROLES = frozenset({ROLE_HEADLINE_ADDITIVE, ROLE_DIAGNOSTIC})

FEASIBLE = "feasible"
INFEASIBLE = "infeasible"
FEASIBILITY_STATUSES = frozenset({FEASIBLE, INFEASIBLE})


class AccountingContractError(ValueError):
    """Raised when a primitive ledger violates the shared contract."""


class InfeasibleValueFunction(AccountingContractError):
    """Raised when evaluation requires an economically unavailable primitive."""


@dataclass(frozen=True)
class AccountingPrimitive:
    """One signed, owned contribution before outcome aggregation.

    ``value`` is signed.  N and D use billion dollars; price sides use log
    points.  ``adjustment_keys`` may contain several keys when a primitive is
    jointly affected by logically distinct parameters; the generic evaluator
    applies their product.  Parameter-to-factor ownership remains configuration.
    """

    primitive_id: str
    outcome: str
    ledger_side: str
    value: Decimal
    unit: str
    period: str
    month_index: int
    scenario_id: str
    state_id: str
    source_kind: str
    source_key: str
    instrument_family: str
    stock_id: str
    contract_id: str
    payer_cell: str
    receiver_cell: str
    maturity_month: str
    reset_month: str
    timing_rule_id: str
    cash_owner_key: str
    incidence_owner_key: str
    outcome_owner_key: str
    overlap_key: str
    evidence_grade: str
    measurement_class: str = "unavailable"
    economic_ledger: str = "current_income"
    cash_component: str = "unspecified"
    recognition_basis: str = "cash_settled"
    headline_rule: str = "additive"
    netting_bucket: str = ""
    adjustment_keys: tuple[str, ...] = ()
    aggregation_role: str = ROLE_HEADLINE_ADDITIVE
    feasibility_status: str = FEASIBLE

    @property
    def structural_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.primitive_id,
            self.outcome,
            self.ledger_side,
            self.unit,
            self.aggregation_role,
        )


@dataclass(frozen=True)
class PrimitiveLedger:
    primitives: tuple[AccountingPrimitive, ...]
    contract_version: str = "rwtam_accounting_primitive_v1"
    expected_rw_y_unit: str = "bil_dollars"

    def __post_init__(self) -> None:
        validate_ledger(self)

    @property
    def adjustment_keys(self) -> frozenset[str]:
        return frozenset(
            key for primitive in self.primitives for key in primitive.adjustment_keys
        )


@dataclass(frozen=True)
class AccountingEvaluation:
    totals: dict[tuple[str, str], Decimal]
    scaled_primitives: tuple[AccountingPrimitive, ...]

    def side(self, outcome: str, ledger_side: str) -> Decimal:
        return self.totals.get((outcome, ledger_side), D(0))

    def rw_y(self) -> Decimal:
        denominator = self.side(OUTCOME_RW_Y, SIDE_D)
        if denominator == 0:
            raise AccountingContractError("RW_Y denominator is zero")
        return self.side(OUTCOME_RW_Y, SIDE_N) / denominator

    def net_price(self, outcome: str) -> Decimal:
        if outcome not in {OUTCOME_CPI_U, OUTCOME_PCE}:
            raise AccountingContractError(f"{outcome!r} is not a price outcome")
        return self.side(outcome, SIDE_PRICE_LOWERING) - self.side(
            outcome, SIDE_PRICE_RAISING
        )


@dataclass(frozen=True)
class OverlapResolution:
    ledger: PrimitiveLedger
    audit_rows: tuple[dict[str, str], ...]


def resolve_overlap_candidates(
    primitives: tuple[AccountingPrimitive, ...],
    *,
    selected_owners: Mapping[tuple[str, str, str], str],
) -> OverlapResolution:
    """Select one declared additive owner and retain every candidate in audit."""

    groups: dict[tuple[str, str, str], list[AccountingPrimitive]] = {}
    passthrough: list[AccountingPrimitive] = []
    for primitive in primitives:
        if primitive.aggregation_role != ROLE_HEADLINE_ADDITIVE:
            passthrough.append(primitive)
            continue
        key = (primitive.outcome, primitive.ledger_side, primitive.overlap_key)
        groups.setdefault(key, []).append(primitive)
    selected: list[AccountingPrimitive] = []
    audit: list[dict[str, str]] = []
    for key, candidates in sorted(groups.items()):
        declared = selected_owners.get(key)
        if len(candidates) == 1:
            winner = candidates[0]
            if declared is not None and declared != winner.outcome_owner_key:
                raise AccountingContractError(
                    f"declared overlap owner {declared!r} does not match {key}"
                )
        else:
            if not declared:
                raise AccountingContractError(
                    f"duplicate overlap candidates require a declared owner: {key}"
                )
            matches = [
                candidate
                for candidate in candidates
                if candidate.outcome_owner_key == declared
            ]
            if len(matches) != 1:
                raise AccountingContractError(
                    f"declared overlap owner must resolve exactly once: {key}/{declared}"
                )
            winner = matches[0]
        selected.append(winner)
        for candidate in candidates:
            is_selected = candidate is winner
            audit.append(
                {
                    "overlap_key": candidate.overlap_key,
                    "candidate_primitive_id": candidate.primitive_id,
                    "candidate_owner": candidate.outcome_owner_key,
                    "selected_owner": winner.outcome_owner_key,
                    "selected": str(is_selected).lower(),
                    "rejection_reason": (
                        "" if is_selected else "declared_overlap_owner_precedence"
                    ),
                    "response_abs_weight": str(abs(candidate.value)),
                    "measurement_class": candidate.measurement_class,
                    "outcome": candidate.outcome,
                    "ledger_side": candidate.ledger_side,
                    "month_index": str(candidate.month_index),
                }
            )
    ledger = PrimitiveLedger(tuple([*selected, *passthrough]))
    return OverlapResolution(ledger=ledger, audit_rows=tuple(audit))


def validate_ledger(ledger: PrimitiveLedger) -> None:
    ids: set[str] = set()
    overlap_seen: dict[tuple[str, str, str], str] = {}
    if ledger.expected_rw_y_unit not in {
        "bil_dollars",
        "normalized_output_units",
    }:
        raise AccountingContractError(
            f"unauthorized RW_Y unit {ledger.expected_rw_y_unit!r}"
        )
    for primitive in ledger.primitives:
        if not primitive.primitive_id:
            raise AccountingContractError("primitive_id must not be empty")
        if primitive.primitive_id in ids:
            raise AccountingContractError(
                f"duplicate primitive_id {primitive.primitive_id!r}"
            )
        ids.add(primitive.primitive_id)
        if primitive.outcome not in OUTCOMES:
            raise AccountingContractError(f"unknown outcome {primitive.outcome!r}")
        if primitive.ledger_side not in LEDGER_SIDES:
            raise AccountingContractError(
                f"unknown ledger side {primitive.ledger_side!r}"
            )
        if primitive.aggregation_role not in AGGREGATION_ROLES:
            raise AccountingContractError(
                f"unknown aggregation role {primitive.aggregation_role!r}"
            )
        if primitive.feasibility_status not in FEASIBILITY_STATUSES:
            raise AccountingContractError(
                f"unknown feasibility status {primitive.feasibility_status!r}"
            )
        if primitive.measurement_class not in MEASUREMENT_CLASSES:
            raise AccountingContractError(
                f"unknown measurement class {primitive.measurement_class!r}"
            )
        if primitive.month_index < 0:
            raise AccountingContractError("month_index must be nonnegative")
        required_owners = (
            primitive.cash_owner_key,
            primitive.incidence_owner_key,
            primitive.outcome_owner_key,
            primitive.overlap_key,
        )
        if any(not owner for owner in required_owners):
            raise AccountingContractError(
                f"primitive {primitive.primitive_id} is missing an ownership key"
            )
        if primitive.outcome == OUTCOME_RW_Y:
            if primitive.ledger_side not in {SIDE_N, SIDE_D}:
                raise AccountingContractError(
                    f"RW_Y primitive {primitive.primitive_id} has a price side"
                )
            if primitive.unit != ledger.expected_rw_y_unit:
                if ledger.expected_rw_y_unit == "bil_dollars":
                    raise AccountingContractError(
                        f"RW_Y primitive {primitive.primitive_id} must use bil_dollars"
                    )
                raise AccountingContractError(
                    f"RW_Y primitive {primitive.primitive_id} must use expected unit "
                    f"{ledger.expected_rw_y_unit!r}"
                )
        else:
            if primitive.ledger_side not in {
                SIDE_PRICE_LOWERING,
                SIDE_PRICE_RAISING,
            }:
                raise AccountingContractError(
                    f"price primitive {primitive.primitive_id} has an N/D side"
                )
            if primitive.unit != "logpt_price_level":
                raise AccountingContractError(
                    f"price primitive {primitive.primitive_id} must use logpt_price_level"
                )
        if len(set(primitive.adjustment_keys)) != len(primitive.adjustment_keys):
            raise AccountingContractError(
                f"primitive {primitive.primitive_id} repeats an adjustment key"
            )
        if primitive.aggregation_role == ROLE_HEADLINE_ADDITIVE:
            overlap_key = (
                primitive.outcome,
                primitive.ledger_side,
                primitive.overlap_key,
            )
            prior = overlap_seen.setdefault(overlap_key, primitive.primitive_id)
            if prior != primitive.primitive_id:
                raise AccountingContractError(
                    "duplicate additive overlap owner "
                    f"{overlap_key}: {prior} and {primitive.primitive_id}"
                )


def evaluate_ledger(
    ledger: PrimitiveLedger,
    *,
    adjustments: dict[str, Decimal] | None = None,
    scale: Decimal = D(1),
    require_feasible: bool = True,
) -> AccountingEvaluation:
    """Apply configured adjustments and aggregate every outcome generically."""

    adjustments = adjustments or {}
    unknown = set(adjustments) - set(ledger.adjustment_keys)
    if unknown:
        raise AccountingContractError(
            f"adjustments do not own a primitive in this ledger: {sorted(unknown)}"
        )
    totals: dict[tuple[str, str], Decimal] = {}
    scaled: list[AccountingPrimitive] = []
    with localcontext() as context:
        context.prec = CALC_PRECISION
        for primitive in ledger.primitives:
            if (
                require_feasible
                and primitive.aggregation_role == ROLE_HEADLINE_ADDITIVE
                and primitive.feasibility_status != FEASIBLE
            ):
                raise InfeasibleValueFunction(
                    f"primitive {primitive.primitive_id} is infeasible"
                )
            multiplier = D(1)
            for key in primitive.adjustment_keys:
                multiplier *= adjustments.get(key, D(1))
            value = primitive.value * multiplier * scale
            scaled_primitive = replace(primitive, value=value)
            scaled.append(scaled_primitive)
            if primitive.aggregation_role == ROLE_HEADLINE_ADDITIVE:
                total_key = (primitive.outcome, primitive.ledger_side)
                totals[total_key] = totals.get(total_key, D(0)) + value
    return AccountingEvaluation(totals=totals, scaled_primitives=tuple(scaled))


def primitive_rows(ledger: PrimitiveLedger) -> list[dict[str, str]]:
    """Serialize the canonical ledger without weakening its typed contract."""

    return [
        {
            "contract_version": ledger.contract_version,
            **(
                {"expected_rw_y_unit": ledger.expected_rw_y_unit}
                if ledger.expected_rw_y_unit != "bil_dollars"
                else {}
            ),
            "primitive_id": item.primitive_id,
            "outcome": item.outcome,
            "ledger_side": item.ledger_side,
            "value": str(item.value),
            "unit": item.unit,
            "period": item.period,
            "month_index": str(item.month_index),
            "scenario_id": item.scenario_id,
            "state_id": item.state_id,
            "source_kind": item.source_kind,
            "source_key": item.source_key,
            "instrument_family": item.instrument_family,
            "stock_id": item.stock_id,
            "contract_id": item.contract_id,
            "payer_cell": item.payer_cell,
            "receiver_cell": item.receiver_cell,
            "maturity_month": item.maturity_month,
            "reset_month": item.reset_month,
            "timing_rule_id": item.timing_rule_id,
            "cash_owner_key": item.cash_owner_key,
            "incidence_owner_key": item.incidence_owner_key,
            "outcome_owner_key": item.outcome_owner_key,
            "overlap_key": item.overlap_key,
            "evidence_grade": item.evidence_grade,
            "measurement_class": item.measurement_class,
            "economic_ledger": item.economic_ledger,
            "cash_component": item.cash_component,
            "recognition_basis": item.recognition_basis,
            "headline_rule": item.headline_rule,
            "netting_bucket": item.netting_bucket,
            "adjustment_keys": ";".join(item.adjustment_keys),
            "aggregation_role": item.aggregation_role,
            "feasibility_status": item.feasibility_status,
        }
        for item in ledger.primitives
    ]


def ledger_from_rows(rows: list[dict[str, str]]) -> PrimitiveLedger:
    """Rehydrate a serialized canonical ledger for downstream scenario slicing."""

    versions = {row["contract_version"] for row in rows}
    if len(versions) > 1:
        raise AccountingContractError(f"mixed primitive contract versions: {versions}")
    items = tuple(
        AccountingPrimitive(
            primitive_id=row["primitive_id"],
            outcome=row["outcome"],
            ledger_side=row["ledger_side"],
            value=D(row["value"]),
            unit=row["unit"],
            period=row["period"],
            month_index=int(row["month_index"]),
            scenario_id=row["scenario_id"],
            state_id=row["state_id"],
            source_kind=row["source_kind"],
            source_key=row["source_key"],
            instrument_family=row["instrument_family"],
            stock_id=row["stock_id"],
            contract_id=row["contract_id"],
            payer_cell=row["payer_cell"],
            receiver_cell=row["receiver_cell"],
            maturity_month=row["maturity_month"],
            reset_month=row["reset_month"],
            timing_rule_id=row["timing_rule_id"],
            cash_owner_key=row["cash_owner_key"],
            incidence_owner_key=row["incidence_owner_key"],
            outcome_owner_key=row["outcome_owner_key"],
            overlap_key=row["overlap_key"],
            evidence_grade=row["evidence_grade"],
            measurement_class=row.get("measurement_class", "unavailable"),
            economic_ledger=row.get("economic_ledger", "current_income"),
            cash_component=row.get("cash_component", "unspecified"),
            recognition_basis=row.get("recognition_basis", "cash_settled"),
            headline_rule=row.get("headline_rule", "additive"),
            netting_bucket=row.get("netting_bucket", ""),
            adjustment_keys=tuple(filter(None, row["adjustment_keys"].split(";"))),
            aggregation_role=row["aggregation_role"],
            feasibility_status=row["feasibility_status"],
        )
        for row in rows
    )
    expected_units = {
        row.get("expected_rw_y_unit", "bil_dollars") for row in rows
    }
    if len(expected_units) > 1:
        raise AccountingContractError(
            f"mixed expected RW_Y units: {sorted(expected_units)}"
        )
    return PrimitiveLedger(
        items,
        contract_version=next(iter(versions), "rwtam_accounting_primitive_v1"),
        expected_rw_y_unit=next(iter(expected_units), "bil_dollars"),
    )


def blend_ledgers(
    first: PrimitiveLedger,
    second: PrimitiveLedger,
    weight: Decimal,
    *,
    state_id: str,
    period: str,
) -> PrimitiveLedger:
    """Interpolate values only; the accounting contract must match exactly."""

    if weight < 0 or weight > 1:
        raise AccountingContractError(f"blend weight outside [0,1]: {weight}")
    if first.contract_version != second.contract_version:
        raise AccountingContractError("cannot blend different contract versions")
    if first.expected_rw_y_unit != second.expected_rw_y_unit:
        raise AccountingContractError("cannot blend different RW_Y unit contracts")
    first_by_key = {primitive.structural_key: primitive for primitive in first.primitives}
    second_by_key = {
        primitive.structural_key: primitive for primitive in second.primitives
    }
    if set(first_by_key) != set(second_by_key):
        raise AccountingContractError("cannot blend ledgers with different primitives")
    blended: list[AccountingPrimitive] = []
    with localcontext() as context:
        context.prec = CALC_PRECISION
        for key in sorted(first_by_key):
            left = first_by_key[key]
            right = second_by_key[key]
            comparable = (
                "month_index",
                "scenario_id",
                "source_kind",
                "instrument_family",
                "stock_id",
                "contract_id",
                "payer_cell",
                "receiver_cell",
                "maturity_month",
                "reset_month",
                "timing_rule_id",
                "cash_owner_key",
                "incidence_owner_key",
                "outcome_owner_key",
                "overlap_key",
                "evidence_grade",
                "measurement_class",
                "adjustment_keys",
                "economic_ledger",
                "cash_component",
                "recognition_basis",
                "headline_rule",
                "netting_bucket",
            )
            for field in comparable:
                if getattr(left, field) != getattr(right, field):
                    raise AccountingContractError(
                        f"cannot blend {left.primitive_id}: {field} differs"
                    )
            blended.append(
                replace(
                    left,
                    value=left.value + weight * (right.value - left.value),
                    state_id=state_id,
                    period=period,
                    feasibility_status=(
                        FEASIBLE
                        if left.feasibility_status == right.feasibility_status == FEASIBLE
                        else INFEASIBLE
                    ),
                )
            )
    return PrimitiveLedger(
        tuple(blended),
        contract_version=first.contract_version,
        expected_rw_y_unit=first.expected_rw_y_unit,
    )

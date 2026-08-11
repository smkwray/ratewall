from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from ratewall.rwtam.accounting_primitives import (
    AccountingContractError,
    AccountingPrimitive,
    InfeasibleValueFunction,
    PrimitiveLedger,
    SIDE_D,
    SIDE_N,
    SIDE_PRICE_LOWERING,
    SIDE_PRICE_RAISING,
    blend_ledgers,
    evaluate_ledger,
    ledger_from_rows,
    primitive_rows,
    resolve_overlap_candidates,
)


D = Decimal


def _primitive(
    primitive_id: str,
    outcome: str,
    side: str,
    value: str,
    *,
    adjustment_keys: tuple[str, ...] = (),
) -> AccountingPrimitive:
    return AccountingPrimitive(
        primitive_id=primitive_id,
        outcome=outcome,
        ledger_side=side,
        value=D(value),
        unit="bil_dollars" if outcome == "rw_y" else "logpt_price_level",
        period="120m",
        month_index=120,
        scenario_id="generic_scenario",
        state_id="generic_state",
        source_kind="test_adapter",
        source_key=primitive_id,
        instrument_family="generic_contract",
        stock_id="stock",
        contract_id="contract",
        payer_cell="payer",
        receiver_cell="receiver",
        maturity_month="",
        reset_month="",
        timing_rule_id="monthly",
        cash_owner_key=f"cash:{primitive_id}",
        incidence_owner_key=f"incidence:{primitive_id}",
        outcome_owner_key=f"outcome:{primitive_id}",
        overlap_key=f"overlap:{primitive_id}",
        evidence_grade="test",
        adjustment_keys=adjustment_keys,
    )


def test_generic_evaluator_aggregates_without_channel_names() -> None:
    ledger = PrimitiveLedger(
        (
            _primitive("support_a", "rw_y", SIDE_N, "10", adjustment_keys=("a",)),
            _primitive("support_b", "rw_y", SIDE_N, "2"),
            _primitive("drag", "rw_y", SIDE_D, "20", adjustment_keys=("d",)),
            _primitive(
                "lower",
                "cpi_u",
                SIDE_PRICE_LOWERING,
                "0.4",
                adjustment_keys=("a", "timing"),
            ),
            _primitive(
                "raise",
                "cpi_u",
                SIDE_PRICE_RAISING,
                "0.1",
            ),
        )
    )
    result = evaluate_ledger(
        ledger,
        adjustments={"a": D("1.5"), "d": D("2"), "timing": D("0.5")},
    )
    assert result.side("rw_y", SIDE_N) == D("17")
    assert result.side("rw_y", SIDE_D) == D("40")
    assert result.rw_y() == D("0.425")
    assert result.net_price("cpi_u") == D("0.2")


def test_contract_rejects_duplicate_ids_owners_units_and_unknown_adjustments() -> None:
    item = _primitive("one", "rw_y", SIDE_N, "1")
    with pytest.raises(AccountingContractError, match="duplicate primitive_id"):
        PrimitiveLedger((item, item))
    with pytest.raises(AccountingContractError, match="missing an ownership key"):
        PrimitiveLedger((replace(item, cash_owner_key=""),))
    with pytest.raises(AccountingContractError, match="must use bil_dollars"):
        PrimitiveLedger((replace(item, unit="logpt_price_level"),))
    with pytest.raises(AccountingContractError, match="measurement class"):
        PrimitiveLedger((replace(item, measurement_class="mixed_source"),))
    ledger = PrimitiveLedger((item,))
    with pytest.raises(AccountingContractError, match="do not own"):
        evaluate_ledger(ledger, adjustments={"orphan": D(1)})


def test_infeasible_primitives_fail_closed() -> None:
    item = replace(
        _primitive("blocked", "rw_y", SIDE_N, "1"),
        feasibility_status="infeasible",
    )
    ledger = PrimitiveLedger((item,))
    with pytest.raises(InfeasibleValueFunction):
        evaluate_ledger(ledger)


def test_blend_changes_values_not_contract() -> None:
    first = PrimitiveLedger(
        (
            _primitive("support", "rw_y", SIDE_N, "2"),
            _primitive("drag", "rw_y", SIDE_D, "10"),
        )
    )
    second = PrimitiveLedger(
        (
            replace(first.primitives[0], value=D("6"), state_id="second"),
            replace(first.primitives[1], value=D("14"), state_id="second"),
        )
    )
    blended = blend_ledgers(
        first,
        second,
        D("0.25"),
        state_id="blended",
        period="intermediate",
    )
    result = evaluate_ledger(blended)
    assert result.side("rw_y", SIDE_N) == D("3")
    assert result.side("rw_y", SIDE_D) == D("11")
    assert {item.state_id for item in blended.primitives} == {"blended"}


def test_blend_preserves_normalized_unit_contract() -> None:
    first_item = replace(
        _primitive("support", "rw_y", SIDE_N, "2"),
        unit="normalized_output_units",
    )
    second_item = replace(first_item, value=D("6"), state_id="second")
    first = PrimitiveLedger(
        (first_item,),
        expected_rw_y_unit="normalized_output_units",
    )
    second = PrimitiveLedger(
        (second_item,),
        expected_rw_y_unit="normalized_output_units",
    )
    blended = blend_ledgers(
        first,
        second,
        D("0.25"),
        state_id="blended",
        period="intermediate",
    )
    assert blended.expected_rw_y_unit == "normalized_output_units"
    assert blended.primitives[0].value == D("3")


def test_measurement_class_round_trips_on_canonical_ledger() -> None:
    ledger = PrimitiveLedger(
        (
            replace(
                _primitive("measured", "rw_y", SIDE_N, "2"),
                measurement_class="measured_aggregate",
            ),
        )
    )
    restored = ledger_from_rows(primitive_rows(ledger))
    assert restored.primitives[0].measurement_class == "measured_aggregate"


def test_economic_contract_fields_round_trip_and_restore_legacy_defaults() -> None:
    fields = {
        "economic_ledger": "financing_stock_transition",
        "cash_component": "principal_repayment",
        "recognition_basis": "accrual",
        "headline_rule": "diagnostic_only",
        "netting_bucket": "shared_financing_bucket",
    }
    ledger = PrimitiveLedger(
        (replace(_primitive("semantic", "rw_y", SIDE_N, "2"), **fields),)
    )
    rows = primitive_rows(ledger)
    restored = ledger_from_rows(rows)
    assert all(
        getattr(restored.primitives[0], field) == value
        for field, value in fields.items()
    )

    legacy_rows = [
        {key: value for key, value in rows[0].items() if key not in fields}
    ]
    legacy = ledger_from_rows(legacy_rows).primitives[0]
    assert legacy.economic_ledger == "current_income"
    assert legacy.cash_component == "unspecified"
    assert legacy.recognition_basis == "cash_settled"
    assert legacy.headline_rule == "additive"
    assert legacy.netting_bucket == ""


@pytest.mark.parametrize(
    ("field", "changed_value"),
    (
        ("month_index", 121),
        ("scenario_id", "other_scenario"),
        ("source_kind", "other_adapter"),
        ("maturity_month", "2030-01"),
        ("reset_month", "2029-01"),
        ("evidence_grade", "assumption"),
        ("measurement_class", "measured_aggregate"),
        ("economic_ledger", "financing_stock_transition"),
        ("cash_component", "principal_repayment"),
        ("recognition_basis", "accrual"),
        ("headline_rule", "diagnostic_only"),
        ("netting_bucket", "shared_financing_bucket"),
    ),
)
def test_blend_rejects_economic_contract_mismatch(
    field: str,
    changed_value: str,
) -> None:
    first_item = _primitive("semantic", "rw_y", SIDE_N, "2")
    first = PrimitiveLedger((first_item,))
    second = PrimitiveLedger(
        (
            replace(
                first_item,
                value=D("4"),
                state_id="second",
                **{field: changed_value},
            ),
        )
    )
    with pytest.raises(AccountingContractError, match=rf"{field} differs"):
        blend_ledgers(
            first,
            second,
            D("0.5"),
            state_id="blended",
            period="intermediate",
        )


def test_declared_overlap_owner_selects_once_and_reports_rejection() -> None:
    first = replace(
        _primitive("first", "rw_y", SIDE_N, "2"),
        overlap_key="shared_atom",
        outcome_owner_key="owner:first",
    )
    second = replace(
        _primitive("second", "rw_y", SIDE_N, "3"),
        overlap_key="shared_atom",
        outcome_owner_key="owner:second",
    )
    key = ("rw_y", SIDE_N, "shared_atom")
    resolved = resolve_overlap_candidates(
        (first, second), selected_owners={key: "owner:second"}
    )
    assert resolved.ledger.primitives == (second,)
    assert {row["selected"] for row in resolved.audit_rows} == {"true", "false"}
    rejected = next(row for row in resolved.audit_rows if row["selected"] == "false")
    assert rejected["candidate_primitive_id"] == "first"
    assert rejected["rejection_reason"] == "declared_overlap_owner_precedence"
    with pytest.raises(AccountingContractError, match="declared owner"):
        resolve_overlap_candidates((first, second), selected_owners={})

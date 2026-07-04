"""Federal Reserve remittance sign conventions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ratewall.accounting.numbers import (
    NumberLike,
    require_nonnegative,
    to_decimal,
)


@dataclass(frozen=True)
class RemittanceImpact:
    fed_interest_payments: Decimal
    current_remittance_reduction: Decimal
    future_remittance_drag: Decimal
    remittance_change: Decimal
    remittance_leakage: Decimal
    deferred_asset_addition: Decimal

    def to_dict(self) -> dict[str, str]:
        return {
            "fed_interest_payments": str(self.fed_interest_payments),
            "current_remittance_reduction": str(self.current_remittance_reduction),
            "future_remittance_drag": str(self.future_remittance_drag),
            "remittance_change": str(self.remittance_change),
            "remittance_leakage": str(self.remittance_leakage),
            "deferred_asset_addition": str(self.deferred_asset_addition),
        }


def estimate_remittance_impact(
    *,
    iorb_payments: NumberLike,
    on_rrp_payments: NumberLike,
    offset_share: NumberLike = Decimal("1"),
    existing_remittance_capacity: NumberLike = Decimal("0"),
) -> RemittanceImpact:
    """Estimate the remittance effect of extra Fed interest payments.

    `remittance_change` is negative when current remittances to Treasury fall.
    If the extra payments exceed the provided positive remittance capacity, the
    excess is represented as a deferred-asset addition / future remittance drag
    rather than current Treasury cash leakage.
    """

    iorb = require_nonnegative(
        to_decimal(iorb_payments, field="iorb_payments"),
        field="iorb_payments",
    )
    on_rrp = require_nonnegative(
        to_decimal(on_rrp_payments, field="on_rrp_payments"),
        field="on_rrp_payments",
    )
    offset = require_nonnegative(
        to_decimal(offset_share, field="offset_share"),
        field="offset_share",
    )
    capacity = require_nonnegative(
        to_decimal(existing_remittance_capacity, field="existing_remittance_capacity"),
        field="existing_remittance_capacity",
    )
    if offset > 1:
        raise ValueError("offset_share must be between 0 and 1")

    fed_interest = iorb + on_rrp
    potential_remittance_leakage = fed_interest * offset
    current_remittance_reduction = min(potential_remittance_leakage, capacity)
    future_remittance_drag = potential_remittance_leakage - current_remittance_reduction
    remittance_change = -current_remittance_reduction
    deferred_asset_addition = future_remittance_drag
    return RemittanceImpact(
        fed_interest_payments=fed_interest,
        current_remittance_reduction=current_remittance_reduction,
        future_remittance_drag=future_remittance_drag,
        remittance_change=remittance_change,
        remittance_leakage=current_remittance_reduction,
        deferred_asset_addition=deferred_asset_addition,
    )

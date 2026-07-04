"""Treasury repricing exposure helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from ratewall.accounting.numbers import NumberLike, require_nonnegative, to_decimal


@dataclass(frozen=True)
class RepricingBucket:
    label: str
    months_to_reprice: NumberLike
    amount: NumberLike


def debt_repricing_within(
    buckets: Iterable[RepricingBucket],
    *,
    months: NumberLike,
) -> Decimal:
    """Sum Treasury amounts that mature or reset within `months`."""

    cutoff = require_nonnegative(to_decimal(months, field="months"), field="months")
    total = Decimal("0")
    for bucket in buckets:
        bucket_months = require_nonnegative(
            to_decimal(bucket.months_to_reprice, field=f"{bucket.label}.months"),
            field=f"{bucket.label}.months",
        )
        amount = require_nonnegative(
            to_decimal(bucket.amount, field=f"{bucket.label}.amount"),
            field=f"{bucket.label}.amount",
        )
        if bucket_months <= cutoff:
            total += amount
    return total


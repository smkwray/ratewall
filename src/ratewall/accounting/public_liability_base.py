"""Public-liability base accounting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ratewall.accounting.numbers import (
    NumberLike,
    require_nonnegative,
    require_positive,
    to_decimal,
)


@dataclass(frozen=True)
class PublicLiabilityInputs:
    """Rate-sensitive public liability stocks in a common currency unit."""

    debt_repricing: NumberLike
    reserves: NumberLike
    on_rrp: NumberLike
    gdp: NumberLike | None = None


@dataclass(frozen=True)
class PublicLiabilityBase:
    debt_repricing: Decimal
    reserves: Decimal
    on_rrp: Decimal
    total: Decimal
    gdp: Decimal | None = None
    gdp_share: Decimal | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "debt_repricing": str(self.debt_repricing),
            "reserves": str(self.reserves),
            "on_rrp": str(self.on_rrp),
            "total": str(self.total),
            "gdp": str(self.gdp) if self.gdp is not None else None,
            "gdp_share": str(self.gdp_share) if self.gdp_share is not None else None,
        }


def compute_public_liability_base(
    inputs: PublicLiabilityInputs,
) -> PublicLiabilityBase:
    """Compute PLB = debt repricing exposure + reserves + ON RRP.

    This is a mechanical stock measure. It does not encode any behavioral
    assumption about inflation, spending, or monetary-policy effectiveness.
    """

    debt_repricing = require_nonnegative(
        to_decimal(inputs.debt_repricing, field="debt_repricing"),
        field="debt_repricing",
    )
    reserves = require_nonnegative(
        to_decimal(inputs.reserves, field="reserves"),
        field="reserves",
    )
    on_rrp = require_nonnegative(
        to_decimal(inputs.on_rrp, field="on_rrp"),
        field="on_rrp",
    )
    total = debt_repricing + reserves + on_rrp

    if inputs.gdp is None:
        return PublicLiabilityBase(
            debt_repricing=debt_repricing,
            reserves=reserves,
            on_rrp=on_rrp,
            total=total,
        )

    gdp = require_positive(to_decimal(inputs.gdp, field="gdp"), field="gdp")
    return PublicLiabilityBase(
        debt_repricing=debt_repricing,
        reserves=reserves,
        on_rrp=on_rrp,
        total=total,
        gdp=gdp,
        gdp_share=total / gdp,
    )


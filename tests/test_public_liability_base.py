from decimal import Decimal

import pytest

from ratewall.accounting.public_liability_base import (
    PublicLiabilityInputs,
    compute_public_liability_base,
)


def test_public_liability_base_sums_rate_sensitive_stocks() -> None:
    result = compute_public_liability_base(
        PublicLiabilityInputs(
            debt_repricing="2000",
            reserves="3000",
            on_rrp="500",
            gdp="25000",
        )
    )

    assert result.total == Decimal("5500")
    assert result.gdp_share == Decimal("0.22")


def test_public_liability_base_rejects_negative_stock() -> None:
    with pytest.raises(ValueError, match="reserves must be nonnegative"):
        compute_public_liability_base(
            PublicLiabilityInputs(debt_repricing="1", reserves="-1", on_rrp="0")
        )


def test_public_liability_base_requires_positive_gdp_when_scaled() -> None:
    with pytest.raises(ValueError, match="gdp must be positive"):
        compute_public_liability_base(
            PublicLiabilityInputs(
                debt_repricing="1",
                reserves="1",
                on_rrp="1",
                gdp="0",
            )
        )


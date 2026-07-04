"""Mechanical rate-hike impulse accounting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from ratewall.accounting.fed_remittances import estimate_remittance_impact
from ratewall.accounting.numbers import (
    NumberLike,
    require_nonnegative,
    require_positive,
    to_decimal,
)


@dataclass(frozen=True)
class HorizonRepricing:
    """Debt repricing stock for a named horizon."""

    label: str
    months: NumberLike
    debt_repricing: NumberLike
    source_status: str = "source_backed_ratewall_impulse"


@dataclass(frozen=True)
class RateImpulseInputs:
    """Inputs for a mechanical rate-hike public-liability impulse."""

    reserves: NumberLike
    on_rrp: NumberLike
    gdp: NumberLike
    horizons: Iterable[HorizonRepricing]
    treasury_pass_through: NumberLike = Decimal("1")
    reserve_pass_through: NumberLike = Decimal("1")
    on_rrp_pass_through: NumberLike = Decimal("1")
    fed_remittance_offset: NumberLike = Decimal("1")
    existing_remittance_capacity: NumberLike = Decimal("0")


@dataclass(frozen=True)
class RateImpulseResult:
    label: str
    months: Decimal
    delta_rate: Decimal
    annualized_treasury_interest: Decimal
    annualized_iorb_payments: Decimal
    annualized_on_rrp_payments: Decimal
    annualized_gross_interest_income: Decimal
    annualized_fed_remittance_change: Decimal
    annualized_fed_remittance_leakage: Decimal
    annualized_fed_future_remittance_drag: Decimal
    annualized_private_recipient_cashflow_impulse: Decimal
    annualized_treasury_financing_impulse_current_cash: Decimal
    annualized_component_display_total_not_macro_impulse: Decimal
    annualized_public_interest_impulse: Decimal
    annualized_public_interest_impulse_gdp_share: Decimal
    period_public_interest_impulse: Decimal
    period_public_interest_impulse_gdp_share: Decimal
    source_status: str

    def to_dict(self) -> dict[str, str]:
        return {
            "label": self.label,
            "months": str(self.months),
            "delta_rate": str(self.delta_rate),
            "annualized_treasury_interest": str(self.annualized_treasury_interest),
            "annualized_iorb_payments": str(self.annualized_iorb_payments),
            "annualized_on_rrp_payments": str(self.annualized_on_rrp_payments),
            "annualized_gross_interest_income": str(
                self.annualized_gross_interest_income
            ),
            "annualized_fed_remittance_change": str(
                self.annualized_fed_remittance_change
            ),
            "annualized_fed_remittance_leakage": str(
                self.annualized_fed_remittance_leakage
            ),
            "annualized_fed_future_remittance_drag": str(
                self.annualized_fed_future_remittance_drag
            ),
            "annualized_private_recipient_cashflow_impulse": str(
                self.annualized_private_recipient_cashflow_impulse
            ),
            "annualized_treasury_financing_impulse_current_cash": str(
                self.annualized_treasury_financing_impulse_current_cash
            ),
            "annualized_component_display_total_not_macro_impulse": str(
                self.annualized_component_display_total_not_macro_impulse
            ),
            "annualized_public_interest_impulse": str(
                self.annualized_public_interest_impulse
            ),
            "annualized_public_interest_impulse_gdp_share": str(
                self.annualized_public_interest_impulse_gdp_share
            ),
            "period_public_interest_impulse": str(
                self.period_public_interest_impulse
            ),
            "period_public_interest_impulse_gdp_share": str(
                self.period_public_interest_impulse_gdp_share
            ),
            "source_status": self.source_status,
        }


def _pass_through(value: NumberLike, *, field: str) -> Decimal:
    parsed = require_nonnegative(to_decimal(value, field=field), field=field)
    if parsed > 1:
        raise ValueError(f"{field} must be between 0 and 1")
    return parsed


def _rate_delta_from_bps(bps: NumberLike) -> Decimal:
    parsed = to_decimal(bps, field="bps")
    return parsed / Decimal("10000")


def compute_rate_impulse(
    inputs: RateImpulseInputs,
    *,
    bps: NumberLike = Decimal("100"),
) -> dict[str, RateImpulseResult]:
    """Compute the mechanical public-interest impulse from a rate change.

    The calculation separates public interest flows from any behavioral claim.
    It does not assume higher rates raise or lower inflation.
    """

    delta_rate = _rate_delta_from_bps(bps)
    reserves = require_nonnegative(
        to_decimal(inputs.reserves, field="reserves"),
        field="reserves",
    )
    on_rrp = require_nonnegative(
        to_decimal(inputs.on_rrp, field="on_rrp"),
        field="on_rrp",
    )
    gdp = require_positive(to_decimal(inputs.gdp, field="gdp"), field="gdp")
    treasury_pass = _pass_through(
        inputs.treasury_pass_through,
        field="treasury_pass_through",
    )
    reserve_pass = _pass_through(
        inputs.reserve_pass_through,
        field="reserve_pass_through",
    )
    on_rrp_pass = _pass_through(
        inputs.on_rrp_pass_through,
        field="on_rrp_pass_through",
    )

    annualized_iorb = reserves * delta_rate * reserve_pass
    annualized_on_rrp = on_rrp * delta_rate * on_rrp_pass
    remittance = estimate_remittance_impact(
        iorb_payments=annualized_iorb,
        on_rrp_payments=annualized_on_rrp,
        offset_share=inputs.fed_remittance_offset,
        existing_remittance_capacity=inputs.existing_remittance_capacity,
    )

    results: dict[str, RateImpulseResult] = {}
    for horizon in inputs.horizons:
        months = require_positive(
            to_decimal(horizon.months, field=f"{horizon.label}.months"),
            field=f"{horizon.label}.months",
        )
        debt_repricing = require_nonnegative(
            to_decimal(
                horizon.debt_repricing,
                field=f"{horizon.label}.debt_repricing",
            ),
            field=f"{horizon.label}.debt_repricing",
        )
        annualized_treasury = debt_repricing * delta_rate * treasury_pass
        private_cashflow_impulse = annualized_treasury + remittance.fed_interest_payments
        treasury_financing_impulse = annualized_treasury + remittance.remittance_leakage
        component_display_total = private_cashflow_impulse + remittance.remittance_leakage
        public_impulse = private_cashflow_impulse
        period_factor = months / Decimal("12")
        period_impulse = public_impulse * period_factor

        results[horizon.label] = RateImpulseResult(
            label=horizon.label,
            months=months,
            delta_rate=delta_rate,
            annualized_treasury_interest=annualized_treasury,
            annualized_iorb_payments=annualized_iorb,
            annualized_on_rrp_payments=annualized_on_rrp,
            annualized_gross_interest_income=private_cashflow_impulse,
            annualized_fed_remittance_change=remittance.remittance_change,
            annualized_fed_remittance_leakage=remittance.remittance_leakage,
            annualized_fed_future_remittance_drag=remittance.future_remittance_drag,
            annualized_private_recipient_cashflow_impulse=private_cashflow_impulse,
            annualized_treasury_financing_impulse_current_cash=(
                treasury_financing_impulse
            ),
            annualized_component_display_total_not_macro_impulse=(
                component_display_total
            ),
            annualized_public_interest_impulse=public_impulse,
            annualized_public_interest_impulse_gdp_share=public_impulse / gdp,
            period_public_interest_impulse=period_impulse,
            period_public_interest_impulse_gdp_share=period_impulse / gdp,
            source_status=horizon.source_status,
        )
    return results

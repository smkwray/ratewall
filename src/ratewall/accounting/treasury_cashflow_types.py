"""Shared types for Treasury contractual cashflow modeling."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Mapping

from ratewall.accounting.numbers import NumberLike, require_nonnegative, to_decimal


class InstrumentType(str, Enum):
    BILL = "bill"
    NOTE = "note"
    BOND = "bond"
    FRN = "frn"
    TIPS = "tips"
    OTHER_UNKNOWN = "other_unknown"


class EventType(str, Enum):
    COUPON = "coupon"
    BILL_DISCOUNT_INTEREST = "bill_discount_interest"
    FRN_INTEREST = "frn_interest"
    TIPS_COUPON = "tips_coupon"
    TIPS_INDEXATION = "tips_indexation"
    PRINCIPAL_REDEMPTION = "principal_redemption"
    ISSUANCE_PROCEEDS = "issuance_proceeds"
    ACCRUED_INTEREST_AT_ISSUE = "accrued_interest_at_issue"
    BUYBACK = "buyback"


class AccountingBasis(str, Enum):
    CASH = "cash"
    BUDGET_ACCRUAL = "budget_accrual"
    FACE_STOCK = "face_stock"


@dataclass(frozen=True, slots=True)
class TreasuryPosition:
    """Opening contractual position, after source-row normalization."""

    position_id: str
    cusip: str
    instrument_type: InstrumentType
    issue_date: date
    maturity_date: date
    original_face_bil: NumberLike
    outstanding_face_bil: NumberLike
    source_as_of: date
    source_status: str
    coupon_rate: NumberLike | None = None
    issue_price_per_100: NumberLike | None = None
    inflation_index_ratio: NumberLike | None = None
    frn_spread_bps: NumberLike | None = None
    frn_index_name: str | None = None
    next_reset_date: date | None = None
    coupon_frequency_months: int = 6
    lot_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.position_id:
            raise ValueError("position_id is required")
        if not self.cusip:
            raise ValueError("cusip is required")
        if self.maturity_date < self.issue_date:
            raise ValueError("maturity_date must be on or after issue_date")
        _set_decimal(self, "original_face_bil", _nonnegative(self.original_face_bil, "original_face_bil"))
        _set_decimal(
            self,
            "outstanding_face_bil",
            _nonnegative(self.outstanding_face_bil, "outstanding_face_bil"),
        )
        if self.outstanding_face_bil > self.original_face_bil:
            raise ValueError("outstanding_face_bil cannot exceed original_face_bil")
        if self.coupon_rate is not None:
            _set_decimal(self, "coupon_rate", _nonnegative(self.coupon_rate, "coupon_rate"))
        if self.issue_price_per_100 is not None:
            _set_decimal(
                self,
                "issue_price_per_100",
                _nonnegative(self.issue_price_per_100, "issue_price_per_100"),
            )
        if self.inflation_index_ratio is not None:
            _set_decimal(
                self,
                "inflation_index_ratio",
                _nonnegative(self.inflation_index_ratio, "inflation_index_ratio"),
            )
        if self.frn_spread_bps is not None:
            _set_decimal(self, "frn_spread_bps", _decimal(self.frn_spread_bps, "frn_spread_bps"))
        if self.coupon_frequency_months <= 0:
            raise ValueError("coupon_frequency_months must be positive")
        object.__setattr__(self, "lot_ids", tuple(sorted(self.lot_ids)))


@dataclass(frozen=True, slots=True)
class TreasuryAuctionLot:
    """Auction/reopening lot that rolls into one contractual CUSIP position."""

    lot_id: str
    position_id: str
    cusip: str
    instrument_type: InstrumentType
    auction_date: date
    issue_date: date
    settlement_date: date
    maturity_date: date
    issued_face_bil: NumberLike
    redeemed_face_bil: NumberLike = Decimal("0")
    issue_price_per_100: NumberLike | None = None
    source_row_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.lot_id:
            raise ValueError("lot_id is required")
        if not self.position_id:
            raise ValueError("position_id is required")
        if not self.cusip:
            raise ValueError("cusip is required")
        if self.maturity_date < self.issue_date:
            raise ValueError("maturity_date must be on or after issue_date")
        _set_decimal(self, "issued_face_bil", _nonnegative(self.issued_face_bil, "issued_face_bil"))
        _set_decimal(
            self,
            "redeemed_face_bil",
            _nonnegative(self.redeemed_face_bil, "redeemed_face_bil"),
        )
        if self.redeemed_face_bil > self.issued_face_bil:
            raise ValueError("redeemed_face_bil cannot exceed issued_face_bil")
        if self.issue_price_per_100 is not None:
            _set_decimal(
                self,
                "issue_price_per_100",
                _nonnegative(self.issue_price_per_100, "issue_price_per_100"),
            )
        object.__setattr__(self, "source_row_ids", tuple(sorted(self.source_row_ids)))

    @property
    def outstanding_face_bil(self) -> Decimal:
        return self.issued_face_bil - self.redeemed_face_bil


@dataclass(frozen=True, slots=True)
class TreasuryFlowEvent:
    """Dated, signed Treasury cashflow event.

    Positive signed amounts mean cash to holders/private sector. Negative signed
    amounts mean cash from holders to Treasury. Face-stock events use positive
    issuance and negative retirement.
    """

    event_id: str
    scenario_id: str
    reference_lineage_id: str
    position_or_cohort_id: str
    cusip: str
    instrument_type: InstrumentType
    event_type: EventType
    accounting_basis: AccountingBasis
    contractual_date: date
    cash_settlement_date: date
    accrual_start: date | None
    accrual_end: date | None
    signed_amount_bil: NumberLike
    source_as_of: date | None
    source_status: str

    def __post_init__(self) -> None:
        for field_name in (
            "event_id",
            "scenario_id",
            "reference_lineage_id",
            "position_or_cohort_id",
            "source_status",
        ):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} is required")
        _set_decimal(
            self,
            "signed_amount_bil",
            _decimal(self.signed_amount_bil, "signed_amount_bil"),
        )
        if (self.accrual_start is None) != (self.accrual_end is None):
            raise ValueError("accrual_start and accrual_end must be paired")
        if (
            self.accrual_start is not None
            and self.accrual_end is not None
            and self.accrual_end < self.accrual_start
        ):
            raise ValueError("accrual_end must be on or after accrual_start")


@dataclass(frozen=True, slots=True)
class TreasuryCurveScenario:
    """Complete dated curve path for scenario pricing of future issuance."""

    scenario_id: str
    as_of: date
    nominal_annual_rates: Mapping[int, NumberLike]
    bill_discount_rates: Mapping[int, NumberLike] | None = None
    real_annual_rates: Mapping[int, NumberLike] | None = None
    frn_index_rates: Mapping[int, NumberLike] | None = None

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id is required")
        object.__setattr__(
            self,
            "nominal_annual_rates",
            _decimal_curve(self.nominal_annual_rates, "nominal_annual_rates"),
        )
        object.__setattr__(
            self,
            "bill_discount_rates",
            _optional_decimal_curve(self.bill_discount_rates, "bill_discount_rates"),
        )
        object.__setattr__(
            self,
            "real_annual_rates",
            _optional_decimal_curve(self.real_annual_rates, "real_annual_rates"),
        )
        object.__setattr__(
            self,
            "frn_index_rates",
            _optional_decimal_curve(self.frn_index_rates, "frn_index_rates"),
        )

    def require_rate(self, tenor_months: int, *, curve: str = "nominal") -> Decimal:
        curves = {
            "nominal": self.nominal_annual_rates,
            "bill": self.bill_discount_rates,
            "real": self.real_annual_rates,
            "frn_index": self.frn_index_rates,
        }
        if curve not in curves:
            raise ValueError(f"unknown curve: {curve}")
        rates = curves[curve]
        if rates is None or tenor_months not in rates:
            raise ValueError(f"missing {curve} curve node for {tenor_months} months")
        return rates[tenor_months]


@dataclass(frozen=True, slots=True)
class IssuancePolicyBucket:
    """One issuance-policy weight, independent of any curve scenario."""

    bucket_id: str
    instrument_type: InstrumentType
    tenor_months: int
    weight: NumberLike
    coupon_frequency_months: int = 6

    def __post_init__(self) -> None:
        if not self.bucket_id:
            raise ValueError("bucket_id is required")
        if self.tenor_months <= 0:
            raise ValueError("tenor_months must be positive")
        _set_decimal(self, "weight", _nonnegative(self.weight, "weight"))
        if self.coupon_frequency_months <= 0:
            raise ValueError("coupon_frequency_months must be positive")


@dataclass(frozen=True, slots=True)
class TreasuryIssuancePolicy:
    """Future issuance mix; WAM/WANRR are derived elsewhere, not controls."""

    policy_id: str
    buckets: tuple[IssuancePolicyBucket, ...]
    source_status: str

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("policy_id is required")
        if not self.buckets:
            raise ValueError("buckets are required")
        if not self.source_status:
            raise ValueError("source_status is required")
        object.__setattr__(self, "buckets", tuple(self.buckets))
        weight_sum = sum((bucket.weight for bucket in self.buckets), Decimal("0"))
        if weight_sum != Decimal("1"):
            raise ValueError("issuance weights must sum to 1")


@dataclass(frozen=True, slots=True)
class TreasuryScenario:
    """Scenario header that separates curve and issuance-policy axes."""

    scenario_id: str
    curve_scenario_id: str
    issuance_policy_id: str
    reference_scenario_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("scenario_id", "curve_scenario_id", "issuance_policy_id"):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} is required")


def treasury_flow_event_field_names() -> tuple[str, ...]:
    return tuple(field.name for field in fields(TreasuryFlowEvent))


def _decimal(value: NumberLike, field: str) -> Decimal:
    return to_decimal(value, field=field)


def _nonnegative(value: NumberLike, field: str) -> Decimal:
    return require_nonnegative(_decimal(value, field), field=field)


def _set_decimal(instance: object, field: str, value: Decimal) -> None:
    object.__setattr__(instance, field, value)


def _decimal_curve(values: Mapping[int, NumberLike], field: str) -> dict[int, Decimal]:
    if not values:
        raise ValueError(f"{field} cannot be empty")
    parsed: dict[int, Decimal] = {}
    for tenor, rate in values.items():
        if isinstance(tenor, bool) or int(tenor) <= 0:
            raise ValueError(f"{field} tenors must be positive months")
        parsed[int(tenor)] = _decimal(rate, f"{field}.{tenor}")
    return dict(sorted(parsed.items()))


def _optional_decimal_curve(
    values: Mapping[int, NumberLike] | None, field: str
) -> dict[int, Decimal] | None:
    if values is None:
        return None
    return _decimal_curve(values, field)
